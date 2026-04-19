from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.models.entities import Evidence
from app.services.timeline import add_timeline_event


class EvidenceAnalysisService:
    def __init__(self) -> None:
        self.ai = AIService()

    def summarize_evidence(self, db: Session, evidence_id: UUID) -> str:
        evidence = db.scalar(select(Evidence).where(Evidence.id == evidence_id))
        if evidence is None:
            raise ValueError("Evidence not found.")

        prompt = json.dumps(
            {
                "title": evidence.title,
                "source": evidence.source,
                "evidence_type": evidence.evidence_type,
                "key_fields": self._safe_highlights(evidence),
            },
            indent=2,
        )
        fallback = evidence.summary or f"{evidence.title} from {evidence.source} is available for review."
        summary = self.ai.generate_for_purpose(
            db,
            purpose="summary",
            messages=[
                {"role": "system", "content": "Summarize cyber evidence in one concise analyst-friendly paragraph."},
                {"role": "user", "content": prompt},
            ],
            fallback_text=fallback,
        )
        evidence.summary = summary
        db.flush()
        if evidence.incident_id:
            add_timeline_event(
                db,
                incident_id=evidence.incident_id,
                event_type="evidence_summarized",
                actor_type="system",
                title="Evidence summarized",
                description=summary,
                metadata={"evidence_id": str(evidence.id), "source": evidence.source},
            )
        return summary

    def _safe_highlights(self, evidence: Evidence) -> dict:
        if isinstance(evidence.content_json, dict):
            rows = evidence.content_json.get("rows")
            return {
                "row_count": len(rows) if isinstance(rows, list) else None,
                "sample": rows[:3] if isinstance(rows, list) else evidence.content_json,
            }
        return {"content_text": (evidence.content_text or "")[:1000]}
