import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.database import get_db
from backend.models.target import Target
from backend.models.user import User
from backend.schemas.pydantic_schemas import TargetCreate, TargetOut, TargetVerifyResponse
from backend.core.deps import get_current_user
from backend.core.ownership import check_ownership

router = APIRouter(prefix="/targets", tags=["targets"])


@router.post("", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
async def create_target(
    payload: TargetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Target:
    # Prevent duplicate unverified targets for the same domain
    existing = await db.execute(
        select(Target).where(
            Target.user_id == current_user.id,
            Target.domain == payload.domain,
        )
    )
    target = existing.scalar_one_or_none()
    if target:
        # Return existing record so the client can re-use the token
        return target

    target = Target(
        user_id=current_user.id,
        domain=payload.domain,
        verification_method=payload.verification_method,
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


@router.get("", response_model=list[TargetOut])
async def list_targets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Target]:
    result = await db.execute(
        select(Target)
        .where(Target.user_id == current_user.id)
        .order_by(Target.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{target_id}", response_model=TargetOut)
async def get_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Target:
    result = await db.execute(
        select(Target).where(
            Target.id == target_id,
            Target.user_id == current_user.id,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target non trovato")
    return target


@router.post("/{target_id}/verify", response_model=TargetVerifyResponse)
async def verify_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TargetVerifyResponse:
    result = await db.execute(
        select(Target).where(
            Target.id == target_id,
            Target.user_id == current_user.id,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target non trovato")

    if target.verified:
        return TargetVerifyResponse(verified=True, detail="Dominio già verificato")

    ok = await check_ownership(
        domain=target.domain,
        token=target.verification_token,
        method=target.verification_method.value,
    )

    if ok:
        target.verified = True
        target.verified_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(target)
        return TargetVerifyResponse(verified=True, detail="Verifica completata con successo")

    # Return instructions based on method
    if target.verification_method.value == "dns_txt":
        detail = (
            f"Record DNS TXT non trovato. Aggiungi un record TXT su "
            f"_pentashield-verify.{target.domain} con valore: {target.verification_token}"
        )
    else:
        detail = (
            f"File non trovato o token non corrispondente. Pubblica il file "
            f"/.well-known/pentashield.txt su {target.domain} con contenuto: "
            f"{target.verification_token}"
        )

    return TargetVerifyResponse(verified=False, detail=detail)


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(Target).where(
            Target.id == target_id,
            Target.user_id == current_user.id,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target non trovato")
    await db.delete(target)
    await db.commit()
