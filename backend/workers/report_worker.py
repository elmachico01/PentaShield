"""
Report worker — Sprint 6.

Steps:
  1. Load scan + findings from DB
  2. Sort findings by CVSS/severity, cap at top 50
  3. Call Claude AI engine for structured Italian report
  4. Persist result to reports table
"""
import json
import logging
import uuid
from datetime import datetime, timezone

from backend.celery_app import celery_app
from backend.db.sync_database import get_sync_db
from backend.models.report import Report, ReportStatus
from backend.models.scan import Scan
from backend.models.finding import Finding
from backend.core.ai_engine import generate_report
from sqlalchemy import select

logger = logging.getLogger(__name__)


@celery_app.task(
    name="workers.generate_report",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=270,
)
def generate_report_task(self, report_id: str) -> dict:
    """
    Generate an AI security report for the given report_id.
    Loads findings from DB, calls Claude, persists structured result.
    """
    rid = uuid.UUID(report_id)
    db = get_sync_db()

    try:
        report: Report | None = db.get(Report, rid)
        if not report:
            logger.error("Report %s not found", report_id)
            return {"error": "report_not_found"}

        scan: Scan | None = db.get(Scan, report.scan_id)
        if not scan:
            logger.error("Scan %s not found for report %s", report.scan_id, report_id)
            _mark_failed(db, report, "Scan non trovato")
            return {"error": "scan_not_found"}

        # Mark as generating
        report.status = ReportStatus.generating
        db.commit()

        # Load all findings for this scan
        findings_result = db.execute(
            select(Finding).where(Finding.scan_id == report.scan_id)
        )
        findings_orm = list(findings_result.scalars().all())

        findings = [
            {
                "title": f.title,
                "description": f.description,
                "severity": f.severity.value if hasattr(f.severity, "value") else f.severity,
                "cvss_score": f.cvss_score,
                "affected_component": f.affected_component,
                "proof": f.proof,
                "fix_suggestion": f.fix_suggestion,
                "nis2_control": f.nis2_control,
                "source": f.source,
            }
            for f in findings_orm
        ]

        logger.info(
            "[%s] Generating AI report for %s (%d findings)",
            report_id[:8],
            scan.target,
            len(findings),
        )

        result = generate_report(
            domain=scan.target,
            findings=findings,
            scan_scope=scan.scope.value if hasattr(scan.scope, "value") else scan.scope,
        )

        report.ai_summary = json.dumps(result, ensure_ascii=False)
        report.nis2_gap_analysis = result.get("nis2_gap_analysis", "")
        report.status = ReportStatus.completed
        report.completed_at = datetime.now(timezone.utc)
        report.error_message = None
        db.commit()

        logger.info("[%s] Report completed successfully", report_id[:8])
        return {
            "report_id": report_id,
            "scan_id": str(report.scan_id),
            "findings_analyzed": len(findings),
            "risk_level": result.get("risk_level"),
        }

    except Exception as exc:
        logger.exception("[%s] Report generation failed: %s", report_id[:8], exc)
        try:
            report = db.get(Report, rid)
            if report:
                _mark_failed(db, report, str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()


def _mark_failed(db, report: Report, message: str) -> None:
    report.status = ReportStatus.failed
    report.error_message = message[:1000]
    db.commit()
