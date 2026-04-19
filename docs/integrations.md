# Integrations

This MVP is designed so external systems can connect quickly without changing the core app shape.

## One-Click Connector Flow

Use the desktop app `Integrations` page for the simplest setup:

1. Select a connector.
2. Fill credentials or local connection settings.
3. Click `Connect Integration`.

The backend endpoint is shared by current and future connectors:

```text
POST /api/settings/integrations/{integration_id}/connect
```

For Wazuh, this saves credentials, tests connectivity, and optionally syncs recent alerts from Wazuh Indexer.
For Velociraptor, this saves settings and tests the configured mock, gRPC API, or HTTP adapter connection.
Raw secrets are never returned to the frontend.

## Wazuh

### Inbound path

- Endpoint: `POST /api/wazuh/alerts`
- Expected payload: Wazuh-like JSON with `timestamp`, `rule`, and optional `agent`
- Connector module: `apps/api/app/connectors/wazuh.py`

### Minimal required fields

```json
{
  "timestamp": "2026-04-15T10:00:00Z",
  "rule": {
    "id": "100200",
    "level": 9,
    "description": "Suspicious PowerShell download command",
    "groups": ["windows", "powershell", "execution"]
  }
}
```

### What happens after receipt

1. Payload is validated by FastAPI/Pydantic.
2. The Wazuh connector normalizes fields.
3. The incident service resolves or creates the asset.
4. The service creates:
   - `alerts`
   - `incidents`
   - `incident_alerts`
   - `timeline_events`

## Velociraptor

### Current MVP mode

- Connector module: `apps/api/app/connectors/velociraptor.py`
- Default mode: `mock`
- Live modes: `grpc_api` with `api_client.yaml`, or an HTTP adapter with `base_url` plus bearer token
- Supported actions:
  - `process_triage`
  - `autoruns_triage`

### Real integration

To connect a real Velociraptor backend, configure it on the desktop `Integrations` page or through the connect endpoint. The UI and AI layers still call internal API/services only:

- `run_artifact(asset_ref, artifact_name, parameters)`
- `get_flow_status(flow_id)`
- `fetch_results(flow_id)`

### Required environment variables

- `VELOCIRAPTOR_MODE`
- `VELOCIRAPTOR_BASE_URL`
- `VELOCIRAPTOR_API_KEY`

## AI / ChatOps

The AI layer is intentionally constrained.

### Allowed internal tools

- `get_incident(incident_id)`
- `list_incident_evidence(incident_id)`
- `summarize_incident(incident_id)`
- `request_host_triage(incident_id, triage_type)`

### Important rules

- AI does not call connectors directly.
- Write actions do not auto-execute.
- Every write request is stored in `command_audit`.
- Execution only happens after explicit confirmation.
