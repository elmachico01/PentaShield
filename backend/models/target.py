import uuid
import secrets
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.db.database import Base


class VerificationMethod(str, PyEnum):
    dns_txt = "dns_txt"
    file_upload = "file_upload"


def _generate_token() -> str:
    return secrets.token_hex(24)


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_method: Mapped[VerificationMethod] = mapped_column(
        Enum(VerificationMethod), nullable=False, default=VerificationMethod.dns_txt
    )
    verification_token: Mapped[str] = mapped_column(
        String(64), nullable=False, default=_generate_token
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="targets")  # noqa: F821
