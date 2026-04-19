"use client";

import { useState } from "react";

const actions = [
  { action_type: "run_triage", label: "Run Triage" },
  { action_type: "collect_processes", label: "Collect Processes" },
  { action_type: "check_persistence", label: "Check Persistence" },
];

export function QuickActions({ incidentId }: { incidentId: string }) {
  const [message, setMessage] = useState("");
  const [auditId, setAuditId] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  async function trigger(actionType: string) {
    setLoading(actionType);
    setMessage("");
    const response = await fetch(`/api/incidents/${incidentId}/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_type: actionType }),
    });
    const data = await response.json();
    setLoading(null);
    setAuditId(data.command_audit_id ?? null);
    setMessage(data.confirmation_message ?? "Action requested. Confirm it from the triage/chat flow before execution.");
  }

  async function confirm() {
    if (!auditId) {
      return;
    }
    setLoading("confirm");
    const response = await fetch("/api/triage/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command_audit_id: auditId, approved_by: "demo-user" }),
    });
    const data = await response.json();
    setLoading(null);
    if (response.ok) {
      setAuditId(null);
      setMessage(`Executed job ${data.job_id} and stored evidence ${data.evidence_id}. Refresh to see new evidence.`);
      return;
    }
    setMessage(data.detail ?? "Could not confirm action.");
  }

  return (
    <div className="card">
      <h2>Quick Actions</h2>
      <p className="muted">Actions create an approval request first; execution still needs explicit confirmation.</p>
      <div className="button-row">
        {actions.map((action) => (
          <button
            className="button ghost"
            disabled={loading !== null}
            key={action.action_type}
            onClick={() => trigger(action.action_type)}
            type="button"
          >
            {loading === action.action_type ? "Requesting..." : action.label}
          </button>
        ))}
      </div>
      <button className="button secondary" disabled={!auditId || loading !== null} onClick={confirm} type="button">
        {loading === "confirm" ? "Executing..." : "Confirm Selected Action"}
      </button>
      {message ? <p className="muted">{message}</p> : null}
    </div>
  );
}
