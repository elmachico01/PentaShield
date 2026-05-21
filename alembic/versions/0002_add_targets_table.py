"""Add targets table and target_id FK on scans

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column(
            "verification_method",
            sa.Enum("dns_txt", "file_upload", name="verificationmethod"),
            nullable=False,
            server_default="dns_txt",
        ),
        sa.Column("verification_token", sa.String(64), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_targets_user_id", "targets", ["user_id"])
    op.create_index(
        "ix_targets_user_domain",
        "targets",
        ["user_id", "domain"],
        unique=False,
    )

    # Add target_id FK to scans (nullable for backward compat with existing rows)
    op.add_column(
        "scans",
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("targets.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("ix_scans_target_id", "scans", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_scans_target_id", table_name="scans")
    op.drop_column("scans", "target_id")
    op.drop_index("ix_targets_user_domain", table_name="targets")
    op.drop_index("ix_targets_user_id", table_name="targets")
    op.drop_table("targets")
    op.execute("DROP TYPE IF EXISTS verificationmethod")
