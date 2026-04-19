# Production Baseline

This repository now includes a production-oriented baseline, not a claim of full enterprise readiness.

## What Is Hardened

- Backend and web containers run as non-root users
- API startup waits for the database before applying migrations
- Postgres, API, and web services include health checks in Docker Compose
- API has separate liveness and readiness endpoints
- Internal web-to-API traffic can be protected with `INTERNAL_API_KEY`
- Wazuh webhook intake can be protected with `WAZUH_SHARED_SECRET`
- Basic request logging and request IDs are enabled
- DB connections use `pool_pre_ping` and recycle settings for non-SQLite databases
- Duplicate Wazuh alerts are handled idempotently
- Triage confirmation is single-use and replay-safe

## Environment Variables You Should Override

- `INTERNAL_API_KEY`
- `WAZUH_SHARED_SECRET`
- `VELOCIRAPTOR_API_KEY`
- `DATABASE_URL`
- `CORS_ORIGINS`
- `ALLOWED_HOSTS`

## Recommended Next Production Steps

- Put the stack behind a real reverse proxy or ingress
- Terminate TLS at the edge
- Send logs to a central log platform
- Add managed Postgres backups
- Replace mock Velociraptor logic with the real API adapter
- Add user authentication and RBAC before exposing the UI outside trusted networks
- Store secrets in a proper secret manager instead of plaintext env files

## Health Endpoints

- Liveness: `/health/live`
- Readiness: `/health/ready`

## Security Model in This Baseline

- Browser clients do not see backend connector credentials
- The Next.js server calls the API with `INTERNAL_API_KEY`
- Wazuh webhook requests can be required to send `X-Webhook-Secret`
- Write actions remain approval-gated even after API authentication
