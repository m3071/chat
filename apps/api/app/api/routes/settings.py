from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.connectors.wazuh import WazuhConnector
from app.connectors.velociraptor import VelociraptorConnector
from app.core.runtime_config import RuntimeConfigService
from app.core.security import require_internal_api_key
from app.db.session import get_db
from app.schemas.common import ApiMessage
from app.schemas.settings import (
    ConnectionTestRequest,
    GenericIntegrationConnect,
    GenericIntegrationUpdate,
    IntegrationSettingsRead,
    SettingsCatalogRead,
    VelociraptorSettingsUpdate,
    WazuhSettingsUpdate,
)
from app.services.incident_service import IncidentService

router = APIRouter(dependencies=[Depends(require_internal_api_key)])
runtime_config = RuntimeConfigService()
incident_service = IncidentService()


@router.get("/integrations", response_model=IntegrationSettingsRead)
def get_integration_settings() -> IntegrationSettingsRead:
    return IntegrationSettingsRead(**runtime_config.public_view())


@router.get("/catalog", response_model=SettingsCatalogRead)
def get_settings_catalog() -> SettingsCatalogRead:
    return SettingsCatalogRead(**runtime_config.catalog_view())


@router.put("/integrations/wazuh", response_model=ApiMessage)
def update_wazuh_settings(payload: WazuhSettingsUpdate) -> ApiMessage:
    runtime_config.update_section("wazuh", payload.model_dump())
    return ApiMessage(message="Wazuh settings saved.")


@router.put("/integrations/velociraptor", response_model=ApiMessage)
def update_velociraptor_settings(payload: VelociraptorSettingsUpdate) -> ApiMessage:
    runtime_config.update_section("velociraptor", payload.model_dump())
    return ApiMessage(message="Velociraptor settings saved.")


@router.put("/integrations/{integration_id}/config", response_model=ApiMessage)
def update_integration_settings(integration_id: str, payload: GenericIntegrationUpdate) -> ApiMessage:
    try:
        runtime_config.update_integration(integration_id, payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiMessage(message=f"{integration_id} settings saved.")


@router.post("/integrations/{integration_id}/connect")
def connect_integration(
    integration_id: str,
    payload: GenericIntegrationConnect,
    db: Session = Depends(get_db),
) -> dict:
    integration_id = integration_id.strip().lower()
    try:
        runtime_config.update_integration(integration_id, payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if integration_id == "wazuh":
        return _connect_wazuh(payload, db)
    if integration_id == "velociraptor":
        return _connect_velociraptor()
    raise HTTPException(status_code=400, detail="Unsupported integration service.")


@router.post("/integrations/test")
def test_integration_connection(payload: ConnectionTestRequest) -> dict:
    service = payload.service.strip().lower()
    if service == "velociraptor":
        try:
            return VelociraptorConnector().test_connection()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if service == "wazuh":
        try:
            return WazuhConnector().test_connection()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail="Unsupported integration service.")


def _connect_wazuh(payload: GenericIntegrationConnect, db: Session) -> dict:
    connector = WazuhConnector()
    try:
        test_result = connector.test_connection()
        imported = 0
        skipped = 0
        if payload.sync_alerts and (payload.config.get("indexer_url") or "").strip():
            for alert_payload in connector.fetch_recent_alerts(limit=payload.sync_limit):
                normalized = connector.normalize_alert(alert_payload)
                existing_alert = incident_service.get_alert_by_external_id(
                    db,
                    source="wazuh",
                    external_id=normalized.external_id,
                )
                if existing_alert is not None:
                    skipped += 1
                    continue
                incident_service.create_alert_and_incident(db, normalized, alert_payload.model_dump(mode="json"))
                imported += 1
            db.commit()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "integration": "wazuh",
        "message": "Wazuh connected successfully.",
        "test": test_result,
        "sync": {
            "enabled": payload.sync_alerts and bool((payload.config.get("indexer_url") or "").strip()),
            "imported": imported,
            "skipped": skipped,
        },
    }


def _connect_velociraptor() -> dict:
    try:
        test_result = VelociraptorConnector().test_connection()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "integration": "velociraptor",
        "message": "Velociraptor connected successfully.",
        "test": test_result,
    }
