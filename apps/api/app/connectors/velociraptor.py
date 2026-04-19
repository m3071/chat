from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
import shutil
import subprocess
from uuid import uuid4

import httpx

from app.core.config import settings
from app.core.runtime_config import RuntimeConfigService


@dataclass
class VelociraptorRunResult:
    flow_id: str
    status: str
    results: dict


class VelociraptorConnector:
    supported_artifacts = {
        "process_triage": "Windows.System.Pslist",
        "autoruns_triage": "Windows.Sys.StartupItems",
    }

    def run_artifact(self, asset_ref: str, artifact_name: str, parameters: dict | None = None) -> VelociraptorRunResult:
        if artifact_name not in self.supported_artifacts:
            raise ValueError(f"Unsupported artifact: {artifact_name}")

        flow_id = f"F.{uuid4()}"
        artifact = self.supported_artifacts[artifact_name]
        now = datetime.now(UTC).isoformat()
        runtime_config = RuntimeConfigService().get_velociraptor_config()
        mode = runtime_config.get("mode", settings.velociraptor_mode)
        base_url = runtime_config.get("base_url", settings.velociraptor_base_url)
        api_key = runtime_config.get("api_key", settings.velociraptor_api_key)
        transport = runtime_config.get("transport", "grpc_api")
        api_client_config = runtime_config.get("api_client_config", "")
        binary_path = runtime_config.get("binary_path", "velociraptor")
        org_id = runtime_config.get("org_id", "root")
        timeout_seconds = int(runtime_config.get("timeout_seconds", 120))
        run_path = runtime_config.get("run_path", "/api/v1/collect")
        verify_tls = bool(runtime_config.get("verify_tls", True))

        if mode == "mock":
            if artifact_name == "process_triage":
                rows = [
                    {"pid": 456, "name": "powershell.exe", "user": "SYSTEM"},
                    {"pid": 912, "name": "cmd.exe", "user": "svc-demo"},
                ]
            else:
                rows = [
                    {"entry": "RunOnce", "path": "C:\\Users\\Public\\temp\\beacon.exe"},
                    {"entry": "Startup", "path": "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\helper.vbs"},
                ]
            return VelociraptorRunResult(
                flow_id=flow_id,
                status="completed",
                results={
                    "asset_ref": asset_ref,
                    "artifact": artifact,
                    "parameters": parameters or {},
                    "rows": rows,
                    "completed_at": now,
                },
            )
        if transport == "grpc_api":
            query = (
                f"LET collection <= collect_client(client_id='{asset_ref}', artifacts='{artifact}', env=dict()) "
                f"LET _ <= SELECT * FROM watch_monitoring(artifact='System.Flow.Completion') "
                f"WHERE FlowId = collection.flow_id LIMIT 1 "
                f"SELECT * FROM source(client_id=collection.request.client_id, flow_id=collection.flow_id, artifact='{artifact}')"
            )
            rows = self._run_api_query(binary_path, api_client_config, org_id, query, timeout_seconds)
            flow_id = self._extract_flow_id(rows) or flow_id
            return VelociraptorRunResult(
                flow_id=flow_id,
                status="completed",
                results={
                    "asset_ref": asset_ref,
                    "artifact": artifact,
                    "parameters": parameters or {},
                    "rows": rows,
                    "completed_at": now,
                    "transport": "grpc_api",
                },
            )
        if not base_url or not api_key:
            raise ValueError("Velociraptor HTTP mode requires base_url and api_key to be configured.")
        request_payload = {"client_id": asset_ref, "artifact": artifact, "parameters": parameters or {}}
        response_json = self._request("POST", base_url, run_path, api_key, verify_tls, json=request_payload)
        flow_id = str(response_json.get("flow_id") or response_json.get("id") or f"F.{uuid4()}")
        results = self.fetch_results(flow_id)
        return VelociraptorRunResult(flow_id=flow_id, status="completed", results=results)

    def get_flow_status(self, flow_id: str) -> dict:
        runtime_config = RuntimeConfigService().get_velociraptor_config()
        mode = runtime_config.get("mode", settings.velociraptor_mode)
        if mode == "mock":
            return {"flow_id": flow_id, "status": "completed"}
        if runtime_config.get("transport", "grpc_api") == "grpc_api":
            return {"flow_id": flow_id, "status": "completed", "transport": "grpc_api"}
        base_url = runtime_config.get("base_url", settings.velociraptor_base_url)
        api_key = runtime_config.get("api_key", settings.velociraptor_api_key)
        status_path = runtime_config.get("status_path", "/api/v1/flows/{flow_id}").replace("{flow_id}", flow_id)
        verify_tls = bool(runtime_config.get("verify_tls", True))
        return self._request("GET", base_url, status_path, api_key, verify_tls)

    def fetch_results(self, flow_id: str) -> dict:
        runtime_config = RuntimeConfigService().get_velociraptor_config()
        mode = runtime_config.get("mode", settings.velociraptor_mode)
        if mode == "mock":
            return {"flow_id": flow_id, "status": "completed"}
        if runtime_config.get("transport", "grpc_api") == "grpc_api":
            return {"flow_id": flow_id, "status": "completed", "transport": "grpc_api"}
        base_url = runtime_config.get("base_url", settings.velociraptor_base_url)
        api_key = runtime_config.get("api_key", settings.velociraptor_api_key)
        results_path = runtime_config.get("results_path", "/api/v1/flows/{flow_id}/results").replace("{flow_id}", flow_id)
        verify_tls = bool(runtime_config.get("verify_tls", True))
        return self._request("GET", base_url, results_path, api_key, verify_tls)

    def test_connection(self) -> dict:
        runtime_config = RuntimeConfigService().get_velociraptor_config()
        mode = runtime_config.get("mode", settings.velociraptor_mode)
        if mode == "mock":
            return {"ok": True, "mode": "mock", "detail": "Mock mode is enabled."}
        if runtime_config.get("transport", "grpc_api") == "grpc_api":
            rows = self._run_api_query(
                runtime_config.get("binary_path", "velociraptor"),
                runtime_config.get("api_client_config", ""),
                runtime_config.get("org_id", "root"),
                "SELECT client_id, os_info.fqdn AS fqdn FROM clients() LIMIT 1",
                int(runtime_config.get("timeout_seconds", 120)),
            )
            return {"ok": True, "mode": "live", "transport": "grpc_api", "detail": "Connection successful.", "rows": rows}
        base_url = runtime_config.get("base_url", settings.velociraptor_base_url)
        api_key = runtime_config.get("api_key", settings.velociraptor_api_key)
        verify_tls = bool(runtime_config.get("verify_tls", True))
        if not base_url or not api_key:
            raise ValueError("Velociraptor live mode requires base_url and api_key to be configured.")
        status = self._request("GET", base_url, "/", api_key, verify_tls)
        return {"ok": True, "mode": "live", "detail": "Connection successful.", "response": status}

    def _request(
        self,
        method: str,
        base_url: str,
        path: str,
        api_key: str,
        verify_tls: bool,
        json: dict | None = None,
    ) -> dict:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=20, verify=verify_tls) as client:
            response = client.request(method, url, headers=headers, json=json)
            response.raise_for_status()
            return response.json() if response.content else {"ok": True}

    def _run_api_query(self, binary_path: str, api_client_config: str, org_id: str, query: str, timeout_seconds: int) -> list[dict]:
        if not api_client_config:
            raise ValueError("Velociraptor gRPC API mode requires api_client_config.")
        config_path = api_client_config.strip()
        if not shutil.which(binary_path) and not os.path.exists(binary_path):
            raise ValueError(f"Velociraptor binary not found: {binary_path}")
        command = [binary_path, "--api_config", config_path, "query", "--format", "jsonl"]
        if org_id:
            command.extend(["--org", org_id])
        command.append(query)
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout_seconds)
        rows: list[dict] = []
        for line in completed.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    def _extract_flow_id(self, rows: list[dict]) -> str | None:
        for row in rows:
            for key in ("flow_id", "FlowId", "session_id"):
                value = row.get(key)
                if value:
                    return str(value)
        return None
