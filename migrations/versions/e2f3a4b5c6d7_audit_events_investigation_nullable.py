"""Allow nullable investigation_id and widen actor_type in audit_events.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-10-12 15:48:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("audit_events", "investigation_id", nullable=True)
    op.alter_column(
        "audit_events",
        "actor_type",
        type_=sa.String(length=64),
        existing_type=sa.String(length=16),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "audit_events",
        "actor_type",
        type_=sa.String(length=16),
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.alter_column("audit_events", "investigation_id", nullable=False)
