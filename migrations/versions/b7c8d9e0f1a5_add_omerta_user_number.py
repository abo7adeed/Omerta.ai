"""Complete missing customer fields.

Revision ID: b7c8d9e0f1a5
Revises: a7b8c9d0e1f2
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a5"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Omerta user number
    op.add_column(
        "customers",
        sa.Column(
            "omerta_user_number",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE customers
        SET omerta_user_number = 'OMR-' || LPAD(id::text, 8, '0')
        WHERE omerta_user_number IS NULL
        """
    )

    op.alter_column(
        "customers",
        "omerta_user_number",
        nullable=False,
    )

    op.create_index(
        "ix_customers_omerta_user_number",
        "customers",
        ["omerta_user_number"],
        unique=True,
    )

    # Link customer to application user
    op.add_column(
        "customers",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_customers_user_id_users",
        "customers",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_customers_user_id",
        "customers",
        ["user_id"],
        unique=True,
    )





def downgrade() -> None:
    op.drop_column(
        "customers",
        "require_transfer_password_change",
    )

    op.drop_column(
        "customers",
        "transfer_unblocked_at",
    )

    op.drop_column(
        "customers",
        "transfer_blocked_at",
    )

    op.drop_column(
        "customers",
        "transfer_failed_attempts",
    )

    op.drop_index(
        "ix_customers_user_id",
        table_name="customers",
    )

    op.drop_constraint(
        "fk_customers_user_id_users",
        "customers",
        type_="foreignkey",
    )

    op.drop_column(
        "customers",
        "user_id",
    )

    op.drop_index(
        "ix_customers_omerta_user_number",
        table_name="customers",
    )

    op.drop_column(
        "customers",
        "omerta_user_number",
    )