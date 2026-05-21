import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.db.database import get_db
from backend.models.scan import Scan, ScanStatus
from backend.models.user import User
from backend.schemas.pydantic_schemas import ScanCreate, ScanOut
from backend.core.deps import get_current_user
from backend.config import get_settings

router = APIRouter(prefix="/scans", tags=["scans"])
settings = get_settings()


@router.post("", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
async def create_scan(
    payload: ScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scan:
    # Enforce max concurrent scans
    running_count_result = await db.execute(
        select(func.count()).where(
            Scan.user_id == current_user.id,
            Scan.status.in_([ScanStatus.pending, ScanStatus.running]),
        )
    )
    running_count = running_count_result.scalar_one()
    if running_count >= settings.max_concurrent_scans_per_user:
        raise HTTPException(
            status_code=429,
            detail=f"Massimo {settings.max_concurrent_scans_per_user} scan contemporanei per utente",
        )

    scan = Scan(
        user_id=current_user.id,
        target=payload.target,
        scope=payload.scope,
        scan_options=payload.scan_options,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
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
