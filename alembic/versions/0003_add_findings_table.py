"""Add findings table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "scan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="severity"),
            nullable=False,
            server_default="INFO",
        ),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("affected_component", sa.String(512), nullable=False),
        sa.Column("proof", sa.Text(), nullable=True),
        sa.Column("fix_suggestion", sa.Text(), nullable=True),
        sa.Column("nis2_control", sa.String(16), nullable=True),
        sa.Column("source", sa.String(64), nullable=False, server_default="recon"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_findings_scan_id", "findings", ["scan_id"])
    op.create_index("ix_findings_severity", "findings", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_findings_severity", table_name="findings")
    op.drop_index("ix_findings_scan_id", table_name="findings")
    op.drop_table("findings")
    op.execute("DROP TYPE IF EXISTS severity")
