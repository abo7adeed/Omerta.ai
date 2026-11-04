"""Add missing customer profile fields.

Revision ID: e10addcustomerfields
Revises: d09fc48cac67
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e10addcustomerfields"
down_revision: str | None = "d09fc48cac67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("declared_country", sa.String(length=2), nullable=True),
    )

    op.execute(
        """
        UPDATE customers
        SET declared_country = COALESCE(country, 'EG')
        WHERE declared_country IS NULL
        """
    )

    op.alter_column(
        "customers",
        "declared_country",
        nullable=False,
        server_default="EG",
    )

    op.create_index(
        "ix_customers_declared_country",
        "customers",
        ["declared_country"],
    )

    op.add_column(
        "customers",
        sa.Column("observed_country", sa.String(length=2), nullable=True),
    )

    op.add_column(
        "customers",
        sa.Column(
            "preferred_currency",
            sa.String(length=3),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE customers
        SET preferred_currency = 'EGP'
        WHERE preferred_currency IS NULL
        """
    )

    op.alter_column(
        "customers",
        "preferred_currency",
        nullable=False,
        server_default="EGP",
    )

    op.create_index(
        "ix_customers_preferred_currency",
        "customers",
        ["preferred_currency"],
    )

    op.add_column(
        "customers",
        sa.Column(
            "device_consent",
            sa.Boolean(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE customers
        SET device_consent = TRUE
        WHERE device_consent IS NULL
        """
    )

    op.alter_column(
        "customers",
        "device_consent",
        nullable=False,
        server_default=sa.text("true"),
    )

    op.add_column(
        "customers",
        sa.Column(
            "device_consent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("customers", "device_consent_at")

    op.drop_column("customers", "device_consent")

    op.drop_index(
        "ix_customers_preferred_currency",
        table_name="customers",
    )
    op.drop_column("customers", "preferred_currency")

    op.drop_column("customers", "observed_country")

    op.drop_index(
        "ix_customers_declared_country",
        table_name="customers",
    )
    op.drop_column("customers", "declared_country")