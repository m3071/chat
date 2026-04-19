from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.chat_service import ChatService
from app.core.security import require_internal_api_key
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
chat_service = ChatService()


@router.post("", response_model=ChatResponse, dependencies=[Depends(require_internal_api_key)])
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    response = chat_service.handle(db, request)
    db.commit()
    return response
