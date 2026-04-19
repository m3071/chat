from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.connectors.velociraptor import VelociraptorConnector
from app.models.entities import CommandAudit, Evidence, Incident, Job
from app.services.timeline import add_timeline_event


class TriageService:
    def __init__(self) -> None:
        self.connector = VelociraptorConnector()

    def execute_triage(self, db: Session, *, incident: Incident, audit: CommandAudit, requested_by: str) -> tuple[Job, Evidence]:
        if incident.asset is None:
            raise ValueError("Incident has no linked asset.")

        triage_type = audit.action_payload["triage_type"]
        job = Job(
            job_type=triage_type,
            status="running",
            priority="normal",
            requested_by=requested_by,
            asset_id=incident.asset_id,
            incident_id=incident.id,
            input_payload=audit.action_payload,
            started_at=datetime.now(UTC),
        )
        db.add(job)
        db.flush()

        add_timeline_event(
            db,
            incident_id=incident.id,
            event_type="triage_started",
            actor_type="user",
            actor_id=requested_by,
            title=f"Triage started: {triage_type}",
            description="Velociraptor artifact execution started.",
            metadata={"job_id": str(job.id)},
        )

        try:
            run = self.connector.run_artifact(str(incident.asset.external_id), triage_type, {"incident_id": str(incident.id)})
            job.status = "completed"
            job.output_payload = {"flow_id": run.flow_id, "results": run.results}
            job.finished_at = datetime.now(UTC)

            evidence = Evidence(
                incident_id=incident.id,
                asset_id=incident.asset_id,
                source="velociraptor",
                evidence_type=triage_type,
                title=f"{triage_type.replace('_', ' ').title()} results",
                summary=f"Velociraptor {triage_type} completed with {len(run.results.get('rows', []))} rows.",
                content_json=run.results,
                content_text=str(run.results),
                collected_at=datetime.now(UTC),
            )
            db.add(evidence)
            db.flush()

            add_timeline_event(
                db,
                incident_id=incident.id,
                event_type="evidence_added",
                actor_type="system",
                actor_id=run.flow_id,
                title="Evidence added",
                description=f"Stored {evidence.title}.",
                metadata={"job_id": str(job.id), "evidence_id": str(evidence.id)},
            )
            add_timeline_event(
                db,
                incident_id=incident.id,
                event_type="triage_completed",
                actor_type="system",
                actor_id=run.flow_id,
                title=f"Triage completed: {triage_type}",
                description="Evidence stored from Velociraptor results.",
                metadata={"job_id": str(job.id), "evidence_id": str(evidence.id)},
            )
            from app.services.evidence_analysis_service import EvidenceAnalysisService
            from app.services.incident_analysis_service import IncidentAnalysisService

            EvidenceAnalysisService().summarize_evidence(db, evidence.id)
            IncidentAnalysisService().analyze_incident(db, incident.id)
            return job, evidence
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.now(UTC)
            add_timeline_event(
                db,
                incident_id=incident.id,
                event_type="triage_failed",
                actor_type="system",
                title=f"Triage failed: {triage_type}",
                description=str(exc),
                metadata={"job_id": str(job.id)},
            )
            raise
