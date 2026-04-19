from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import CommandAudit


class ApprovalPolicyService:
    def create_pending_write(
        self,
        db: Session,
        *,
        user_id: str | None,
        command_text: str,
        parsed_intent: dict,
        action_type: str,
        action_payload: dict,
        risk_level: str = "medium",
    ) -> CommandAudit:
        audit = CommandAudit(
            user_id=user_id,
            command_text=command_text,
            parsed_intent=parsed_intent,
            risk_level=risk_level,
            action_type=action_type,
            action_payload=action_payload,
            approval_status="pending",
            executed=False,
        )
        db.add(audit)
        db.flush()
        return audit

    def approve(self, db: Session, audit_id: UUID, approver: str) -> CommandAudit:
        audit = db.get(CommandAudit, audit_id)
        if audit is None:
            raise ValueError("Command audit not found.")
        if audit.executed or audit.approval_status == "executed":
            raise ValueError("Command audit was already executed.")
        if audit.approval_status != "pending":
            raise ValueError(f"Command audit is not pending; current status is {audit.approval_status}.")
        audit.approval_status = "approved"
        audit.user_id = approver
        db.flush()
        return audit

    def mark_executed(self, db: Session, audit: CommandAudit, result_summary: str) -> CommandAudit:
        audit.executed = True
        audit.executed_at = datetime.now(UTC)
        audit.approval_status = "executed"
        audit.result_summary = result_summary
        db.flush()
        return audit
