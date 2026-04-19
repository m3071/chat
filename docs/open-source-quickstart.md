# Open Source Quickstart

This repo is intended to be easy to fork, run, and adapt.

## Fastest Demo Path

1. Clone the repo.
2. Start the local stack:

```bash
docker compose up --build
```

3. Post the sample alert:

```bash
curl -X POST http://localhost:8000/api/wazuh/alerts \
  -H "Content-Type: application/json" \
  --data-binary "@sample-data/wazuh-alert.json"
```

4. Open:
   - `http://localhost:3000/incidents`
   - `http://localhost:3000/chat`

## Easy Forking Guidelines

- Keep the current table set unless a new flow truly needs more schema.
- Extend connectors first, not UI-side credentials.
- Add new actions through policy approval before exposing them in chat.
- Prefer adding small docs and sample payloads when introducing new integrations.

## Recommended First Customizations

- Replace mock Velociraptor connector logic with your environment's API calls
- Add your Wazuh field mapping rules
- Tune incident creation or dedup behavior
- Point the web app to your hosted API via `NEXT_PUBLIC_API_BASE_URL`
