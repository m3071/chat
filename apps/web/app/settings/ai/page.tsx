import { AiSettingsPanel } from "../../../components/AiSettingsPanel";
import { getAiModels, getAiProviders } from "../../../lib/api";

export default async function AiSettingsPage() {
  const [providers, models] = await Promise.all([getAiProviders(), getAiModels()]);

  return (
    <div className="stack">
      <div className="card">
        <p className="muted">AI Configuration</p>
        <h1>Providers and Models</h1>
        <p>
          Configure one API key per provider, then attach multiple models by purpose:
          chat, summary, and triage_explanation.
        </p>
      </div>
      <AiSettingsPanel initialProviders={providers} initialModels={models} />
    </div>
  );
}
