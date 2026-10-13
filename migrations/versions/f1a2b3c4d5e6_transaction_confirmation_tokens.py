"""Create transaction_confirmation_tokens table for secure single-use confirmation actions.

Revision ID: f1a2b3c4d5e6
Revises: e2f3a4b5c6d7
Create Date: 2026-10-13 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transaction_confirmation_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("allowed_action", sa.String(length=16), nullable=False, server_default="ANY"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transaction_confirmation_tokens_token_hash",
        "transaction_confirmation_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_transaction_confirmation_tokens_transaction_id",
        "transaction_confirmation_tokens",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_transaction_confirmation_tokens_customer_id",
        "transaction_confirmation_tokens",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_confirmation_tokens_customer_id", table_name="transaction_confirmation_tokens")
    op.drop_index("ix_transaction_confirmation_tokens_transaction_id", table_name="transaction_confirmation_tokens")
    op.drop_index("ix_transaction_confirmation_tokens_token_hash", table_name="transaction_confirmation_tokens")
    op.drop_table("transaction_confirmation_tokens")
