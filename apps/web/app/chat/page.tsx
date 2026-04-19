import { ChatConsole } from "../../components/ChatConsole";
import { getIncidents } from "../../lib/api";

export default async function ChatPage() {
  const incidents = await getIncidents();

  return (
    <div className="stack">
      <div className="card">
        <h1>ChatOps</h1>
        <p className="muted">
          Read actions execute immediately. Triage requests are turned into structured intent and wait for explicit confirmation.
        </p>
      </div>
      <ChatConsole incidents={incidents.map((incident) => ({ id: incident.id, title: incident.title }))} />
    </div>
  );
}
