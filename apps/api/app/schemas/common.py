from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ApiMessage(BaseModel):
    message: str


class TimelineEventRead(BaseModel):
    id: UUID
    event_type: str
    actor_type: str
    actor_id: str | None
    title: str
    description: str | None
    event_metadata: dict | None
    event_time: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class HumanTimelineEventRead(BaseModel):
    id: UUID
    event_type: str
    timestamp: datetime
    title: str
    description: str | None
    actor_type: str
    actor_id: str | None
    metadata: dict | None
