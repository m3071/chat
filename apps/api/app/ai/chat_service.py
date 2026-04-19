from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.ai.tools import AiToolService
from app.schemas.chat import ChatRequest, ChatResponse


class ChatService:
    def __init__(self) -> None:
        self.tools = AiToolService()
        self.ai = AIService()

    def handle(self, db: Session, request: ChatRequest) -> ChatResponse:
        message = request.message.lower()
        incident_id = request.incident_id
        wants_summary = "summary" in message or "summarize" in message
        if ("incident" in message or "เหตุการณ์" in message) and "ล่าสุด" in message:
            incidents = self.tools.search_incidents(db, limit=1)
            if not incidents:
                return ChatResponse(mode="read", response="ยังไม่มี incident ในระบบ")
            item = incidents[0]
            return ChatResponse(
                mode="read",
                response=(
                    f"Incident ล่าสุดคือ {item['title']} "
                    f"(severity {item['severity']}, risk {item['risk_level']}, status {item['status']}). "
                    f"{item.get('summary') or ''}"
                ).strip(),
            )
        if "host" in message and ("alert สูง" in message or "สูง" in message or "high" in message):
            alerts = self.tools.list_alerts(db, min_severity=7, limit=50)
            if not alerts:
                return ChatResponse(mode="read", response="ยังไม่พบ high-severity alert ที่ผูกกับ host")
            counts = Counter(item.get("hostname") or "unknown-host" for item in alerts)
            host, count = counts.most_common(1)[0]
            return ChatResponse(mode="read", response=f"Host ที่โดน alert สูงมากที่สุดตอนนี้คือ {host} จำนวน {count} alert(s).")
        if message.startswith("asset ") or message.startswith("host "):
            hostname = request.message.split(maxsplit=1)[1].strip() if len(request.message.split(maxsplit=1)) > 1 else ""
            if hostname:
                profile = self.tools.get_asset_profile(db, hostname)
                if profile is None:
                    return ChatResponse(mode="read", response=f"ไม่พบ asset/host: {hostname}")
                return ChatResponse(
                    mode="read",
                    response=(
                        f"{profile['hostname']} มี {profile['alert_count']} alert(s), "
                        f"{profile['incident_count']} incident(s), IP: {profile['ip_addresses'] or '-'}"
                    ),
                )
        if "evidence" in message and wants_summary and incident_id:
            return ChatResponse(mode="read", response=self.tools.summarize_evidence(db, incident_id))
        if wants_summary and incident_id:
            return ChatResponse(mode="read", response=self.tools.summarize_incident(db, incident_id))
        if any(keyword in message for keyword in ["triage", "autoruns", "process"]) and incident_id:
            triage_type = "autoruns_triage" if "autoruns" in message or "startup" in message else "process_triage"
            audit = self.tools.request_host_triage(
                db,
                incident_id=incident_id,
                triage_type=triage_type,
                user_id=request.user_id,
                command_text=request.message,
            )
            return ChatResponse(
                mode="write_pending_confirmation",
                response=f"Triage request prepared for {triage_type}. Confirm before execution.",
                intent=audit.parsed_intent,
                command_audit_id=audit.id,
            )
        fallback = "Ask for an incident summary, an evidence summary, or request process/autoruns triage for a specific incident."
        response = self.ai.generate_for_purpose(
            db,
            purpose="chat",
            messages=[
                {"role": "system", "content": "You are a constrained cyber ChatOps assistant."},
                {"role": "user", "content": request.message},
            ],
            fallback_text=fallback,
        )
        return ChatResponse(
            mode="read",
            response=response,
        )
