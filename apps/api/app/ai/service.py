from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai.model_registry import ModelRegistry
from app.ai.provider_factory import ProviderFactory


class AIService:
    def __init__(self) -> None:
        self.registry = ModelRegistry()
        self.providers = ProviderFactory()

    def generate_for_purpose(
        self,
        db: Session,
        *,
        purpose: str,
        messages: list[dict],
        fallback_text: str | None = None,
    ) -> str:
        try:
            model = self.registry.resolve_model(db, purpose)
        except ValueError:
            if fallback_text is not None:
                return fallback_text
            raise

        client = self.providers.create(model.provider)
        return client.generate(model_name=model.model_name, messages=messages)
