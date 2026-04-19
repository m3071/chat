from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    incident_id: UUID | None = None
    require_confirmation: bool = Field(default=True)
    user_id: str = Field(default="demo-user")


class ChatResponse(BaseModel):
    mode: str
    response: str
    intent: dict[str, Any] | None = None
    command_audit_id: UUID | None = None
