from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TriageRequestCreate(BaseModel):
    incident_id: UUID
    triage_type: Literal["process_triage", "autoruns_triage"]
    requested_by: str = Field(default="demo-user")


class TriageConfirmRequest(BaseModel):
    command_audit_id: UUID
    approved_by: str = Field(default="demo-user")


class TriageRequestResponse(BaseModel):
    command_audit_id: UUID
    approval_status: str
    intent: dict
    confirmation_message: str


class TriageExecutionResponse(BaseModel):
    job_id: UUID
    evidence_id: UUID
    status: str
