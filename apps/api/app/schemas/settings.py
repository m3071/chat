from pydantic import BaseModel, Field


class WazuhSettingsUpdate(BaseModel):
    credential_name: str = Field(default="Wazuh default credential")
    connection_mode: str = Field(default="indexer_sync")
    auth_type: str = Field(default="basic")
    webhook_secret: str = Field(default="")
    manager_url: str = Field(default="")
    api_url: str = Field(default="")
    api_username: str = Field(default="")
    api_password: str = Field(default="")
    indexer_url: str = Field(default="")
    indexer_username: str = Field(default="")
    indexer_password: str = Field(default="")
    indexer_alert_index: str = Field(default="wazuh-alerts-*")
    verify_tls: bool = Field(default=True)


class VelociraptorSettingsUpdate(BaseModel):
    credential_name: str = Field(default="Velociraptor default credential")
    credential_type: str = Field(default="mock")
    auth_type: str = Field(default="api_client_config")
    mode: str = Field(default="mock")
    transport: str = Field(default="grpc_api")
    base_url: str = Field(default="")
    api_key: str = Field(default="")
    api_client_config: str = Field(default="")
    binary_path: str = Field(default="velociraptor")
    org_id: str = Field(default="root")
    timeout_seconds: int = Field(default=120)
    run_path: str = Field(default="/api/v1/collect")
    status_path: str = Field(default="/api/v1/flows/{flow_id}")
    results_path: str = Field(default="/api/v1/flows/{flow_id}/results")
    verify_tls: bool = Field(default=True)


class IntegrationSettingsRead(BaseModel):
    wazuh: dict
    velociraptor: dict


class ConnectionTestRequest(BaseModel):
    service: str


class GenericIntegrationUpdate(BaseModel):
    config: dict = Field(default_factory=dict)


class GenericIntegrationConnect(BaseModel):
    config: dict = Field(default_factory=dict)
    sync_alerts: bool = Field(default=True)
    sync_limit: int = Field(default=25, ge=1, le=200)


class IntegrationFieldDefinition(BaseModel):
    key: str
    label: str
    input: str
    required: bool = False
    sensitive: bool = False
    advanced: bool = False
    placeholder: str | None = None
    help_text: str | None = None
    options: list[dict] = Field(default_factory=list)


class IntegrationCatalogItem(BaseModel):
    id: str
    name: str
    description: str
    category: str
    tools: list[str]
    fields: list[IntegrationFieldDefinition]
    status: str
    enabled: bool
    config: dict


class ToolCatalogItem(BaseModel):
    id: str
    name: str
    access: str
    description: str


class PolicyCatalogItem(BaseModel):
    id: str
    name: str
    scope: str
    description: str


class SettingsCatalogRead(BaseModel):
    integrations: list[IntegrationCatalogItem]
    tools: list[ToolCatalogItem]
    policies: list[PolicyCatalogItem]
