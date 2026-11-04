"""Create transfers table.

Revision ID: g7b8c9d0e1f4
Revises: f6a29b8c1d3e
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "g7b8c9d0e1f4"
down_revision: str | None = "f6a29b8c1d3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transfers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("sender_customer_id", sa.Integer(), nullable=False),
        sa.Column("sender_account_id", sa.Integer(), nullable=False),
        sa.Column("recipient_customer_id", sa.Integer(), nullable=False),
        sa.Column("recipient_account_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="COMPLETED",
        ),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["sender_customer_id"],
            ["customers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sender_account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_customer_id"],
            ["customers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("external_id"),
        sa.UniqueConstraint("idempotency_key"),
    )

    op.create_index(
        "ix_transfers_external_id",
        "transfers",
        ["external_id"],
        unique=True,
    )
    op.create_index(
        "ix_transfers_idempotency_key",
        "transfers",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_transfers_sender_customer_id",
        "transfers",
        ["sender_customer_id"],
    )
    op.create_index(
        "ix_transfers_sender_account_id",
        "transfers",
        ["sender_account_id"],
    )
    op.create_index(
        "ix_transfers_recipient_customer_id",
        "transfers",
        ["recipient_customer_id"],
    )
    op.create_index(
        "ix_transfers_recipient_account_id",
        "transfers",
        ["recipient_account_id"],
    )
    op.create_index(
        "ix_transfers_status",
        "transfers",
        ["status"],
    )
    op.create_index(
        "ix_transfers_transaction_id",
        "transfers",
        ["transaction_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transfers_transaction_id", table_name="transfers")
    op.drop_index("ix_transfers_status", table_name="transfers")
    op.drop_index(
        "ix_transfers_recipient_account_id",
        table_name="transfers",
    )
    op.drop_index(
        "ix_transfers_recipient_customer_id",
        table_name="transfers",
    )
    op.drop_index(
        "ix_transfers_sender_account_id",
        table_name="transfers",
    )
    op.drop_index(
        "ix_transfers_sender_customer_id",
        table_name="transfers",
    )
    op.drop_index(
        "ix_transfers_idempotency_key",
        table_name="transfers",
    )
    op.drop_index(
        "ix_transfers_external_id",
        table_name="transfers",
    )
    op.drop_table("transfers")