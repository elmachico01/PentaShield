import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.db.database import get_db
from backend.models.finding import Finding
from backend.models.scan import Scan, ScanStatus
from backend.models.target import Target
from backend.models.user import User
from backend.schemas.pydantic_schemas import ScanCreate, ScanOut, FindingOut
from backend.core.deps import get_current_user
from backend.core.orchestrator import dispatch_scan
from backend.config import get_settings

router = APIRouter(prefix="/scans", tags=["scans"])
settings = get_settings()


@router.post("", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
async def create_scan(
    payload: ScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scan:
    # Resolve target — must belong to the user and be verified
    target_result = await db.execute(
        select(Target).where(
            Target.id == payload.target_id,
            Target.user_id == current_user.id,
        )
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target non trovato")
    if not target.verified:
        raise HTTPException(
            status_code=403,
            detail="Il dominio non è stato verificato. Completa la verifica prima di avviare uno scan.",
        )

    # Enforce max concurrent scans per user
    running_result = await db.execute(
        select(func.count()).where(
            Scan.user_id == current_user.id,
            Scan.status.in_([ScanStatus.pending, ScanStatus.running]),
        )
    )
    if running_result.scalar_one() >= settings.max_concurrent_scans_per_user:
        raise HTTPException(
            status_code=429,
            detail=f"Massimo {settings.max_concurrent_scans_per_user} scan contemporanei per utente",
        )

    scan = Scan(
        user_id=current_user.id,
        target_id=target.id,
        target=target.domain,
        scope=payload.scope,
        scan_options=payload.scan_options,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Dispatch async workers — fire and forget
    dispatch_scan(scan.id, scan.scope)

    return scan


@router.get("", response_model=list[ScanOut])
async def list_scans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Scan]:
    result = await db.execute(
        select(Scan).where(Scan.user_id == current_user.id).order_by(Scan.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scan:
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trovato")
    return scan


@router.get("/{scan_id}/findings", response_model=list[FindingOut])
async def get_scan_findings(
    scan_id: uuid.UUID,
    severity: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Finding]:
    # Verify scan ownership
    scan_result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == current_user.id)
    )
    if not scan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Scan non trovato")

    query = select(Finding).where(Finding.scan_id == scan_id)
    if severity:
        query = query.where(Finding.severity == severity.upper())
    query = query.order_by(Finding.severity, Finding.created_at)

    result = await db.execute(query)
    return list(result.scalars().all())
