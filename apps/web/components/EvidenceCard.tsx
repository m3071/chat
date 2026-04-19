"use client";

import { Evidence } from "../lib/types";

export function EvidenceCard({ evidence }: { evidence: Evidence }) {
  const content = evidence.content_pretty ?? JSON.stringify(evidence.content_json ?? {}, null, 2);

  function copyJson() {
    navigator.clipboard.writeText(content);
  }

  function downloadJson() {
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${evidence.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "evidence"}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <details className="item evidence-card">
      <summary>
        <strong>{evidence.title}</strong>
        <span className="badge">{evidence.evidence_type}</span>
      </summary>
      <p>{evidence.summary ?? "No summary"}</p>
      <div className="button-row">
        <button className="button ghost" onClick={copyJson} type="button">Copy JSON</button>
        <button className="button ghost" onClick={downloadJson} type="button">Download JSON</button>
      </div>
      {content ? <pre className="json-block">{content}</pre> : null}
    </details>
  );
}
