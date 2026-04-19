from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobRead(BaseModel):
    id: UUID
    job_type: str
    status: str
    priority: str | None
    requested_by: str
    asset_id: UUID | None
    incident_id: UUID | None
    input_payload: dict
    output_payload: dict | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
