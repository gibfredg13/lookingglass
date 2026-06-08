"""AskAnything Q&A service using LLM for natural language queries."""
import json
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AskAnythingQuery, Event, Outlook, Scenario


def _gather_context(db: Session, owner_id: int) -> dict[str, list[dict[str, Any]]]:
    """Gather relevant context from events, outlooks, and scenarios."""
    # Get recent events
    events_stmt = (
        select(Event)
        .where(Event.owner_id == owner_id)
        .order_by(Event.occurred_at.desc())
        .limit(20)
    )
    events = db.scalars(events_stmt).all()

    # Get recent outlooks
    outlooks_stmt = (
        select(Outlook)
        .where(Outlook.owner_id == owner_id)
        .order_by(Outlook.generated_at.desc())
        .limit(10)
    )
    outlooks = db.scalars(outlooks_stmt).all()

    # Get scenarios
    scenarios_stmt = (
        select(Scenario)
        .where(Scenario.owner_id == owner_id)
        .order_by(Scenario.created_at.desc())
        .limit(10)
    )
    scenarios = db.scalars(scenarios_stmt).all()

    return {
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "summary": e.summary,
                "region": e.region,
                "theme": e.theme,
                "severity": e.severity,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
        "outlooks": [
            {
                "id": o.id,
                "horizon_hours": o.horizon_hours,
                "expected_developments": o.expected_developments,
                "key_indicators": o.key_indicators,
                "implications": o.implications,
                "confidence": o.confidence,
            }
            for o in outlooks
        ],
        "scenarios": [
            {
                "id": s.id,
                "name": s.name,
                "case_type": s.case_type,
                "triggers": s.triggers,
                "impacts": s.impacts,
            }
            for s in scenarios
        ],
    }


def _detect_sentiment(answer: str) -> str:
    """Simple sentiment detection based on keywords."""
    neg_keywords = ["risk", "threat", "escalation", "concern", "negative", "downside", "crisis", "conflict"]
    pos_keywords = ["opportunity", "improvement", "de-escalation", "positive", "upside", "stabilization"]

    answer_lower = answer.lower()
    neg_count = sum(1 for kw in neg_keywords if kw in answer_lower)
    pos_count = sum(1 for kw in pos_keywords if kw in answer_lower)

    if neg_count > pos_count + 2:
        return "negative"
    if pos_count > neg_count + 2:
        return "positive"
    if neg_count > 0 and pos_count > 0:
        return "mixed"
    return "neutral"


def _build_prompt(question: str, context: dict[str, list[dict[str, Any]]]) -> str:
    """Build a prompt for the LLM."""
    events_text = "\n".join(
        f"- [{e['id']}] {e['title']} ({e['region']}, severity {e['severity']}): {e['summary'][:200]}"
        for e in context["events"][:10]
    )
    outlooks_text = "\n".join(
        f"- [{o['id']}] {o['horizon_hours']}h outlook (confidence {o['confidence']:.0%}): {o['expected_developments'][:200]}"
        for o in context["outlooks"][:5]
    )
    scenarios_text = "\n".join(
        f"- [{s['id']}] {s['name']} ({s['case_type']}): triggers={s['triggers'][:100]}, impacts={s['impacts'][:100]}"
        for s in context["scenarios"][:5]
    )

    return f"""You are an expert geopolitical intelligence analyst assistant. Answer the following question based on the available intelligence data.

RECENT EVENTS:
{events_text or "No events available."}

ACTIVE OUTLOOKS:
{outlooks_text or "No outlooks available."}

SCENARIOS:
{scenarios_text or "No scenarios available."}

QUESTION: {question}

Provide a clear, concise answer. Reference specific event/outlook/scenario IDs when relevant. Include:
1. Direct answer to the question
2. Supporting evidence from the data
3. Confidence assessment
4. Any relevant caveats or uncertainties

ANSWER:"""


def _call_llm(prompt: str) -> str:
    """Call LLM API. Falls back to rule-based response if no API key."""
    settings = get_settings()
    api_key = os.getenv("OPENAI_API_KEY")
    use_live_ai = settings.ai_mode.lower() == "live" and bool(api_key)

    if use_live_ai:
        try:
            import httpx

            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.3,
                },
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"LLM call failed: {e}. Please check your API key configuration."

    # Fallback: rule-based summary
    return _generate_fallback_response(prompt)


def _generate_fallback_response(prompt: str) -> str:
    """Generate a basic response without LLM."""
    lines = prompt.split("\n")
    question = ""
    for line in lines:
        if line.startswith("QUESTION:"):
            question = line.replace("QUESTION:", "").strip()
            break

    return f"""Based on the available intelligence data:

The question "{question}" relates to the geopolitical events and scenarios in the analyst's workspace.

Demo mode is active, so responses intentionally use deterministic mock logic.
To enable live LLM responses, set AL_AI_MODE=live and configure OPENAI_API_KEY.

Current data summary:
- Review the recent events section for relevant intelligence items
- Check active outlooks for 24/48/72 hour trend assessments
- Examine scenarios for baseline/upside/downside projections

Note: This is a fallback response. For full natural-language Q&A capabilities, an LLM API connection is required."""


def ask_anything(
    db: Session,
    question: str,
    owner_id: int,
) -> dict[str, Any]:
    """Process a natural language question and return an answer with sources."""
    context = _gather_context(db, owner_id)
    prompt = _build_prompt(question, context)
    answer = _call_llm(prompt)
    sentiment = _detect_sentiment(answer)

    # Extract referenced IDs from answer (basic pattern matching)
    sources = []
    for event in context["events"]:
        if f"[{event['id']}]" in answer or event["title"].lower() in answer.lower():
            sources.append({"type": "event", "id": event["id"], "title": event["title"]})
    for outlook in context["outlooks"]:
        if f"[{outlook['id']}]" in answer:
            sources.append({"type": "outlook", "id": outlook["id"], "horizon": outlook["horizon_hours"]})
    for scenario in context["scenarios"]:
        if f"[{scenario['id']}]" in answer or scenario["name"].lower() in answer.lower():
            sources.append({"type": "scenario", "id": scenario["id"], "name": scenario["name"]})

    # Confidence based on data availability
    confidence = min(0.9, 0.3 + len(context["events"]) * 0.03 + len(context["outlooks"]) * 0.05)

    # Store query for audit
    query_record = AskAnythingQuery(
        question=question,
        answer=answer,
        sources_cited=json.dumps(sources) if sources else None,
        confidence=confidence,
        owner_id=owner_id,
    )
    db.add(query_record)
    db.commit()

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "sentiment": sentiment,
    }


def get_query_history(db: Session, owner_id: int, limit: int = 20) -> list[AskAnythingQuery]:
    """Get recent Q&A history for an analyst."""
    stmt = (
        select(AskAnythingQuery)
        .where(AskAnythingQuery.owner_id == owner_id)
        .order_by(AskAnythingQuery.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())

