import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.db.database import Base


class Severity(str, PyEnum):
    info = "INFO"
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    critical = "CRITICAL"


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity), nullable=False, default=Severity.info
    )
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    affected_component: Mapped[str] = mapped_column(String(512), nullable=False)
    proof: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    nis2_control: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="recon")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scan: Mapped["Scan"] = relationship("Scan", back_populates="findings")  # noqa: F821
