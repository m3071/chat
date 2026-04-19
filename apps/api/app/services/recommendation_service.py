from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.models.entities import Incident
from app.services.incident_service import IncidentService


ALLOWED_ACTIONS = {
    "run_triage": {
        "label": "Run Windows Triage",
        "reason": "Collect broad host triage to establish current state.",
    },
    "collect_processes": {
        "label": "Collect Running Processes",
        "reason": "Inspect active processes related to suspicious execution.",
    },
    "check_persistence": {
        "label": "Check Persistence",
        "reason": "Review autoruns and startup locations for persistence.",
    },
}
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}


class RecommendationService:
    def __init__(self) -> None:
        self.incidents = IncidentService()
        self.ai = AIService()

    def get_recommendations(self, db: Session, incident_id: UUID) -> dict:
        incident = self.incidents.get_incident_detail(db, incident_id)
        if incident is None:
            raise ValueError("Incident not found.")

        fallback = self._fallback_recommendations(incident)
        response = self.ai.generate_for_purpose(
            db,
            purpose="triage_explanation",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Recommend incident response actions. Return only JSON shaped as "
                        "{\"suggested_actions\":[{\"action_type\":\"run_triage|collect_processes|check_persistence\","
                        "\"label\":\"...\",\"reason\":\"...\",\"risk_level\":\"low|medium|high\"}]}. "
                        "Do not invent action types."
                    ),
                },
                {"role": "user", "content": self._build_prompt(db, incident)},
            ],
            fallback_text=json.dumps(fallback),
        )
        return {"suggested_actions": self._parse_and_validate(response, fallback["suggested_actions"])}

    def _build_prompt(self, db: Session, incident: Incident) -> str:
        evidence = [
            {"title": item.title, "type": item.evidence_type, "summary": item.summary}
            for item in incident.evidence_items[:5]
        ]
        return json.dumps(
            {
                "incident_summary": incident.summary,
                "severity": incident.severity,
                "risk_level": incident.risk_level,
                "evidence_highlights": evidence,
                "related_incidents": [
                    {
                        "title": item.title,
                        "summary": item.summary,
                        "risk_level": item.risk_level,
                        "evidence_summaries": [evidence.summary for evidence in item.evidence_items if evidence.summary],
                    }
                    for item in self.incidents.get_related_incidents(db, incident.id, limit=3)
                ],
                "allowed_actions": list(ALLOWED_ACTIONS.keys()),
            },
            indent=2,
        )

    def _fallback_recommendations(self, incident: Incident) -> dict:
        actions = []
        if incident.severity >= 8 or incident.risk_level == "high":
            actions.append(self._action("run_triage", "high"))
        if any("process" in (link.alert.rule_group or "").lower() or "execution" in (link.alert.rule_group or "").lower() for link in incident.alert_links):
            actions.append(self._action("collect_processes", incident.risk_level or "medium"))
        if any("persistence" in (link.alert.rule_group or "").lower() or "autorun" in (link.alert.title or "").lower() for link in incident.alert_links):
            actions.append(self._action("check_persistence", incident.risk_level or "medium"))
        if not actions:
            actions.append(self._action("run_triage", incident.risk_level or "medium"))
        return {"suggested_actions": actions}

    def _action(self, action_type: str, risk_level: str) -> dict:
        definition = ALLOWED_ACTIONS[action_type]
        return {
            "action_type": action_type,
            "label": definition["label"],
            "reason": definition["reason"],
            "risk_level": risk_level if risk_level in ALLOWED_RISK_LEVELS else "medium",
        }

    def _parse_and_validate(self, response: str, fallback: list[dict]) -> list[dict]:
        try:
            payload = json.loads(response)
            raw_actions = payload.get("suggested_actions", [])
            if not isinstance(raw_actions, list):
                return fallback
            validated = []
            seen = set()
            for item in raw_actions:
                if not isinstance(item, dict):
                    continue
                action_type = str(item.get("action_type", "")).strip()
                if action_type not in ALLOWED_ACTIONS or action_type in seen:
                    continue
                seen.add(action_type)
                definition = ALLOWED_ACTIONS[action_type]
                risk_level = str(item.get("risk_level", "medium")).strip().lower()
                validated.append(
                    {
                        "action_type": action_type,
                        "label": str(item.get("label") or definition["label"]),
                        "reason": str(item.get("reason") or definition["reason"]),
                        "risk_level": risk_level if risk_level in ALLOWED_RISK_LEVELS else "medium",
                    }
                )
            return validated or fallback
        except Exception:
            return fallback
