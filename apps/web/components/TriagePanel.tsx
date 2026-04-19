"use client";

import { useState, useTransition } from "react";

type Props = {
  incidentId: string;
};

export function TriagePanel({ incidentId }: Props) {
  const [triageType, setTriageType] = useState<"process_triage" | "autoruns_triage">("process_triage");
  const [requestId, setRequestId] = useState<string | null>(null);
  const [message, setMessage] = useState<string>("No pending action.");
  const [isPending, startTransition] = useTransition();

  async function requestTriage() {
    startTransition(async () => {
      const response = await fetch("/api/triage/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incident_id: incidentId, triage_type: triageType, requested_by: "demo-user" }),
      });
      const data = await response.json();
      setRequestId(data.command_audit_id);
      setMessage(data.confirmation_message);
    });
  }

  async function confirmTriage() {
    if (!requestId) {
      return;
    }
    startTransition(async () => {
      const response = await fetch("/api/triage/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_audit_id: requestId, approved_by: "demo-user" }),
      });
      const data = await response.json();
      setMessage(`Executed job ${data.job_id} and stored evidence ${data.evidence_id}.`);
      setRequestId(null);
    });
  }

  return (
    <div className="card stack">
      <div>
        <h3>Host Triage</h3>
        <p className="muted">All write actions stay behind an explicit approval step.</p>
      </div>
      <select className="select" value={triageType} onChange={(event) => setTriageType(event.target.value as typeof triageType)}>
        <option value="process_triage">Process triage</option>
        <option value="autoruns_triage">Autoruns/startup triage</option>
      </select>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button className="button" onClick={requestTriage} disabled={isPending}>
          Request triage
        </button>
        <button className="button secondary" onClick={confirmTriage} disabled={isPending || !requestId}>
          Confirm execution
        </button>
      </div>
      <p className="muted">{message}</p>
    </div>
  );
}
