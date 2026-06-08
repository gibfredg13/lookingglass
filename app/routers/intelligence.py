"""
Intelligence sources and monitoring router.
Handles:
- Source configuration (RSS feeds, APIs)
- Raw item ingestion
- AI processing pipeline
- Signal detection
"""
from datetime import datetime, timezone
from typing import Annotated
import json

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.routers.dependencies import CurrentAnalyst, get_db
from app.models import IntelligenceSource, RawIntelItem, Signal, PriorityArea, Event
from app.services.intelligence import IntelligenceService, seed_demo_sources

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ============================================================================
# Schemas
# ============================================================================

class SourceCreate(BaseModel):
    name: str
    source_type: str = "rss"
    url: str | None = None
    api_key: str | None = None
    check_interval_minutes: int = 15
    reliability_score: float = 0.7
    default_region: str | None = None
    default_theme: str | None = None
    priority_keywords: list[str] | None = None


class SourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    url: str | None
    is_active: bool
    status: str
    reliability_score: float
    default_region: str | None
    default_theme: str | None
    last_checked_at: datetime | None
    last_error: str | None
    item_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class RawItemResponse(BaseModel):
    id: int
    source_id: int
    source_name: str
    title: str
    content: str
    url: str | None
    published_at: datetime | None
    fetched_at: datetime
    is_processed: bool
    is_relevant: bool | None
    is_duplicate: bool
    ai_summary: str | None
    ai_region: str | None
    ai_country: str | None
    ai_theme: str | None
    ai_severity: int | None
    ai_confidence: float | None
    ai_tags: list[str]
    event_id: int | None

    model_config = ConfigDict(from_attributes=True)


class SignalResponse(BaseModel):
    id: int
    title: str
    description: str
    signal_type: str
    severity: str
    confidence: float
    region: str
    countries: list[str]
    themes: list[str]
    evidence_summary: str
    key_indicators: str
    watch_for: str
    detected_at: datetime
    expires_at: datetime | None
    is_active: bool
    is_acknowledged: bool
    analyst_notes: str | None

    model_config = ConfigDict(from_attributes=True)


class PriorityAreaCreate(BaseModel):
    name: str
    description: str
    regions: list[str]
    countries: list[str] | None = None
    themes: list[str]
    keywords: list[str]
    severity_threshold: int = 3
    alert_on_new_events: bool = True


class PriorityAreaResponse(BaseModel):
    id: int
    name: str
    description: str
    regions: list[str]
    themes: list[str]
    keywords: list[str]
    severity_threshold: int
    alert_on_new_events: bool
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class FetchResult(BaseModel):
    source_id: int
    source_name: str
    items_fetched: int
    items_new: int


class ProcessResult(BaseModel):
    items_processed: int
    events_created: int
    duplicates_found: int


class DetectionResult(BaseModel):
    events_analyzed: int
    signals_detected: int


# ============================================================================
# Sources Endpoints
# ============================================================================

@router.get("/sources", response_model=list[SourceResponse])
def list_sources(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    active_only: bool = False
):
    """List all configured intelligence sources."""
    query = db.query(IntelligenceSource)
    if active_only:
        query = query.filter(IntelligenceSource.is_active == True)

    sources = query.order_by(IntelligenceSource.name).all()

    result = []
    for source in sources:
        item_count = db.query(RawIntelItem).filter(
            RawIntelItem.source_id == source.id
        ).count()

        resp = SourceResponse(
            id=source.id,
            name=source.name,
            source_type=source.source_type,
            url=source.url,
            is_active=source.is_active,
            status=source.status,
            reliability_score=source.reliability_score,
            default_region=source.default_region,
            default_theme=source.default_theme,
            last_checked_at=source.last_checked_at,
            last_error=source.last_error,
            item_count=item_count
        )
        result.append(resp)

    return result


@router.post("/sources", response_model=SourceResponse, status_code=201)
def create_source(
    data: SourceCreate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new intelligence source."""
    source = IntelligenceSource(
        name=data.name,
        source_type=data.source_type,
        url=data.url,
        api_key=data.api_key,
        check_interval_minutes=data.check_interval_minutes,
        reliability_score=data.reliability_score,
        default_region=data.default_region,
        default_theme=data.default_theme,
        priority_keywords=json.dumps(data.priority_keywords) if data.priority_keywords else None,
        created_by_id=analyst.id
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    return SourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        url=source.url,
        is_active=source.is_active,
        status=source.status,
        reliability_score=source.reliability_score,
        default_region=source.default_region,
        default_theme=source.default_theme,
        last_checked_at=source.last_checked_at,
        last_error=source.last_error,
        item_count=0
    )


@router.post("/sources/seed-demo", response_model=list[SourceResponse])
def seed_sources(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Seed demo intelligence sources (Reuters, BBC, Al Jazeera)."""
    sources = seed_demo_sources(db)

    all_sources = db.query(IntelligenceSource).all()
    return [
        SourceResponse(
            id=s.id,
            name=s.name,
            source_type=s.source_type,
            url=s.url,
            is_active=s.is_active,
            status=s.status,
            reliability_score=s.reliability_score,
            default_region=s.default_region,
            default_theme=s.default_theme,
            last_checked_at=s.last_checked_at,
            last_error=s.last_error,
            item_count=0
        )
        for s in all_sources
    ]


@router.post("/sources/{source_id}/fetch", response_model=FetchResult)
async def fetch_source(
    source_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Fetch new items from a source."""
    source = db.query(IntelligenceSource).filter(
        IntelligenceSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    service = IntelligenceService(db)

    try:
        items = await service.fetch_source(source)
        total_items = db.query(RawIntelItem).filter(
            RawIntelItem.source_id == source_id
        ).count()

        return FetchResult(
            source_id=source.id,
            source_name=source.name,
            items_fetched=total_items,
            items_new=len(items)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Delete an intelligence source."""
    source = db.query(IntelligenceSource).filter(
        IntelligenceSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    db.delete(source)
    db.commit()

    return {"status": "deleted", "source_id": source_id}


# ============================================================================
# Raw Items Endpoints
# ============================================================================

@router.get("/items", response_model=list[RawItemResponse])
def list_raw_items(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    source_id: int | None = None,
    processed: bool | None = None,
    relevant: bool | None = None,
    limit: int = Query(default=50, le=200)
):
    """List raw intelligence items."""
    query = db.query(RawIntelItem)

    if source_id:
        query = query.filter(RawIntelItem.source_id == source_id)
    if processed is not None:
        query = query.filter(RawIntelItem.is_processed == processed)
    if relevant is not None:
        query = query.filter(RawIntelItem.is_relevant == relevant)

    items = query.order_by(RawIntelItem.fetched_at.desc()).limit(limit).all()

    return [
        RawItemResponse(
            id=item.id,
            source_id=item.source_id,
            source_name=item.source.name,
            title=item.title,
            content=item.content[:500],
            url=item.url,
            published_at=item.published_at,
            fetched_at=item.fetched_at,
            is_processed=item.is_processed,
            is_relevant=item.is_relevant,
            is_duplicate=item.is_duplicate,
            ai_summary=item.ai_summary,
            ai_region=item.ai_region,
            ai_country=item.ai_country,
            ai_theme=item.ai_theme,
            ai_severity=item.ai_severity,
            ai_confidence=item.ai_confidence,
            ai_tags=json.loads(item.ai_tags) if item.ai_tags else [],
            event_id=item.event_id
        )
        for item in items
    ]


@router.post("/items/{item_id}/process")
async def process_item(
    item_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Process a raw item through AI analysis."""
    item = db.query(RawIntelItem).filter(RawIntelItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    service = IntelligenceService(db)
    analysis = await service.process_item(item)

    return {
        "item_id": item.id,
        "analysis": analysis
    }


@router.post("/items/{item_id}/promote")
async def promote_item(
    item_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Promote a raw item to a full Event."""
    item = db.query(RawIntelItem).filter(RawIntelItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    service = IntelligenceService(db)
    event = await service.promote_to_event(item, analyst.id)

    return {
        "item_id": item.id,
        "event_id": event.id,
        "is_duplicate": item.is_duplicate,
        "event_title": event.title
    }


@router.post("/items/process-batch", response_model=ProcessResult)
async def process_batch(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=10, le=50),
    auto_promote: bool = True
):
    """Process a batch of unprocessed items."""
    items = db.query(RawIntelItem).filter(
        RawIntelItem.is_processed == False
    ).limit(limit).all()

    service = IntelligenceService(db)

    events_created = 0
    duplicates = 0

    for item in items:
        await service.process_item(item)

        if auto_promote and item.is_relevant:
            event = await service.promote_to_event(item, analyst.id)
            if item.is_duplicate:
                duplicates += 1
            else:
                events_created += 1

    return ProcessResult(
        items_processed=len(items),
        events_created=events_created,
        duplicates_found=duplicates
    )


# ============================================================================
# Signals Endpoints
# ============================================================================

@router.get("/signals", response_model=list[SignalResponse])
def list_signals(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    active_only: bool = True,
    severity: str | None = None,
    region: str | None = None
):
    """List detected signals."""
    query = db.query(Signal)

    if active_only:
        query = query.filter(Signal.is_active == True)
    if severity:
        query = query.filter(Signal.severity == severity)
    if region:
        query = query.filter(Signal.region == region)

    signals = query.order_by(Signal.detected_at.desc()).all()

    return [
        SignalResponse(
            id=s.id,
            title=s.title,
            description=s.description,
            signal_type=s.signal_type,
            severity=s.severity,
            confidence=s.confidence,
            region=s.region,
            countries=json.loads(s.countries) if s.countries else [],
            themes=json.loads(s.themes) if s.themes else [],
            evidence_summary=s.evidence_summary,
            key_indicators=s.key_indicators,
            watch_for=s.watch_for,
            detected_at=s.detected_at,
            expires_at=s.expires_at,
            is_active=s.is_active,
            is_acknowledged=s.is_acknowledged,
            analyst_notes=s.analyst_notes
        )
        for s in signals
    ]


@router.post("/signals/detect", response_model=DetectionResult)
async def run_signal_detection(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Run signal detection on recent events."""
    service = IntelligenceService(db)
    result = await service.run_detection_cycle()

    return DetectionResult(
        events_analyzed=result["events_analyzed"],
        signals_detected=result["signals_detected"]
    )


@router.post("/signals/{signal_id}/acknowledge")
def acknowledge_signal(
    signal_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    notes: str | None = None
):
    """Acknowledge a signal."""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    signal.is_acknowledged = True
    signal.acknowledged_by_id = analyst.id
    if notes:
        signal.analyst_notes = notes

    db.commit()

    return {"status": "acknowledged", "signal_id": signal_id}


# ============================================================================
# Priority Areas Endpoints
# ============================================================================

@router.get("/priority-areas", response_model=list[PriorityAreaResponse])
def list_priority_areas(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """List priority monitoring areas."""
    areas = db.query(PriorityArea).filter(
        PriorityArea.owner_id == analyst.id
    ).all()

    return [
        PriorityAreaResponse(
            id=a.id,
            name=a.name,
            description=a.description,
            regions=json.loads(a.regions),
            themes=json.loads(a.themes),
            keywords=json.loads(a.keywords),
            severity_threshold=a.severity_threshold,
            alert_on_new_events=a.alert_on_new_events,
            is_active=a.is_active
        )
        for a in areas
    ]


@router.post("/priority-areas", response_model=PriorityAreaResponse, status_code=201)
def create_priority_area(
    data: PriorityAreaCreate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Create a priority monitoring area."""
    area = PriorityArea(
        name=data.name,
        description=data.description,
        regions=json.dumps(data.regions),
        countries=json.dumps(data.countries) if data.countries else None,
        themes=json.dumps(data.themes),
        keywords=json.dumps(data.keywords),
        severity_threshold=data.severity_threshold,
        alert_on_new_events=data.alert_on_new_events,
        owner_id=analyst.id
    )
    db.add(area)
    db.commit()
    db.refresh(area)

    return PriorityAreaResponse(
        id=area.id,
        name=area.name,
        description=area.description,
        regions=json.loads(area.regions),
        themes=json.loads(area.themes),
        keywords=json.loads(area.keywords),
        severity_threshold=area.severity_threshold,
        alert_on_new_events=area.alert_on_new_events,
        is_active=area.is_active
    )






