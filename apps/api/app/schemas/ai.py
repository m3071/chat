from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AiProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    api_key: str | None = None
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Provider name is required.")
        return normalized


class AiProviderUpdate(BaseModel):
    label: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    is_active: bool | None = None


class AiProviderRead(BaseModel):
    id: UUID
    name: str
    label: str
    base_url: str
    has_api_key: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AiModelCreate(BaseModel):
    provider_id: UUID
    model_name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    purpose: list[str] = Field(default_factory=list)
    supports_tools: bool = False
    supports_vision: bool = False
    is_default: bool = False
    is_active: bool = True

    @field_validator("purpose")
    @classmethod
    def normalize_purpose(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip().lower() for value in values if value.strip()})
        if not normalized:
            raise ValueError("At least one purpose is required.")
        return normalized


class AiModelUpdate(BaseModel):
    model_name: str | None = None
    label: str | None = None
    purpose: list[str] | None = None
    supports_tools: bool | None = None
    supports_vision: bool | None = None
    is_default: bool | None = None
    is_active: bool | None = None

    @field_validator("purpose")
    @classmethod
    def normalize_optional_purpose(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = sorted({value.strip().lower() for value in values if value.strip()})
        if not normalized:
            raise ValueError("At least one purpose is required.")
        return normalized


class AiModelRead(BaseModel):
    id: UUID
    provider_id: UUID
    provider_name: str
    model_name: str
    label: str
    purpose: list[str]
    supports_tools: bool
    supports_vision: bool
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
