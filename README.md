# Cyber ChatOps MVP

This project is a fast, open-source cyber ChatOps starter that is intentionally small enough to fork and connect quickly. It receives Wazuh alerts, stores alerts and incidents in PostgreSQL, allows a user to trigger two Velociraptor-style triage actions behind an approval step, stores resulting evidence, and exposes a constrained AI/chat summary workflow.

## Open Source Goals

- Easy to run locally with Docker Compose
- Easy to fork without understanding a huge codebase
- Easy to connect Wazuh first, then replace mock Velociraptor later
- Safe by default: connector credentials stay in the backend, and write actions require approval
- Production baseline included: health checks, runtime hardening, shared-secret protection, and safer container defaults

## What This MVP Does

- Accepts Wazuh-like JSON alerts with `POST /api/wazuh/alerts`
- Resolves or creates an asset, then creates an alert, incident, and timeline events
- Shows alerts and incidents in a minimal Next.js UI
- Allows `process_triage` and `autoruns_triage` requests from the incident page
- Requires explicit confirmation before executing write actions
- Stores triage runs as jobs and evidence
- Supports incident/evidence summaries, memory-aware recommendations, and triage intents through chat
- Includes demo mode so a user can generate a full fake incident from the UI or API

## Architecture Overview

- `apps/api`
  FastAPI modular monolith with boundaries for connectors, services, policies, AI, persistence, and API routes.
- `apps/web`
  Next.js TypeScript UI for alerts, incidents, incident detail, and chat.
- `infra/docker`
  Dockerfiles for the API and web apps.
- `sample-data`
  Demo Wazuh payloads for local testing.
- `tests`
  Critical backend integration-style tests for ingestion, triage, and chat intent flows.

## Quickstart

Fastest path:

```bash
docker compose up --build
```

On Windows, the easiest option is to run [install-and-run.bat](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/install-and-run.bat>).
It checks Docker, creates `.env` from `.env.example` if needed, and starts the stack in the background.

PowerShell version: [install-and-run.ps1](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/install-and-run.ps1>)

Then post a sample alert:

```bash
curl -X POST http://localhost:8000/api/wazuh/alerts ^
  -H "Content-Type: application/json" ^
  --data-binary "@sample-data/wazuh-alert.json"
```

On Windows, you can also double-click [demo-post-alert.bat](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/demo-post-alert.bat>).

## One-Click Local Start

Recommended for Windows:

1. Run [install-and-run.bat](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/install-and-run.bat>)
2. Run [demo-post-alert.bat](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/demo-post-alert.bat>)
3. Open `http://localhost:3000/incidents`

Windows desktop `.exe` path:

1. Build the launcher with [build-exe.bat](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/build-exe.bat>)
2. Run `dist\CyberRed\CyberRed.exe`
3. Configure integrations from the desktop program and open the workspace from there

Windows installer path:

1. Build the installer with [build-installer.bat](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/build-installer.bat>)
2. Run `dist\CyberRedSetup.exe`
3. Launch the program from the desktop or start menu shortcut

Then open:

- `http://localhost:3000/incidents`
- `http://localhost:3000/chat`
- `http://localhost:3000/settings/ai`
- `http://localhost:3000/diagnostics`

Instant demo:

- Open `http://localhost:3000/incidents`
- Click `Generate Demo Incident`
- Open the generated incident to see alerts, evidence, risk, AI summary, and timeline

## Local Run

1. Copy `.env.example` values into your preferred shell environment if you want to override defaults.
2. Start the stack:

```bash
docker compose up --build
```

3. Open:
   - Web UI: `http://localhost:3000`
   - API docs: `http://localhost:8000/docs`

## Environment Variables

- `DATABASE_URL`
- `CORS_ORIGINS`
- `ALLOWED_HOSTS`
- `INTERNAL_API_KEY`
- `WAZUH_SHARED_SECRET`
- `SECRETS_ENCRYPTION_KEY`
- `VELOCIRAPTOR_MODE`
- `VELOCIRAPTOR_BASE_URL`
- `VELOCIRAPTOR_API_KEY`
- `AI_PROVIDER`
- `NEXT_PUBLIC_API_BASE_URL`
- `API_BASE_URL`

Recommended defaults for open-source users:

- Start with `VELOCIRAPTOR_MODE=mock`
- Keep `AI_PROVIDER=mock`
- Only replace backend secrets after the local demo flow works
- Generate a production encryption key with `python scripts/generate_secret_key.py`
- Set `INTERNAL_API_KEY`, `WAZUH_SHARED_SECRET`, and `SECRETS_ENCRYPTION_KEY` before exposing the API beyond localhost

## Test Wazuh Alert Ingestion

Use the sample payload:

```bash
curl -X POST http://localhost:8000/api/wazuh/alerts ^
  -H "Content-Type: application/json" ^
  --data-binary "@sample-data/wazuh-alert.json"
```

Expected result:

- One asset is created or updated
- One alert is stored
- One incident is opened
- Timeline events are created
- The incident appears in the web UI

## Easiest Wazuh Connection

CyberRed supports two Wazuh connection styles:

- `Connect Integration`: enter Wazuh Indexer credentials, then CyberRed tests the connection and pulls recent alerts.
- `Webhook Intake`: configure Wazuh custom integration to POST alerts continuously.

For the easiest credential-style setup, open the CyberRed desktop program:

1. Go to `Integrations`.
2. Select `Wazuh`.
3. Fill `Indexer URL`, `Indexer Username`, `Indexer Password`, and keep `Alert Index Pattern` as `wazuh-alerts-*`.
4. Optional: fill Wazuh Manager `API URL`, `API Username`, and `API Password` for manager connection tests.
5. Click `Connect Integration`.

The same flow is available through the API:

```bash
curl -X POST http://localhost:8000/api/settings/integrations/wazuh/connect \
  -H "Content-Type: application/json" \
  -H "X-Internal-Api-Key: demo-internal-key" \
  -d '{
    "config": {
      "indexer_url": "https://wazuh-indexer:9200",
      "indexer_username": "admin",
      "indexer_password": "password",
      "indexer_alert_index": "wazuh-alerts-*",
      "verify_tls": false
    },
    "sync_alerts": true,
    "sync_limit": 25
  }'
```

CyberRed saves the credentials server-side, tests connectivity, imports recent alerts, deduplicates existing alerts, and creates incidents automatically.

Velociraptor uses the same connector flow:

```bash
curl -X POST http://localhost:8000/api/settings/integrations/velociraptor/connect \
  -H "Content-Type: application/json" \
  -H "X-Internal-Api-Key: demo-internal-key" \
  -d '{
    "config": {
      "mode": "mock",
      "transport": "grpc_api",
      "api_client_config": "",
      "binary_path": "velociraptor"
    }
  }'
```

## Test Velociraptor Triage Flow

1. Open an incident in the UI.
2. Choose `process triage` or `autoruns/startup triage`.
3. Click `Request triage`.
4. Click `Confirm execution`.

Expected result:

- A `command_audit` record is created with `pending` approval
- Confirmation executes the mocked Velociraptor connector
- A `job` record is stored
- An `evidence` record is attached to the incident
- Timeline events show triage started and completed

## Test Chat Flow

Use the Chat page to:

- Ask for an incident summary
- Ask for an evidence summary
- Request triage in natural language
- Confirm the pending write action
- Ask real database questions like `incident ล่าสุดคืออะไร` or `host ไหนโดน alert สูง`

## Demo Mode

Generate a full local demo chain without configuring Wazuh first:

```bash
curl -X POST http://localhost:8000/api/demo/generate
```

Expected result:

- A fake asset, Wazuh-style alert, incident, and mock Velociraptor evidence are created
- Evidence is summarized and attached to the incident
- Incident risk and confidence are updated
- Timeline includes ingestion, incident creation, evidence, and AI summary events

## AI Providers And Models

CyberRed stores API keys at the provider level and routes model usage by purpose.
This lets multiple models share one provider credential while the runtime selects the right model for `chat`, `summary`, or `triage_explanation`.

Provider API keys are backend-only. API responses return `has_api_key` and never return raw keys.

Create a provider:

```bash
curl -X POST http://localhost:8000/api/ai/providers ^
  -H "Content-Type: application/json" ^
  -H "X-Internal-Api-Key: demo-internal-key" ^
  -d "{\"name\":\"openai\",\"label\":\"OpenAI\",\"base_url\":\"https://api.openai.com/v1\",\"api_key\":\"YOUR_KEY\"}"
```

Create a model for one or more purposes:

```bash
curl -X POST http://localhost:8000/api/ai/models ^
  -H "Content-Type: application/json" ^
  -H "X-Internal-Api-Key: demo-internal-key" ^
  -d "{\"provider_id\":\"PROVIDER_UUID\",\"model_name\":\"gpt-5-mini\",\"label\":\"GPT-5 Mini\",\"purpose\":[\"chat\",\"summary\"],\"supports_tools\":true,\"is_default\":true}"
```

Purpose routing:

- `chat` is used for general ChatOps responses.
- `summary` is used for incident and evidence summaries.
- `triage_explanation` is used when preparing write-action explanations.

Incident analysis:

- New incidents are analyzed automatically after Wazuh ingestion.
- Incidents are analyzed again after evidence is added.
- Results are stored on the incident as `summary`, `risk_level`, and `confidence`.
- The analyzer uses linked alerts and evidence highlights, not raw payload dumps.
- If no AI model is configured or the provider fails, CyberRed falls back to a simple rules-based summary and risk score.

AI suggested actions:

- `GET /api/incidents/{id}/recommendations` returns button-ready playbook recommendations.
- Recommendations use `purpose="triage_explanation"`.
- Allowed action types are `run_triage`, `collect_processes`, and `check_persistence`.
- Unknown or invented AI actions are filtered before the response reaches the UI.
- Recommendations include simple AI memory from related incidents and past evidence summaries. There is no vector database yet; related incidents are matched by same asset or overlapping Wazuh rule IDs.

Quick actions:

- `POST /api/incidents/{id}/actions` creates a pending approved-action request for `run_triage`, `collect_processes`, or `check_persistence`.
- The incident detail page renders quick action buttons and a direct `Confirm Selected Action` button.

Timeline and evidence:

- `GET /api/incidents/{id}/timeline` returns human-readable timeline events sorted ascending.
- `GET /api/incidents/{id}/evidence` returns evidence with `summary` and pretty JSON text for the UI.
- Evidence collected from triage is summarized automatically with `purpose="summary"`.
- Evidence cards support copy JSON and download JSON from the browser.

Reports and diagnostics:

- `GET /api/incidents/{id}/report?format=md` exports a Markdown incident report.
- `GET /api/incidents/{id}/report?format=json` exports a JSON incident report.
- `GET /api/diagnostics` returns database, AI, Wazuh, Velociraptor, and object-count health information.
- The UI exposes these at the incident detail page and `/diagnostics`.
- `/diagnostics` also includes buttons to test Wazuh and Velociraptor connections through backend-only credentials.
- `/diagnostics` reports a production-readiness score based on database, migration, AI, integration, and security checks.
- `GET /api/audit/commands/export?format=csv` exports command/action audit logs for review.
- Write endpoints have a simple per-client/path rate limit controlled by `RATE_LIMIT_PER_MINUTE`.

Security baseline:

- Optional UI authentication can be enabled with `AUTH_ENABLED=true`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `APP_SESSION_SECRET`.
- Auth sessions use signed, HttpOnly cookies and protect app pages plus frontend proxy routes.
- Internal API and Wazuh webhook secrets use constant-time comparison.
- In production mode, protected endpoints reject requests if `INTERNAL_API_KEY` or the Wazuh webhook secret is missing.
- Runtime integration secrets and newly saved AI provider API keys are encrypted at rest when `SECRETS_ENCRYPTION_KEY` is configured.
- Frontend responses expose only configured booleans such as `has_api_key`; raw provider secrets stay backend-only.
- API responses include defensive headers such as `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy`.
- Catalog/settings views redact secret fields instead of returning raw credentials.
- Docker Compose runs API and web containers with `no-new-privileges` and all Linux capabilities dropped.
- CI workflow runs backend compile/tests, Python dependency audit with `pip-audit`, frontend typecheck/audit/build, and Docker image scanning with Trivy.
- Windows release workflow builds `CyberRed.exe`, builds `CyberRedSetup.exe`, creates SHA-256 checksums plus a release manifest, and can code-sign both executable and installer when signing certificate secrets are configured.

Deduplication:

- Wazuh alerts with the same hostname, same `rule_id`, and a 10-minute event-time window attach to the existing incident instead of opening a new one.
- A timeline event records deduplicated alert attachment.

Seed demo providers and models:

```bash
python scripts/seed_ai.py
```

The seed adds OpenAI, OpenRouter, and Ollama provider rows plus sample model rows. It does not store real API keys.

## Backend Checks

From `cyber-chatops-mvp`:

```bash
python -m pytest tests
```

## Clean Generated Files

To remove local build outputs and caches before packaging or sharing the repo:

```bat
clean.bat
```

This removes generated folders such as `build`, `dist`, `.next`, `node_modules`, Python bytecode, and temporary build metadata. Re-run `install-and-run.bat`, `docker compose up --build`, or `build-exe.bat` when you want to restore dependencies/build outputs.

## Open Source Docs

- Quickstart: [docs/open-source-quickstart.md](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/docs/open-source-quickstart.md>)
- Integrations: [docs/integrations.md](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/docs/integrations.md>)
- Production baseline: [docs/production.md](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/docs/production.md>)
- Windows EXE launcher: [docs/windows-exe.md](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/docs/windows-exe.md>)
- Contributing: [CONTRIBUTING.md](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/CONTRIBUTING.md>)
- License: [LICENSE](</c:/Users/nonpo/OneDrive/Documents/GitHub/cyber-chatops-mvp/LICENSE>)

## Notes

- Velociraptor is mocked in this MVP to keep the stack fast to demo locally.
- The AI layer is intentionally deterministic and constrained to approved internal tools.
- Write actions never execute directly from chat without explicit user confirmation.
