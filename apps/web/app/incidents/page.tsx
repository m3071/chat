import Link from "next/link";

import { DemoIncidentButton } from "../../components/DemoIncidentButton";
import { SeverityBadge } from "../../components/SeverityBadge";
import { getIncidents } from "../../lib/api";

export default async function IncidentsPage() {
  const incidents = await getIncidents();

  return (
    <div className="card">
      <div className="page-heading">
        <div>
          <h1>Incidents</h1>
          <p className="muted">Generate a demo incident if you want to test the full flow instantly.</p>
        </div>
        <DemoIncidentButton />
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Opened</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id}>
              <td>
                <Link href={`/incidents/${incident.id}`}>{incident.title}</Link>
              </td>
              <td><SeverityBadge severity={incident.severity} /></td>
              <td><span className="badge">{incident.status}</span></td>
              <td>{new Date(incident.opened_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
