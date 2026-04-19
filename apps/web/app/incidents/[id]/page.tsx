import { QuickActions } from "../../../components/QuickActions";
import { EvidenceCard } from "../../../components/EvidenceCard";
import { TriagePanel } from "../../../components/TriagePanel";
import { getIncident, getIncidentTimeline } from "../../../lib/api";

export default async function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const incident = await getIncident(id);
  const timeline = await getIncidentTimeline(id);

  return (
    <div className="stack">
      <div className="card">
        <p className="muted">Incident Detail</p>
        <h1>{incident.title}</h1>
        <p>{incident.summary ?? "No summary recorded yet."}</p>
        <p className="muted">Risk: {incident.risk_level} · Confidence: {Math.round(incident.confidence * 100)}%</p>
        <div className="button-row">
          <a className="button ghost" href={`/api/incidents/${incident.id}/report?format=md`}>Export Markdown</a>
          <a className="button ghost" href={`/api/incidents/${incident.id}/report?format=json`}>Export JSON</a>
        </div>
      </div>

      <div className="two-col">
        <div className="stack">
          <div className="card">
            <h2>Linked Alerts</h2>
            <div className="list">
              {incident.alerts.map((alert) => (
                <div className="item" key={alert.id}>
                  <strong>{alert.title}</strong>
                  <p className="muted">{alert.rule_group} / {alert.rule_id}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2>Evidence</h2>
            <div className="list">
              {incident.evidence.length === 0 ? (
                <div className="item">No evidence collected yet.</div>
              ) : (
                incident.evidence.map((item) => (
                  <EvidenceCard evidence={item} key={item.id} />
                ))
              )}
            </div>
          </div>
        </div>

        <div className="stack">
          <QuickActions incidentId={incident.id} />
          <TriagePanel incidentId={incident.id} />
          <div className="card">
            <h2>Timeline</h2>
            <div className="timeline">
              {timeline.map((event) => (
                <div className="timeline-item" key={event.id}>
                  <div className="timeline-dot" />
                  <div className="item">
                    <strong>{event.title}</strong>
                    <p>{event.description ?? "No description"}</p>
                    <div className="muted">{new Date(event.timestamp).toLocaleString()} · {event.event_type}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
