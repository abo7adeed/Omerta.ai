"""Add pseudonym hash to devices.

Revision ID: e11adddevicehash
Revises: e10addcustomerfields
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e11adddevicehash"
down_revision: str | None = "e10addcustomerfields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column(
            "pseudonym_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_devices_pseudonym_hash",
        "devices",
        ["pseudonym_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_devices_pseudonym_hash",
        table_name="devices",
    )
    op.drop_column("devices", "pseudonym_hash")