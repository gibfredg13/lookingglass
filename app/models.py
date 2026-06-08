from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


event_tags = Table(
    "event_tags",
    Base.metadata,
    Column("event_id", ForeignKey("events.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class OutlookStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"


class ScenarioCaseType(str, Enum):
    BASELINE = "baseline"
    UPSIDE = "upside"
    DOWNSIDE = "downside"


class AnalystRole(str, Enum):
    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    ADMIN = "admin"


class IntelSourceType(str, Enum):
    RSS = "rss"
    API = "api"
    MANUAL = "manual"
    TWITTER = "twitter"
    TELEGRAM = "telegram"


class IntelSourceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class SignalSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourceVerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    RETRACTED = "retracted"


class NewsStoryStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ============================================================================
# INTELLIGENCE SOURCES - Where we pull data from
# ============================================================================
class IntelligenceSource(Base):
    """Configured intelligence feed sources (RSS, APIs, etc.)"""
    __tablename__ = "intelligence_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # rss, api, manual, twitter
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Encrypted in production

    # Monitoring configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    check_interval_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=IntelSourceStatus.ACTIVE.value, nullable=False)

    # Source metadata
    reliability_score: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)  # 0-1
    default_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_theme: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)

    raw_items: Mapped[list[RawIntelItem]] = relationship("RawIntelItem", back_populates="source")


class RawIntelItem(Base):
    """Raw intelligence items before AI processing"""
    __tablename__ = "raw_intel_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("intelligence_sources.id"), nullable=False)

    # Raw content
    external_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)  # GUID, tweet ID, etc.
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Processing status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_relevant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # AI determines relevance
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # AI Analysis results
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_theme: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Link to created event (if promoted)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)

    source: Mapped[IntelligenceSource] = relationship("IntelligenceSource", back_populates="raw_items")
    event: Mapped[Event | None] = relationship("Event", back_populates="raw_items")


# ============================================================================
# SIGNALS - AI-detected emerging trends and early warnings
# ============================================================================
class Signal(Base):
    """AI-detected emerging signals and early warning indicators"""
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)  # emerging_trend, escalation, de-escalation, inflection_point
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Geographic scope
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    countries: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Thematic scope
    themes: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array

    # Evidence
    supporting_event_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Indicators
    key_indicators: Mapped[str] = mapped_column(Text, nullable=False)
    watch_for: Mapped[str] = mapped_column(Text, nullable=False)  # What to monitor next

    # Lifecycle
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)
    analyst_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================================================
# MARKET INDICATORS - Economic and market data
# ============================================================================
class MarketIndicator(Base):
    """Economic and market indicator tracking"""
    __tablename__ = "market_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # e.g., BRENT, EURUSD
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # energy, currency, commodity, index

    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Geopolitical relevance
    relevant_regions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    relevant_themes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_source: Mapped[str | None] = mapped_column(String(200), nullable=True)


class PredictionMarket(Base):
    """Prediction market signals (e.g., Polymarket-style)"""
    __tablename__ = "prediction_markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # polymarket, metaculus, etc.
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    probability_yes: Mapped[float] = mapped_column(Float, nullable=False)
    probability_change_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Geopolitical tagging
    region: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    theme: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# ============================================================================
# PRIORITY AREAS - Analyst-defined monitoring focus
# ============================================================================
class PriorityArea(Base):
    """Predefined priority monitoring areas"""
    __tablename__ = "priority_areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Scope definition
    regions: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    countries: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    themes: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    keywords: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array for AI matching

    # Alert thresholds
    severity_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    alert_on_new_events: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)


# ============================================================================
# EXISTING MODELS (UPDATED)
# ============================================================================
class Analyst(Base):
    __tablename__ = "analysts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=AnalystRole.ANALYST.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    events: Mapped[list[Event]] = relationship("Event", back_populates="owner")
    outlooks: Mapped[list[Outlook]] = relationship("Outlook", back_populates="owner")
    scenarios: Mapped[list[Scenario]] = relationship("Scenario", back_populates="owner", foreign_keys="[Scenario.owner_id]")


def compute_event_fingerprint(title: str, region: str, occurred_at: datetime) -> str:
    """Generate a stable fingerprint for duplicate detection."""
    normalized = f"{title.strip().lower()}|{region.strip().lower()}|{occurred_at.date().isoformat()}"
    return sha256(normalized.encode()).hexdigest()[:32]


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    theme: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    risk_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    severity: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    fingerprint: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)

    # AI source tracking
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_source_id: Mapped[int | None] = mapped_column(ForeignKey("intelligence_sources.id"), nullable=True)

    owner: Mapped[Analyst | None] = relationship("Analyst", back_populates="events")
    tags: Mapped[list[Tag]] = relationship("Tag", secondary=event_tags, back_populates="events")
    sources: Mapped[list[Source]] = relationship("Source", back_populates="event", cascade="all, delete-orphan")
    timeline_entries: Mapped[list[EventTimelineEntry]] = relationship(
        "EventTimelineEntry", back_populates="event", cascade="all, delete-orphan", order_by="EventTimelineEntry.recorded_at"
    )
    raw_items: Mapped[list[RawIntelItem]] = relationship("RawIntelItem", back_populates="event")

    __table_args__ = (Index("ix_events_fingerprint_owner", "fingerprint", "owner_id"),)


class EventTimelineEntry(Base):
    __tablename__ = "event_timeline_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)  # manual, ai_update, source_update

    event: Mapped[Event] = relationship("Event", back_populates="timeline_entries")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reliability: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    
    # Verification status
    verification_status: Mapped[str] = mapped_column(String(20), default=SourceVerificationStatus.UNVERIFIED.value, nullable=False)

    event: Mapped[Event] = relationship("Event", back_populates="sources")
    verifications: Mapped[list[SourceVerification]] = relationship("SourceVerification", back_populates="source", cascade="all, delete-orphan")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # region, theme, sector, custom

    events: Mapped[list[Event]] = relationship("Event", secondary=event_tags, back_populates="tags")


class Outlook(Base):
    __tablename__ = "outlooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)

    # Scope
    region: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    theme: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Content
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_developments: Mapped[str] = mapped_column(Text, nullable=False)
    key_indicators: Mapped[str] = mapped_column(Text, nullable=False)
    implications: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    # AI analysis
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)  # positive, negative, neutral, mixed
    risk_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)  # increasing, decreasing, stable

    # Source events
    source_event_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Workflow
    status: Mapped[str] = mapped_column(String(20), default=OutlookStatus.DRAFT.value, nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)
    owner: Mapped[Analyst | None] = relationship("Analyst", back_populates="outlooks")


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    case_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Scope
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Content
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggers: Mapped[str] = mapped_column(Text, nullable=False)
    warning_indicators: Mapped[str | None] = mapped_column(Text, nullable=True)
    impacts: Mapped[str] = mapped_column(Text, nullable=False)
    operational_impacts: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_impacts: Mapped[str | None] = mapped_column(Text, nullable=True)

    time_horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True)

    owner_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)
    owner: Mapped[Analyst | None] = relationship("Analyst", back_populates="scenarios", foreign_keys=[owner_id])
    template: Mapped[Scenario | None] = relationship("Scenario", remote_side=[id], foreign_keys=[template_id])


class AskAnythingQuery(Base):
    """Store Q&A history for audit and learning."""
    __tablename__ = "ask_anything_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources_cited: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    owner_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)


# ============================================================================
# SOURCE VERIFICATION - Track source credibility and verification
# ============================================================================
class SourceVerification(Base):
    """Verification record for intelligence sources"""
    __tablename__ = "source_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    
    # Verification details
    status: Mapped[str] = mapped_column(String(20), default=SourceVerificationStatus.UNVERIFIED.value, nullable=False)
    verification_method: Mapped[str | None] = mapped_column(String(100), nullable=True)  # cross-reference, official_confirmation, multiple_sources
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Link to verification evidence
    
    # Audit
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    source: Mapped[Source] = relationship("Source", back_populates="verifications")


# ============================================================================
# NEWS STORIES - Redistributable content generated from events
# ============================================================================
class NewsStory(Base):
    """Redistributable news story generated from verified intelligence events"""
    __tablename__ = "news_stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Content
    headline: Mapped[str] = mapped_column(String(300), nullable=False)
    subheadline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Classification
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    theme: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Impact assessment
    impact_level: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    business_implications: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Source events (JSON array of event IDs)
    source_event_ids: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Verification status
    all_sources_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Workflow
    status: Mapped[str] = mapped_column(String(20), default=NewsStoryStatus.DRAFT.value, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Ownership
    author_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("analysts.id"), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Distribution
    distribution_channels: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)  # ID in external system


