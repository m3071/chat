from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "apps" / "api"))

from app.db.session import SessionLocal
from app.models.entities import AiModel, AiProvider


PROVIDERS = [
    {"name": "openai", "label": "OpenAI", "base_url": "https://api.openai.com/v1"},
    {"name": "openrouter", "label": "OpenRouter", "base_url": "https://openrouter.ai/api/v1"},
    {"name": "ollama", "label": "Ollama", "base_url": "http://host.docker.internal:11434/v1"},
]

MODELS = [
    {"provider": "openai", "model_name": "gpt-5-mini", "label": "GPT-5 Mini", "purpose": ["chat", "summary"], "supports_tools": True, "is_default": True},
    {"provider": "openai", "model_name": "gpt-5.4", "label": "GPT-5.4", "purpose": ["summary", "triage_explanation"], "supports_tools": True, "is_default": True},
    {"provider": "ollama", "model_name": "llama3.1:8b", "label": "Llama 3.1 8B", "purpose": ["chat"], "supports_tools": False, "is_default": False},
]


def main() -> None:
    with SessionLocal() as db:
        providers: dict[str, AiProvider] = {}
        for item in PROVIDERS:
            provider = db.scalar(select(AiProvider).where(AiProvider.name == item["name"]))
            if provider is None:
                provider = AiProvider(**item, api_key=None, is_active=True)
                db.add(provider)
                db.flush()
            providers[provider.name] = provider

        for item in MODELS:
            provider = providers[item["provider"]]
            existing = db.scalar(
                select(AiModel).where(AiModel.provider_id == provider.id, AiModel.model_name == item["model_name"])
            )
            if existing is None:
                db.add(
                    AiModel(
                        provider_id=provider.id,
                        model_name=item["model_name"],
                        label=item["label"],
                        purpose=item["purpose"],
                        supports_tools=item["supports_tools"],
                        supports_vision=False,
                        is_default=item["is_default"],
                        is_active=True,
                    )
                )
        db.commit()
    print("AI provider/model seed complete.")


if __name__ == "__main__":
    main()
