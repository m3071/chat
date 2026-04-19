"use client";

import { useState } from "react";
import { Diagnostics } from "../lib/types";

export function DiagnosticsPanel({ initialDiagnostics }: { initialDiagnostics: Diagnostics }) {
  const [diagnostics, setDiagnostics] = useState(initialDiagnostics);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState<string | null>(null);

  async function refresh() {
    const response = await fetch("/api/diagnostics");
    setDiagnostics(await response.json());
  }

  async function testIntegration(service: "wazuh" | "velociraptor") {
    setLoading(service);
    setMessage("");
    const response = await fetch("/api/settings/integrations/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service }),
    });
    const data = await response.json();
    setLoading(null);
    setMessage(response.ok ? `${service} test passed: ${data.detail ?? data.status ?? "ok"}` : `${service} test failed: ${data.detail}`);
    await refresh();
  }

  return (
    <div className="stack">
      <div className="card">
        <p>Overall status: <span className="badge">{diagnostics.status}</span></p>
        <p className="muted">
          Alerts: {diagnostics.counts.alerts} · Incidents: {diagnostics.counts.incidents}
        </p>
        {diagnostics.production_readiness ? (
          <p>
            Production readiness: <span className="badge">{diagnostics.production_readiness.score}/100</span>{" "}
            <span className="muted">{diagnostics.production_readiness.level}</span>
          </p>
        ) : null}
        <div className="button-row">
          <button className="button ghost" type="button" onClick={refresh}>Refresh</button>
          <button className="button ghost" type="button" disabled={loading !== null} onClick={() => testIntegration("wazuh")}>
            {loading === "wazuh" ? "Testing..." : "Test Wazuh"}
          </button>
          <button className="button ghost" type="button" disabled={loading !== null} onClick={() => testIntegration("velociraptor")}>
            {loading === "velociraptor" ? "Testing..." : "Test Velociraptor"}
          </button>
        </div>
        {message ? <p className="muted">{message}</p> : null}
      </div>

      <div className="card">
        <h2>Checks</h2>
        <div className="list">
          {diagnostics.checks.map((check) => (
            <div className="item" key={check.name}>
              <strong>{check.name}</strong>
              <span className={`badge status-${check.status}`}>{check.status}</span>
              <p>{check.detail}</p>
              {check.metadata ? <pre className="json-block">{JSON.stringify(check.metadata, null, 2)}</pre> : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
