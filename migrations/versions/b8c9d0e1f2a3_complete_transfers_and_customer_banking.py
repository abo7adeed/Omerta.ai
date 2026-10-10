"""Complete transfers, customer banking, and double-entry ledger schema.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-10 12:00:00.000000

Adds:
- Customer user linkage and omerta_user_number columns
- transfers table for simulated banking movements
- account_ledger_entries table for double-entry records
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()
    columns = [c["name"] for c in insp.get_columns("customers")]

    # 1. Customer linkage & profile attributes
    if "omerta_user_number" not in columns:
        op.add_column("customers", sa.Column("omerta_user_number", sa.String(length=32), nullable=True))
        op.create_index("ix_customers_omerta_user_number", "customers", ["omerta_user_number"], unique=True)
    if "user_id" not in columns:
        op.add_column("customers", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True))
        op.create_index("ix_customers_user_id", "customers", ["user_id"], unique=True)
    if "declared_country" not in columns:
        op.add_column("customers", sa.Column("declared_country", sa.String(length=2), nullable=False, server_default="EG"))
    if "observed_country" not in columns:
        op.add_column("customers", sa.Column("observed_country", sa.String(length=2), nullable=True))
    if "preferred_currency" not in columns:
        op.add_column("customers", sa.Column("preferred_currency", sa.String(length=3), nullable=False, server_default="EGP"))
    if "device_consent" not in columns:
        op.add_column("customers", sa.Column("device_consent", sa.Boolean(), nullable=False, server_default="true"))
    if "device_consent_at" not in columns:
        op.add_column("customers", sa.Column("device_consent_at", sa.DateTime(timezone=True), nullable=True))

    # 2. Transfers table
    if "transfers" not in tables:
        op.create_table(
            "transfers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("external_id", sa.String(length=64), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("sender_customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("sender_account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("recipient_customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("recipient_account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("note", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="COMPLETED"),
            sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_transfers_external_id", "transfers", ["external_id"], unique=True)
        op.create_index("ix_transfers_idempotency_key", "transfers", ["idempotency_key"], unique=True)
        op.create_index("ix_transfers_sender_customer", "transfers", ["sender_customer_id"])
        op.create_index("ix_transfers_recipient_customer", "transfers", ["recipient_customer_id"])
        op.create_index("ix_transfers_status", "transfers", ["status"])

    # 3. Account Ledger Entries table
    if "account_ledger_entries" not in tables:
        op.create_table(
            "account_ledger_entries",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("external_id", sa.String(length=64), nullable=False),
            sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("transfer_id", sa.Integer(), sa.ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("entry_type", sa.String(length=32), nullable=False),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("balance_after", sa.Numeric(18, 2), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_account_ledger_entries_external_id", "account_ledger_entries", ["external_id"], unique=True)
        op.create_index("ix_account_ledger_entries_account_id", "account_ledger_entries", ["account_id"])
        op.create_index("ix_account_ledger_entries_entry_type", "account_ledger_entries", ["entry_type"])


def downgrade() -> None:
    pass
