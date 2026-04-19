# Contributing

This project is intentionally small and demo-focused. Contributions are welcome, but changes should preserve the MVP shape:

- Prefer a modular monolith over new services
- Avoid adding background queues unless a demo flow truly needs them
- Keep integrations behind connector boundaries
- Keep write actions behind the approval layer
- Optimize for local Docker Compose usability

## Development Flow

1. Start the stack with Docker Compose or run the API and web app locally.
2. Use the sample Wazuh payload to create demo data.
3. Keep PRs focused on one end-to-end improvement.
4. Add or update tests when changing ingestion, triage, policy, or chat behavior.

## Good First Contributions

- More Wazuh field normalization
- Real Velociraptor API adapter behind the existing connector
- Better incident grouping logic
- Improved evidence rendering in the UI
- Additional safe read-only AI tools

## Out of Scope for This MVP

- Multi-tenant access control
- Full SIEM analytics
- Full SOAR playbook engine
- Unbounded AI agent execution
- Frontend connector credentials
