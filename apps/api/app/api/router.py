from fastapi import APIRouter

from app.api.routes import ai, alerts, audit, chat, demo, diagnostics, incidents, jobs, settings, triage, wazuh

api_router = APIRouter()
api_router.include_router(wazuh.router, prefix="/wazuh", tags=["wazuh"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(triage.router, prefix="/triage", tags=["triage"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"])
