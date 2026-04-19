from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import AiModel


class ModelRegistry:
    def resolve_model(self, db: Session, purpose: str) -> AiModel:
        requested = purpose.strip().lower()
        if not requested:
            raise ValueError("AI model purpose is required.")

        models = db.scalars(
            select(AiModel)
            .options(selectinload(AiModel.provider))
            .where(AiModel.is_active.is_(True))
            .order_by(AiModel.is_default.desc(), AiModel.created_at.asc())
        ).all()
        candidates = [
            model
            for model in models
            if model.provider is not None
            and model.provider.is_active
            and requested in [item.strip().lower() for item in (model.purpose or [])]
        ]
        if not candidates:
            raise ValueError(f"No active AI model configured for purpose '{requested}'.")
        defaults = [model for model in candidates if model.is_default]
        return defaults[0] if defaults else candidates[0]
