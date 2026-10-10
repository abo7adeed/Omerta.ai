"""Add pseudonym_hash to devices and review columns to transactions.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-10 12:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    dev_cols = [c["name"] for c in insp.get_columns("devices")]
    if "pseudonym_hash" not in dev_cols:
        op.add_column("devices", sa.Column("pseudonym_hash", sa.String(length=64), nullable=True))
        op.create_index("ix_devices_pseudonym_hash", "devices", ["pseudonym_hash"])

    txn_cols = [c["name"] for c in insp.get_columns("transactions")]
    if "is_new_device" not in txn_cols:
        op.add_column("transactions", sa.Column("is_new_device", sa.Boolean(), nullable=False, server_default="false"))
    if "is_new_ip" not in txn_cols:
        op.add_column("transactions", sa.Column("is_new_ip", sa.Boolean(), nullable=False, server_default="false"))
    if "review_status" not in txn_cols:
        op.add_column("transactions", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="NOT_REQUIRED"))
    if "txn_metadata" not in txn_cols:
        op.add_column("transactions", sa.Column("txn_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
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
