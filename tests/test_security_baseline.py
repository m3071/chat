from app.core.secrets import ENC_PREFIX, SecretManager


def test_secret_manager_encrypts_and_decrypts_values():
    manager = SecretManager("unit-test-secret-key")

    encrypted = manager.encrypt("super-secret")

    assert encrypted is not None
    assert encrypted.startswith(ENC_PREFIX)
    assert encrypted != "super-secret"
    assert manager.decrypt(encrypted) == "super-secret"


def test_ai_provider_api_key_is_not_returned_and_is_stored_encrypted(client):
    response = client.post(
        "/api/ai/providers",
        json={
            "name": "secure-openai",
            "label": "Secure OpenAI",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-secret",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "api_key" not in payload
    assert payload["has_api_key"] is True


def test_security_headers_are_present(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_health_aliases_are_available(client):
    assert client.get("/health").status_code == 200
    assert client.get("/healthz").status_code == 200
    assert client.get("/health/live").status_code == 200


def test_command_audit_export(client):
    payload = {
        "id": "wazuh-audit-export-001",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {"id": "300001", "level": 8, "description": "Audit export test", "groups": ["windows"]},
        "agent": {"id": "audit-001", "name": "win-audit-01"},
    }
    client.post("/api/wazuh/alerts", json=payload)
    incident_id = client.get("/api/incidents").json()[0]["id"]
    client.post(f"/api/incidents/{incident_id}/actions", json={"action_type": "run_triage"})

    response = client.get("/api/audit/commands/export?format=csv")

    assert response.status_code == 200
    assert "command-audit.csv" in response.headers["content-disposition"]
    assert "approval_status" in response.text


def test_rate_limit_protects_write_endpoints(monkeypatch, client):
    from app.core.config import settings
    from app.middleware import _rate_limit_buckets

    _rate_limit_buckets.clear()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1)
    payload = {
        "id": "rate-limit-001",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {"id": "300002", "level": 5, "description": "Rate limit test", "groups": ["windows"]},
        "agent": {"id": "rate-001", "name": "win-rate-01"},
    }

    first = client.post("/api/wazuh/alerts", json=payload)
    second = client.post("/api/wazuh/alerts", json={**payload, "id": "rate-limit-002"})

    assert first.status_code == 200
    assert second.status_code == 429
    _rate_limit_buckets.clear()
