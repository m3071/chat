from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_internal_api_key
from app.db.session import get_db
from app.models.entities import Alert
from app.schemas.alerts import AlertRead

router = APIRouter()


@router.get("", response_model=list[AlertRead], dependencies=[Depends(require_internal_api_key)])
def list_alerts(db: Session = Depends(get_db)) -> list[Alert]:
    return list(db.scalars(select(Alert).order_by(Alert.ingested_at.desc())))


@router.get("/{alert_id}", response_model=AlertRead, dependencies=[Depends(require_internal_api_key)])
def get_alert(alert_id: UUID, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert
