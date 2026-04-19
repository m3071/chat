from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.connectors.wazuh import WazuhConnector
from app.core.security import require_internal_api_key
from app.db.session import get_db
from app.models.entities import Evidence
from app.schemas.common import ApiMessage
from app.schemas.wazuh import WazuhAgentPayload, WazuhAlertPayload, WazuhDataPayload, WazuhRulePayload
from app.services.evidence_analysis_service import EvidenceAnalysisService
from app.services.incident_analysis_service import IncidentAnalysisService
from app.services.incident_service import IncidentService
from app.services.timeline import add_timeline_event

router = APIRouter()


@router.post("/generate", response_model=ApiMessage, dependencies=[Depends(require_internal_api_key)])
def generate_demo_incident(db: Session = Depends(get_db)) -> ApiMessage:
    payload = WazuhAlertPayload(
        id=f"demo-{uuid4()}",
        timestamp=datetime.now(UTC),
        rule=WazuhRulePayload(
            id="100200",
            level=9,
            description="Suspicious PowerShell process detected",
            groups=["process_execution", "demo"],
        ),
        agent=WazuhAgentPayload(id="demo-agent-001", name="win-demo-01"),
        data=WazuhDataPayload(srcip="10.10.5.23", destip="10.10.5.10"),
        full_log="powershell.exe -nop -w hidden suspicious encoded command",
        location="demo",
    )
    connector = WazuhConnector()
    incident = IncidentService().create_alert_and_incident(db, connector.normalize_alert(payload), payload.model_dump(mode="json"))
    evidence = Evidence(
        incident_id=incident.id,
        asset_id=incident.asset_id,
        source="velociraptor",
        evidence_type="process_triage",
        title="Mock process triage results",
        summary="Mock Velociraptor triage found suspicious PowerShell and cmd.exe activity.",
        content_json={
            "artifact": "Windows.System.Pslist",
            "rows": [
                {"pid": 456, "name": "powershell.exe", "user": "SYSTEM", "cmdline": "-nop -w hidden"},
                {"pid": 912, "name": "cmd.exe", "user": "svc-demo", "cmdline": "/c whoami"},
            ],
        },
        content_text="powershell.exe -nop -w hidden; cmd.exe /c whoami",
        collected_at=datetime.now(UTC),
    )
    db.add(evidence)
    db.flush()
    add_timeline_event(
        db,
        incident_id=incident.id,
        event_type="evidence_added",
        actor_type="demo",
        title="Demo evidence added",
        description="Mock Velociraptor process triage evidence was attached.",
        metadata={"evidence_id": str(evidence.id)},
    )
    EvidenceAnalysisService().summarize_evidence(db, evidence.id)
    IncidentAnalysisService().analyze_incident(db, incident.id)
    db.commit()
    return ApiMessage(message=f"Demo incident generated: {incident.id}")
