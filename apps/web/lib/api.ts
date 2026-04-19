import { AiModel, AiProvider, Alert, Diagnostics, HumanTimelineEvent, Incident, IncidentDetail, Job } from "./types";

const apiBaseUrl = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const internalApiKey = process.env.INTERNAL_API_KEY;

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(internalApiKey ? { "X-Internal-Api-Key": internalApiKey } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed for ${path}`);
  }

  return response.json() as Promise<T>;
}

export function getAlerts(): Promise<Alert[]> {
  return apiFetch("/api/alerts");
}

export function getIncidents(): Promise<Incident[]> {
  return apiFetch("/api/incidents");
}

export function getIncident(id: string): Promise<IncidentDetail> {
  return apiFetch(`/api/incidents/${id}`);
}

export function getIncidentTimeline(id: string): Promise<HumanTimelineEvent[]> {
  return apiFetch(`/api/incidents/${id}/timeline`);
}

export function getJobs(): Promise<Job[]> {
  return apiFetch("/api/jobs");
}

export function getAiProviders(): Promise<AiProvider[]> {
  return apiFetch("/api/ai/providers");
}

export function getAiModels(): Promise<AiModel[]> {
  return apiFetch("/api/ai/models");
}

export function getDiagnostics(): Promise<Diagnostics> {
  return apiFetch("/api/diagnostics");
}
