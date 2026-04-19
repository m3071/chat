from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.models.entities import Incident
from app.services.incident_service import IncidentService
from app.services.timeline import add_timeline_event


@dataclass
class IncidentAnalysis:
    summary: str
    risk_level: str
    confidence: float
    recommended_actions: list[str]


class IncidentAnalysisService:
    def __init__(self) -> None:
        self.incidents = IncidentService()
        self.ai = AIService()

    def analyze_incident(self, db: Session, incident_id: UUID) -> dict:
        incident = self.incidents.get_incident_detail(db, incident_id)
        if incident is None:
            raise ValueError("Incident not found.")

        fallback = self._rule_based_analysis(incident)
        prompt = self._build_prompt(db, incident)
        response = self.ai.generate_for_purpose(
            db,
            purpose="summary",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyze the incident and return only compact JSON with keys: "
                        "summary, risk_level, confidence, recommended_actions."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            fallback_text=json.dumps(fallback.__dict__),
        )

        analysis = self._parse_or_fallback(response, fallback)
        incident.summary = analysis.summary
        incident.risk_level = analysis.risk_level
        incident.confidence = analysis.confidence
        db.flush()

        add_timeline_event(
            db,
            incident_id=incident.id,
            event_type="ai_summary_generated",
            actor_type="ai",
            actor_id="summary",
            title="AI summary generated",
            description=analysis.summary,
            metadata={
                "risk_level": analysis.risk_level,
                "confidence": analysis.confidence,
                "recommended_actions": analysis.recommended_actions,
            },
        )
        db.flush()
        return analysis.__dict__

    def _build_prompt(self, db: Session, incident: Incident) -> str:
        alert_highlights = [
            {
                "title": link.alert.title,
                "severity": link.alert.severity,
                "rule_id": link.alert.rule_id,
                "rule_group": link.alert.rule_group,
                "description": link.alert.rule_description,
            }
            for link in incident.alert_links[:5]
        ]
        evidence_highlights = [
            {
                "title": item.title,
                "type": item.evidence_type,
                "summary": item.summary,
            }
            for item in incident.evidence_items[:5]
        ]
        return json.dumps(
            {
                "incident": {
                    "title": incident.title,
                    "severity": incident.severity,
                    "status": incident.status,
                    "asset": incident.asset.hostname if incident.asset else None,
                },
                "linked_alerts": alert_highlights,
                "evidence_highlights": evidence_highlights,
                "related_incidents": self._related_context(db, incident),
            },
            indent=2,
        )

    def _related_context(self, db: Session, incident: Incident) -> list[dict]:
        return [
            {
                "title": item.title,
                "summary": item.summary,
                "risk_level": item.risk_level,
                "evidence_summaries": [evidence.summary for evidence in item.evidence_items if evidence.summary],
            }
            for item in self.incidents.get_related_incidents(db, incident.id, limit=3)
        ]

    def _rule_based_analysis(self, incident: Incident) -> IncidentAnalysis:
        evidence_count = len(incident.evidence_items)
        alert_count = len(incident.alert_links)
        suspicious_text = " ".join(
            [
                incident.title or "",
                *(link.alert.title or "" for link in incident.alert_links),
                *(item.summary or "" for item in incident.evidence_items),
                *(item.content_text or "" for item in incident.evidence_items),
            ]
        ).lower()
        has_suspicious_process = any(keyword in suspicious_text for keyword in ["powershell", "cmd.exe", "suspicious process", "process"])
        risk_score = incident.severity + (2 if has_suspicious_process else 0)
        if risk_score > 6:
            risk_level = "high"
            confidence = 0.82 if evidence_count else 0.72
        elif risk_score >= 4:
            risk_level = "medium"
            confidence = 0.68 if evidence_count else 0.58
        else:
            risk_level = "low"
            confidence = 0.55

        actions = ["Review linked Wazuh alerts", "Validate host context and affected asset"]
        if evidence_count:
            actions.append("Review collected Velociraptor evidence")
        if risk_level == "high":
            actions.append("Prioritize containment decision")
        else:
            actions.append("Continue monitoring and collect triage if needed")

        latest_evidence = incident.evidence_items[-1].summary if incident.evidence_items else "No evidence collected yet."
        return IncidentAnalysis(
            summary=(
                f"{incident.title} is open with severity {incident.severity}, "
                f"{alert_count} linked alert(s), and {evidence_count} evidence item(s). "
                f"Latest evidence: {latest_evidence}"
            ),
            risk_level=risk_level,
            confidence=confidence,
            recommended_actions=actions,
        )

    def _parse_or_fallback(self, response: str, fallback: IncidentAnalysis) -> IncidentAnalysis:
        try:
            payload = json.loads(response)
            risk_level = str(payload.get("risk_level", fallback.risk_level)).lower()
            if risk_level not in {"low", "medium", "high"}:
                risk_level = fallback.risk_level
            confidence = float(payload.get("confidence", fallback.confidence))
            confidence = max(0.0, min(1.0, confidence))
            recommended = payload.get("recommended_actions", fallback.recommended_actions)
            if not isinstance(recommended, list) or not all(isinstance(item, str) for item in recommended):
                recommended = fallback.recommended_actions
            summary = str(payload.get("summary") or fallback.summary)
            return IncidentAnalysis(
                summary=summary,
                risk_level=risk_level,
                confidence=confidence,
                recommended_actions=recommended,
            )
        except Exception:
            return fallback
