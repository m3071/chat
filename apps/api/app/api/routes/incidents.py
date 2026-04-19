from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.core.security import require_internal_api_key
from app.db.session import get_db
from app.schemas.evidence import EvidenceRead
from app.ai.tools import AiToolService
from app.schemas.common import HumanTimelineEventRead
from app.schemas.incidents import IncidentActionRequest, IncidentActionResponse, IncidentDetail, IncidentRead, IncidentRecommendations
from app.services.incident_service import IncidentService
from app.services.recommendation_service import RecommendationService
from app.services.timeline import add_timeline_event

router = APIRouter()
service = IncidentService()
recommendations = RecommendationService()
ai_tools = AiToolService()

ACTION_TO_TRIAGE = {
    "run_triage": "process_triage",
    "collect_processes": "process_triage",
    "check_persistence": "autoruns_triage",
}

ACTION_LABELS = {
    "run_triage": "Run Triage",
    "collect_processes": "Collect Processes",
    "check_persistence": "Check Persistence",
}


@router.get("", response_model=list[IncidentRead], dependencies=[Depends(require_internal_api_key)])
def list_incidents(db: Session = Depends(get_db)):
    return service.list_incidents(db)


@router.get("/{incident_id}", response_model=IncidentDetail, dependencies=[Depends(require_internal_api_key)])
def get_incident(incident_id: UUID, db: Session = Depends(get_db)):
    incident = service.get_incident_detail(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return IncidentDetail(
        **IncidentRead.model_validate(incident).model_dump(),
        alerts=[link.alert for link in incident.alert_links],
        evidence=incident.evidence_items,
        timeline=sorted(incident.timeline_events, key=lambda item: item.event_time, reverse=True),
    )


@router.get("/{incident_id}/evidence", response_model=list[EvidenceRead], dependencies=[Depends(require_internal_api_key)])
def list_incident_evidence(incident_id: UUID, db: Session = Depends(get_db)):
    return service.list_evidence(db, incident_id)


@router.get(
    "/{incident_id}/timeline",
    response_model=list[HumanTimelineEventRead],
    dependencies=[Depends(require_internal_api_key)],
)
def get_incident_timeline(incident_id: UUID, db: Session = Depends(get_db)):
    incident = service.get_incident_detail(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return [
        HumanTimelineEventRead(
            id=event.id,
            event_type=event.event_type,
            timestamp=event.event_time,
            title=event.title,
            description=event.description,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            metadata=event.event_metadata,
        )
        for event in sorted(incident.timeline_events, key=lambda item: item.event_time)
    ]


@router.get("/{incident_id}/report", dependencies=[Depends(require_internal_api_key)])
def export_incident_report(incident_id: UUID, format: str = "md", db: Session = Depends(get_db)):
    incident = service.get_incident_detail(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    payload = _incident_report_payload(incident)
    if format.lower() == "json":
        return JSONResponse(
            payload,
            headers={"Content-Disposition": f'attachment; filename="incident-{incident.id}.json"'},
        )
    markdown = _incident_report_markdown(payload)
    return PlainTextResponse(
        markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="incident-{incident.id}.md"'},
    )


@router.get(
    "/{incident_id}/recommendations",
    response_model=IncidentRecommendations,
    dependencies=[Depends(require_internal_api_key)],
)
def get_incident_recommendations(incident_id: UUID, db: Session = Depends(get_db)):
    try:
        return recommendations.get_recommendations(db, incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{incident_id}/actions",
    response_model=IncidentActionResponse,
    dependencies=[Depends(require_internal_api_key)],
)
def trigger_incident_action(incident_id: UUID, payload: IncidentActionRequest, db: Session = Depends(get_db)):
    action_type = payload.action_type.strip().lower()
    triage_type = ACTION_TO_TRIAGE.get(action_type)
    if triage_type is None:
        raise HTTPException(status_code=400, detail="Unsupported incident action.")

    incident = service.get_incident_detail(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")

    audit = ai_tools.request_host_triage(
        db,
        incident_id=incident_id,
        triage_type=triage_type,
        user_id=payload.requested_by,
        command_text=f"{ACTION_LABELS[action_type]} requested for incident {incident_id}",
    )
    if audit.action_payload is not None:
        audit.action_payload["quick_action_type"] = action_type
    if audit.parsed_intent is not None:
        audit.parsed_intent["quick_action_type"] = action_type

    add_timeline_event(
        db,
        incident_id=incident_id,
        event_type="action_triggered",
        actor_type="user",
        actor_id=payload.requested_by,
        title="User triggered action",
        description=f"{ACTION_LABELS[action_type]} requested and is pending confirmation.",
        metadata={"action_type": action_type, "triage_type": triage_type, "command_audit_id": str(audit.id)},
    )
    db.commit()
    return IncidentActionResponse(
        action_type=action_type,
        command_audit_id=audit.id,
        approval_status=audit.approval_status,
        confirmation_required=True,
        confirmation_message=f"Confirm {ACTION_LABELS[action_type]} to execute {triage_type}.",
        intent=audit.parsed_intent or {},
    )


def _incident_report_payload(incident) -> dict:
    return {
        "id": str(incident.id),
        "title": incident.title,
        "status": incident.status,
        "severity": incident.severity,
        "risk_level": incident.risk_level,
        "confidence": incident.confidence,
        "summary": incident.summary,
        "asset": incident.asset.hostname if incident.asset else None,
        "opened_at": incident.opened_at.isoformat(),
        "alerts": [
            {
                "title": link.alert.title,
                "severity": link.alert.severity,
                "rule_id": link.alert.rule_id,
                "rule_group": link.alert.rule_group,
                "event_time": link.alert.event_time.isoformat(),
            }
            for link in incident.alert_links
        ],
        "evidence": [
            {
                "title": item.title,
                "source": item.source,
                "evidence_type": item.evidence_type,
                "summary": item.summary,
                "collected_at": item.collected_at.isoformat() if item.collected_at else None,
            }
            for item in incident.evidence_items
        ],
        "timeline": [
            {
                "event_type": item.event_type,
                "title": item.title,
                "description": item.description,
                "event_time": item.event_time.isoformat(),
            }
            for item in sorted(incident.timeline_events, key=lambda event: event.event_time)
        ],
    }


def _incident_report_markdown(payload: dict) -> str:
    lines = [
        f"# {payload['title']}",
        "",
        f"- Status: {payload['status']}",
        f"- Severity: {payload['severity']}",
        f"- Risk: {payload['risk_level']}",
        f"- Confidence: {round(float(payload['confidence']) * 100)}%",
        f"- Asset: {payload['asset'] or 'unknown'}",
        f"- Opened: {payload['opened_at']}",
        "",
        "## Summary",
        payload["summary"] or "No summary recorded.",
        "",
        "## Alerts",
    ]
    lines.extend([f"- [{item['severity']}] {item['title']} ({item['rule_id']}, {item['rule_group']})" for item in payload["alerts"]] or ["- None"])
    lines.extend(["", "## Evidence"])
    lines.extend([f"- {item['title']} ({item['evidence_type']}): {item['summary'] or 'No summary'}" for item in payload["evidence"]] or ["- None"])
    lines.extend(["", "## Timeline"])
    lines.extend([f"- {item['event_time']} - {item['title']}: {item['description'] or ''}" for item in payload["timeline"]] or ["- None"])
    return "\n".join(lines) + "\n"
