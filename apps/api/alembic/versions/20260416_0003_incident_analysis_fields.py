"""add incident analysis fields

Revision ID: 20260416_0003
Revises: 20260416_0002
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20260416_0003"
down_revision = "20260416_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"))
    op.add_column("incidents", sa.Column("confidence", sa.Float(), nullable=False, server_default="0.6"))


def downgrade() -> None:
    op.drop_column("incidents", "confidence")
    op.drop_column("incidents", "risk_level")
