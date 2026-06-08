"""
News Stories Router - Turn verified events into redistributable news stories.

Workflow:
1. Select events to include in story
2. Verify all sources
3. Generate/edit news story content
4. Review and approve
5. Publish for distribution
"""
from datetime import datetime, timezone
from typing import Annotated
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.routers.dependencies import CurrentAnalyst, get_db
from app.models import (
    NewsStory, Event, Source, SourceVerification,
    SourceVerificationStatus, NewsStoryStatus, utcnow
)
from app.schemas import (
    NewsStoryCreate, NewsStoryRead, NewsStoryStatusUpdate,
    NewsStoryGenerateRequest, SourceVerificationCreate, SourceVerificationRead,
    SourceWithVerificationRead
)

router = APIRouter(prefix="/stories", tags=["news-stories"])


# ============================================================================
# Helper Functions
# ============================================================================

def _check_event_sources_verified(db: Session, event_ids: list[int]) -> tuple[bool, str]:
    """Check if all sources for the given events are verified."""
    verified_count = 0
    total_count = 0
    unverified_sources = []

    for event_id in event_ids:
        event = db.get(Event, event_id)
        if event:
            for source in event.sources:
                total_count += 1
                if source.verification_status == SourceVerificationStatus.VERIFIED.value:
                    verified_count += 1
                else:
                    unverified_sources.append(f"{source.name} (Event #{event_id})")

    all_verified = verified_count == total_count and total_count > 0

    if all_verified:
        summary = f"All {total_count} sources verified"
    elif total_count == 0:
        summary = "No sources found"
    else:
        summary = f"{verified_count}/{total_count} sources verified. Unverified: {', '.join(unverified_sources[:5])}"
        if len(unverified_sources) > 5:
            summary += f" and {len(unverified_sources) - 5} more"

    return all_verified, summary


def _to_story_read(story: NewsStory) -> NewsStoryRead:
    """Convert NewsStory model to response schema."""
    return NewsStoryRead(
        id=story.id,
        headline=story.headline,
        subheadline=story.subheadline,
        body=story.body,
        executive_summary=story.executive_summary,
        region=story.region,
        theme=story.theme,
        sector=story.sector,
        impact_level=story.impact_level,
        business_implications=story.business_implications,
        recommended_actions=story.recommended_actions,
        source_event_ids=json.loads(story.source_event_ids) if story.source_event_ids else [],
        all_sources_verified=story.all_sources_verified,
        verification_summary=story.verification_summary,
        status=story.status,
        created_at=story.created_at,
        reviewed_at=story.reviewed_at,
        approved_at=story.approved_at,
        published_at=story.published_at,
        author_id=story.author_id,
        reviewer_id=story.reviewer_id,
        reviewer_notes=story.reviewer_notes,
        distribution_channels=json.loads(story.distribution_channels) if story.distribution_channels else None
    )


async def _generate_story_content(events: list[Event]) -> dict:
    """Generate news story content from events with banking sector relevance."""
    api_key = os.getenv("OPENAI_API_KEY")

    # Prepare event summaries
    event_texts = []
    for e in events:
        event_texts.append(f"- {e.title}: {e.summary}")
    events_summary = "\n".join(event_texts)

    # Get common attributes
    regions = list(set(e.region for e in events))
    themes = list(set(e.theme for e in events))
    max_severity = max(e.severity for e in events)

    if api_key:
        import httpx

        prompt = f"""Generate a professional intelligence brief for a major Dutch bank's geopolitical risk team.
Focus on implications for banking operations, trade finance, sanctions compliance, and risk management.

EVENTS:
{events_summary}

REGION(S): {', '.join(regions)}
THEME(S): {', '.join(themes)}
MAX SEVERITY: {max_severity}/5

Generate JSON with banking-focused content:
{{
    "headline": "Concise, professional headline (max 150 chars)",
    "subheadline": "Supporting detail emphasizing banking/financial relevance (max 250 chars)",
    "executive_summary": "2-3 sentence executive summary for senior banking leadership",
    "body": "Full news story (3-5 paragraphs, professional tone, emphasizing banking sector implications)",
    "business_implications": "Specific implications for: 1) Trade finance operations, 2) Sanctions compliance, 3) Client exposure, 4) Correspondent banking relationships, 5) Credit/country risk",
    "recommended_actions": "Specific recommended actions for banking operations: compliance review, client communication, risk committee escalation, etc."
}}"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.5,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                return json.loads(result["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"AI generation failed: {e}, using heuristics")

    # Heuristic fallback with banking focus
    primary_event = max(events, key=lambda e: e.severity)

    body_paragraphs = []
    body_paragraphs.append(f"{primary_event.title}. {primary_event.summary}")

    if len(events) > 1:
        other_events = [e for e in events if e.id != primary_event.id]
        body_paragraphs.append("Related developments include: " +
            "; ".join(f"{e.title}" for e in other_events[:3]))

    impact = "low" if max_severity <= 2 else "medium" if max_severity <= 3 else "high" if max_severity <= 4 else "critical"

    # Add banking context paragraph
    banking_context = _get_banking_implications(themes[0], regions[0], impact)
    body_paragraphs.append(banking_context)

    # Get banking-specific implications and actions
    implications = _get_detailed_banking_implications(themes[0], regions[0], impact)
    actions = _get_banking_recommended_actions(themes[0], impact)

    return {
        "headline": primary_event.title[:150],
        "subheadline": f"Banking Sector Impact: {themes[0].title()} developments in {regions[0]}"[:250],
        "executive_summary": primary_event.summary[:500],
        "body": "\n\n".join(body_paragraphs),
        "business_implications": implications,
        "recommended_actions": actions
    }


def _get_banking_implications(theme: str, region: str, impact: str) -> str:
    """Generate banking-focused context paragraph."""
    base = f"The overall impact level for banking operations is assessed as {impact}. "

    theme_context = {
        "sanctions": "This development has direct implications for sanctions compliance, correspondent banking relationships, and trade finance operations. Enhanced due diligence on affected counterparties is advised.",
        "shipping": "Trade finance exposure related to shipping routes through the affected region should be reviewed. Letter of credit and documentary collection processing may require additional scrutiny.",
        "conflict": "Country risk assessments should be updated. Client exposure to the affected region requires immediate review. Credit risk provisions may need reassessment.",
        "cyber": "Operational resilience implications for banking IT infrastructure. Review third-party vendor exposure to affected regions. Incident response protocols should be on standby.",
        "energy": "Commodity finance exposure requires review. Energy sector clients may face increased credit risk. Trade finance for energy commodities should be monitored closely.",
        "trade": "Trade finance operations may be affected. Review exposure to affected trade corridors. Import/export finance transactions require enhanced monitoring.",
        "elections": "Political transition risk may affect banking operations in the region. Monitor for potential policy changes affecting financial sector regulation."
    }

    context = theme_context.get(theme, f"This development affects the {region} region and may have implications for banking operations and client exposure in the area.")
    return base + context


def _get_detailed_banking_implications(theme: str, region: str, impact: str) -> str:
    """Generate detailed banking implications."""
    implications = {
        "sanctions": f"1) Sanctions Compliance: Review all transactions with nexus to affected region. 2) Correspondent Banking: Assess exposure through correspondent relationships. 3) Trade Finance: Enhanced screening for letters of credit and trade transactions. 4) Client Exposure: Identify clients with operations in affected areas. 5) KYC Review: Update due diligence for affected counterparties.",
        "shipping": f"1) Trade Finance: Review outstanding letters of credit for affected shipping routes. 2) Documentary Collections: Monitor for delays in documentation. 3) Insurance: Verify cargo insurance coverage remains valid. 4) Client Communication: Proactive outreach to shipping/trading clients. 5) Credit Risk: Reassess exposure to shipping sector clients.",
        "conflict": f"1) Country Risk: Immediate update to country risk ratings for {region}. 2) Credit Exposure: Review all lending exposure to affected region. 3) Provisions: Assess need for additional credit loss provisions. 4) Client Safety: Confirm status of any personnel or operations in region. 5) Correspondent Banking: Review relationships with banks in affected area.",
        "cyber": f"1) IT Security: Heighten monitoring of banking infrastructure. 2) Third Parties: Review vendor exposure to affected systems. 3) Incident Response: Ensure cyber incident protocols are ready. 4) Client Communication: Prepare customer advisory if needed. 5) Business Continuity: Verify backup systems are operational.",
        "energy": f"1) Commodity Finance: Review energy sector trade finance exposure. 2) Credit Risk: Reassess energy sector client creditworthiness. 3) Collateral: Monitor commodity price impacts on collateral values. 4) Hedging: Review hedge effectiveness for energy exposures. 5) Stress Testing: Run scenarios for energy price shocks.",
        "trade": f"1) Trade Finance Portfolio: Review exposure to affected trade corridors. 2) Documentation: Expect potential delays in trade documentation. 3) Tariff Impact: Assess client exposure to new trade barriers. 4) Supply Chain: Monitor client supply chain disruptions. 5) Working Capital: Clients may need additional working capital support."
    }
    return implications.get(theme, f"Review all banking operations and client exposure related to {region}. Assess impact on trade finance, credit risk, and operational continuity. Update country risk assessments as needed.")


def _get_banking_recommended_actions(theme: str, impact: str) -> str:
    """Generate banking-specific recommended actions."""
    urgency = "Immediate action required: " if impact in ["high", "critical"] else "Recommended actions: "

    actions = {
        "sanctions": f"{urgency}1) Run sanctions screening on affected counterparties. 2) Brief Compliance team. 3) Review pending transactions for sanctions risk. 4) Update screening lists when new designations published. 5) Document all decisions and escalate to senior management.",
        "shipping": f"{urgency}1) Contact Trade Finance desk to review shipping-related exposure. 2) Liaise with insurance partners on coverage status. 3) Proactive client outreach for affected routes. 4) Monitor shipping industry advisories. 5) Brief Risk Committee at next meeting.",
        "conflict": f"{urgency}1) Convene Country Risk Committee. 2) Update country limits and ratings. 3) Review all credit exposure to affected region. 4) Client outreach to assess operational status. 5) Prepare board briefing on exposure and risk mitigation.",
        "cyber": f"{urgency}1) Alert IT Security team. 2) Increase monitoring of critical systems. 3) Review third-party connections to affected sectors. 4) Prepare client communication if banking services affected. 5) Document incident and response for regulatory reporting.",
        "energy": f"{urgency}1) Brief Commodity Finance team. 2) Run stress tests on energy sector exposure. 3) Review collateral valuations. 4) Client outreach to energy sector borrowers. 5) Update sector risk appetite if warranted.",
        "trade": f"{urgency}1) Brief Trade Finance team on potential impacts. 2) Review pending trade transactions for affected routes. 3) Client advisory on potential delays. 4) Coordinate with correspondent banks. 5) Monitor trade policy announcements."
    }
    return actions.get(theme, f"{urgency}1) Brief relevant business lines. 2) Review client and country exposure. 3) Update risk assessments. 4) Prepare management briefing. 5) Monitor situation for escalation.")


# ============================================================================
# Source Verification Endpoints
# ============================================================================

@router.post("/sources/{source_id}/verify", response_model=SourceVerificationRead, status_code=status.HTTP_201_CREATED)
def verify_source(
    source_id: int,
    data: SourceVerificationCreate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Verify a source with evidence and method."""
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Create verification record
    verification = SourceVerification(
        source_id=source_id,
        status=data.status,
        verification_method=data.verification_method,
        verification_notes=data.verification_notes,
        verified_url=data.verified_url,
        verified_at=utcnow() if data.status == "verified" else None,
        verified_by_id=analyst.id
    )
    db.add(verification)

    # Update source verification status
    source.verification_status = data.status

    db.commit()
    db.refresh(verification)

    return SourceVerificationRead.model_validate(verification)


@router.get("/events/{event_id}/sources", response_model=list[SourceWithVerificationRead])
def list_event_sources(
    event_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """List all sources for an event with their verification status."""
    event = db.scalar(
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.sources).selectinload(Source.verifications))
    )

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return [
        SourceWithVerificationRead(
            id=s.id,
            name=s.name,
            url=s.url,
            reliability=s.reliability,
            verification_status=s.verification_status,
            verifications=[SourceVerificationRead.model_validate(v) for v in s.verifications]
        )
        for s in event.sources
    ]


@router.get("/verification-status", response_model=dict)
def check_verification_status(
    event_ids: str,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Check verification status for a set of events."""
    try:
        ids = [int(x.strip()) for x in event_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_ids format")

    all_verified, summary = _check_event_sources_verified(db, ids)

    return {
        "event_ids": ids,
        "all_sources_verified": all_verified,
        "summary": summary
    }


# ============================================================================
# News Story Endpoints
# ============================================================================

@router.post("", response_model=NewsStoryRead, status_code=status.HTTP_201_CREATED)
def create_story(
    data: NewsStoryCreate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new news story from events."""
    # Validate events exist
    for event_id in data.source_event_ids:
        event = db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    # Check source verification
    all_verified, summary = _check_event_sources_verified(db, data.source_event_ids)

    # Determine impact level mapping from severity
    story = NewsStory(
        headline=data.headline,
        subheadline=data.subheadline,
        body=data.body,
        executive_summary=data.executive_summary,
        region=data.region,
        theme=data.theme,
        sector=data.sector,
        impact_level=data.impact_level,
        business_implications=data.business_implications,
        recommended_actions=data.recommended_actions,
        source_event_ids=json.dumps(data.source_event_ids),
        all_sources_verified=all_verified,
        verification_summary=summary,
        status=NewsStoryStatus.DRAFT.value,
        author_id=analyst.id,
        distribution_channels=json.dumps(data.distribution_channels) if data.distribution_channels else None
    )

    db.add(story)
    db.commit()
    db.refresh(story)

    return _to_story_read(story)


@router.post("/generate", response_model=NewsStoryRead, status_code=status.HTTP_201_CREATED)
async def generate_story(
    data: NewsStoryGenerateRequest,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Generate a news story from events using AI."""
    # Fetch events
    events = []
    for event_id in data.event_ids:
        event = db.scalar(
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.sources))
        )
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        events.append(event)

    # Check source verification
    all_verified, summary = _check_event_sources_verified(db, data.event_ids)

    # Generate content
    content = await _generate_story_content(events)

    # Determine impact level
    max_severity = max(e.severity for e in events)
    impact_map = {1: "low", 2: "low", 3: "medium", 4: "high", 5: "critical"}

    # Get common region/theme
    regions = list(set(e.region for e in events))
    themes = list(set(e.theme for e in events))

    story = NewsStory(
        headline=content["headline"],
        subheadline=content.get("subheadline"),
        body=content["body"],
        executive_summary=content.get("executive_summary"),
        region=regions[0] if regions else "Global",
        theme=themes[0] if themes else "general",
        impact_level=impact_map.get(max_severity, "medium"),
        business_implications=content.get("business_implications") if data.include_business_implications else None,
        recommended_actions=content.get("recommended_actions") if data.include_recommended_actions else None,
        source_event_ids=json.dumps(data.event_ids),
        all_sources_verified=all_verified,
        verification_summary=summary,
        status=NewsStoryStatus.DRAFT.value,
        author_id=analyst.id
    )

    db.add(story)
    db.commit()
    db.refresh(story)

    return _to_story_read(story)


@router.get("", response_model=list[NewsStoryRead])
def list_stories(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = None,
    verified_only: bool = False,
    limit: int = Query(default=50, le=200)
):
    """List news stories with optional filters."""
    query = select(NewsStory).order_by(NewsStory.created_at.desc())

    if status_filter:
        query = query.where(NewsStory.status == status_filter)
    if verified_only:
        query = query.where(NewsStory.all_sources_verified == True)

    stories = db.scalars(query.limit(limit)).all()
    return [_to_story_read(s) for s in stories]


@router.get("/published", response_model=list[NewsStoryRead])
def list_published_stories(
    db: Annotated[Session, Depends(get_db)],
    region: str | None = None,
    theme: str | None = None,
    limit: int = Query(default=50, le=200)
):
    """Public endpoint: List published news stories."""
    query = select(NewsStory).where(
        NewsStory.status == NewsStoryStatus.PUBLISHED.value
    ).order_by(NewsStory.published_at.desc())

    if region:
        query = query.where(NewsStory.region == region)
    if theme:
        query = query.where(NewsStory.theme == theme)

    stories = db.scalars(query.limit(limit)).all()
    return [_to_story_read(s) for s in stories]


@router.get("/{story_id}", response_model=NewsStoryRead)
def get_story(
    story_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Get a single news story."""
    story = db.get(NewsStory, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return _to_story_read(story)


@router.patch("/{story_id}", response_model=NewsStoryRead)
def update_story(
    story_id: int,
    data: NewsStoryCreate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Update a news story (only allowed in draft/review status)."""
    story = db.get(NewsStory, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status not in [NewsStoryStatus.DRAFT.value, NewsStoryStatus.REVIEW.value]:
        raise HTTPException(status_code=400, detail="Can only edit stories in draft or review status")

    # Update fields
    story.headline = data.headline
    story.subheadline = data.subheadline
    story.body = data.body
    story.executive_summary = data.executive_summary
    story.region = data.region
    story.theme = data.theme
    story.sector = data.sector
    story.impact_level = data.impact_level
    story.business_implications = data.business_implications
    story.recommended_actions = data.recommended_actions
    story.source_event_ids = json.dumps(data.source_event_ids)
    story.distribution_channels = json.dumps(data.distribution_channels) if data.distribution_channels else None

    # Re-check verification
    all_verified, summary = _check_event_sources_verified(db, data.source_event_ids)
    story.all_sources_verified = all_verified
    story.verification_summary = summary

    db.commit()
    db.refresh(story)

    return _to_story_read(story)


@router.patch("/{story_id}/status", response_model=NewsStoryRead)
def update_story_status(
    story_id: int,
    data: NewsStoryStatusUpdate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Update story status through workflow."""
    story = db.get(NewsStory, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Validate status transitions
    valid_transitions = {
        "draft": ["review"],
        "review": ["draft", "approved"],
        "approved": ["review", "published"],
        "published": ["archived"],
        "archived": []
    }

    if data.status not in valid_transitions.get(story.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {story.status} to {data.status}"
        )

    # Block publishing unverified stories
    if data.status == "published" and not story.all_sources_verified:
        raise HTTPException(
            status_code=400,
            detail="Cannot publish story with unverified sources"
        )

    # Update status and timestamps
    story.status = data.status
    if data.reviewer_notes:
        story.reviewer_notes = data.reviewer_notes

    if data.status == "review":
        story.reviewed_at = utcnow()
        story.reviewer_id = analyst.id
    elif data.status == "approved":
        story.approved_at = utcnow()
    elif data.status == "published":
        story.published_at = utcnow()

    db.commit()
    db.refresh(story)

    return _to_story_read(story)


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(
    story_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a news story (only drafts)."""
    story = db.get(NewsStory, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != NewsStoryStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Can only delete draft stories")

    db.delete(story)
    db.commit()

