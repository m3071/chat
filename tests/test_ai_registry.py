import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "apps" / "api"))

from app.ai.model_registry import ModelRegistry  # noqa: E402
from app.models.entities import AiModel, AiProvider  # noqa: E402


def create_provider_and_models(db):
    provider = AiProvider(
        name="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key="secret-key",
        is_active=True,
    )
    db.add(provider)
    db.flush()
    fallback_model = AiModel(
        provider_id=provider.id,
        model_name="gpt-5-mini",
        label="GPT-5 Mini",
        purpose=["chat", "summary"],
        is_default=False,
        is_active=True,
    )
    default_model = AiModel(
        provider_id=provider.id,
        model_name="gpt-5.4",
        label="GPT-5.4",
        purpose=["summary", "triage_explanation"],
        is_default=True,
        is_active=True,
    )
    db.add_all([fallback_model, default_model])
    db.commit()
    return provider, fallback_model, default_model


def get_test_session(client):
    override = next(iter(client.app.dependency_overrides.values()))
    generator = override()
    return generator, next(generator)


def test_model_registry_prefers_default_model(client, monkeypatch):
    generator, session = get_test_session(client)
    try:
        _, _, default_model = create_provider_and_models(session)
        resolved = ModelRegistry().resolve_model(session, "summary")
        assert resolved.id == default_model.id
    finally:
        session.close()
        generator.close()


def test_model_registry_falls_back_to_any_active_model(client):
    generator, session = get_test_session(client)
    try:
        _, fallback_model, _ = create_provider_and_models(session)
        resolved = ModelRegistry().resolve_model(session, "chat")
        assert resolved.id == fallback_model.id
    finally:
        session.close()
        generator.close()


def test_model_registry_raises_for_missing_purpose(client):
    generator, session = get_test_session(client)
    try:
        create_provider_and_models(session)
        with pytest.raises(ValueError, match="No active AI model configured"):
            ModelRegistry().resolve_model(session, "does_not_exist")
    finally:
        session.close()
        generator.close()


def test_ai_provider_response_does_not_expose_api_key(client):
    response = client.post(
        "/api/ai/providers",
        json={
            "name": "openai",
            "label": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "api_key": "secret-key",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["has_api_key"] is True
    assert "api_key" not in payload

    providers_response = client.get("/api/ai/providers")
    assert providers_response.status_code == 200
    listed = providers_response.json()[0]
    assert listed["has_api_key"] is True
    assert "api_key" not in listed
