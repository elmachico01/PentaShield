"""
Web worker — Sprint 5.

Steps:
  1. Nuclei: safe template scan (CVEs, misconfigs, exposures)
  2. ZAP passive scan: spider + passive analysis
  3. ZAP active scan: only when scope=full
  4. Normalize → deduplicate → save findings
"""
import logging
import uuid

from backend.celery_app import celery_app
from backend.db.sync_database import get_sync_db
from backend.models.finding import Finding
from backend.models.scan import Scan, ScanScope
from backend.workers.network.deduplicator import deduplicate
from backend.workers.web.nuclei_scanner import scan as nuclei_scan
from backend.workers.web.zap_scanner import scan as zap_scan
from backend.workers.web.normalizer import normalize_nuclei, normalize_zap

logger = logging.getLogger(__name__)


@celery_app.task(
    name="workers.run_web_scan",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=1200,
    soft_time_limit=1140,
)
def run_web_scan(self, scan_id: str) -> dict:
    """
    Execute full web scan pipeline for a given scan_id.
    Scope=full enables ZAP active scan; all other scopes use passive only.
    """
    sid = uuid.UUID(scan_id)
    db = get_sync_db()

    try:
        scan: Scan | None = db.get(Scan, sid)
        if not scan:
            logger.error("Scan %s not found", scan_id)
            return {"error": "scan_not_found"}

        domain = scan.target
        run_active = scan.scope == ScanScope.full
        all_findings: list[dict] = []

        # ── Step 1: Nuclei ────────────────────────────────────────────────
        logger.info("[%s] Running nuclei on %s", scan_id[:8], domain)
        nuclei_raw = nuclei_scan(domain)
        for raw in nuclei_raw:
            all_findings.append(normalize_nuclei(raw, domain))
        logger.info("[%s] nuclei: %d results", scan_id[:8], len(nuclei_raw))

        # ── Step 2 & 3: ZAP scan ─────────────────────────────────────────
        logger.info(
            "[%s] Running ZAP scan on %s (active=%s)", scan_id[:8], domain, run_active
        )
        zap_alerts = zap_scan(domain, active=run_active)
        for alert in zap_alerts:
            all_findings.append(normalize_zap(alert))
        logger.info("[%s] ZAP: %d alerts", scan_id[:8], len(zap_alerts))

        # ── Deduplicate ───────────────────────────────────────────────────
        unique_findings = deduplicate(db, sid, all_findings)
        logger.info(
            "[%s] %d unique web findings (dropped %d duplicates)",
            scan_id[:8],
            len(unique_findings),
            len(all_findings) - len(unique_findings),
        )

        # ── Save ──────────────────────────────────────────────────────────
        for f in unique_findings:
            db.add(
                Finding(
                    scan_id=sid,
                    title=f.get("title", ""),
                    description=f.get("description", ""),
                    severity=f.get("severity", "INFO"),
                    cvss_score=f.get("cvss_score"),
                    affected_component=f.get("affected_component", domain),
                    proof=f.get("proof"),
                    fix_suggestion=f.get("fix_suggestion"),
                    nis2_control=f.get("nis2_control"),
                    source=f.get("source", "web"),
                )
            )
        db.commit()

        return {
            "scan_id": scan_id,
            "nuclei_results": len(nuclei_raw),
            "zap_alerts": len(zap_alerts),
            "findings_saved": len(unique_findings),
        }

    except Exception as exc:
        logger.exception("[%s] Web scan failed: %s", scan_id[:8], exc)
        raise self.retry(exc=exc)
    finally:
        db.close()
