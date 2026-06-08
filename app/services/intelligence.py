"""
AI-powered intelligence ingestion and analysis service.

This service:
1. Fetches raw intelligence from configured sources (RSS, APIs)
2. Uses AI to analyze, classify, and tag content
3. Detects duplicates and consolidates events
4. Identifies emerging signals and trends
"""
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any
import hashlib
import re

import feedparser
import httpx
from sqlalchemy.orm import Session

from app.models import (
    IntelligenceSource, RawIntelItem, Event, Signal, EventTimelineEntry,
    compute_event_fingerprint, Tag, Source
)


# Priority regions and themes - with focus on banking/financial sector relevance
# Particularly relevant for Dutch financial institutions
PRIORITY_REGIONS = [
    "Netherlands", "Europe", "Middle East", "Gulf", "China", "Taiwan",
    "United States", "South America", "Russia", "Ukraine", "Asia Pacific", "Africa"
]

PRIORITY_THEMES = [
    "sanctions", "trade", "conflict", "cyber", "energy", "shipping",
    "tariffs", "elections", "terrorism", "hybrid warfare", "tech wars",
    "strategic competition", "financial regulation", "banking"
]

SECTORS = [
    "finance", "banking", "energy", "shipping", "technology", "manufacturing",
    "agriculture", "defense", "telecommunications", "commodities"
]

# Banking relevance keywords for enhanced analysis
BANKING_RELEVANCE_KEYWORDS = [
    "bank", "financial", "credit", "loan", "capital", "investment", "sanctions",
    "swift", "payment", "transaction", "compliance", "aml", "kyc", "correspondent",
    "trade finance", "treasury", "forex", "currency", "central bank", "ecb",
    "dutch", "netherlands", "amsterdam", "rotterdam", "ing", "abn", "rabobank"
]


class AIAnalyzer:
    """AI-powered content analysis using OpenAI or fallback heuristics."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.use_ai = bool(self.api_key)

    async def analyze_content(self, title: str, content: str, source_context: dict) -> dict:
        """
        Analyze raw intelligence content and extract structured data.
        Returns: dict with region, country, theme, sector, severity, confidence, summary, tags
        """
        if self.use_ai:
            return await self._ai_analyze(title, content, source_context)
        return self._heuristic_analyze(title, content, source_context)

    async def _ai_analyze(self, title: str, content: str, source_context: dict) -> dict:
        """Use OpenAI to analyze content with focus on banking/financial sector relevance."""
        prompt = f"""Analyze this geopolitical intelligence item for a major Dutch bank.
Focus on implications for banking, financial services, trade finance, and operations in the Netherlands/Europe.

TITLE: {title}

CONTENT: {content[:3000]}

SOURCE CONTEXT: {json.dumps(source_context)}

Respond with JSON only:
{{
    "is_relevant": true/false (is this relevant for banking/financial sector?),
    "summary": "2-3 sentence summary emphasizing banking/financial sector implications",
    "region": "primary region from: {', '.join(PRIORITY_REGIONS)}",
    "country": "specific country if applicable or null",
    "theme": "primary theme from: {', '.join(PRIORITY_THEMES)}",
    "sector": "affected sector from: {', '.join(SECTORS)} or null",
    "severity": 1-5 (1=low impact on banking, 5=critical impact on banking operations),
    "confidence": 0.0-1.0 (confidence in analysis),
    "tags": ["list", "of", "relevant", "tags"],
    "banking_relevance": "specific relevance to banking sector: sanctions compliance, trade finance, correspondent banking, credit risk, operational risk, etc.",
    "netherlands_impact": "specific impact on Dutch/European financial sector if applicable",
    "reasoning": "brief explanation of classification and banking relevance"
}}"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return json.loads(result["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"AI analysis failed: {e}, falling back to heuristics")
            return self._heuristic_analyze(title, content, source_context)

    def _heuristic_analyze(self, title: str, content: str, source_context: dict) -> dict:
        """Fallback heuristic analysis with banking sector focus."""
        text = f"{title} {content}".lower()

        # Detect region - prioritize Netherlands/Europe for banking relevance
        region = source_context.get("default_region", "Global")
        if "netherlands" in text or "dutch" in text or "amsterdam" in text or "rotterdam" in text:
            region = "Netherlands"
        else:
            for r in PRIORITY_REGIONS:
                if r.lower() in text:
                    region = r
                    break

        # Detect country
        country = None
        country_patterns = {
            "netherlands": "Netherlands", "dutch": "Netherlands",
            "iran": "Iran", "israel": "Israel", "china": "China", "russia": "Russia",
            "ukraine": "Ukraine", "taiwan": "Taiwan", "united states": "United States",
            "saudi": "Saudi Arabia", "yemen": "Yemen", "iraq": "Iraq", "syria": "Syria",
            "germany": "Germany", "france": "France", "belgium": "Belgium"
        }
        for pattern, name in country_patterns.items():
            if pattern in text:
                country = name
                break

        # Detect theme - prioritize banking-relevant themes
        theme = source_context.get("default_theme", "other")
        theme_keywords = {
            "sanctions": ["sanction", "embargo", "restrict", "ban", "penalty", "ofac", "swift"],
            "trade": ["trade", "export", "import", "tariff", "commerce", "trade finance"],
            "cyber": ["cyber", "hack", "breach", "ransomware", "malware", "it security"],
            "conflict": ["war", "attack", "strike", "military", "combat", "fighting"],
            "energy": ["oil", "gas", "energy", "pipeline", "refinery", "opec"],
            "shipping": ["ship", "vessel", "port", "maritime", "cargo", "freight"],
            "elections": ["election", "vote", "ballot", "campaign", "poll"],
            "terrorism": ["terror", "attack", "bomb", "militant", "extremist"],
            "financial regulation": ["regulation", "compliance", "aml", "kyc", "central bank", "ecb"]
        }
        for t, keywords in theme_keywords.items():
            if any(k in text for k in keywords):
                theme = t
                break

        # Detect sector - prioritize banking/finance
        sector = None
        sector_keywords = {
            "banking": ["bank", "banking", "loan", "credit", "mortgage", "deposit"],
            "finance": ["financial", "investment", "capital", "stock", "market", "treasury"],
            "energy": ["oil", "gas", "energy", "power", "electricity"],
            "shipping": ["ship", "port", "maritime", "cargo", "vessel"],
            "technology": ["tech", "semiconductor", "chip", "software", "ai"]
        }
        for s, keywords in sector_keywords.items():
            if any(k in text for k in keywords):
                sector = s
                break

        # Check banking relevance
        banking_relevant = any(k in text for k in BANKING_RELEVANCE_KEYWORDS)

        # Estimate severity - higher for banking-relevant items
        severity = 2  # Default low-medium
        high_severity_words = ["crisis", "critical", "emergency", "war", "attack", "strike", "killed", "sanctions"]
        medium_severity_words = ["tension", "threat", "warning", "conflict", "dispute", "compliance"]

        if any(w in text for w in high_severity_words):
            severity = 4
        elif any(w in text for w in medium_severity_words):
            severity = 3
        
        # Boost severity for banking-relevant items
        if banking_relevant and severity < 4:
            severity += 1

        # Generate summary
        sentences = re.split(r'[.!?]+', content)
        summary = '. '.join(sentences[:2]).strip()
        if len(summary) > 300:
            summary = summary[:297] + "..."

        # Generate tags - include banking if relevant
        tags = []
        if region != "Global":
            tags.append(region.lower().replace(" ", "-"))
        if country:
            tags.append(country.lower().replace(" ", "-"))
        tags.append(theme)
        if sector:
            tags.append(sector)
        if banking_relevant:
            tags.append("banking-relevant")

        # Determine banking relevance description
        banking_relevance = None
        if banking_relevant:
            if "sanction" in text:
                banking_relevance = "Sanctions compliance implications for correspondent banking and trade finance"
            elif "cyber" in text:
                banking_relevance = "Operational risk and IT security implications for banking infrastructure"
            elif "trade" in text or "shipping" in text:
                banking_relevance = "Trade finance exposure and letter of credit implications"
            else:
                banking_relevance = "Potential impact on banking operations and client exposure"

        return {
            "is_relevant": True,
            "summary": summary or title,
            "region": region,
            "country": country,
            "theme": theme,
            "sector": sector,
            "severity": severity,
            "confidence": 0.6,
            "tags": tags,
            "banking_relevance": banking_relevance,
            "netherlands_impact": "Monitor for impact on Dutch financial sector" if region in ["Netherlands", "Europe"] else None,
            "reasoning": "Analyzed using keyword heuristics with banking sector focus"
        }


class SignalDetector:
    """Detects emerging signals and trends from event patterns."""

    def __init__(self, session: Session):
        self.session = session
        self.api_key = os.getenv("OPENAI_API_KEY")

    async def detect_signals(self, recent_events: list[Event]) -> list[dict]:
        """Analyze recent events for emerging signals."""
        if len(recent_events) < 3:
            return []

        # Group events by region and theme
        grouped = {}
        for event in recent_events:
            key = f"{event.region}|{event.theme}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(event)

        signals = []

        # Detect patterns
        for key, events in grouped.items():
            if len(events) >= 3:  # Minimum events for a signal
                region, theme = key.split("|")

                # Calculate average severity trend
                recent = sorted(events, key=lambda e: e.occurred_at, reverse=True)[:5]
                avg_severity = sum(e.severity for e in recent) / len(recent)

                if avg_severity >= 3.5:  # Escalation signal
                    signal = {
                        "title": f"Escalating {theme} activity in {region}",
                        "description": f"Detected {len(events)} related events with increasing severity",
                        "signal_type": "escalation",
                        "severity": "high" if avg_severity >= 4 else "medium",
                        "confidence": min(0.9, 0.5 + (len(events) * 0.1)),
                        "region": region,
                        "themes": [theme],
                        "supporting_event_ids": [e.id for e in recent],
                        "evidence_summary": f"Multiple {theme} events detected. Average severity: {avg_severity:.1f}/5",
                        "key_indicators": f"Event frequency: {len(events)} events, Severity trend: {'increasing' if avg_severity > 3 else 'stable'}",
                        "watch_for": f"Further {theme} developments in {region}"
                    }
                    signals.append(signal)

        return signals


class IntelligenceFetcher:
    """Fetches raw intelligence from configured sources."""

    async def fetch_rss(self, source: IntelligenceSource) -> list[dict]:
        """Fetch items from RSS feed."""
        items = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(source.url, timeout=30.0)
                response.raise_for_status()
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:20]:  # Limit to 20 most recent
                    items.append({
                        "external_id": entry.get("id") or entry.get("link"),
                        "title": entry.get("title", "Untitled"),
                        "content": entry.get("summary") or entry.get("description") or "",
                        "url": entry.get("link"),
                        "published_at": self._parse_date(entry.get("published"))
                    })
        except Exception as e:
            raise RuntimeError(f"RSS fetch failed: {e}")

        return items

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse various date formats."""
        if not date_str:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return None


class IntelligenceService:
    """Main intelligence processing service."""

    def __init__(self, session: Session):
        self.session = session
        self.analyzer = AIAnalyzer()
        self.fetcher = IntelligenceFetcher()
        self.signal_detector = SignalDetector(session)

    async def fetch_source(self, source: IntelligenceSource) -> list[RawIntelItem]:
        """Fetch and store raw items from a source."""
        items = []

        try:
            if source.source_type == "rss":
                raw_items = await self.fetcher.fetch_rss(source)
            else:
                raise ValueError(f"Unsupported source type: {source.source_type}")

            for raw in raw_items:
                # Check for duplicates by external_id
                existing = self.session.query(RawIntelItem).filter(
                    RawIntelItem.source_id == source.id,
                    RawIntelItem.external_id == raw["external_id"]
                ).first()

                if not existing:
                    item = RawIntelItem(
                        source_id=source.id,
                        external_id=raw["external_id"],
                        title=raw["title"],
                        content=raw["content"],
                        url=raw["url"],
                        published_at=raw["published_at"]
                    )
                    self.session.add(item)
                    items.append(item)

            source.last_checked_at = datetime.now(timezone.utc)
            source.status = "active"
            source.last_error = None
            self.session.commit()

        except Exception as e:
            source.status = "error"
            source.last_error = str(e)
            self.session.commit()
            raise

        return items

    async def process_item(self, item: RawIntelItem) -> dict:
        """Process a raw item through AI analysis."""
        source = item.source
        source_context = {
            "source_name": source.name,
            "default_region": source.default_region,
            "default_theme": source.default_theme,
            "reliability": source.reliability_score
        }

        analysis = await self.analyzer.analyze_content(
            item.title, item.content, source_context
        )

        # Update item with analysis
        item.is_processed = True
        item.processed_at = datetime.now(timezone.utc)
        item.is_relevant = analysis.get("is_relevant", True)
        item.ai_summary = analysis.get("summary")
        item.ai_region = analysis.get("region")
        item.ai_country = analysis.get("country")
        item.ai_theme = analysis.get("theme")
        item.ai_sector = analysis.get("sector")
        item.ai_severity = analysis.get("severity")
        item.ai_confidence = analysis.get("confidence")
        item.ai_tags = json.dumps(analysis.get("tags", []))
        item.ai_reasoning = analysis.get("reasoning")

        self.session.commit()
        return analysis

    async def promote_to_event(self, item: RawIntelItem, owner_id: int | None = None) -> Event:
        """Promote a processed raw item to a full Event."""
        if not item.is_processed:
            await self.process_item(item)

        occurred_at = item.published_at or item.fetched_at
        fingerprint = compute_event_fingerprint(item.title, item.ai_region or "Global", occurred_at)

        # Check for duplicate event
        existing = self.session.query(Event).filter(
            Event.fingerprint == fingerprint
        ).first()

        if existing:
            item.is_duplicate = True
            item.event_id = existing.id
            # Add timeline entry for the new source
            entry = EventTimelineEntry(
                event_id=existing.id,
                description=f"Additional source: {item.source.name}",
                entry_type="source_update"
            )
            self.session.add(entry)
            self.session.commit()
            return existing

        # Create new event
        event = Event(
            title=item.title[:200],
            summary=item.ai_summary or item.content[:500],
            region=item.ai_region or "Global",
            country=item.ai_country,
            theme=item.ai_theme or "other",
            sector=item.ai_sector,
            severity=item.ai_severity or 2,
            confidence=item.ai_confidence or 0.5,
            occurred_at=occurred_at,
            fingerprint=fingerprint,
            owner_id=owner_id,
            is_ai_generated=True,
            ai_source_id=item.source_id
        )
        self.session.add(event)
        self.session.flush()

        # Add source reference
        source_ref = Source(
            name=item.source.name,
            url=item.url,
            reliability=item.source.reliability_score,
            event_id=event.id
        )
        self.session.add(source_ref)

        # Add creation timeline entry
        entry = EventTimelineEntry(
            event_id=event.id,
            description="Event auto-generated from intelligence feed",
            entry_type="ai_update"
        )
        self.session.add(entry)

        # Add tags
        tags_list = json.loads(item.ai_tags) if item.ai_tags else []
        for tag_name in tags_list[:5]:  # Limit to 5 tags
            tag = self.session.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                self.session.add(tag)
            event.tags.append(tag)

        item.event_id = event.id
        self.session.commit()

        return event

    async def run_detection_cycle(self) -> dict:
        """Run a full signal detection cycle."""
        # Get recent events (last 48 hours)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        recent_events = self.session.query(Event).filter(
            Event.occurred_at >= cutoff
        ).all()

        signals = await self.signal_detector.detect_signals(recent_events)

        created_signals = []
        for signal_data in signals:
            signal = Signal(
                title=signal_data["title"],
                description=signal_data["description"],
                signal_type=signal_data["signal_type"],
                severity=signal_data["severity"],
                confidence=signal_data["confidence"],
                region=signal_data["region"],
                themes=json.dumps(signal_data["themes"]),
                supporting_event_ids=json.dumps(signal_data["supporting_event_ids"]),
                evidence_summary=signal_data["evidence_summary"],
                key_indicators=signal_data["key_indicators"],
                watch_for=signal_data["watch_for"],
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
            )
            self.session.add(signal)
            created_signals.append(signal)

        self.session.commit()

        return {
            "events_analyzed": len(recent_events),
            "signals_detected": len(created_signals)
        }


# Demo RSS sources for geopolitical intelligence
DEMO_SOURCES = [
    {
        "name": "Reuters World News",
        "source_type": "rss",
        "url": "https://feeds.reuters.com/Reuters/worldNews",
        "default_region": "Global",
        "default_theme": "conflict",
        "reliability_score": 0.9
    },
    {
        "name": "BBC World",
        "source_type": "rss",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "default_region": "Global",
        "default_theme": "conflict",
        "reliability_score": 0.9
    },
    {
        "name": "Al Jazeera",
        "source_type": "rss",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "default_region": "Middle East",
        "default_theme": "conflict",
        "reliability_score": 0.8
    }
]


def seed_demo_sources(session: Session) -> list[IntelligenceSource]:
    """Seed demo intelligence sources."""
    sources = []
    for src_data in DEMO_SOURCES:
        existing = session.query(IntelligenceSource).filter(
            IntelligenceSource.name == src_data["name"]
        ).first()
        if not existing:
            source = IntelligenceSource(**src_data)
            session.add(source)
            sources.append(source)
    session.commit()
    return sources

