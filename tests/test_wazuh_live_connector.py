from __future__ import annotations

import base64
import json
import threading
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterator

from app.connectors.wazuh import WazuhConnector
from app.core.runtime_config import RuntimeConfigService


class FakeWazuhHandler(BaseHTTPRequestHandler):
    calls: list[tuple[str, str, str | None]] = []

    def log_message(self, format: str, *args):  # noqa: A002
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        auth = self.headers.get("Authorization")
        self.calls.append(("GET", self.path, auth))
        expected_basic = "Basic " + base64.b64encode(b"admin:secret").decode("ascii")

        if self.path == "/":
            if auth != expected_basic:
                self._send_json({"error": "unauthorized"}, status=401)
                return
            self._send_json({"cluster_name": "fake-wazuh-indexer", "version": {"number": "4.9.0"}})
            return

        if self.path.startswith("/security/user/authenticate"):
            if auth != expected_basic:
                self._send_json({"error": "unauthorized"}, status=401)
                return
            token = b"fake-jwt"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(token)))
            self.end_headers()
            self.wfile.write(token)
            return

        if self.path == "/agents/summary/status":
            if auth != "Bearer fake-jwt":
                self._send_json({"error": "unauthorized"}, status=401)
                return
            self._send_json({"data": {"active": 1, "disconnected": 0}})
            return

        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        auth = self.headers.get("Authorization")
        self.calls.append(("POST", self.path, auth))
        expected_basic = "Basic " + base64.b64encode(b"admin:secret").decode("ascii")
        if auth != expected_basic:
            self._send_json({"error": "unauthorized"}, status=401)
            return
        if self.path.endswith("/_search"):
            self._send_json(
                {
                    "hits": {
                        "hits": [
                            {
                                "_id": "fake-alert-001",
                                "_source": {
                                    "@timestamp": "2026-04-15T10:00:00Z",
                                    "rule": {
                                        "id": "100200",
                                        "level": 9,
                                        "description": "Fake Wazuh live connector alert",
                                        "groups": ["syscheck"],
                                    },
                                    "agent": {"id": "001", "name": "win-live-01"},
                                    "data": {"srcip": "10.0.0.5"},
                                    "location": "Security",
                                },
                            }
                        ]
                    }
                }
            )
            return
        self._send_json({"error": "not found"}, status=404)


@contextmanager
def fake_wazuh_server() -> Iterator[str]:
    FakeWazuhHandler.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeWazuhHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_wazuh_connector_uses_real_http_for_indexer_and_manager():
    with fake_wazuh_server() as base_url:
        RuntimeConfigService().update_section(
            "wazuh",
            {
                "api_url": base_url,
                "api_username": "admin",
                "api_password": "secret",
                "indexer_url": base_url,
                "indexer_username": "admin",
                "indexer_password": "secret",
                "indexer_alert_index": "wazuh-alerts-*",
                "verify_tls": False,
            },
        )

        result = WazuhConnector().test_connection()

    assert result["ok"] is True
    assert result["indexer"]["connected"] is True
    assert result["indexer"]["cluster_name"] == "fake-wazuh-indexer"
    assert result["auth"] == "jwt"
    assert result["agents_summary"]["active"] == 1
    assert ("GET", "/", "Basic " + base64.b64encode(b"admin:secret").decode("ascii")) in FakeWazuhHandler.calls
    assert any(call[1].startswith("/security/user/authenticate") for call in FakeWazuhHandler.calls)
    assert ("GET", "/agents/summary/status", "Bearer fake-jwt") in FakeWazuhHandler.calls


def test_wazuh_connector_fetches_recent_alerts_from_indexer_search():
    with fake_wazuh_server() as base_url:
        RuntimeConfigService().update_section(
            "wazuh",
            {
                "indexer_url": base_url,
                "indexer_username": "admin",
                "indexer_password": "secret",
                "indexer_alert_index": "wazuh-alerts-*",
                "verify_tls": False,
            },
        )

        alerts = WazuhConnector().fetch_recent_alerts(limit=5)

    assert len(alerts) == 1
    assert alerts[0].id == "fake-alert-001"
    assert alerts[0].timestamp == datetime.fromisoformat("2026-04-15T10:00:00+00:00")
    assert alerts[0].rule.id == "100200"
    assert alerts[0].rule.description == "Fake Wazuh live connector alert"
    assert alerts[0].agent.name == "win-live-01"
    assert any(method == "POST" and path.endswith("/_search") for method, path, _ in FakeWazuhHandler.calls)


def test_wazuh_connect_endpoint_with_simulated_live_wazuh(client):
    with fake_wazuh_server() as base_url:
        response = client.post(
            "/api/settings/integrations/wazuh/connect",
            json={
                "config": {
                    "connection_mode": "manager_and_indexer",
                    "auth_type": "basic",
                    "webhook_secret": "simulated-secret",
                    "api_url": base_url,
                    "api_username": "admin",
                    "api_password": "secret",
                    "indexer_url": base_url,
                    "indexer_username": "admin",
                    "indexer_password": "secret",
                    "indexer_alert_index": "wazuh-alerts-*",
                    "verify_tls": False,
                },
                "sync_alerts": True,
                "sync_limit": 5,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["integration"] == "wazuh"
    assert payload["test"]["indexer"]["connected"] is True
    assert payload["test"]["auth"] == "jwt"
    assert payload["sync"]["enabled"] is True
    assert payload["sync"]["imported"] == 1

    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 1
    assert incidents[0]["title"] == "Fake Wazuh live connector alert on win-live-01"
    assert any(method == "POST" and path.endswith("/_search") for method, path, _ in FakeWazuhHandler.calls)
