from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.db.session import get_db
from app.models import User
from app.schemas.chat import ChatRequest
from app.services.ai_assistant import run_assistant
from app.utils.response import success_response

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    AI shopping assistant. Works for guests (search/browse) and logged-in
    users (search/browse + add to cart). The client sends the full
    conversation each time (stateless) - same pattern as any other Claude
    API integration; there's no server-side chat history storage here.
    """
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    result = run_assistant(db, current_user, messages, product_slug=payload.product_slug)
    return success_response(result)
