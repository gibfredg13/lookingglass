from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl


# --- Auth ---
class AnalystCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    role: Literal["analyst", "senior_analyst", "admin"] = "analyst"


class AnalystRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# --- Timeline ---
class TimelineEntryRead(BaseModel):
    id: int
    description: str
    recorded_at: datetime
    entry_type: str = "manual"

    model_config = {"from_attributes": True}


# --- Sources ---
class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: HttpUrl | None = None
    reliability: float = Field(ge=0.0, le=1.0, default=0.5)


class SourceRead(BaseModel):
    id: int
    name: str
    url: str | None
    reliability: float

    model_config = {"from_attributes": True}


# --- Source Verification ---
class SourceVerificationCreate(BaseModel):
    source_id: int
    status: Literal["unverified", "verified", "disputed", "retracted"] = "verified"
    verification_method: str | None = None
    verification_notes: str | None = None
    verified_url: str | None = None


class SourceVerificationRead(BaseModel):
    id: int
    source_id: int
    status: str
    verification_method: str | None = None
    verification_notes: str | None = None
    verified_url: str | None = None
    verified_at: datetime | None = None
    verified_by_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceWithVerificationRead(BaseModel):
    id: int
    name: str
    url: str | None
    reliability: float
    verification_status: str
    verifications: list[SourceVerificationRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# --- Events ---
class EventCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    summary: str = Field(min_length=10)
    region: str = Field(min_length=2, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    theme: str = Field(min_length=2, max_length=100)
    sector: str | None = Field(default=None, max_length=100)
    risk_type: str | None = Field(default=None, max_length=100)
    severity: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0.0, le=1.0)
    occurred_at: datetime
    tags: list[str] = Field(default_factory=list)
    sources: list[SourceCreate] = Field(default_factory=list)


class EventRead(BaseModel):
    id: int
    title: str
    summary: str
    region: str
    country: str | None
    theme: str
    sector: str | None = None
    risk_type: str | None = None
    severity: int
    confidence: float
    occurred_at: datetime
    created_at: datetime
    fingerprint: str
    owner_id: int | None
    is_published: bool = False
    published_at: datetime | None = None
    is_ai_generated: bool = False
    tags: list[str]
    sources: list[SourceRead]
    timeline: list[TimelineEntryRead] = Field(default_factory=list)


class EventSearchParams(BaseModel):
    region: str | None = None
    theme: str | None = None
    sector: str | None = None
    risk_type: str | None = None
    severity_min: int | None = Field(default=None, ge=1, le=5)
    severity_max: int | None = Field(default=None, ge=1, le=5)
    date_from: datetime | None = None
    date_to: datetime | None = None
    is_published: bool | None = None
    q: str | None = None  # Full-text search query


class EventPublishRequest(BaseModel):
    publish: bool = True


class DuplicateEventResponse(BaseModel):
    duplicate: bool
    existing_event_id: int | None = None
    message: str


# --- Outlooks ---
class OutlookRead(BaseModel):
    id: int
    horizon_hours: int
    region: str | None = None
    theme: str | None = None
    executive_summary: str | None = None
    expected_developments: str
    key_indicators: str
    implications: str
    confidence: float
    rationale: str
    sentiment: str | None = None
    risk_direction: str | None = None
    status: str
    generated_at: datetime
    reviewed_at: datetime | None = None
    published_at: datetime | None = None
    reviewer_notes: str | None = None
    owner_id: int | None = None

    model_config = {"from_attributes": True}


class OutlookGenerateRequest(BaseModel):
    horizons: list[int] = Field(default_factory=lambda: [24, 48, 72])


class OutlookStatusUpdate(BaseModel):
    status: Literal["draft", "reviewed", "published"]
    reviewer_notes: str | None = None


# --- Scenarios ---
class ScenarioCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    case_type: Literal["baseline", "upside", "downside"]
    triggers: str = Field(min_length=10)
    impacts: str = Field(min_length=10)
    time_horizon_hours: int = Field(gt=0, le=720)
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
    is_template: bool = False
    template_id: int | None = None


class ScenarioRead(BaseModel):
    id: int
    name: str
    case_type: str
    region: str | None = None
    theme: str | None = None
    description: str | None = None
    triggers: str
    warning_indicators: str | None = None
    impacts: str
    operational_impacts: str | None = None
    market_impacts: str | None = None
    time_horizon_hours: int
    probability: float | None
    created_at: datetime
    is_template: bool = False
    template_id: int | None = None
    owner_id: int | None = None

    model_config = {"from_attributes": True}


class ScenarioCloneRequest(BaseModel):
    name: str = Field(min_length=3, max_length=200)


# --- AskAnything ---
class AskAnythingRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2000)


class AskAnythingResponse(BaseModel):
    answer: str
    sources: list[dict]  # List of referenced events/outlooks/scenarios
    confidence: float
    sentiment: Literal["positive", "negative", "neutral", "mixed"]

    model_config = {"from_attributes": True}


class AskAnythingHistoryRead(BaseModel):
    id: int
    question: str
    answer: str
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}


# --- News Stories ---
class NewsStoryCreate(BaseModel):
    headline: str = Field(min_length=5, max_length=300)
    subheadline: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=50)
    executive_summary: str | None = None
    region: str = Field(min_length=2, max_length=100)
    theme: str = Field(min_length=2, max_length=100)
    sector: str | None = None
    impact_level: Literal["low", "medium", "high", "critical"]
    business_implications: str | None = None
    recommended_actions: str | None = None
    source_event_ids: list[int] = Field(min_length=1)  # Must have at least one source event
    distribution_channels: list[str] | None = None


class NewsStoryRead(BaseModel):
    id: int
    headline: str
    subheadline: str | None = None
    body: str
    executive_summary: str | None = None
    region: str
    theme: str
    sector: str | None = None
    impact_level: str
    business_implications: str | None = None
    recommended_actions: str | None = None
    source_event_ids: list[int]
    all_sources_verified: bool
    verification_summary: str | None = None
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    published_at: datetime | None = None
    author_id: int | None = None
    reviewer_id: int | None = None
    reviewer_notes: str | None = None
    distribution_channels: list[str] | None = None

    model_config = {"from_attributes": True}


class NewsStoryStatusUpdate(BaseModel):
    status: Literal["draft", "review", "approved", "published", "archived"]
    reviewer_notes: str | None = None


class NewsStoryGenerateRequest(BaseModel):
    event_ids: list[int] = Field(min_length=1)
    include_business_implications: bool = True
    include_recommended_actions: bool = True
