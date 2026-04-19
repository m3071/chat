"use client";

import { useState } from "react";
import { AiModel, AiProvider } from "../lib/types";

export function AiSettingsPanel({ initialProviders, initialModels }: { initialProviders: AiProvider[]; initialModels: AiModel[] }) {
  const [providers, setProviders] = useState(initialProviders);
  const [models, setModels] = useState(initialModels);
  const [message, setMessage] = useState("");

  async function refresh() {
    const [providerResponse, modelResponse] = await Promise.all([fetch("/api/ai/providers"), fetch("/api/ai/models")]);
    setProviders(await providerResponse.json());
    setModels(await modelResponse.json());
  }

  async function createProvider(formData: FormData) {
    setMessage("");
    const response = await fetch("/api/ai/providers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: String(formData.get("name") ?? ""),
        label: String(formData.get("label") ?? ""),
        base_url: String(formData.get("base_url") ?? ""),
        api_key: String(formData.get("api_key") ?? "") || null,
        is_active: true,
      }),
    });
    const data = await response.json();
    setMessage(response.ok ? "Provider saved. API key stayed backend-only." : data.detail ?? "Provider save failed.");
    if (response.ok) await refresh();
  }

  async function createModel(formData: FormData) {
    setMessage("");
    const response = await fetch("/api/ai/models", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider_id: String(formData.get("provider_id") ?? ""),
        model_name: String(formData.get("model_name") ?? ""),
        label: String(formData.get("label") ?? ""),
        purpose: String(formData.get("purpose") ?? "").split(",").map((item) => item.trim()).filter(Boolean),
        supports_tools: formData.get("supports_tools") === "on",
        supports_vision: formData.get("supports_vision") === "on",
        is_default: formData.get("is_default") === "on",
        is_active: true,
      }),
    });
    const data = await response.json();
    setMessage(response.ok ? "Model saved and ready for purpose routing." : data.detail ?? "Model save failed.");
    if (response.ok) await refresh();
  }

  return (
    <div className="stack">
      <div className="two-col">
        <form className="card stack" action={createProvider}>
          <h2>Add AI Provider</h2>
          <input className="input" name="name" placeholder="openai / openrouter / ollama" required />
          <input className="input" name="label" placeholder="Provider label" required />
          <input className="input" name="base_url" placeholder="https://api.openai.com/v1" required />
          <input className="input" name="api_key" placeholder="API key (server-side only)" type="password" />
          <button className="button" type="submit">Save Provider</button>
          <p className="muted">Raw API keys are never returned to the browser after save.</p>
        </form>

        <form className="card stack" action={createModel}>
          <h2>Add Model</h2>
          <select className="select" name="provider_id" required>
            <option value="">Select provider</option>
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id}>{provider.label}</option>
            ))}
          </select>
          <input className="input" name="model_name" placeholder="gpt-5-mini / llama3.1:8b" required />
          <input className="input" name="label" placeholder="Display label" required />
          <input className="input" name="purpose" placeholder="chat,summary,triage_explanation" required />
          <label><input name="supports_tools" type="checkbox" /> Supports tools</label>
          <label><input name="supports_vision" type="checkbox" /> Supports vision</label>
          <label><input name="is_default" type="checkbox" /> Default for matching purpose</label>
          <button className="button" type="submit">Save Model</button>
        </form>
      </div>

      {message ? <div className="item">{message}</div> : null}

      <div className="two-col">
        <div className="card">
          <h2>Providers</h2>
          <div className="list">
            {providers.map((provider) => (
              <div className="item" key={provider.id}>
                <strong>{provider.label}</strong>
                <p className="muted">{provider.name} · {provider.base_url}</p>
                <span className="badge">{provider.has_api_key ? "API key configured" : "No API key"}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h2>Models</h2>
          <div className="list">
            {models.map((model) => (
              <div className="item" key={model.id}>
                <strong>{model.label}</strong>
                <p className="muted">{model.provider_name} · {model.model_name}</p>
                <p>{model.purpose.join(", ")}</p>
                <span className="badge">{model.is_default ? "default" : "fallback"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
