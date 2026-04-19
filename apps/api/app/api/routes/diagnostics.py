from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.runtime_config import RuntimeConfigService
from app.core.security import require_internal_api_key
from app.core.secrets import SecretManager
from app.db.session import get_db
from app.models.entities import AiModel, AiProvider, Alert, Incident

router = APIRouter(dependencies=[Depends(require_internal_api_key)])


@router.get("")
def get_diagnostics(db: Session = Depends(get_db)) -> dict:
    checks = []
    try:
        db.execute(text("SELECT 1"))
        checks.append({"name": "database", "status": "ok", "detail": "Database connection is ready."})
    except Exception as exc:
        checks.append({"name": "database", "status": "error", "detail": str(exc)})

    migration_status = _migration_status(db)
    checks.append(migration_status)

    security_status = _security_status()
    checks.append(security_status)

    active_providers = len(db.scalars(select(AiProvider).where(AiProvider.is_active.is_(True))).all())
    active_models = len(db.scalars(select(AiModel).where(AiModel.is_active.is_(True))).all())
    checks.append(
        {
            "name": "ai",
            "status": "ok" if active_providers and active_models else "warning",
            "detail": f"{active_providers} active provider(s), {active_models} active model(s).",
        }
    )

    runtime = RuntimeConfigService().public_view()
    checks.append(
        {
            "name": "wazuh",
            "status": "ok",
            "detail": "Webhook intake is available. Outbound Wazuh credentials are optional.",
            "metadata": runtime.get("wazuh", {}),
        }
    )
    checks.append(
        {
            "name": "velociraptor",
            "status": "ok" if runtime.get("velociraptor", {}).get("mode") == "mock" else "warning",
            "detail": f"Mode: {runtime.get('velociraptor', {}).get('mode', 'unknown')}.",
            "metadata": runtime.get("velociraptor", {}),
        }
    )

    alert_count = len(db.scalars(select(Alert.id)).all())
    incident_count = len(db.scalars(select(Incident.id)).all())
    return {
        "status": "ok" if all(item["status"] != "error" for item in checks) else "error",
        "checks": checks,
        "counts": {"alerts": alert_count, "incidents": incident_count},
        "production_readiness": _readiness_score(checks),
    }


def _migration_status(db: Session) -> dict:
    try:
        current = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        current = None
    expected = "20260416_0003"
    if current == expected:
        return {"name": "migrations", "status": "ok", "detail": f"Database schema is current ({current})."}
    return {"name": "migrations", "status": "warning", "detail": f"Current migration is {current or 'missing'}, expected {expected}."}


def _security_status() -> dict:
    findings = []
    if settings.environment.lower() in {"production", "prod"} and not settings.internal_api_key:
        findings.append("INTERNAL_API_KEY missing in production")
    if not SecretManager().enabled:
        findings.append("SECRETS_ENCRYPTION_KEY is not configured; new secrets are stored in plain text")
    if settings.debug:
        findings.append("debug mode is enabled")
    if "*" in settings.allowed_hosts:
        findings.append("allowed_hosts contains wildcard")
    if settings.rate_limit_per_minute <= 0:
        findings.append("rate limiting is disabled")
    status = "ok" if not findings else "warning"
    return {
        "name": "security",
        "status": status,
        "detail": "Security baseline checks passed." if not findings else "; ".join(findings),
        "metadata": {
            "environment": settings.environment,
            "secret_encryption_enabled": SecretManager().enabled,
            "internal_api_key_configured": bool(settings.internal_api_key),
            "debug": settings.debug,
        },
    }


def _readiness_score(checks: list[dict]) -> dict:
    score = 100
    for item in checks:
        if item["status"] == "warning":
            score -= 10
        if item["status"] == "error":
            score -= 30
    score = max(0, score)
    return {
        "score": score,
        "level": "production_baseline" if score >= 80 else "needs_attention",
    }
