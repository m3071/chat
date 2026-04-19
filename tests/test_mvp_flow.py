def test_wazuh_ingest_creates_incident_chain(client):
    payload = {
        "id": "wazuh-test-001",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {
            "id": "100200",
            "level": 9,
            "description": "Suspicious PowerShell download command",
            "groups": ["windows", "powershell", "execution"],
        },
        "agent": {"id": "007", "name": "win-demo-01"},
        "data": {"srcip": "10.10.20.15", "destip": "185.199.108.153"},
        "location": "WinEvtLog",
    }

    response = client.post("/api/wazuh/alerts", json=payload)
    assert response.status_code == 200

    alerts_response = client.get("/api/alerts")
    incidents_response = client.get("/api/incidents")
    assert len(alerts_response.json()) == 1
    assert len(incidents_response.json()) == 1

    incident_id = incidents_response.json()[0]["id"]
    detail_response = client.get(f"/api/incidents/{incident_id}")
    detail = detail_response.json()
    assert len(detail["alerts"]) == 1
    assert len(detail["timeline"]) >= 2
    assert detail["summary"]
    assert detail["risk_level"] in {"low", "medium", "high"}
    assert 0 <= detail["confidence"] <= 1
    assert any(event["event_type"] == "ai_summary_generated" for event in detail["timeline"])


def test_triage_request_and_confirmation_store_evidence(client):
    payload = {
        "id": "wazuh-test-002",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {
            "id": "100201",
            "level": 8,
            "description": "Suspicious autoruns modification",
            "groups": ["windows", "persistence"],
        },
        "agent": {"id": "008", "name": "win-demo-02"},
    }

    client.post("/api/wazuh/alerts", json=payload)
    incident_id = client.get("/api/incidents").json()[0]["id"]

    request_response = client.post(
        "/api/triage/request",
        json={"incident_id": incident_id, "triage_type": "process_triage", "requested_by": "analyst"},
    )
    assert request_response.status_code == 200
    audit_id = request_response.json()["command_audit_id"]

    confirm_response = client.post(
        "/api/triage/confirm",
        json={"command_audit_id": audit_id, "approved_by": "analyst"},
    )
    assert confirm_response.status_code == 200

    detail = client.get(f"/api/incidents/{incident_id}").json()
    assert len(detail["evidence"]) == 1
    assert any(event["event_type"] == "triage_completed" for event in detail["timeline"])
    assert any(event["event_type"] == "ai_summary_generated" for event in detail["timeline"])
    assert detail["summary"]
    assert detail["risk_level"] in {"low", "medium", "high"}


def test_chat_summary_and_write_intent(client):
    payload = {
        "id": "wazuh-test-003",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {
            "id": "100202",
            "level": 7,
            "description": "Encoded command observed",
            "groups": ["windows", "execution"],
        },
        "agent": {"id": "009", "name": "win-demo-03"},
    }
    client.post("/api/wazuh/alerts", json=payload)
    incident_id = client.get("/api/incidents").json()[0]["id"]

    summary_response = client.post("/api/chat", json={"message": "Summarize this incident", "incident_id": incident_id})
    assert summary_response.status_code == 200
    assert "severity" in summary_response.json()["response"]

    triage_response = client.post(
        "/api/chat",
        json={"message": "Run autoruns triage on this host", "incident_id": incident_id},
    )
    assert triage_response.status_code == 200
    assert triage_response.json()["mode"] == "write_pending_confirmation"
    assert triage_response.json()["command_audit_id"] is not None


def test_duplicate_wazuh_alert_is_idempotent(client):
    payload = {
        "id": "wazuh-test-dup",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {
            "id": "100203",
            "level": 5,
            "description": "Duplicate-safe test",
            "groups": ["windows"],
        },
        "agent": {"id": "010", "name": "win-demo-04"},
    }

    first = client.post("/api/wazuh/alerts", json=payload)
    second = client.post("/api/wazuh/alerts", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["message"] == "Alert already ingested."
    assert len(client.get("/api/alerts").json()) == 1
    assert len(client.get("/api/incidents").json()) == 1


def test_similar_alerts_are_deduplicated_into_existing_incident(client):
    base_payload = {
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {
            "id": "100205",
            "level": 6,
            "description": "Repeated suspicious process",
            "groups": ["windows", "execution"],
        },
        "agent": {"id": "012", "name": "win-demo-06"},
    }

    client.post("/api/wazuh/alerts", json={**base_payload, "id": "wazuh-dedup-001"})
    client.post("/api/wazuh/alerts", json={**base_payload, "id": "wazuh-dedup-002", "timestamp": "2026-04-15T10:05:00Z"})

    incidents = client.get("/api/incidents").json()
    assert len(client.get("/api/alerts").json()) == 2
    assert len(incidents) == 1
    detail = client.get(f"/api/incidents/{incidents[0]['id']}").json()
    assert len(detail["alerts"]) == 2
    assert any(event["event_type"] == "alert_ingested" for event in detail["timeline"])


def test_timeline_endpoint_is_human_readable_and_ascending(client):
    payload = {
        "id": "wazuh-timeline-001",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {"id": "100206", "level": 7, "description": "Timeline test", "groups": ["windows"]},
        "agent": {"id": "013", "name": "win-demo-07"},
    }
    client.post("/api/wazuh/alerts", json=payload)
    incident_id = client.get("/api/incidents").json()[0]["id"]

    timeline = client.get(f"/api/incidents/{incident_id}/timeline").json()
    timestamps = [event["timestamp"] for event in timeline]

    assert timestamps == sorted(timestamps)
    assert {"timestamp", "title", "description", "event_type"}.issubset(timeline[0].keys())


def test_demo_generate_creates_full_demo_chain(client):
    response = client.post("/api/demo/generate")

    assert response.status_code == 200
    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    detail = client.get(f"/api/incidents/{incidents[0]['id']}").json()
    assert detail["evidence"]
    assert detail["summary"]
    assert any(event["event_type"] == "evidence_added" for event in detail["timeline"])


def test_chat_answers_real_database_queries(client):
    payload = {
        "id": "wazuh-chat-query-001",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {"id": "100207", "level": 9, "description": "High alert host test", "groups": ["windows"]},
        "agent": {"id": "014", "name": "win-chat-01"},
    }
    client.post("/api/wazuh/alerts", json=payload)

    latest = client.post("/api/chat", json={"message": "incident ล่าสุดคืออะไร"})
    host = client.post("/api/chat", json={"message": "host ไหนโดน alert สูง"})

    assert latest.status_code == 200
    assert "High alert host test" in latest.json()["response"]
    assert host.status_code == 200
    assert "win-chat-01" in host.json()["response"]


def test_quick_action_can_be_confirmed_and_stores_evidence(client):
    payload = {
        "id": "wazuh-quick-action-001",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {"id": "100208", "level": 8, "description": "Quick action test", "groups": ["windows", "execution"]},
        "agent": {"id": "015", "name": "win-quick-01"},
    }
    client.post("/api/wazuh/alerts", json=payload)
    incident_id = client.get("/api/incidents").json()[0]["id"]

    action = client.post(f"/api/incidents/{incident_id}/actions", json={"action_type": "collect_processes"})
    assert action.status_code == 200
    audit_id = action.json()["command_audit_id"]

    confirm = client.post("/api/triage/confirm", json={"command_audit_id": audit_id, "approved_by": "analyst"})
    assert confirm.status_code == 200
    detail = client.get(f"/api/incidents/{incident_id}").json()
    assert detail["evidence"]
    assert any(event["event_type"] == "action_triggered" for event in detail["timeline"])


def test_incident_report_and_diagnostics(client):
    payload = {
        "id": "wazuh-report-001",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {"id": "100209", "level": 6, "description": "Report test", "groups": ["windows"]},
        "agent": {"id": "016", "name": "win-report-01"},
    }
    client.post("/api/wazuh/alerts", json=payload)
    incident_id = client.get("/api/incidents").json()[0]["id"]

    report = client.get(f"/api/incidents/{incident_id}/report")
    diagnostics = client.get("/api/diagnostics")

    assert report.status_code == 200
    assert "# Report test on win-report-01" in report.text
    assert diagnostics.status_code == 200
    assert diagnostics.json()["counts"]["incidents"] == 1


def test_confirming_same_audit_twice_is_blocked(client):
    payload = {
        "id": "wazuh-test-replay",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {
            "id": "100204",
            "level": 8,
            "description": "Replay-safe triage test",
            "groups": ["windows", "execution"],
        },
        "agent": {"id": "011", "name": "win-demo-05"},
    }

    client.post("/api/wazuh/alerts", json=payload)
    incident_id = client.get("/api/incidents").json()[0]["id"]

    request_response = client.post(
        "/api/triage/request",
        json={"incident_id": incident_id, "triage_type": "process_triage", "requested_by": "analyst"},
    )
    audit_id = request_response.json()["command_audit_id"]

    first_confirm = client.post(
        "/api/triage/confirm",
        json={"command_audit_id": audit_id, "approved_by": "analyst"},
    )
    second_confirm = client.post(
        "/api/triage/confirm",
        json={"command_audit_id": audit_id, "approved_by": "analyst"},
    )

    assert first_confirm.status_code == 200
    assert second_confirm.status_code == 409
    detail = client.get(f"/api/incidents/{incident_id}").json()
    assert len(detail["evidence"]) == 1


def test_settings_update_and_connection_test_endpoint(client):
    wazuh_update = client.put(
        "/api/settings/integrations/wazuh",
        json={
            "webhook_secret": "new-secret",
            "manager_url": "",
            "api_key": "",
        },
    )
    velo_update = client.put(
        "/api/settings/integrations/velociraptor/config",
        json={
            "mode": "mock",
            "base_url": "https://velociraptor.example.invalid",
            "api_key": "",
            "run_path": "/api/v1/collect",
            "status_path": "/api/v1/flows/{flow_id}",
            "results_path": "/api/v1/flows/{flow_id}/results",
            "verify_tls": True,
        },
    )

    assert wazuh_update.status_code == 200
    assert velo_update.status_code == 200

    settings_response = client.get("/api/settings/integrations")
    payload = settings_response.json()
    assert payload["wazuh"]["webhook_secret_configured"] is True
    assert payload["velociraptor"]["mode"] == "mock"

    wazuh_test = client.post("/api/settings/integrations/test", json={"service": "wazuh"})
    velo_test = client.post("/api/settings/integrations/test", json={"service": "velociraptor"})
    assert wazuh_test.status_code == 200
    assert velo_test.status_code == 200
    assert velo_test.json()["mode"] == "mock"


def test_settings_catalog_and_generic_update_endpoint(client):
    update_response = client.put(
        "/api/settings/integrations/velociraptor/config",
        json={
            "config": {
                "mode": "live",
                "base_url": "https://velo.local",
                "api_key": "secret-token",
                "run_path": "/collect",
                "status_path": "/flows/{flow_id}",
                "results_path": "/flows/{flow_id}/results",
                "verify_tls": False,
            }
        },
    )
    assert update_response.status_code == 200

    catalog_response = client.get("/api/settings/catalog")
    assert catalog_response.status_code == 200
    catalog = catalog_response.json()

    integration_ids = {item["id"] for item in catalog["integrations"]}
    assert "wazuh" in integration_ids
    assert "velociraptor" in integration_ids
    assert any(tool["id"] == "request_host_triage" for tool in catalog["tools"])
    assert any(policy["id"] == "write_requires_confirmation" for policy in catalog["policies"])

    velociraptor = next(item for item in catalog["integrations"] if item["id"] == "velociraptor")
    assert velociraptor["config"]["mode"] == "live"
    assert velociraptor["config"]["verify_tls"] is False


def test_wazuh_indexer_sync_imports_alerts(monkeypatch, client):
    from app.api.routes import wazuh as wazuh_route
    from app.schemas.wazuh import WazuhAgentPayload, WazuhAlertPayload, WazuhRulePayload
    from datetime import datetime

    def fake_fetch_recent_alerts(limit=25):
        return [
            WazuhAlertPayload(
                id="indexer-alert-001",
                timestamp=datetime.fromisoformat("2026-04-15T10:00:00+00:00"),
                rule=WazuhRulePayload(id="900001", level=9, description="Indexer credential alert", groups=["indexer"]),
                agent=WazuhAgentPayload(id="idx-001", name="win-indexer-01"),
            )
        ]

    monkeypatch.setattr(wazuh_route.connector, "fetch_recent_alerts", fake_fetch_recent_alerts)

    response = client.post("/api/wazuh/sync?limit=1")

    assert response.status_code == 200
    assert "imported=1" in response.json()["message"]
    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    assert "Indexer credential alert" in incidents[0]["title"]


def test_wazuh_connect_saves_credentials_and_syncs(monkeypatch, client):
    from app.api.routes import wazuh as wazuh_route
    from app.schemas.wazuh import WazuhAgentPayload, WazuhAlertPayload, WazuhRulePayload
    from datetime import datetime

    monkeypatch.setattr(wazuh_route.connector, "test_connection", lambda: {"ok": True, "detail": "Connection successful."})
    monkeypatch.setattr(
        wazuh_route.connector,
        "fetch_recent_alerts",
        lambda limit=25: [
            WazuhAlertPayload(
                id="connect-alert-001",
                timestamp=datetime.fromisoformat("2026-04-15T10:00:00+00:00"),
                rule=WazuhRulePayload(id="900002", level=8, description="Connect and sync alert", groups=["connect"]),
                agent=WazuhAgentPayload(id="connect-001", name="win-connect-01"),
            )
        ],
    )

    response = client.post(
        "/api/wazuh/connect",
        json={
            "webhook_secret": "secret",
            "indexer_url": "https://indexer.local:9200",
            "indexer_username": "admin",
            "indexer_password": "password",
            "sync_alerts": True,
            "sync_limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["sync"]["imported"] == 1
    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    assert "Connect and sync alert" in incidents[0]["title"]


def test_generic_wazuh_connect_saves_credentials_and_syncs(monkeypatch, client):
    from datetime import datetime

    from app.connectors.wazuh import WazuhConnector
    from app.schemas.wazuh import WazuhAgentPayload, WazuhAlertPayload, WazuhRulePayload

    monkeypatch.setattr(WazuhConnector, "test_connection", lambda self: {"ok": True, "detail": "Connection successful."})
    monkeypatch.setattr(
        WazuhConnector,
        "fetch_recent_alerts",
        lambda self, limit=25: [
            WazuhAlertPayload(
                id="generic-connect-alert-001",
                timestamp=datetime.fromisoformat("2026-04-15T10:00:00+00:00"),
                rule=WazuhRulePayload(id="900003", level=8, description="Generic connect alert", groups=["connect"]),
                agent=WazuhAgentPayload(id="generic-connect-001", name="win-generic-connect-01"),
            )
        ],
    )

    response = client.post(
        "/api/settings/integrations/wazuh/connect",
        json={
            "config": {
                "webhook_secret": "secret",
                "indexer_url": "https://indexer.local:9200",
                "indexer_username": "admin",
                "indexer_password": "password",
            },
            "sync_alerts": True,
            "sync_limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["integration"] == "wazuh"
    assert response.json()["sync"]["imported"] == 1
    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    assert "Generic connect alert" in incidents[0]["title"]


def test_generic_velociraptor_connect_saves_credentials_and_tests(monkeypatch, client):
    from app.connectors.velociraptor import VelociraptorConnector

    monkeypatch.setattr(
        VelociraptorConnector,
        "test_connection",
        lambda self: {"ok": True, "mode": "mock", "detail": "Mock mode is enabled."},
    )

    response = client.post(
        "/api/settings/integrations/velociraptor/connect",
        json={
            "config": {
                "mode": "mock",
                "transport": "grpc_api",
                "api_client_config": "",
                "base_url": "",
                "api_key": "secret-key",
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["integration"] == "velociraptor"
    assert response.json()["test"]["ok"] is True
    settings_response = client.get("/api/settings/integrations")
    assert settings_response.json()["velociraptor"]["api_key_configured"] is True
    assert "secret-key" not in settings_response.text
