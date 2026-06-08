from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Outlook, utcnow
from app.routers.dependencies import CurrentAnalyst, get_db
from app.schemas import OutlookGenerateRequest, OutlookRead, OutlookStatusUpdate
from app.services.outlook_engine import generate_outlooks

router = APIRouter(prefix="/outlooks", tags=["outlooks"])


@router.post("/generate", response_model=list[OutlookRead])
def create_outlooks(
    payload: OutlookGenerateRequest,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> list[OutlookRead]:
    horizons = sorted(set(payload.horizons))
    generated = generate_outlooks(db, horizons=horizons, owner_id=analyst.id)
    return [OutlookRead.model_validate(item) for item in generated]


@router.get("/published", response_model=list[OutlookRead])
def list_published_outlooks(
    db: Annotated[Session, Depends(get_db)],
    horizon_hours: int | None = None,
    limit: int = Query(default=50, le=200),
) -> list[OutlookRead]:
    """List all published outlooks (stakeholder feed)."""
    stmt = select(Outlook).where(Outlook.status == "published")
    if horizon_hours:
        stmt = stmt.where(Outlook.horizon_hours == horizon_hours)
    stmt = stmt.order_by(Outlook.generated_at.desc()).limit(limit)
    outlooks = db.scalars(stmt).all()
    return [OutlookRead.model_validate(item) for item in outlooks]


@router.get("", response_model=list[OutlookRead])
def list_outlooks(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    outlook_status: str | None = None,
    horizon_hours: int | None = None,
) -> list[OutlookRead]:
    stmt = select(Outlook).where(Outlook.owner_id == analyst.id)
    if outlook_status:
        stmt = stmt.where(Outlook.status == outlook_status)
    if horizon_hours:
        stmt = stmt.where(Outlook.horizon_hours == horizon_hours)
    stmt = stmt.order_by(Outlook.generated_at.desc())
    outlooks = db.scalars(stmt).all()
    return [OutlookRead.model_validate(item) for item in outlooks]


@router.get("/{outlook_id}", response_model=OutlookRead)
def get_outlook(
    outlook_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> OutlookRead:
    stmt = select(Outlook).where(Outlook.id == outlook_id, Outlook.owner_id == analyst.id)
    outlook = db.scalar(stmt)
    if outlook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlook not found")
    return OutlookRead.model_validate(outlook)


@router.patch("/{outlook_id}/status", response_model=OutlookRead)
def update_outlook_status(
    outlook_id: int,
    payload: OutlookStatusUpdate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> OutlookRead:
    """Update outlook status (draft -> reviewed -> published)."""
    stmt = select(Outlook).where(Outlook.id == outlook_id, Outlook.owner_id == analyst.id)
    outlook = db.scalar(stmt)
    if outlook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlook not found")

    # Validate status transitions
    valid_transitions = {
        "draft": ["reviewed", "published"],
        "reviewed": ["draft", "published"],
        "published": ["draft", "reviewed"],
    }
    if payload.status not in valid_transitions.get(outlook.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {outlook.status} to {payload.status}",
        )

    outlook.status = payload.status
    if payload.reviewer_notes:
        outlook.reviewer_notes = payload.reviewer_notes

    now = utcnow()
    if payload.status == "reviewed":
        outlook.reviewed_at = now
    elif payload.status == "published":
        outlook.published_at = now

    db.commit()
    db.refresh(outlook)
    return OutlookRead.model_validate(outlook)
