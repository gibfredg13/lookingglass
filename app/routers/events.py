from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Event,
    EventTimelineEntry,
    Source,
    Tag,
    compute_event_fingerprint,
    utcnow,
)
from app.routers.dependencies import CurrentAnalyst, get_db
from app.schemas import (
    DuplicateEventResponse,
    EventCreate,
    EventPublishRequest,
    EventRead,
    TimelineEntryRead,
)

router = APIRouter(prefix="/events", tags=["events"])


def _fetch_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    clean_names = sorted(set(name.strip().lower() for name in names if name.strip()))
    if not clean_names:
        return []

    existing = db.scalars(select(Tag).where(Tag.name.in_(clean_names))).all()
    existing_by_name = {tag.name: tag for tag in existing}

    tags: list[Tag] = []
    for name in clean_names:
        tag = existing_by_name.get(name)
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def _to_event_read(event: Event) -> EventRead:
    return EventRead(
        id=event.id,
        title=event.title,
        summary=event.summary,
        region=event.region,
        country=event.country,
        theme=event.theme,
        sector=event.sector,
        risk_type=event.risk_type,
        severity=event.severity,
        confidence=event.confidence,
        occurred_at=event.occurred_at,
        created_at=event.created_at,
        fingerprint=event.fingerprint,
        owner_id=event.owner_id,
        is_published=event.is_published,
        published_at=event.published_at,
        is_ai_generated=event.is_ai_generated or False,
        tags=[tag.name for tag in event.tags],
        sources=event.sources,
        timeline=[TimelineEntryRead.model_validate(e) for e in event.timeline_entries],
    )


def _check_duplicate(db: Session, fingerprint: str, owner_id: int | None) -> Event | None:
    stmt = select(Event).where(Event.fingerprint == fingerprint, Event.owner_id == owner_id)
    return db.scalar(stmt)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> EventRead:
    fingerprint = compute_event_fingerprint(payload.title, payload.region, payload.occurred_at)
    existing = _check_duplicate(db, fingerprint, analyst.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate event detected (existing id={existing.id})",
        )

    event = Event(
        title=payload.title,
        summary=payload.summary,
        region=payload.region,
        country=payload.country,
        theme=payload.theme,
        sector=payload.sector,
        risk_type=payload.risk_type,
        severity=payload.severity,
        confidence=payload.confidence,
        occurred_at=payload.occurred_at,
        fingerprint=fingerprint,
        owner_id=analyst.id,
    )
    event.tags = _fetch_or_create_tags(db, payload.tags)

    for source in payload.sources:
        event.sources.append(
            Source(
                name=source.name,
                url=str(source.url) if source.url else None,
                reliability=source.reliability,
            )
        )

    event.timeline_entries.append(EventTimelineEntry(description="Event created"))

    db.add(event)
    db.commit()
    db.refresh(event)
    return _to_event_read(event)


@router.get("/check-duplicate", response_model=DuplicateEventResponse)
def check_duplicate(
    title: str,
    region: str,
    occurred_at: str,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> DuplicateEventResponse:
    try:
        dt = datetime.fromisoformat(occurred_at)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid occurred_at format")

    fingerprint = compute_event_fingerprint(title, region, dt)
    existing = _check_duplicate(db, fingerprint, analyst.id)
    if existing:
        return DuplicateEventResponse(duplicate=True, existing_event_id=existing.id, message="Duplicate found")
    return DuplicateEventResponse(duplicate=False, message="No duplicate")


@router.get("/published", response_model=list[EventRead])
def list_published_events(
    db: Annotated[Session, Depends(get_db)],
    region: str | None = None,
    theme: str | None = None,
    sector: str | None = None,
    severity_min: int | None = Query(default=None, ge=1, le=5),
    severity_max: int | None = Query(default=None, ge=1, le=5),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
) -> list[EventRead]:
    """List all published events (public feed for stakeholders)."""
    stmt = (
        select(Event)
        .where(Event.is_published == True)
        .options(selectinload(Event.tags), selectinload(Event.sources), selectinload(Event.timeline_entries))
    )

    if region:
        stmt = stmt.where(Event.region == region)
    if theme:
        stmt = stmt.where(Event.theme == theme)
    if sector:
        stmt = stmt.where(Event.sector == sector)
    if severity_min:
        stmt = stmt.where(Event.severity >= severity_min)
    if severity_max:
        stmt = stmt.where(Event.severity <= severity_max)
    if date_from:
        stmt = stmt.where(Event.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(Event.occurred_at <= date_to)
    if q:
        stmt = stmt.where(or_(Event.title.ilike(f"%{q}%"), Event.summary.ilike(f"%{q}%")))

    stmt = stmt.order_by(Event.occurred_at.desc()).offset(offset).limit(limit)
    events = db.scalars(stmt).all()
    return [_to_event_read(event) for event in events]


@router.get("", response_model=list[EventRead])
def list_events(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    region: str | None = None,
    theme: str | None = None,
    sector: str | None = None,
    risk_type: str | None = None,
    severity_min: int | None = Query(default=None, ge=1, le=5),
    severity_max: int | None = Query(default=None, ge=1, le=5),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    is_published: bool | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
) -> list[EventRead]:
    """List events in analyst's workspace with search/filter."""
    stmt = (
        select(Event)
        .where(Event.owner_id == analyst.id)
        .options(selectinload(Event.tags), selectinload(Event.sources), selectinload(Event.timeline_entries))
    )

    if region:
        stmt = stmt.where(Event.region == region)
    if theme:
        stmt = stmt.where(Event.theme == theme)
    if sector:
        stmt = stmt.where(Event.sector == sector)
    if risk_type:
        stmt = stmt.where(Event.risk_type == risk_type)
    if severity_min:
        stmt = stmt.where(Event.severity >= severity_min)
    if severity_max:
        stmt = stmt.where(Event.severity <= severity_max)
    if date_from:
        stmt = stmt.where(Event.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(Event.occurred_at <= date_to)
    if is_published is not None:
        stmt = stmt.where(Event.is_published == is_published)
    if q:
        stmt = stmt.where(or_(Event.title.ilike(f"%{q}%"), Event.summary.ilike(f"%{q}%")))

    stmt = stmt.order_by(Event.occurred_at.desc()).offset(offset).limit(limit)
    events = db.scalars(stmt).all()
    return [_to_event_read(event) for event in events]


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: int, analyst: CurrentAnalyst, db: Annotated[Session, Depends(get_db)]) -> EventRead:
    stmt = (
        select(Event)
        .where(Event.id == event_id, Event.owner_id == analyst.id)
        .options(selectinload(Event.tags), selectinload(Event.sources), selectinload(Event.timeline_entries))
    )
    event = db.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return _to_event_read(event)


@router.patch("/{event_id}/publish", response_model=EventRead)
def publish_event(
    event_id: int,
    payload: EventPublishRequest,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> EventRead:
    """Publish or unpublish an event to stakeholder feed."""
    stmt = (
        select(Event)
        .where(Event.id == event_id, Event.owner_id == analyst.id)
        .options(selectinload(Event.tags), selectinload(Event.sources), selectinload(Event.timeline_entries))
    )
    event = db.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    event.is_published = payload.publish
    event.published_at = utcnow() if payload.publish else None

    action = "published" if payload.publish else "unpublished"
    event.timeline_entries.append(EventTimelineEntry(description=f"Event {action}"))

    db.commit()
    db.refresh(event)
    return _to_event_read(event)


@router.post("/{event_id}/timeline", response_model=TimelineEntryRead, status_code=status.HTTP_201_CREATED)
def add_timeline_entry(
    event_id: int,
    description: str,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> TimelineEntryRead:
    stmt = select(Event).where(Event.id == event_id, Event.owner_id == analyst.id)
    event = db.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    entry = EventTimelineEntry(event_id=event.id, description=description)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return TimelineEntryRead.model_validate(entry)
