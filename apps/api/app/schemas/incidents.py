from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.alerts import AlertRead
from app.schemas.common import TimelineEventRead
from app.schemas.evidence import EvidenceRead


class IncidentRead(BaseModel):
    id: UUID
    title: str
    summary: str | None
    severity: int
    risk_level: str
    confidence: float
    status: str
    asset_id: UUID | None
    opened_at: datetime
    closed_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentDetail(IncidentRead):
    alerts: list[AlertRead]
    evidence: list[EvidenceRead]
    timeline: list[TimelineEventRead]


class SuggestedAction(BaseModel):
    action_type: str
    label: str
    reason: str
    risk_level: str


class IncidentRecommendations(BaseModel):
    suggested_actions: list[SuggestedAction]


class IncidentActionRequest(BaseModel):
    action_type: str
    requested_by: str = "demo-user"


class IncidentActionResponse(BaseModel):
    action_type: str
    command_audit_id: UUID
    approval_status: str
    confirmation_required: bool
    confirmation_message: str
    intent: dict
