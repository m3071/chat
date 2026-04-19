from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.entities import Alert, Asset, CommandAudit, Incident
from app.ai.service import AIService
from app.policies.approval import ApprovalPolicyService
from app.services.incident_service import IncidentService


class AiToolService:
    def __init__(self) -> None:
        self.incidents = IncidentService()
        self.policy = ApprovalPolicyService()
        self.ai = AIService()

    def get_incident(self, db: Session, incident_id: UUID) -> Incident | None:
        return self.incidents.get_incident_detail(db, incident_id)

    def list_incident_evidence(self, db: Session, incident_id: UUID) -> list:
        return self.incidents.list_evidence(db, incident_id)

    def search_incidents(self, db: Session, query: str | None = None, limit: int = 5) -> list[dict]:
        stmt = select(Incident).order_by(Incident.opened_at.desc()).limit(limit)
        if query:
            stmt = (
                select(Incident)
                .where(Incident.title.ilike(f"%{query}%"))
                .order_by(Incident.opened_at.desc())
                .limit(limit)
            )
        rows = db.scalars(stmt).all()
        result = [
            {
                "id": str(item.id),
                "title": item.title,
                "severity": item.severity,
                "risk_level": item.risk_level,
                "status": item.status,
                "opened_at": item.opened_at.isoformat(),
                "summary": item.summary,
            }
            for item in rows
        ]
        self.log_tool_usage(db, "search_incidents", {"query": query, "limit": limit}, f"Returned {len(result)} incident(s).")
        return result

    def list_alerts(self, db: Session, min_severity: int = 0, limit: int = 10) -> list[dict]:
        rows = db.execute(
            select(Alert, Asset.hostname)
            .outerjoin(Asset, Alert.asset_id == Asset.id)
            .where(Alert.severity >= min_severity)
            .order_by(Alert.event_time.desc())
            .limit(limit)
        ).all()
        result = [
            {
                "id": str(alert.id),
                "title": alert.title,
                "severity": alert.severity,
                "rule_id": alert.rule_id,
                "hostname": hostname,
                "event_time": alert.event_time.isoformat(),
            }
            for alert, hostname in rows
        ]
        self.log_tool_usage(db, "list_alerts", {"min_severity": min_severity, "limit": limit}, f"Returned {len(result)} alert(s).")
        return result

    def get_asset_profile(self, db: Session, hostname: str) -> dict | None:
        asset = db.scalar(
            select(Asset).where(
                or_(
                    Asset.hostname.ilike(hostname),
                    Asset.external_id.ilike(hostname),
                    Asset.fqdn.ilike(hostname),
                )
            )
        )
        if asset is None:
            self.log_tool_usage(db, "get_asset_profile", {"hostname": hostname}, "No asset found.")
            return None
        alert_count = db.scalar(select(func.count(Alert.id)).where(Alert.asset_id == asset.id)) or 0
        incident_count = db.scalar(select(func.count(Incident.id)).where(Incident.asset_id == asset.id)) or 0
        result = {
            "id": str(asset.id),
            "hostname": asset.hostname,
            "external_id": asset.external_id,
            "ip_addresses": asset.ip_addresses,
            "platform": asset.platform,
            "status": asset.status,
            "alert_count": alert_count,
            "incident_count": incident_count,
        }
        self.log_tool_usage(db, "get_asset_profile", {"hostname": hostname}, f"Returned profile for {asset.hostname}.")
        return result

    def log_tool_usage(self, db: Session, tool_name: str, input_payload: dict, result_summary: str) -> None:
        db.add(
            CommandAudit(
                command_text=f"tool:{tool_name}",
                parsed_intent={"tool": tool_name, "input": input_payload},
                risk_level="low",
                action_type="tool_usage",
                action_payload=input_payload,
                approval_status="not_required",
                executed=True,
                executed_at=datetime.now(UTC),
                result_summary=result_summary,
            )
        )
        db.flush()

    def summarize_incident(self, db: Session, incident_id: UUID) -> str:
        incident = self.incidents.get_incident_detail(db, incident_id)
        if incident is None:
            raise ValueError("Incident not found.")
        alert_count = len(incident.alert_links)
        evidence_count = len(incident.evidence_items)
        latest_evidence = incident.evidence_items[-1].summary if incident.evidence_items else "No evidence collected yet."
        fallback = (
            f"Incident {incident.title} is {incident.status} with severity {incident.severity}. "
            f"It has {alert_count} linked alert(s), {evidence_count} evidence item(s), and latest evidence summary: {latest_evidence}"
        )
        return self.ai.generate_for_purpose(
            db,
            purpose="summary",
            messages=[
                {"role": "system", "content": "Summarize cyber incidents concisely for an analyst."},
                {
                    "role": "user",
                    "content": (
                        f"Title: {incident.title}\nStatus: {incident.status}\nSeverity: {incident.severity}\n"
                        f"Linked alerts: {alert_count}\nEvidence count: {evidence_count}\nLatest evidence: {latest_evidence}"
                    ),
                },
            ],
            fallback_text=fallback,
        )

    def summarize_evidence(self, db: Session, incident_id: UUID) -> str:
        evidence = self.incidents.list_evidence(db, incident_id)
        if not evidence:
            return "No evidence is attached to this incident yet."
        parts = [f"{item.title}: {item.summary or 'No summary'}" for item in evidence]
        fallback = " | ".join(parts)
        return self.ai.generate_for_purpose(
            db,
            purpose="summary",
            messages=[
                {"role": "system", "content": "Summarize incident evidence concisely for an analyst."},
                {"role": "user", "content": fallback},
            ],
            fallback_text=fallback,
        )

    def request_host_triage(
        self, db: Session, *, incident_id: UUID, triage_type: str, user_id: str, command_text: str
    ) -> CommandAudit:
        parsed_intent = {
            "kind": "write_action",
            "action": "request_host_triage",
            "incident_id": str(incident_id),
            "triage_type": triage_type,
        }
        explanation = self.ai.generate_for_purpose(
            db,
            purpose="triage_explanation",
            messages=[
                {"role": "system", "content": "Explain why this triage request requires approval."},
                {"role": "user", "content": f"Requested {triage_type} for incident {incident_id}."},
            ],
            fallback_text=f"Prepared {triage_type}. This write action requires explicit approval before execution.",
        )
        parsed_intent["explanation"] = explanation
        return self.policy.create_pending_write(
            db,
            user_id=user_id,
            command_text=command_text,
            parsed_intent=parsed_intent,
            action_type="request_host_triage",
            action_payload={"incident_id": str(incident_id), "triage_type": triage_type},
            risk_level="medium",
        )
