"""
Demo data seeder for Analyst Lens.

Creates a complete demo workflow:
- Intelligence sources (RSS feeds)
- Events with multiple sources
- Verified and unverified sources
- News stories in various workflow states
- Signals and outlooks
"""
from datetime import datetime, timezone, timedelta
import json

from app.db import build_engine, build_session_factory
from app.models import (
    Base, Analyst, Event, Source, SourceVerification, Tag,
    NewsStory, Signal, Outlook, Scenario, EventTimelineEntry,
    IntelligenceSource, RawIntelItem
)
from app.services.auth import hash_password

DATABASE_URL = "sqlite:///./data/analyst_lens.db"


def seed_demo_data(session_factory) -> None:
    """Seed comprehensive demo data for the application."""

    with session_factory() as db:
        # Check if demo already seeded
        if db.query(NewsStory).count() > 0:
            print("Demo data already exists. Skipping.")
            return

        # Get or create demo analyst
        analyst = db.query(Analyst).filter(Analyst.email == "demo@analyst-lens.local").first()
        if not analyst:
            analyst = Analyst(
                email="demo@analyst-lens.local",
                hashed_password=hash_password("demo123"),
                full_name="Demo Analyst",
                role="admin",
                is_active=True
            )
            db.add(analyst)
            db.flush()

        # Create tags
        tag_names = ["shipping", "energy", "sanctions", "conflict", "cyber", "elections", "trade", "terrorism"]
        tags = {}
        for name in tag_names:
            existing = db.query(Tag).filter(Tag.name == name).first()
            if not existing:
                tag = Tag(name=name, category="theme")
                db.add(tag)
                tags[name] = tag
            else:
                tags[name] = existing
        db.flush()

        now = datetime.now(timezone.utc)

        # =====================================================================
        # Event 1: Red Sea Shipping (Verified - Ready for publication)
        # =====================================================================
        event1 = Event(
            title="Houthi forces target commercial vessel in Red Sea",
            summary="A commercial cargo vessel was targeted by Houthi forces while transiting the Bab el-Mandeb strait. The vessel sustained minor damage but continued to its destination. This marks the fifth incident this week, indicating an escalation in militia activity targeting international shipping lanes.",
            region="Middle East",
            country="Yemen",
            theme="shipping",
            sector="shipping",
            risk_type="operational",
            severity=4,
            confidence=0.85,
            occurred_at=now - timedelta(hours=6),
            fingerprint="abc123def456",
            owner_id=analyst.id,
            is_ai_generated=False
        )
        event1.tags = [tags["shipping"], tags["conflict"]]
        db.add(event1)
        db.flush()

        # Add verified sources
        source1a = Source(
            name="Reuters Maritime",
            url="https://reuters.com/maritime/red-sea-attack",
            reliability=0.9,
            event_id=event1.id,
            verification_status="verified"
        )
        db.add(source1a)
        db.flush()

        # Add verification record
        verif1a = SourceVerification(
            source_id=source1a.id,
            status="verified",
            verification_method="cross-reference",
            verification_notes="Confirmed by Lloyd's List and shipping industry sources",
            verified_url="https://lloydslist.maritimeintelligence.informa.com/",
            verified_at=now - timedelta(hours=4),
            verified_by_id=analyst.id
        )
        db.add(verif1a)

        source1b = Source(
            name="UKMTO Official Statement",
            url="https://ukmto.gov.uk/statement/2024-red-sea",
            reliability=0.95,
            event_id=event1.id,
            verification_status="verified"
        )
        db.add(source1b)
        db.flush()

        verif1b = SourceVerification(
            source_id=source1b.id,
            status="verified",
            verification_method="official_confirmation",
            verification_notes="Official UK Maritime Trade Operations statement",
            verified_at=now - timedelta(hours=3),
            verified_by_id=analyst.id
        )
        db.add(verif1b)

        # Timeline entries
        db.add(EventTimelineEntry(
            event_id=event1.id,
            description="Event created from intelligence monitoring",
            entry_type="manual"
        ))
        db.add(EventTimelineEntry(
            event_id=event1.id,
            description="Source verified: Reuters Maritime (cross-reference)",
            entry_type="source_update",
            recorded_at=now - timedelta(hours=4)
        ))
        db.add(EventTimelineEntry(
            event_id=event1.id,
            description="Source verified: UKMTO Official Statement",
            entry_type="source_update",
            recorded_at=now - timedelta(hours=3)
        ))

        # =====================================================================
        # Event 2: China-Taiwan Tensions (Mixed verification)
        # =====================================================================
        event2 = Event(
            title="PLA conducts large-scale exercises near Taiwan Strait",
            summary="The Chinese People's Liberation Army has commenced large-scale military exercises in waters near the Taiwan Strait. The exercises include live-fire drills and simulated amphibious landing operations. Taiwan has raised its alert level in response.",
            region="Asia Pacific",
            country="China",
            theme="conflict",
            sector="defense",
            risk_type="geopolitical",
            severity=5,
            confidence=0.78,
            occurred_at=now - timedelta(hours=12),
            fingerprint="xyz789ghi012",
            owner_id=analyst.id,
            is_ai_generated=False
        )
        event2.tags = [tags["conflict"]]
        db.add(event2)
        db.flush()

        source2a = Source(
            name="Taiwan Ministry of Defense",
            url="https://mnd.gov.tw/statement",
            reliability=0.88,
            event_id=event2.id,
            verification_status="verified"
        )
        db.add(source2a)
        db.flush()

        verif2a = SourceVerification(
            source_id=source2a.id,
            status="verified",
            verification_method="official_confirmation",
            verification_notes="Official statement from Taiwan MOD",
            verified_at=now - timedelta(hours=10),
            verified_by_id=analyst.id
        )
        db.add(verif2a)

        source2b = Source(
            name="Social Media Reports",
            url="https://twitter.com/thread/123456",
            reliability=0.45,
            event_id=event2.id,
            verification_status="unverified"
        )
        db.add(source2b)

        db.add(EventTimelineEntry(
            event_id=event2.id,
            description="Event created - high priority monitoring",
            entry_type="manual"
        ))

        # =====================================================================
        # Event 3: EU Sanctions (Verified)
        # =====================================================================
        event3 = Event(
            title="EU announces new sanctions package targeting Russian energy sector",
            summary="The European Union has announced its 14th sanctions package targeting Russia, with new restrictions on the energy sector including LNG transshipments and shadow fleet operations. The measures are expected to impact global energy markets and shipping routes.",
            region="Europe",
            country="Multi-country",
            theme="sanctions",
            sector="energy",
            risk_type="regulatory",
            severity=4,
            confidence=0.92,
            occurred_at=now - timedelta(days=1),
            fingerprint="eu14sanc2024",
            owner_id=analyst.id,
            is_ai_generated=False,
            is_published=True,
            published_at=now - timedelta(hours=20)
        )
        event3.tags = [tags["sanctions"], tags["energy"]]
        db.add(event3)
        db.flush()

        source3a = Source(
            name="European Commission Press Release",
            url="https://ec.europa.eu/press/sanctions-14",
            reliability=0.98,
            event_id=event3.id,
            verification_status="verified"
        )
        db.add(source3a)
        db.flush()

        verif3a = SourceVerification(
            source_id=source3a.id,
            status="verified",
            verification_method="official_confirmation",
            verification_notes="Official EC press release",
            verified_at=now - timedelta(hours=22),
            verified_by_id=analyst.id
        )
        db.add(verif3a)

        source3b = Source(
            name="Financial Times Analysis",
            url="https://ft.com/eu-sanctions-analysis",
            reliability=0.88,
            event_id=event3.id,
            verification_status="verified"
        )
        db.add(source3b)
        db.flush()

        verif3b = SourceVerification(
            source_id=source3b.id,
            status="verified",
            verification_method="cross-reference",
            verification_notes="Detailed analysis corroborating official announcement",
            verified_at=now - timedelta(hours=21),
            verified_by_id=analyst.id
        )
        db.add(verif3b)

        # =====================================================================
        # Event 4: Cyber Attack (Under investigation - disputed source)
        # =====================================================================
        event4 = Event(
            title="Major cyberattack reported on European port infrastructure",
            summary="Multiple European ports are reporting IT system disruptions that appear to be the result of a coordinated cyberattack. Operations at several terminals have been suspended while incident response teams investigate.",
            region="Europe",
            country="Netherlands",
            theme="cyber",
            sector="shipping",
            risk_type="operational",
            severity=4,
            confidence=0.65,
            occurred_at=now - timedelta(hours=3),
            fingerprint="europort_cyber1",
            owner_id=analyst.id,
            is_ai_generated=True
        )
        event4.tags = [tags["cyber"], tags["shipping"]]
        db.add(event4)
        db.flush()

        source4a = Source(
            name="Port of Rotterdam Statement",
            url="https://portofrotterdam.com/incident",
            reliability=0.85,
            event_id=event4.id,
            verification_status="verified"
        )
        db.add(source4a)
        db.flush()

        verif4a = SourceVerification(
            source_id=source4a.id,
            status="verified",
            verification_method="official_confirmation",
            verification_notes="Port authority confirmed operational disruption",
            verified_at=now - timedelta(hours=2),
            verified_by_id=analyst.id
        )
        db.add(verif4a)

        source4b = Source(
            name="Anonymous Telegram Channel",
            url="https://t.me/hackergroup/12345",
            reliability=0.2,
            event_id=event4.id,
            verification_status="disputed"
        )
        db.add(source4b)
        db.flush()

        verif4b = SourceVerification(
            source_id=source4b.id,
            status="disputed",
            verification_method="cross-reference",
            verification_notes="Claims of Russian involvement cannot be verified. Conflicting attribution.",
            verified_at=now - timedelta(hours=1),
            verified_by_id=analyst.id
        )
        db.add(verif4b)

        db.flush()

        # =====================================================================
        # NEWS STORIES
        # =====================================================================

        # Story 1: Published (all sources verified)
        story1 = NewsStory(
            headline="Red Sea Shipping Faces Escalating Threat from Houthi Attacks",
            subheadline="Fifth incident this week signals growing risk to international trade routes",
            body="""Commercial shipping through the Red Sea faces increasingly severe operational risks as Houthi forces continue to target vessels transiting the Bab el-Mandeb strait.

The latest incident, involving a commercial cargo vessel that sustained minor damage while transiting the strait, marks the fifth attack this week. While the vessel successfully continued to its destination, the pattern indicates a concerning escalation in militia activity.

Industry sources report that shipping rates for the route have increased by approximately 200% over the past month, with several major carriers now routing vessels around the Cape of Good Hope, adding 10-14 days to transit times between Asia and Europe.

The UK Maritime Trade Operations (UKMTO) has issued updated guidance recommending enhanced security measures for all vessels transiting the region. Naval coalition forces have increased patrol activities, but the dispersed nature of attacks continues to challenge interdiction efforts.""",
            executive_summary="Houthi attacks on Red Sea shipping have escalated to five incidents this week, causing significant disruption to global trade routes and driving up shipping costs.",
            region="Middle East",
            theme="shipping",
            sector="shipping",
            impact_level="high",
            business_implications="Supply chain delays of 10-14 days for Asia-Europe routes. Shipping costs increased 200%. Insurance premiums rising. Consider alternative sourcing or inventory buffer strategies.",
            recommended_actions="Review supply chain exposure to Red Sea routes. Engage with logistics providers on contingency planning. Monitor insurance policy coverage for conflict zones.",
            source_event_ids=json.dumps([event1.id]),
            all_sources_verified=True,
            verification_summary="2/2 sources verified",
            status="published",
            published_at=now - timedelta(hours=2),
            author_id=analyst.id
        )
        db.add(story1)

        # Story 2: Approved (ready to publish, all verified)
        story2 = NewsStory(
            headline="EU's 14th Sanctions Package Targets Russian Energy and Shadow Fleet",
            subheadline="New measures expected to disrupt global LNG trade and shipping patterns",
            body="""The European Union has unveiled its 14th sanctions package against Russia, introducing significant new restrictions on the energy sector that could reshape global trade flows.

Key measures include:
- Prohibition on transshipment of Russian LNG through EU ports
- Enhanced targeting of shadow fleet vessels engaged in sanctions evasion
- New restrictions on dual-use technology exports
- Expanded list of sanctioned individuals and entities

Energy market analysts expect these measures to impact LNG pricing and availability, particularly for Asian buyers who have relied on EU transshipment facilities. The shadow fleet restrictions may force restructuring of Russian crude oil export logistics.

Implementation timelines vary by measure, with most entering into force within 30-60 days of official publication in the EU Official Journal.""",
            executive_summary="EU's 14th sanctions package introduces major new restrictions on Russian energy sector, targeting LNG transshipments and shadow fleet operations.",
            region="Europe",
            theme="sanctions",
            sector="energy",
            impact_level="high",
            business_implications="LNG supply patterns may shift. Shadow fleet disruption could affect crude oil pricing. Compliance review needed for any Russian energy exposure.",
            recommended_actions="Conduct sanctions compliance review. Assess exposure to LNG supply disruptions. Review shipping counterparty due diligence.",
            source_event_ids=json.dumps([event3.id]),
            all_sources_verified=True,
            verification_summary="2/2 sources verified",
            status="approved",
            approved_at=now - timedelta(hours=1),
            author_id=analyst.id
        )
        db.add(story2)

        # Story 3: In Review (needs verification)
        story3 = NewsStory(
            headline="Taiwan Strait Tensions Rise as PLA Conducts Major Exercises",
            subheadline="Live-fire drills and amphibious landing simulations prompt regional alert",
            body="""Geopolitical tensions in the Taiwan Strait have intensified as the Chinese People's Liberation Army commenced large-scale military exercises in waters near Taiwan.

The exercises, which include live-fire drills and simulated amphibious landing operations, represent one of the largest military activities in the region this year. Taiwan has elevated its alert status in response.

Regional analysts note that the timing coincides with recent diplomatic developments and military exercises may serve multiple strategic signaling purposes.

Maritime traffic in the strait continues to operate, though with enhanced monitoring. No direct impact on commercial shipping has been reported at this time.""",
            executive_summary="PLA military exercises near Taiwan Strait have prompted elevated alert levels, though commercial maritime traffic remains unaffected.",
            region="Asia Pacific",
            theme="conflict",
            sector="defense",
            impact_level="critical",
            business_implications="Monitor for potential shipping disruptions. Semiconductor supply chain exposure should be reviewed. Regional operational continuity plans may need activation.",
            recommended_actions="Review Taiwan-related supply chain dependencies. Monitor shipping advisories. Prepare contingency communication plans.",
            source_event_ids=json.dumps([event2.id]),
            all_sources_verified=False,
            verification_summary="1/2 sources verified. Unverified: Social Media Reports",
            status="review",
            reviewed_at=now - timedelta(minutes=30),
            author_id=analyst.id,
            reviewer_notes="Need to verify or remove social media source before publishing"
        )
        db.add(story3)

        # Story 4: Draft (cyber attack, under investigation)
        story4 = NewsStory(
            headline="European Port Infrastructure Hit by Coordinated Cyberattack",
            subheadline="Multiple terminals report IT disruptions as investigation continues",
            body="""A coordinated cyberattack has disrupted operations at multiple European port facilities, with initial reports indicating widespread IT system failures.

The Port of Rotterdam has confirmed operational disruptions, with container terminal systems affected. Similar incidents have been reported at other major European ports, suggesting a coordinated campaign.

Incident response teams are currently investigating the scope and origin of the attack. While some sources have attributed the attack to specific threat actors, these claims remain unverified.

Port authorities are working to restore operations and have implemented emergency procedures to maintain critical functions.""",
            executive_summary="Coordinated cyberattack disrupts multiple European port facilities. Investigation ongoing with attribution unconfirmed.",
            region="Europe",
            theme="cyber",
            sector="shipping",
            impact_level="high",
            business_implications="Potential delays at affected ports. Review cybersecurity posture for connected systems. Supply chain visibility may be temporarily reduced.",
            recommended_actions="Contact logistics providers for shipment status updates. Review own IT security measures. Prepare for potential operational delays.",
            source_event_ids=json.dumps([event4.id]),
            all_sources_verified=False,
            verification_summary="1/2 sources verified. Disputed: Anonymous Telegram Channel",
            status="draft",
            author_id=analyst.id
        )
        db.add(story4)

        # =====================================================================
        # SIGNALS
        # =====================================================================

        signal1 = Signal(
            title="Escalating Red Sea shipping disruptions",
            description="Pattern analysis indicates sustained and increasing Houthi targeting of commercial vessels in the Red Sea corridor.",
            signal_type="escalation",
            severity="high",
            confidence=0.82,
            region="Middle East",
            countries=json.dumps(["Yemen", "Saudi Arabia", "Djibouti"]),
            themes=json.dumps(["shipping", "conflict"]),
            supporting_event_ids=json.dumps([event1.id]),
            evidence_summary="5 incidents in past week, up from 2 previous week. Increasing sophistication of attacks noted.",
            key_indicators="Attack frequency, weapon systems employed, vessel types targeted",
            watch_for="Coalition military response, major carrier route changes, insurance market reactions",
            is_active=True,
            is_acknowledged=False
        )
        db.add(signal1)

        signal2 = Signal(
            title="Cyber threat to European critical infrastructure",
            description="Emerging pattern of cyberattacks targeting European port and logistics infrastructure.",
            signal_type="emerging_trend",
            severity="medium",
            confidence=0.65,
            region="Europe",
            countries=json.dumps(["Netherlands", "Germany", "Belgium"]),
            themes=json.dumps(["cyber", "shipping"]),
            supporting_event_ids=json.dumps([event4.id]),
            evidence_summary="First coordinated attack on multiple EU port facilities. Attribution unclear but methodology consistent with state-sponsored actors.",
            key_indicators="Target selection, attack vectors, timing coordination",
            watch_for="Attribution claims, additional targets, defensive measures announced",
            is_active=True,
            is_acknowledged=True,
            acknowledged_by_id=analyst.id,
            analyst_notes="Monitoring closely. Have alerted IT security team."
        )
        db.add(signal2)

        # =====================================================================
        # OUTLOOKS
        # =====================================================================

        outlook24 = Outlook(
            horizon_hours=24,
            region="Middle East",
            theme="shipping",
            executive_summary="Red Sea situation expected to remain tense with high probability of additional incidents.",
            expected_developments="Continued Houthi activity likely. Coalition naval presence may conduct visible patrols. Shipping industry guidance updates expected.",
            key_indicators="UKMTO advisories, naval coalition statements, shipping traffic patterns, insurance rate movements",
            implications="Short-term supply chain disruptions likely to persist. Premium on alternative routing capacity.",
            confidence=0.75,
            rationale="Based on attack pattern analysis and lack of de-escalation indicators.",
            sentiment="negative",
            risk_direction="increasing",
            source_event_ids=json.dumps([event1.id]),
            status="published",
            published_at=now - timedelta(hours=4),
            owner_id=analyst.id
        )
        db.add(outlook24)

        outlook48 = Outlook(
            horizon_hours=48,
            region="Europe",
            theme="cyber",
            executive_summary="Investigation into port cyberattack expected to progress. Additional targets possible.",
            expected_developments="Attribution analysis may emerge. Affected ports working to restore full operations. Enhanced security measures likely across sector.",
            key_indicators="Official attribution statements, restored operations timeline, security advisories",
            implications="Short-term logistics friction. Longer-term cybersecurity investment acceleration.",
            confidence=0.6,
            rationale="Limited information available. Situation still developing.",
            sentiment="negative",
            risk_direction="stable",
            source_event_ids=json.dumps([event4.id]),
            status="reviewed",
            reviewed_at=now - timedelta(hours=1),
            reviewer_notes="Good analysis given limited info. Publish when we have more clarity.",
            owner_id=analyst.id
        )
        db.add(outlook48)

        outlook72 = Outlook(
            horizon_hours=72,
            region="Global",
            theme="trade",
            executive_summary="Multiple geopolitical flashpoints create elevated risk environment for global trade.",
            expected_developments="EU sanctions implementation begins. Red Sea alternative routing solidifies. Taiwan situation bears monitoring.",
            key_indicators="Shipping rates, insurance costs, commodity prices, official statements",
            implications="Structurally higher logistics costs. Supply chain resilience paramount. Regional exposure to be carefully managed.",
            confidence=0.7,
            rationale="Convergence of multiple risk factors in key trade corridors.",
            sentiment="mixed",
            risk_direction="increasing",
            source_event_ids=json.dumps([event1.id, event3.id, event2.id]),
            status="draft",
            owner_id=analyst.id
        )
        db.add(outlook72)

        # =====================================================================
        # SCENARIOS
        # =====================================================================

        scenario1 = Scenario(
            name="Red Sea Escalation - Baseline",
            case_type="baseline",
            region="Middle East",
            theme="shipping",
            description="Continued Houthi attacks at current pace with gradual shipping industry adaptation.",
            triggers="Sustained militia capability, limited international military intervention effectiveness",
            warning_indicators="Attack frequency remains stable, major carriers maintain alternative routing",
            impacts="10-15% increase in shipping costs for affected routes. 7-14 day transit delays.",
            operational_impacts="Need for enhanced supply chain visibility and buffer inventory.",
            market_impacts="Moderate energy price premium. Shipping sector repricing.",
            time_horizon_hours=720,
            probability=0.55,
            owner_id=analyst.id,
            is_template=False
        )
        db.add(scenario1)

        scenario2 = Scenario(
            name="Red Sea Escalation - Downside",
            case_type="downside",
            region="Middle East",
            theme="shipping",
            description="Major escalation leading to effective closure of Red Sea corridor to commercial traffic.",
            triggers="Successful attack causing significant casualties or vessel loss, direct state involvement",
            warning_indicators="Major carrier complete withdrawal, naval combat operations, regional military escalation",
            impacts="50%+ increase in shipping costs. Extended transit delays. Commodity supply shocks.",
            operational_impacts="Significant supply chain restructuring required. Emergency inventory measures.",
            market_impacts="Sharp energy price spikes. Broad market volatility. Flight to safety.",
            time_horizon_hours=720,
            probability=0.15,
            owner_id=analyst.id,
            is_template=False
        )
        db.add(scenario2)

        scenario_template = Scenario(
            name="Regional Conflict Template",
            case_type="baseline",
            description="Template for analyzing regional conflict scenarios affecting trade routes.",
            triggers="[Define specific conflict triggers]",
            warning_indicators="[Define early warning indicators]",
            impacts="[Define general and specific impacts]",
            operational_impacts="[Define operational impact categories]",
            market_impacts="[Define market impact categories]",
            time_horizon_hours=168,
            owner_id=analyst.id,
            is_template=True
        )
        db.add(scenario_template)

        db.commit()
        print("Demo data seeded successfully!")
        print(f"  - 4 events with sources")
        print(f"  - 4 news stories (published, approved, review, draft)")
        print(f"  - 2 active signals")
        print(f"  - 3 outlooks (24h, 48h, 72h)")
        print(f"  - 3 scenarios")


def main() -> None:
    engine = build_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    session_factory = build_session_factory(engine)
    seed_demo_data(session_factory)


if __name__ == "__main__":
    main()

