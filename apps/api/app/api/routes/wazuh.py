from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.connectors.wazuh import WazuhConnector
from app.core.runtime_config import RuntimeConfigService
from app.core.security import require_internal_api_key, require_wazuh_shared_secret
from app.db.session import get_db
from app.schemas.common import ApiMessage
from app.schemas.wazuh import WazuhAlertPayload, WazuhConnectRequest
from app.services.incident_service import IncidentService

router = APIRouter()
connector = WazuhConnector()
service = IncidentService()
runtime_config = RuntimeConfigService()


@router.post("/alerts", response_model=ApiMessage, dependencies=[Depends(require_wazuh_shared_secret)])
def ingest_alert(payload: WazuhAlertPayload, db: Session = Depends(get_db)) -> ApiMessage:
    normalized = connector.normalize_alert(payload)
    existing_alert = service.get_alert_by_external_id(db, source="wazuh", external_id=normalized.external_id)
    if existing_alert is not None:
        return ApiMessage(message="Alert already ingested.")
    service.create_alert_and_incident(db, normalized, payload.model_dump(mode="json"))
    db.commit()
    return ApiMessage(message="Alert ingested successfully.")


@router.post("/sync", response_model=ApiMessage, dependencies=[Depends(require_internal_api_key)])
def sync_indexer_alerts(limit: int = 25, db: Session = Depends(get_db)) -> ApiMessage:
    imported = 0
    skipped = 0
    for payload in connector.fetch_recent_alerts(limit=limit):
        normalized = connector.normalize_alert(payload)
        existing_alert = service.get_alert_by_external_id(db, source="wazuh", external_id=normalized.external_id)
        if existing_alert is not None:
            skipped += 1
            continue
        service.create_alert_and_incident(db, normalized, payload.model_dump(mode="json"))
        imported += 1
    db.commit()
    return ApiMessage(message=f"Wazuh indexer sync completed. imported={imported} skipped={skipped}")


@router.post("/connect", dependencies=[Depends(require_internal_api_key)])
def connect_wazuh(payload: WazuhConnectRequest, db: Session = Depends(get_db)) -> dict:
    runtime_config.update_section(
        "wazuh",
        {
            "webhook_secret": payload.webhook_secret,
            "manager_url": payload.manager_url,
            "api_url": payload.api_url or payload.manager_url,
            "api_username": payload.api_username,
            "api_password": payload.api_password,
            "indexer_url": payload.indexer_url,
            "indexer_username": payload.indexer_username,
            "indexer_password": payload.indexer_password,
            "indexer_alert_index": payload.indexer_alert_index or "wazuh-alerts-*",
            "verify_tls": payload.verify_tls,
        },
    )
    test_result = connector.test_connection()
    imported = 0
    skipped = 0
    if payload.sync_alerts and payload.indexer_url:
        for alert_payload in connector.fetch_recent_alerts(limit=payload.sync_limit):
            normalized = connector.normalize_alert(alert_payload)
            existing_alert = service.get_alert_by_external_id(db, source="wazuh", external_id=normalized.external_id)
            if existing_alert is not None:
                skipped += 1
                continue
            service.create_alert_and_incident(db, normalized, alert_payload.model_dump(mode="json"))
            imported += 1
        db.commit()
    return {
        "ok": True,
        "message": "Wazuh connected successfully.",
        "test": test_result,
        "sync": {"imported": imported, "skipped": skipped, "enabled": payload.sync_alerts and bool(payload.indexer_url)},
    }
