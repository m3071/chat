from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.security import require_internal_api_key
from app.core.secrets import SecretManager
from app.db.session import get_db
from app.models.entities import AiModel, AiProvider
from app.schemas.ai import AiModelCreate, AiModelRead, AiModelUpdate, AiProviderCreate, AiProviderRead, AiProviderUpdate

router = APIRouter(dependencies=[Depends(require_internal_api_key)])


def provider_read(provider: AiProvider) -> AiProviderRead:
    return AiProviderRead(
        id=provider.id,
        name=provider.name,
        label=provider.label,
        base_url=provider.base_url,
        has_api_key=bool(provider.api_key),
        is_active=provider.is_active,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def model_read(model: AiModel) -> AiModelRead:
    return AiModelRead(
        id=model.id,
        provider_id=model.provider_id,
        provider_name=model.provider.name if model.provider else "",
        model_name=model.model_name,
        label=model.label,
        purpose=model.purpose or [],
        supports_tools=model.supports_tools,
        supports_vision=model.supports_vision,
        is_default=model.is_default,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/providers", response_model=list[AiProviderRead])
def list_providers(db: Session = Depends(get_db)) -> list[AiProviderRead]:
    providers = db.scalars(select(AiProvider).order_by(AiProvider.name.asc())).all()
    return [provider_read(provider) for provider in providers]


@router.post("/providers", response_model=AiProviderRead)
def create_provider(payload: AiProviderCreate, db: Session = Depends(get_db)) -> AiProviderRead:
    values = payload.model_dump()
    values["api_key"] = SecretManager().encrypt(values.get("api_key"))
    provider = AiProvider(**values)
    db.add(provider)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="AI provider name already exists.") from exc
    db.refresh(provider)
    return provider_read(provider)


@router.patch("/providers/{provider_id}", response_model=AiProviderRead)
def update_provider(provider_id: UUID, payload: AiProviderUpdate, db: Session = Depends(get_db)) -> AiProviderRead:
    provider = db.get(AiProvider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "api_key":
            value = SecretManager().encrypt(value)
        setattr(provider, key, value)
    db.commit()
    db.refresh(provider)
    return provider_read(provider)


@router.get("/models", response_model=list[AiModelRead])
def list_models(db: Session = Depends(get_db)) -> list[AiModelRead]:
    models = db.scalars(select(AiModel).options(selectinload(AiModel.provider)).order_by(AiModel.created_at.asc())).all()
    return [model_read(model) for model in models]


@router.post("/models", response_model=AiModelRead)
def create_model(payload: AiModelCreate, db: Session = Depends(get_db)) -> AiModelRead:
    provider = db.get(AiProvider, payload.provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found.")
    model = AiModel(**payload.model_dump())
    db.add(model)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="AI model already exists for this provider.") from exc
    db.refresh(model)
    db.refresh(provider)
    model.provider = provider
    return model_read(model)


@router.patch("/models/{model_id}", response_model=AiModelRead)
def update_model(model_id: UUID, payload: AiModelUpdate, db: Session = Depends(get_db)) -> AiModelRead:
    model = db.scalar(select(AiModel).where(AiModel.id == model_id).options(selectinload(AiModel.provider)))
    if model is None:
        raise HTTPException(status_code=404, detail="AI model not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    db.commit()
    db.refresh(model)
    return model_read(model)
