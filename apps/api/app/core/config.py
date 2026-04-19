import json
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    app_name: str = "Cyber ChatOps MVP"
    environment: str = "development"
    debug: bool = False
    runtime_config_path: str = "./data/runtime-config.json"
    database_url: str = "sqlite+pysqlite:///./cyber_chatops.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "testserver"])
    internal_api_key: str | None = None
    wazuh_shared_secret: str | None = None
    secrets_encryption_key: str | None = None
    velociraptor_mode: str = "mock"
    velociraptor_base_url: str = "https://velociraptor.example.invalid"
    velociraptor_api_key: str = "changeme"
    ai_provider: str = "mock"
    log_level: str = "INFO"
    rate_limit_per_minute: int = 120

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                return json.loads(raw)
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                return json.loads(raw)
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if isinstance(value, str):
            raw = value.strip().lower()
            if raw in {"1", "true", "yes", "on", "debug"}:
                return True
            if raw in {"0", "false", "no", "off", "release", "prod", "production", ""}:
                return False
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
