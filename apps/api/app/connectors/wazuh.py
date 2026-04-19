from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.runtime_config import RuntimeConfigService
from app.schemas.wazuh import WazuhAgentPayload, WazuhAlertPayload, WazuhDataPayload, WazuhRulePayload


@dataclass
class NormalizedWazuhAlert:
    external_id: str
    severity: int
    title: str
    rule_id: str
    rule_group: str
    rule_description: str | None
    event_time: str
    asset_external_id: str
    hostname: str
    ip_addresses: list[str]
    normalized_payload: dict


class WazuhConnector:
    source = "wazuh"

    def normalize_alert(self, payload: WazuhAlertPayload) -> NormalizedWazuhAlert:
        agent_id = payload.agent.id if payload.agent and payload.agent.id else "unknown-agent"
        hostname = payload.agent.name if payload.agent and payload.agent.name else payload.location or "unknown-host"
        rule_group = payload.rule.groups[0] if payload.rule.groups else "uncategorized"
        ip_addresses = [
            ip
            for ip in [payload.data.srcip if payload.data else None, payload.data.destip if payload.data else None]
            if ip
        ]

        return NormalizedWazuhAlert(
            external_id=payload.id or f"{agent_id}:{payload.timestamp.isoformat()}",
            severity=payload.rule.level,
            title=payload.rule.description or f"Wazuh alert {payload.rule.id}",
            rule_id=payload.rule.id,
            rule_group=rule_group,
            rule_description=payload.rule.description,
            event_time=payload.timestamp.isoformat(),
            asset_external_id=agent_id,
            hostname=hostname,
            ip_addresses=ip_addresses,
            normalized_payload={
                "hostname": hostname,
                "agent_id": agent_id,
                "rule_groups": payload.rule.groups,
                "location": payload.location,
                "decoder": payload.decoder,
                "manager": payload.manager,
            },
        )

    def test_connection(self) -> dict:
        config = RuntimeConfigService().load().get("wazuh", {}) or {}
        api_url = (config.get("api_url") or config.get("manager_url") or "").strip()
        username = (config.get("api_username") or "").strip()
        password = (config.get("api_password") or "").strip()
        verify_tls = bool(config.get("verify_tls", True))

        indexer_url = (config.get("indexer_url") or "").strip()
        indexer_username = (config.get("indexer_username") or "").strip()
        indexer_password = (config.get("indexer_password") or "").strip()

        if not api_url and not indexer_url:
            return {"ok": True, "detail": "Webhook-only mode configured. No outbound Wazuh connection required."}
        results: dict = {"ok": True, "detail": "Connection successful."}

        if indexer_url:
            if not indexer_username or not indexer_password:
                raise ValueError("Wazuh Indexer sync requires indexer_url, indexer_username, and indexer_password.")
            with httpx.Client(base_url=indexer_url.rstrip("/"), timeout=20, verify=verify_tls) as client:
                response = client.get("/", auth=(indexer_username, indexer_password))
                response.raise_for_status()
                payload = response.json() if response.content else {}
            results["indexer"] = {"connected": True, "cluster_name": payload.get("cluster_name"), "version": payload.get("version")}

        if not api_url:
            return results
        if not username or not password:
            raise ValueError("Wazuh live mode requires api_url, api_username, and api_password.")

        base_url = api_url.rstrip("/")
        with httpx.Client(base_url=base_url, timeout=20, verify=verify_tls) as client:
            token_response = client.get("/security/user/authenticate", auth=(username, password), params={"raw": "true"})
            token_response.raise_for_status()
            token = token_response.text.strip().strip('"')
            if not token:
                raise ValueError("Wazuh authentication succeeded but returned an empty JWT.")
            summary_response = client.get("/agents/summary/status", headers={"Authorization": f"Bearer {token}"})
            summary_response.raise_for_status()
            summary = summary_response.json() if summary_response.content else {}

        results.update({"auth": "jwt", "agents_summary": summary.get("data", summary)})
        return results

    def fetch_recent_alerts(self, limit: int = 25) -> list[WazuhAlertPayload]:
        config = RuntimeConfigService().load().get("wazuh", {}) or {}
        indexer_url = (config.get("indexer_url") or "").strip()
        username = (config.get("indexer_username") or "").strip()
        password = (config.get("indexer_password") or "").strip()
        index = (config.get("indexer_alert_index") or "wazuh-alerts-*").strip()
        verify_tls = bool(config.get("verify_tls", True))
        if not indexer_url or not username or not password:
            raise ValueError("Configure Wazuh Indexer URL, username, and password before syncing alerts.")

        query = {
            "size": max(1, min(limit, 200)),
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {"match_all": {}},
        }
        with httpx.Client(base_url=indexer_url.rstrip("/"), timeout=30, verify=verify_tls) as client:
            response = client.post(f"/{index}/_search", auth=(username, password), json=query)
            response.raise_for_status()
            payload = response.json()

        hits = (((payload or {}).get("hits") or {}).get("hits") or [])
        return [self._source_to_payload(item) for item in hits if isinstance(item, dict)]

    def _source_to_payload(self, hit: dict) -> WazuhAlertPayload:
        source = hit.get("_source") or {}
        rule = source.get("rule") or {}
        agent = source.get("agent") or {}
        data = source.get("data") or {}
        timestamp = source.get("@timestamp") or source.get("timestamp") or datetime.now(UTC).isoformat()
        groups = rule.get("groups") or []
        if isinstance(groups, str):
            groups = [groups]
        return WazuhAlertPayload(
            id=str(source.get("id") or hit.get("_id") or f"indexer:{agent.get('id', 'unknown')}:{timestamp}"),
            timestamp=datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")),
            rule=WazuhRulePayload(
                id=str(rule.get("id") or rule.get("rule_id") or "unknown-rule"),
                level=int(rule.get("level") or source.get("level") or source.get("severity") or 3),
                description=rule.get("description") or source.get("message") or source.get("full_log") or "Wazuh indexer alert",
                groups=[str(item) for item in groups],
            ),
            agent=WazuhAgentPayload(id=str(agent.get("id") or "unknown-agent"), name=agent.get("name") or source.get("host", {}).get("name")),
            data=WazuhDataPayload(srcip=data.get("srcip") or data.get("src_ip"), destip=data.get("destip") or data.get("dst_ip")),
            full_log=source.get("full_log") or source.get("message"),
            decoder=source.get("decoder"),
            location=source.get("location"),
            manager=source.get("manager"),
        )
