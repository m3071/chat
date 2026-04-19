export type Alert = {
  id: string;
  source: string;
  external_id: string;
  asset_id: string | null;
  severity: number;
  title: string;
  rule_id: string;
  rule_group: string;
  rule_description: string | null;
  event_time: string;
  ingested_at: string;
  status: string;
};

export type Evidence = {
  id: string;
  incident_id: string | null;
  asset_id: string | null;
  source: string;
  evidence_type: string;
  title: string;
  summary: string | null;
  content_json: Record<string, unknown> | null;
  content_pretty: string | null;
  content_text: string | null;
  collected_at: string | null;
  created_at: string;
};

export type TimelineEvent = {
  id: string;
  event_type: string;
  actor_type: string;
  actor_id: string | null;
  title: string;
  description: string | null;
  event_metadata: Record<string, unknown> | null;
  event_time: string;
  created_at: string;
};

export type HumanTimelineEvent = {
  id: string;
  event_type: string;
  timestamp: string;
  title: string;
  description: string | null;
  actor_type: string;
  actor_id: string | null;
  metadata: Record<string, unknown> | null;
};

export type Incident = {
  id: string;
  title: string;
  summary: string | null;
  severity: number;
  risk_level: string;
  confidence: number;
  status: string;
  asset_id: string | null;
  opened_at: string;
  closed_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type IncidentDetail = Incident & {
  alerts: Alert[];
  evidence: Evidence[];
  timeline: TimelineEvent[];
};

export type Job = {
  id: string;
  job_type: string;
  status: string;
  requested_by: string;
  created_at: string;
};

export type AiProvider = {
  id: string;
  name: string;
  label: string;
  base_url: string;
  has_api_key: boolean;
  is_active: boolean;
};

export type AiModel = {
  id: string;
  provider_id: string;
  provider_name: string;
  model_name: string;
  label: string;
  purpose: string[];
  supports_tools: boolean;
  supports_vision: boolean;
  is_default: boolean;
  is_active: boolean;
};

export type Diagnostics = {
  status: string;
  counts: { alerts: number; incidents: number };
  production_readiness?: { score: number; level: string };
  checks: Array<{
    name: string;
    status: "ok" | "warning" | "error";
    detail: string;
    metadata?: Record<string, unknown>;
  }>;
};
