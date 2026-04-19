import Link from "next/link";

import { getAlerts, getIncidents, getJobs } from "../lib/api";

export default async function HomePage() {
  const [alerts, incidents, jobs] = await Promise.all([getAlerts(), getIncidents(), getJobs()]);

  return (
    <div className="stack">
      <section className="hero">
        <div className="card">
          <p className="muted">Cyber ChatOps MVP</p>
          <h1>Fast path from Wazuh alert to triage evidence and AI summary.</h1>
          <p>
            This demo keeps the architecture intentionally narrow: webhook intake, incident tracking, auditable
            triage actions, and a constrained chat interface.
          </p>
        </div>
        <div className="card stack">
          <div>
            <strong>{alerts.length}</strong>
            <div className="muted">alerts</div>
          </div>
          <div>
            <strong>{incidents.length}</strong>
            <div className="muted">incidents</div>
          </div>
          <div>
            <strong>{jobs.length}</strong>
            <div className="muted">jobs</div>
          </div>
        </div>
      </section>

      <section className="two-col">
        <div className="card">
          <h2>Demo Flow</h2>
          <div className="list">
            <div className="item">1. POST a sample Wazuh alert to the backend.</div>
            <div className="item">2. Review the generated alert and incident in the UI.</div>
            <div className="item">3. Request process or autoruns triage and confirm execution.</div>
            <div className="item">4. Ask chat for an incident or evidence summary.</div>
          </div>
        </div>
        <div className="card">
          <h2>Shortcuts</h2>
          <div className="list">
            <Link className="item" href="/alerts">Open alerts queue</Link>
            <Link className="item" href="/incidents">Open incident workbench</Link>
            <Link className="item" href="/chat">Open constrained chat</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
