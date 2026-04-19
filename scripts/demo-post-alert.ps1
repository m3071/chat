$ErrorActionPreference = "Stop"

$body = Get-Content "sample-data/wazuh-alert.json" -Raw
$secret = if ($env:WAZUH_SHARED_SECRET) { $env:WAZUH_SHARED_SECRET } else { "demo-wazuh-secret" }
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/wazuh/alerts" `
  -ContentType "application/json" `
  -Headers @{ "X-Webhook-Secret" = $secret } `
  -Body $body
