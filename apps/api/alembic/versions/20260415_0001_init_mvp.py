"""init mvp schema

Revision ID: 20260415_0001
Revises:
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260415_0001"
down_revision = None
branch_labels = None
depends_on = None


def json_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


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


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("fqdn", sa.String(length=255), nullable=True),
        sa.Column("ip_addresses", json_type(), nullable=False),
        sa.Column("os_name", sa.String(length=255), nullable=True),
        sa.Column("os_version", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("tags", json_type(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
        sa.UniqueConstraint("source_type", "external_id", name="uq_assets_source_external"),
    )

    op.create_table(
        "alerts",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("asset_id", uuid_type(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("rule_group", sa.String(length=255), nullable=False),
        sa.Column("rule_description", sa.Text(), nullable=True),
        sa.Column("raw_payload", json_type(), nullable=False),
        sa.Column("normalized_payload", json_type(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("source", "external_id", name="uq_alerts_source_external"),
    )

    op.create_table(
        "incidents",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("asset_id", uuid_type(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
    )

    op.create_table(
        "incident_alerts",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("incident_id", uuid_type(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("alert_id", uuid_type(), sa.ForeignKey("alerts.id"), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
    )

    op.create_table(
        "jobs",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("asset_id", uuid_type(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("incident_id", uuid_type(), sa.ForeignKey("incidents.id"), nullable=True),
        sa.Column("input_payload", json_type(), nullable=False),
        sa.Column("output_payload", json_type(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
    )

    op.create_table(
        "evidence",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("incident_id", uuid_type(), sa.ForeignKey("incidents.id"), nullable=True),
        sa.Column("asset_id", uuid_type(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("evidence_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_json", json_type(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
    )

    op.create_table(
        "timeline_events",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("incident_id", uuid_type(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", json_type(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
    )

    op.create_table(
        "command_audit",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("command_text", sa.Text(), nullable=False),
        sa.Column("parsed_intent", json_type(), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=True),
        sa.Column("action_payload", json_type(), nullable=True),
        sa.Column("approval_status", sa.String(length=50), nullable=False),
        sa.Column("executed", sa.Boolean(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_sql()),
    )


def downgrade() -> None:
    for table_name in [
        "command_audit",
        "timeline_events",
        "evidence",
        "jobs",
        "incident_alerts",
        "incidents",
        "alerts",
        "assets",
    ]:
        op.drop_table(table_name)
