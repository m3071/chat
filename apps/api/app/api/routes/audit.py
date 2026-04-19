from __future__ import annotations

import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_internal_api_key
from app.db.session import get_db
from app.models.entities import CommandAudit

router = APIRouter(dependencies=[Depends(require_internal_api_key)])


@router.get("/commands")
def list_command_audit(limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    audits = db.scalars(select(CommandAudit).order_by(CommandAudit.created_at.desc()).limit(min(limit, 500))).all()
    return [_audit_read(item) for item in audits]


@router.get("/commands/export")
def export_command_audit(format: str = "json", limit: int = 500, db: Session = Depends(get_db)):
    audits = db.scalars(select(CommandAudit).order_by(CommandAudit.created_at.desc()).limit(min(limit, 5000))).all()
    rows = [_audit_read(item) for item in audits]
    if format.lower() == "csv":
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "id",
                "user_id",
                "risk_level",
                "action_type",
                "approval_status",
                "executed",
                "executed_at",
                "result_summary",
                "created_at",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})
        return PlainTextResponse(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="command-audit.csv"'},
        )
    return JSONResponse(rows, headers={"Content-Disposition": 'attachment; filename="command-audit.json"'})


@router.get("/commands/{audit_id}")
def get_command_audit(audit_id: UUID, db: Session = Depends(get_db)) -> dict:
    audit = db.get(CommandAudit, audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="Command audit not found.")
    return _audit_read(audit, include_payload=True)


def _audit_read(audit: CommandAudit, include_payload: bool = False) -> dict:
    payload = {
        "id": str(audit.id),
        "user_id": audit.user_id,
        "command_text": audit.command_text,
        "risk_level": audit.risk_level,
        "action_type": audit.action_type,
        "approval_status": audit.approval_status,
        "executed": audit.executed,
        "executed_at": audit.executed_at.isoformat() if audit.executed_at else None,
        "result_summary": audit.result_summary,
        "created_at": audit.created_at.isoformat(),
    }
    if include_payload:
        payload["parsed_intent"] = audit.parsed_intent
        payload["action_payload"] = audit.action_payload
    return payload
