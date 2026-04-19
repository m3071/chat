"use client";

import { useState, useTransition } from "react";

type Props = {
  incidents: Array<{ id: string; title: string }>;
};

export function ChatConsole({ incidents }: Props) {
  const [incidentId, setIncidentId] = useState<string>(incidents[0]?.id ?? "");
  const [message, setMessage] = useState("Summarize this incident");
  const [reply, setReply] = useState("No conversation yet.");
  const [pendingAuditId, setPendingAuditId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  async function sendMessage() {
    startTransition(async () => {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, incident_id: incidentId, user_id: "demo-user" }),
      });
      const data = await response.json();
      setReply(data.response);
      setPendingAuditId(data.command_audit_id ?? null);
    });
  }

  async function confirm() {
    if (!pendingAuditId) {
      return;
    }
    startTransition(async () => {
      const response = await fetch("/api/triage/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_audit_id: pendingAuditId, approved_by: "demo-user" }),
      });
      const data = await response.json();
      setReply(`Confirmed. Job ${data.job_id} completed and evidence ${data.evidence_id} was stored.`);
      setPendingAuditId(null);
    });
  }

  return (
    <div className="card stack">
      <label>
        Incident
        <select className="select" value={incidentId} onChange={(event) => setIncidentId(event.target.value)}>
          {incidents.map((incident) => (
            <option key={incident.id} value={incident.id}>
              {incident.title}
            </option>
          ))}
        </select>
      </label>
      <label>
        Message
        <textarea className="textarea" rows={5} value={message} onChange={(event) => setMessage(event.target.value)} />
      </label>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button className="button" onClick={sendMessage} disabled={isPending || !incidentId}>
          Send
        </button>
        <button className="button secondary" onClick={confirm} disabled={isPending || !pendingAuditId}>
          Confirm pending write
        </button>
      </div>
      <div className="item">
        <strong>Assistant</strong>
        <p>{reply}</p>
      </div>
    </div>
  );
}
