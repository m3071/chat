from __future__ import annotations

import httpx

from app.core.secrets import SecretManager
from app.models.entities import AiProvider


def redact_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


class OpenAICompatibleClient:
    def __init__(self, provider: AiProvider) -> None:
        self.provider = provider

    def generate(self, *, model_name: str, messages: list[dict], temperature: float = 0.2) -> str:
        url = f"{self.provider.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        api_key = SecretManager().decrypt(self.provider.api_key)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"model": model_name, "messages": messages, "temperature": temperature}
        with httpx.Client(timeout=45) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Provider returned an unsupported chat completion response.") from exc


class ProviderFactory:
    def create(self, provider: AiProvider) -> OpenAICompatibleClient:
        if not provider.base_url:
            raise ValueError(f"Provider {provider.name} has no base_url configured.")
        return OpenAICompatibleClient(provider)
