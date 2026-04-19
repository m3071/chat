import { getAlerts } from "../../lib/api";
import { SeverityBadge } from "../../components/SeverityBadge";

export default async function AlertsPage() {
  const alerts = await getAlerts();

  return (
    <div className="card">
      <h1>Recent Alerts</h1>
      <table className="table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Severity</th>
            <th>Rule</th>
            <th>Source</th>
            <th>Event Time</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id}>
              <td>{alert.title}</td>
              <td><SeverityBadge severity={alert.severity} /></td>
              <td>{alert.rule_group} / {alert.rule_id}</td>
              <td>{alert.source}</td>
              <td>{new Date(alert.event_time).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
