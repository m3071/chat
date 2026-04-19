from datetime import datetime
import json
from uuid import UUID

from pydantic import BaseModel, model_validator


class EvidenceRead(BaseModel):
    id: UUID
    incident_id: UUID | None
    asset_id: UUID | None
    source: str
    evidence_type: str
    title: str
    summary: str | None
    content_json: dict | None
    content_pretty: str | None = None
    content_text: str | None
    collected_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def set_pretty_json(self):
        if self.content_json is not None:
            self.content_pretty = json.dumps(self.content_json, indent=2, sort_keys=True)
        return self
