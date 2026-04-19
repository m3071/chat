#!/usr/bin/env sh
set -eu

SECRET="${WAZUH_SHARED_SECRET:-demo-wazuh-secret}"

curl -X POST http://localhost:8000/api/wazuh/alerts \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: ${SECRET}" \
  --data-binary "@sample-data/wazuh-alert.json"
