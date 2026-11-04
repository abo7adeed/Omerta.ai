"""No-op migration.

Revision ID: d09fc48cac67
Revises: b7c8d9e0f1a5
"""

from collections.abc import Sequence


revision: str = "d09fc48cac67"
down_revision: str | None = "b7c8d9e0f1a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass