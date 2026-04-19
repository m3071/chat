"""add ai provider and model registry

Revision ID: 20260416_0002
Revises: 20260415_0001
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260416_0002"
down_revision = "20260415_0001"
branch_labels = None
depends_on = None


def uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def now_sql():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("now()")
    return sa.text("CURRENT_TIMESTAMP")


def purpose_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.ARRAY(sa.Text())
    return sa.JSON()


def purpose_default():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("'{}'::text[]")
    return sa.text("'[]'")


def upgrade() -> None:
    op.create_table(
        "ai_providers",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
        sa.UniqueConstraint("name", name="uq_ai_providers_name"),
    )
    op.create_table(
        "ai_models",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("provider_id", uuid_type(), sa.ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("purpose", purpose_type(), nullable=False, server_default=purpose_default()),
        sa.Column("supports_tools", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("supports_vision", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
        sa.UniqueConstraint("provider_id", "model_name", name="uq_ai_models_provider_model"),
    )


def downgrade() -> None:
    op.drop_table("ai_models")
    op.drop_table("ai_providers")
