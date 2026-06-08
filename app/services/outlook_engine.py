from collections import Counter

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Event, Outlook


def _build_developments(theme_counts: Counter[str], horizon: int) -> str:
    if not theme_counts:
        return f"No material event activity detected for the next {horizon} hours."

    top_themes = ", ".join(theme for theme, _ in theme_counts.most_common(3))
    return (
        f"For the next {horizon} hours, analysts should track continued movement across: {top_themes}. "
        "Expect volatility around high-severity event clusters and policy responses."
    )


def _build_indicators(region_counts: Counter[str]) -> str:
    if not region_counts:
        return "No leading indicators available until new events are ingested."

    top_regions = ", ".join(region for region, _ in region_counts.most_common(3))
    return (
        f"Primary signposts: escalation language, sanctions posture changes, and force-mobility signals in {top_regions}."
    )


def _build_implications(avg_severity: float) -> str:
    if avg_severity >= 4:
        return "Elevated risk to energy, shipping, and sovereign sentiment channels."
    if avg_severity >= 2.5:
        return "Moderate pressure on supply chains and market confidence indicators."
    return "Contained short-term impact with localized disruptions."


def _build_confidence(event_count: int) -> float:
    if event_count >= 20:
        return 0.85
    if event_count >= 8:
        return 0.72
    if event_count >= 3:
        return 0.6
    return 0.45


def generate_outlooks(db: Session, horizons: list[int], owner_id: int | None = None) -> list[Outlook]:
    stmt: Select[tuple[Event]] = select(Event)
    if owner_id is not None:
        stmt = stmt.where(Event.owner_id == owner_id)
    events = db.scalars(stmt).all()

    theme_counts = Counter(event.theme for event in events)
    region_counts = Counter(event.region for event in events)
    avg_severity = (sum(event.severity for event in events) / len(events)) if events else 0
    confidence = _build_confidence(len(events))

    generated: list[Outlook] = []
    for horizon in horizons:
        outlook = Outlook(
            horizon_hours=horizon,
            expected_developments=_build_developments(theme_counts, horizon),
            key_indicators=_build_indicators(region_counts),
            implications=_build_implications(avg_severity),
            confidence=confidence,
            rationale=(
                "Generated from current event/taxonomy distribution. "
                "Analyst review is required before publication."
            ),
            status="draft",
            owner_id=owner_id,
        )
        db.add(outlook)
        generated.append(outlook)

    db.commit()
    for item in generated:
        db.refresh(item)
    return generated

