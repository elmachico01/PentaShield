"""
Recon worker — Sprint 3.

Steps:
  1. Subfinder: enumerate subdomains
  2. Shodan:    IP enrichment + known CVEs
  3. Fingerprint: HTTP header tech detection

All findings are saved to the DB with severity=INFO (or higher when warranted).
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.celery_app import celery_app
from backend.db.sync_database import get_sync_db
from backend.models.finding import Finding
from backend.models.scan import Scan, ScanStatus
from backend.workers.recon.subfinder import enumerate_subdomains
from backend.workers.recon.shodan_lookup import lookup as shodan_lookup
from backend.workers.recon.fingerprint import fingerprint

logger = logging.getLogger(__name__)


def _save_findings(db: Session, scan_id: uuid.UUID, raw_findings: list[dict]) -> int:
    """Bulk-insert findings, return count saved."""
    for f in raw_findings:
        finding = Finding(
            scan_id=scan_id,
            title=f.get("title", ""),
            description=f.get("description", ""),
            severity=f.get("severity", "INFO"),
            cvss_score=f.get("cvss_score"),
            affected_component=f.get("affected_component", ""),
            proof=f.get("proof"),
            fix_suggestion=f.get("fix_suggestion"),
            nis2_control=f.get("nis2_control"),
            source=f.get("source", "recon"),
        )
        db.add(finding)
    db.commit()
    return len(raw_findings)


@celery_app.task(
    name="workers.run_recon",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=600,
    soft_time_limit=540,
)
def run_recon(self, scan_id: str) -> dict:
    """
    Execute full recon pipeline for a given scan_id.
    Updates scan status to running/completed/failed.
    """
    sid = uuid.UUID(scan_id)
    db = get_sync_db()

    try:
        scan: Scan | None = db.get(Scan, sid)
        if not scan:
            logger.error("Scan %s not found", scan_id)
            return {"error": "scan_not_found"}

        domain = scan.target

        # Mark scan as running
        scan.status = ScanStatus.running
        scan.started_at = datetime.now(timezone.utc)
        db.commit()

        all_findings: list[dict] = []

        # ── Step 1: Subfinder ─────────────────────────────────────────────
        logger.info("[%s] Running subfinder on %s", scan_id[:8], domain)
        subdomains = enumerate_subdomains(domain)
        logger.info("[%s] Found %d subdomains", scan_id[:8], len(subdomains))

        for sub in subdomains:
            if sub == domain:
                continue
            all_findings.append(
                {
                    "title": f"Sottodominio scoperto: {sub}",
                    "description": (
                        f"Il sottodominio '{sub}' è stato scoperto tramite enumerazione passiva. "
                        f"Verificare che non esponga servizi non intenzionali."
                    ),
                    "severity": "INFO",
                    "affected_component": sub,
                    "proof": f"subfinder output: {sub}",
                    "source": "subfinder",
                    "nis2_control": "21.2.a",
                }
            )

        # ── Step 2: Shodan ────────────────────────────────────────────────
        targets_to_lookup = [domain] + [s for s in subdomains if s != domain][:5]
        for host in targets_to_lookup:
            logger.info("[%s] Shodan lookup for %s", scan_id[:8], host)
            shodan_findings = shodan_lookup(host)
            all_findings.extend(shodan_findings)

        # ── Step 3: Header fingerprinting ─────────────────────────────────
        for host in targets_to_lookup[:10]:
            logger.info("[%s] Fingerprinting %s", scan_id[:8], host)
            fp_findings = fingerprint(host)
            all_findings.extend(fp_findings)

        # ── Save findings ─────────────────────────────────────────────────
        count = _save_findings(db, sid, all_findings)
        logger.info("[%s] Saved %d findings", scan_id[:8], count)

        # Mark scan completed
        scan.status = ScanStatus.completed
        scan.finished_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "scan_id": scan_id,
            "subdomains": len(subdomains),
            "findings": count,
        }

    except Exception as exc:
        logger.exception("[%s] Recon failed: %s", scan_id[:8], exc)
        try:
            scan = db.get(Scan, sid)
            if scan:
                scan.status = ScanStatus.failed
                scan.finished_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()
