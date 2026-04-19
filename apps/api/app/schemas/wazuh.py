from datetime import datetime

from pydantic import BaseModel, Field


class WazuhRulePayload(BaseModel):
    id: str
    level: int
    description: str | None = None
    groups: list[str] = Field(default_factory=list)


class WazuhAgentPayload(BaseModel):
    id: str | None = None
    name: str | None = None


class WazuhDataPayload(BaseModel):
    srcip: str | None = None
    destip: str | None = None


class WazuhAlertPayload(BaseModel):
    id: str | None = None
    timestamp: datetime
    rule: WazuhRulePayload
    agent: WazuhAgentPayload | None = None
    data: WazuhDataPayload | None = None
    full_log: str | None = None
    decoder: dict | None = None
    location: str | None = None
    manager: dict | None = None


class WazuhConnectRequest(BaseModel):
    webhook_secret: str = ""
    manager_url: str = ""
    api_url: str = ""
    api_username: str = ""
    api_password: str = ""
    indexer_url: str = ""
    indexer_username: str = ""
    indexer_password: str = ""
    indexer_alert_index: str = "wazuh-alerts-*"
    verify_tls: bool = True
    sync_alerts: bool = True
    sync_limit: int = Field(default=25, ge=1, le=200)
