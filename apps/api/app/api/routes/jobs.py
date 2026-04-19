from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_internal_api_key
from app.db.session import get_db
from app.models.entities import Job
from app.schemas.jobs import JobRead

router = APIRouter()


@router.get("", response_model=list[JobRead], dependencies=[Depends(require_internal_api_key)])
def list_jobs(db: Session = Depends(get_db)) -> list[Job]:
    return list(db.scalars(select(Job).order_by(Job.created_at.desc())))
