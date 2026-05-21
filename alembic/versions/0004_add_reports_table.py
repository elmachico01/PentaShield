"""Add reports table

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "scan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "generating", "completed", "failed", name="reportstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("nis2_gap_analysis", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reports_scan_id", "reports", ["scan_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_scan_id", table_name="reports")
    op.drop_table("reports")
    op.execute("DROP TYPE IF EXISTS reportstatus")
