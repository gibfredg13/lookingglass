from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.routers.dependencies import CurrentAnalyst, get_db
from app.schemas import AskAnythingHistoryRead, AskAnythingRequest, AskAnythingResponse
from app.services.ask_anything import ask_anything, get_query_history

router = APIRouter(prefix="/ask", tags=["ask-anything"])


@router.post("", response_model=AskAnythingResponse)
def ask_question(
    payload: AskAnythingRequest,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> AskAnythingResponse:
    """Ask a natural-language question about events, outlooks, and scenarios."""
    result = ask_anything(db, payload.question, analyst.id)
    return AskAnythingResponse(**result)


@router.get("/history", response_model=list[AskAnythingHistoryRead])
def list_history(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=20, le=100),
) -> list[AskAnythingHistoryRead]:
    """Get Q&A history for the current analyst."""
    queries = get_query_history(db, analyst.id, limit)
    return [AskAnythingHistoryRead.model_validate(q) for q in queries]

