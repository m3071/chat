from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import JsonType, UpdatedTimestampMixin, uuid_pk


class Asset(Base, UpdatedTimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("source_type", "external_id", name="uq_assets_source_external"),)

    id: Mapped = uuid_pk()
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    fqdn: Mapped[str | None] = mapped_column(String(255))
    ip_addresses: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    os_name: Mapped[str | None] = mapped_column(String(255))
    os_version: Mapped[str | None] = mapped_column(String(255))
    platform: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[list | None] = mapped_column(JsonType)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    alerts: Mapped[list["Alert"]] = relationship(back_populates="asset")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="asset")
    jobs: Mapped[list["Job"]] = relationship(back_populates="asset")
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="asset")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_alerts_source_external"),)

    id: Mapped = uuid_pk()
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_id: Mapped = mapped_column(ForeignKey("assets.id"), nullable=True)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_group: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_description: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict] = mapped_column(JsonType, nullable=False)
    normalized_payload: Mapped[dict | None] = mapped_column(JsonType)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")

    asset: Mapped[Asset | None] = relationship(back_populates="alerts")
    incident_links: Mapped[list["IncidentAlert"]] = relationship(back_populates="alert")


class Incident(Base, UpdatedTimestampMixin):
    __tablename__ = "incidents"

    id: Mapped = uuid_pk()
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_id: Mapped = mapped_column(ForeignKey("assets.id"), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    asset: Mapped[Asset | None] = relationship(back_populates="incidents")
    alert_links: Mapped[list["IncidentAlert"]] = relationship(back_populates="incident")
    jobs: Mapped[list["Job"]] = relationship(back_populates="incident")
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="incident")
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="incident")


class IncidentAlert(Base):
    __tablename__ = "incident_alerts"

    id: Mapped = uuid_pk()
    incident_id: Mapped = mapped_column(ForeignKey("incidents.id"), nullable=False)
    alert_id: Mapped = mapped_column(ForeignKey("alerts.id"), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="alert_links")
    alert: Mapped[Alert] = relationship(back_populates="incident_links")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped = uuid_pk()
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(50))
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_id: Mapped = mapped_column(ForeignKey("assets.id"), nullable=True)
    incident_id: Mapped = mapped_column(ForeignKey("incidents.id"), nullable=True)
    input_payload: Mapped[dict] = mapped_column(JsonType, nullable=False)
    output_payload: Mapped[dict | None] = mapped_column(JsonType)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asset: Mapped[Asset | None] = relationship(back_populates="jobs")
    incident: Mapped[Incident | None] = relationship(back_populates="jobs")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped = uuid_pk()
    incident_id: Mapped = mapped_column(ForeignKey("incidents.id"), nullable=True)
    asset_id: Mapped = mapped_column(ForeignKey("assets.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content_json: Mapped[dict | None] = mapped_column(JsonType)
    content_text: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incident: Mapped[Incident | None] = relationship(back_populates="evidence_items")
    asset: Mapped[Asset | None] = relationship(back_populates="evidence_items")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped = uuid_pk()
    incident_id: Mapped = mapped_column(ForeignKey("incidents.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JsonType)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="timeline_events")


class CommandAudit(Base):
    __tablename__ = "command_audit"

    id: Mapped = uuid_pk()
    user_id: Mapped[str | None] = mapped_column(String(100))
    command_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_intent: Mapped[dict | None] = mapped_column(JsonType)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    action_type: Mapped[str | None] = mapped_column(String(100))
    action_payload: Mapped[dict | None] = mapped_column(JsonType)
    approval_status: Mapped[str] = mapped_column(String(50), nullable=False)
    executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AiProvider(Base, UpdatedTimestampMixin):
    __tablename__ = "ai_providers"
    __table_args__ = (UniqueConstraint("name", name="uq_ai_providers_name"),)

    id: Mapped = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    models: Mapped[list["AiModel"]] = relationship(
        back_populates="provider",
        cascade="all, delete-orphan",
    )


class AiModel(Base, UpdatedTimestampMixin):
    __tablename__ = "ai_models"
    __table_args__ = (UniqueConstraint("provider_id", "model_name", name="uq_ai_models_provider_model"),)

    id: Mapped = uuid_pk()
    provider_id: Mapped = mapped_column(ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    provider: Mapped[AiProvider] = relationship(back_populates="models")
