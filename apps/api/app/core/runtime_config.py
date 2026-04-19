from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.integration_registry import INTEGRATION_REGISTRY, POLICY_CATALOG, TOOL_CATALOG
from app.core.secrets import SecretManager


DEFAULT_RUNTIME_CONFIG = {
    "wazuh": {
        "credential_name": "Wazuh default credential",
        "connection_mode": "indexer_sync",
        "auth_type": "basic",
        "webhook_secret": settings.wazuh_shared_secret or "",
        "manager_url": "",
        "api_url": "",
        "api_username": "",
        "api_password": "",
        "indexer_url": "",
        "indexer_username": "",
        "indexer_password": "",
        "indexer_alert_index": "wazuh-alerts-*",
        "verify_tls": True,
    },
    "velociraptor": {
        "credential_name": "Velociraptor default credential",
        "credential_type": "mock",
        "auth_type": "api_client_config",
        "mode": settings.velociraptor_mode,
        "base_url": settings.velociraptor_base_url,
        "api_key": settings.velociraptor_api_key or "",
        "transport": "grpc_api",
        "api_client_config": "",
        "binary_path": "velociraptor",
        "org_id": "root",
        "timeout_seconds": 120,
        "run_path": "/api/v1/collect",
        "status_path": "/api/v1/flows/{flow_id}",
        "results_path": "/api/v1/flows/{flow_id}/results",
        "verify_tls": True,
    },
}


class RuntimeConfigService:
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or settings.runtime_config_path)

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return json.loads(json.dumps(DEFAULT_RUNTIME_CONFIG))
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return SecretManager().decrypt_config(self._merge_with_defaults(raw))

    def save(self, config: dict[str, Any]) -> dict[str, Any]:
        self._ensure_parent()
        merged = self._merge_with_defaults(config)
        encrypted = SecretManager().encrypt_config(merged)
        self.path.write_text(json.dumps(encrypted, indent=2), encoding="utf-8")
        return SecretManager().decrypt_config(encrypted)

    def update_section(self, section: str, values: dict[str, Any]) -> dict[str, Any]:
        config = self.load()
        config.setdefault(section, {})
        config[section].update(values)
        return self.save(config)

    def get_wazuh_webhook_secret(self) -> str | None:
        config = self.load()
        return (config.get("wazuh", {}) or {}).get("webhook_secret") or None

    def get_velociraptor_config(self) -> dict[str, Any]:
        config = self.load()
        return config.get("velociraptor", {}) or {}

    def public_view(self) -> dict[str, Any]:
        config = self.load()
        wazuh = config.get("wazuh", {}) or {}
        velociraptor = config.get("velociraptor", {}) or {}
        return {
            "wazuh": {
                "credential_name": wazuh.get("credential_name", "Wazuh default credential"),
                "connection_mode": wazuh.get("connection_mode", "indexer_sync"),
                "auth_type": wazuh.get("auth_type", "basic"),
                "webhook_secret_configured": bool(wazuh.get("webhook_secret")),
                "manager_url": wazuh.get("manager_url", "") or wazuh.get("api_url", ""),
                "api_url": wazuh.get("api_url", "") or wazuh.get("manager_url", ""),
                "api_username": wazuh.get("api_username", ""),
                "api_password_configured": bool(wazuh.get("api_password")),
                "api_key_configured": bool(wazuh.get("api_password")),
                "indexer_url": wazuh.get("indexer_url", ""),
                "indexer_username": wazuh.get("indexer_username", ""),
                "indexer_password_configured": bool(wazuh.get("indexer_password")),
                "indexer_alert_index": wazuh.get("indexer_alert_index", "wazuh-alerts-*"),
                "verify_tls": bool(wazuh.get("verify_tls", True)),
            },
            "velociraptor": {
                "credential_name": velociraptor.get("credential_name", "Velociraptor default credential"),
                "credential_type": velociraptor.get("credential_type", "mock"),
                "auth_type": velociraptor.get("auth_type", "api_client_config"),
                "mode": velociraptor.get("mode", "mock"),
                "transport": velociraptor.get("transport", "grpc_api"),
                "base_url": velociraptor.get("base_url", ""),
                "api_key_configured": bool(velociraptor.get("api_key")),
                "api_client_config": velociraptor.get("api_client_config", ""),
                "binary_path": velociraptor.get("binary_path", "velociraptor"),
                "org_id": velociraptor.get("org_id", "root"),
                "timeout_seconds": int(velociraptor.get("timeout_seconds", 120)),
                "run_path": velociraptor.get("run_path", "/api/v1/collect"),
                "status_path": velociraptor.get("status_path", "/api/v1/flows/{flow_id}"),
                "results_path": velociraptor.get("results_path", "/api/v1/flows/{flow_id}/results"),
                "verify_tls": bool(velociraptor.get("verify_tls", True)),
            },
        }

    def full_view(self) -> dict[str, Any]:
        return self.load()

    def update_integration(self, integration_id: str, values: dict[str, Any]) -> dict[str, Any]:
        if integration_id not in INTEGRATION_REGISTRY:
            raise ValueError(f"Unsupported integration: {integration_id}")
        return self.update_section(integration_id, values)

    def catalog_view(self) -> dict[str, Any]:
        config = self.load()
        integrations: list[dict[str, Any]] = []
        for integration_id, definition in INTEGRATION_REGISTRY.items():
            integration_config = config.get(integration_id, {}) or {}
            configured = any(
                bool(integration_config.get(field["key"]))
                for field in definition.get("fields", [])
                if field.get("input") != "checkbox"
            )
            integrations.append(
                {
                    **definition,
                    "status": "configured" if configured else "not_configured",
                    "enabled": True,
                    "config": self._public_integration_config(integration_config),
                }
            )
        return {
            "integrations": integrations,
            "tools": TOOL_CATALOG,
            "policies": POLICY_CATALOG,
        }

    def _merge_with_defaults(self, config: dict[str, Any]) -> dict[str, Any]:
        merged = json.loads(json.dumps(DEFAULT_RUNTIME_CONFIG))
        for section, values in config.items():
            if isinstance(values, dict):
                merged.setdefault(section, {})
                merged[section].update(values)
            else:
                merged[section] = values
        return merged

    def _public_integration_config(self, config: dict[str, Any]) -> dict[str, Any]:
        public = {}
        for key, value in config.items():
            if key in {"api_key", "api_password", "webhook_secret", "password", "secret", "token"}:
                public[f"{key}_configured"] = bool(value)
            else:
                public[key] = value
        return public
