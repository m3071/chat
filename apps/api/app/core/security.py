from secrets import compare_digest

from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.core.runtime_config import RuntimeConfigService


def require_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    if not settings.internal_api_key:
        if settings.environment.lower() in {"production", "prod"}:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="INTERNAL_API_KEY is required in production.")
        return
    if not x_internal_api_key or not compare_digest(x_internal_api_key, settings.internal_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key.")


def require_wazuh_shared_secret(x_webhook_secret: str | None = Header(default=None)) -> None:
    expected_secret = RuntimeConfigService().get_wazuh_webhook_secret()
    if not expected_secret:
        if settings.environment.lower() in {"production", "prod"}:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Wazuh webhook secret is required in production.")
        return
    if not x_webhook_secret or not compare_digest(x_webhook_secret, expected_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret.")
