"""
Network worker — Sprint 4.

Steps:
  1. Nmap: TCP connect scan, service + version detection (top 1000 ports)
  2. NVD:  CVE lookup for each identified product/version
  3. Dedup: drop findings already in DB for this scan
  4. Save: bulk insert unique findings
"""
import logging
import uuid
from datetime import datetime, timezone

from backend.celery_app import celery_app
from backend.db.sync_database import get_sync_db
from backend.models.finding import Finding
from backend.models.scan import Scan, ScanStatus
from backend.workers.network.nmap_scanner import scan as nmap_scan
from backend.workers.network.nvd_lookup import lookup_cves
from backend.workers.network.deduplicator import deduplicate

logger = logging.getLogger(__name__)

# Severity ordering for escalation (port finding → CVE finding)
_SEVERITY_RANK = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _port_severity(port: int, service: str) -> str:
    """Heuristic severity for an open port finding."""
    risky = {
        21: "MEDIUM",   # FTP
        22: "INFO",     # SSH (expected)
        23: "HIGH",     # Telnet
        25: "MEDIUM",   # SMTP
        445: "HIGH",    # SMB
        1433: "HIGH",   # MSSQL
        3306: "HIGH",   # MySQL
        3389: "HIGH",   # RDP
        5432: "HIGH",   # PostgreSQL
        6379: "HIGH",   # Redis
        27017: "HIGH",  # MongoDB
        9200: "HIGH",   # Elasticsearch
    }
    return risky.get(port, "LOW" if service not in ("http", "https") else "INFO")


def _build_port_finding(port_result) -> dict:
    severity = _port_severity(port_result.port, port_result.service)
    title = f"Porta aperta: {port_result.port}/{port_result.protocol}"
    if port_result.version_string:
        title += f" — {port_result.version_string}"

    return {
        "title": title,
        "description": (
            f"Nmap ha rilevato la porta {port_result.port}/{port_result.protocol} aperta "
            f"su {port_result.host} ({port_result.ip}). "
            f"Servizio: {port_result.service or 'sconosciuto'}. "
            f"{('Versione: ' + port_result.version_string) if port_result.version_string else ''}"
        ).strip(),
        "severity": severity,
        "cvss_score": None,
        "affected_component": port_result.component,
        "proof": (
            f"nmap: {port_result.host}:{port_result.port}/{port_result.protocol} "
            f"[{port_result.service} {port_result.version_string}]"
        ),
        "fix_suggestion": (
            f"Verificare se il servizio sulla porta {port_result.port} è necessario. "
            "Se non utilizzato, chiuderlo con un firewall."
        ) if severity in ("HIGH", "MEDIUM") else None,
        "source": "nmap",
        "nis2_control": "21.2.a",
    }


@celery_app.task(
    name="workers.run_network_scan",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=900,
    soft_time_limit=840,
)
def run_network_scan(self, scan_id: str) -> dict:
    """
    Execute Nmap + NVD pipeline for a given scan_id.
    Does NOT change scan status (orchestrator manages overall status via recon_worker).
    """
    sid = uuid.UUID(scan_id)
    db = get_sync_db()

    try:
        scan: Scan | None = db.get(Scan, sid)
        if not scan:
            logger.error("Scan %s not found", scan_id)
            return {"error": "scan_not_found"}

        domain = scan.target
        all_findings: list[dict] = []

        # ── Step 1: Nmap ──────────────────────────────────────────────────
        logger.info("[%s] Running nmap on %s", scan_id[:8], domain)
        port_results = nmap_scan(domain)
        logger.info("[%s] nmap found %d open ports", scan_id[:8], len(port_results))

        # Track unique (product, version) pairs to avoid redundant NVD queries
        queried_versions: set[tuple[str, str]] = set()

        for pr in port_results:
            all_findings.append(_build_port_finding(pr))

            # ── Step 2: NVD CVE lookup ────────────────────────────────────
            if pr.product and (pr.product, pr.version) not in queried_versions:
                queried_versions.add((pr.product, pr.version))
                logger.info(
                    "[%s] NVD lookup: %s %s", scan_id[:8], pr.product, pr.version
                )
                cve_findings = lookup_cves(pr.product, pr.version)
                for cve in cve_findings:
                    cve["affected_component"] = pr.component
                all_findings.extend(cve_findings)

        # ── Step 3: Deduplicate ───────────────────────────────────────────
        unique_findings = deduplicate(db, sid, all_findings)
        logger.info(
            "[%s] %d findings after dedup (dropped %d)",
            scan_id[:8],
            len(unique_findings),
            len(all_findings) - len(unique_findings),
        )

        # ── Step 4: Save ──────────────────────────────────────────────────
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
                    source=f.get("source", "nmap"),
                )
            )
        db.commit()

        return {
            "scan_id": scan_id,
            "open_ports": len(port_results),
            "findings": len(unique_findings),
        }

    except Exception as exc:
        logger.exception("[%s] Network scan failed: %s", scan_id[:8], exc)
        raise self.retry(exc=exc)
    finally:
        db.close()
