import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.database import get_db
from backend.models.report import Report, ReportStatus
from backend.models.scan import Scan, ScanStatus
from backend.models.user import User
from backend.schemas.pydantic_schemas import ReportOut
from backend.core.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/scans/{scan_id}",
    response_model=ReportOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_report(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    """Trigger AI report generation for a completed scan."""
    scan_result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == current_user.id)
    )
    scan = scan_result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trovato")
    if scan.status != ScanStatus.completed:
        raise HTTPException(
            status_code=409,
            detail=f"Lo scan è in stato '{scan.status.value}'. Il report può essere generato solo da scan completati.",
        )

    # Check for existing report
    existing_result = await db.execute(
        select(Report).where(Report.scan_id == scan_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        if existing.status in (ReportStatus.pending, ReportStatus.generating):
            return existing
        if existing.status == ReportStatus.completed:
            raise HTTPException(
                status_code=409,
                detail="Il report è già stato generato. Usa GET /reports/scans/{scan_id} per recuperarlo.",
            )
        # Failed — delete and re-create
        await db.delete(existing)
        await db.flush()

    report = Report(scan_id=scan_id, status=ReportStatus.pending)
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Dispatch Celery task
    from backend.workers.report_worker import generate_report_task
    generate_report_task.delay(str(report.id))

    return report


@router.get("/scans/{scan_id}", response_model=ReportOut)
async def get_report(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    """Fetch the AI report for a scan."""
    scan_result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == current_user.id)
    )
    if not scan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Scan non trovato")

    report_result = await db.execute(
        select(Report).where(Report.scan_id == scan_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report non trovato. Usa POST /reports/scans/{scan_id} per avviare la generazione.",
        )
    return report
