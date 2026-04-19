from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.connectors.wazuh import NormalizedWazuhAlert
from app.models.entities import Alert, Asset, Evidence, Incident, IncidentAlert
from app.services.timeline import add_timeline_event


class IncidentService:
    def resolve_or_create_asset(self, db: Session, alert: NormalizedWazuhAlert) -> Asset:
        asset = db.scalar(
            select(Asset).where(
                (Asset.source_type == "wazuh")
                & or_(Asset.external_id == alert.asset_external_id, Asset.hostname == alert.hostname)
            )
        )
        now = datetime.now(UTC)
        if asset is None:
            asset = Asset(
                source_type="wazuh",
                external_id=alert.asset_external_id,
                hostname=alert.hostname,
                ip_addresses=alert.ip_addresses,
                platform="windows" if alert.hostname.lower().startswith("win") else None,
                status="active",
                first_seen_at=now,
                last_seen_at=now,
            )
            db.add(asset)
            db.flush()
            return asset

        asset.hostname = alert.hostname or asset.hostname
        asset.ip_addresses = sorted(set((asset.ip_addresses or []) + alert.ip_addresses))
        asset.last_seen_at = now
        db.flush()
        return asset

    def get_alert_by_external_id(self, db: Session, *, source: str, external_id: str) -> Alert | None:
        return db.scalar(select(Alert).where(Alert.source == source, Alert.external_id == external_id))

    def get_incident_for_alert(self, db: Session, alert_id: UUID) -> Incident | None:
        return db.scalar(
            select(Incident)
            .join(IncidentAlert, IncidentAlert.incident_id == Incident.id)
            .where(IncidentAlert.alert_id == alert_id)
        )

    def find_duplicate_incident(self, db: Session, *, asset_id: UUID, rule_id: str, event_time: datetime) -> Incident | None:
        window_start = event_time - timedelta(minutes=10)
        window_end = event_time + timedelta(minutes=10)
        return db.scalar(
            select(Incident)
            .join(IncidentAlert, IncidentAlert.incident_id == Incident.id)
            .join(Alert, Alert.id == IncidentAlert.alert_id)
            .where(
                Incident.asset_id == asset_id,
                Alert.rule_id == rule_id,
                Alert.event_time >= window_start,
                Alert.event_time <= window_end,
            )
            .order_by(Incident.opened_at.desc())
            .options(
                selectinload(Incident.alert_links).selectinload(IncidentAlert.alert),
                selectinload(Incident.evidence_items),
                selectinload(Incident.timeline_events),
                selectinload(Incident.asset),
            )
        )

    def create_alert_and_incident(self, db: Session, normalized: NormalizedWazuhAlert, raw_payload: dict) -> Incident:
        asset = self.resolve_or_create_asset(db, normalized)
        alert = Alert(
            source="wazuh",
            external_id=normalized.external_id,
            asset_id=asset.id,
            severity=normalized.severity,
            title=normalized.title,
            rule_id=normalized.rule_id,
            rule_group=normalized.rule_group,
            rule_description=normalized.rule_description,
            raw_payload=raw_payload,
            normalized_payload=normalized.normalized_payload,
            event_time=datetime.fromisoformat(normalized.event_time),
            status="new",
        )
        db.add(alert)
        db.flush()

        duplicate = self.find_duplicate_incident(db, asset_id=asset.id, rule_id=alert.rule_id, event_time=alert.event_time)
        if duplicate is not None:
            db.add(IncidentAlert(incident_id=duplicate.id, alert_id=alert.id))
            add_timeline_event(
                db,
                incident_id=duplicate.id,
                event_type="alert_ingested",
                actor_type="connector",
                actor_id="wazuh",
                title="Wazuh alert ingested",
                description=f"Deduplicated alert attached: {normalized.title}",
                metadata={"alert_id": str(alert.id), "rule_id": normalized.rule_id, "deduplicated": True},
                event_time=alert.event_time,
            )
            db.flush()
            from app.services.incident_analysis_service import IncidentAnalysisService

            IncidentAnalysisService().analyze_incident(db, duplicate.id)
            return duplicate

        incident = Incident(
            title=f"{normalized.title} on {asset.hostname}",
            severity=normalized.severity,
            status="open",
            asset_id=asset.id,
            opened_at=alert.event_time,
            created_by="wazuh-webhook",
            summary=f"Incident opened from Wazuh alert {normalized.rule_id} for {asset.hostname}.",
        )
        db.add(incident)
        db.flush()

        db.add(IncidentAlert(incident_id=incident.id, alert_id=alert.id))
        db.flush()

        add_timeline_event(
            db,
            incident_id=incident.id,
            event_type="alert_ingested",
            actor_type="connector",
            actor_id="wazuh",
            title="Wazuh alert ingested",
            description=normalized.title,
            metadata={"alert_id": str(alert.id), "rule_id": normalized.rule_id},
            event_time=alert.event_time,
        )
        add_timeline_event(
            db,
            incident_id=incident.id,
            event_type="incident_created",
            actor_type="system",
            title="Incident created",
            description="Created automatically from a Wazuh alert.",
            metadata={"asset_id": str(asset.id)},
            event_time=alert.event_time,
        )
        db.flush()
        from app.services.incident_analysis_service import IncidentAnalysisService

        IncidentAnalysisService().analyze_incident(db, incident.id)
        return incident

    def list_incidents(self, db: Session) -> list[Incident]:
        return list(db.scalars(select(Incident).order_by(Incident.opened_at.desc())))

    def get_incident_detail(self, db: Session, incident_id: UUID) -> Incident | None:
        return db.scalar(
            select(Incident)
            .where(Incident.id == incident_id)
            .options(
                selectinload(Incident.alert_links).selectinload(IncidentAlert.alert),
                selectinload(Incident.evidence_items),
                selectinload(Incident.timeline_events),
                selectinload(Incident.asset),
            )
        )

    def list_evidence(self, db: Session, incident_id: UUID) -> list[Evidence]:
        incident = self.get_incident_detail(db, incident_id)
        return incident.evidence_items if incident else []

    def get_related_incidents(self, db: Session, incident_id: UUID, limit: int = 5) -> list[Incident]:
        incident = self.get_incident_detail(db, incident_id)
        if incident is None:
            return []
        rule_ids = {link.alert.rule_id for link in incident.alert_links}
        stmt = (
            select(Incident)
            .where(Incident.id != incident_id)
            .options(
                selectinload(Incident.alert_links).selectinload(IncidentAlert.alert),
                selectinload(Incident.evidence_items),
                selectinload(Incident.asset),
            )
            .order_by(Incident.opened_at.desc())
        )
        candidates = db.scalars(stmt).all()
        related = []
        for candidate in candidates:
            same_asset = incident.asset_id is not None and candidate.asset_id == incident.asset_id
            candidate_rule_ids = {link.alert.rule_id for link in candidate.alert_links}
            same_rule = bool(rule_ids.intersection(candidate_rule_ids))
            if same_asset or same_rule:
                related.append(candidate)
            if len(related) >= limit:
                break
        return related
