from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AlertRead(BaseModel):
    id: UUID
    source: str
    external_id: str
    asset_id: UUID | None
    severity: int
    title: str
    rule_id: str
    rule_group: str
    rule_description: str | None
    raw_payload: dict
    normalized_payload: dict | None
    event_time: datetime
    ingested_at: datetime
    status: str

    model_config = {"from_attributes": True}
