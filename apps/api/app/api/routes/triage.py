from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.tools import AiToolService
from app.core.security import require_internal_api_key
from app.db.session import get_db
from app.models.entities import CommandAudit, Incident
from app.policies.approval import ApprovalPolicyService
from app.schemas.triage import (
    TriageConfirmRequest,
    TriageExecutionResponse,
    TriageRequestCreate,
    TriageRequestResponse,
)
from app.services.triage_service import TriageService

router = APIRouter()
ai_tools = AiToolService()
policy = ApprovalPolicyService()
triage_service = TriageService()


@router.post("/request", response_model=TriageRequestResponse, dependencies=[Depends(require_internal_api_key)])
def request_triage(payload: TriageRequestCreate, db: Session = Depends(get_db)) -> TriageRequestResponse:
    incident = db.get(Incident, payload.incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")

    audit = ai_tools.request_host_triage(
        db,
        incident_id=payload.incident_id,
        triage_type=payload.triage_type,
        user_id=payload.requested_by,
        command_text=f"Run {payload.triage_type} for incident {payload.incident_id}",
    )
    db.commit()
    return TriageRequestResponse(
        command_audit_id=audit.id,
        approval_status=audit.approval_status,
        intent=audit.parsed_intent or {},
        confirmation_message=f"Confirm {payload.triage_type} for incident {payload.incident_id}.",
    )


@router.post("/confirm", response_model=TriageExecutionResponse, dependencies=[Depends(require_internal_api_key)])
def confirm_triage(payload: TriageConfirmRequest, db: Session = Depends(get_db)) -> TriageExecutionResponse:
    try:
        audit = policy.approve(db, payload.command_audit_id, payload.approved_by)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    incident_id = UUID(audit.action_payload["incident_id"])
    incident = db.scalar(select(Incident).where(Incident.id == incident_id).options(selectinload(Incident.asset)))
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")

    job, evidence = triage_service.execute_triage(db, incident=incident, audit=audit, requested_by=payload.approved_by)
    policy.mark_executed(db, audit, f"Executed {audit.action_payload['triage_type']} with job {job.id}")
    db.commit()
    return TriageExecutionResponse(job_id=job.id, evidence_id=evidence.id, status=job.status)


@router.get("/audits/{command_audit_id}", dependencies=[Depends(require_internal_api_key)])
def get_command_audit(command_audit_id: UUID, db: Session = Depends(get_db)) -> dict:
    audit = db.get(CommandAudit, command_audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="Command audit not found.")
    return {
        "id": str(audit.id),
        "approval_status": audit.approval_status,
        "executed": audit.executed,
        "parsed_intent": audit.parsed_intent,
        "result_summary": audit.result_summary,
    }
