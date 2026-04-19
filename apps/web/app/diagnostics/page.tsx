import { DiagnosticsPanel } from "../../components/DiagnosticsPanel";
import { getDiagnostics } from "../../lib/api";

export default async function DiagnosticsPage() {
  const diagnostics = await getDiagnostics();

  return (
    <div className="stack">
      <div className="card">
        <p className="muted">System Diagnostics</p>
        <h1>CyberRed Health</h1>
        <p>Check database, integrations, AI routing, and object counts from one place.</p>
      </div>
      <DiagnosticsPanel initialDiagnostics={diagnostics} />
    </div>
  );
}
