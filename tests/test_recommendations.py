from app.services.recommendation_service import RecommendationService


def test_incident_recommendations_endpoint_returns_button_ready_actions(client):
    payload = {
        "id": "wazuh-reco-001",
        "timestamp": "2026-04-15T10:00:00Z",
        "rule": {
            "id": "200100",
            "level": 9,
            "description": "Suspicious process execution",
            "groups": ["windows", "execution"],
        },
        "agent": {"id": "021", "name": "win-reco-01"},
    }
    client.post("/api/wazuh/alerts", json=payload)
    incident_id = client.get("/api/incidents").json()[0]["id"]

    response = client.get(f"/api/incidents/{incident_id}/recommendations")
    assert response.status_code == 200
    actions = response.json()["suggested_actions"]

    assert actions
    assert actions[0]["action_type"] in {"run_triage", "collect_processes", "check_persistence"}
    assert actions[0]["label"]
    assert actions[0]["reason"]
    assert actions[0]["risk_level"] in {"low", "medium", "high"}


def test_recommendation_service_filters_unknown_ai_actions():
    service = RecommendationService()
    fallback = [
        {
            "action_type": "run_triage",
            "label": "Run Windows Triage",
            "reason": "Fallback",
            "risk_level": "medium",
        }
    ]
    actions = service._parse_and_validate(
        """
        {
          "suggested_actions": [
            {"action_type": "delete_host", "label": "Delete host", "reason": "bad", "risk_level": "critical"},
            {"action_type": "collect_processes", "label": "Collect Processes", "reason": "Suspicious process", "risk_level": "medium"}
          ]
        }
        """,
        fallback,
    )

    assert len(actions) == 1
    assert actions[0]["action_type"] == "collect_processes"
    assert actions[0]["risk_level"] == "medium"
