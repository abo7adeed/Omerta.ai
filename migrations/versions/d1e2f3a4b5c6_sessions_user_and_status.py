"""Add user_id and active/revocation flags to sessions.

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-10-10 12:40:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    sess_cols = [c["name"] for c in insp.get_columns("sessions")]
    if "user_id" not in sess_cols:
        op.add_column("sessions", sa.Column("user_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_sessions_user_id_users", "sessions", "users", ["user_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    if "is_active" not in sess_cols:
        op.add_column("sessions", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))
    if "revoked_at" not in sess_cols:
        op.add_column("sessions", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    pass
