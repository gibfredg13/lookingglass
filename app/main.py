from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
import json

from app.config import get_settings
from app.db import build_engine, build_session_factory
from app.models import (
    Analyst, Base, Event, Source, SourceVerification, Tag,
    NewsStory, Signal, Outlook, Scenario, EventTimelineEntry
)
from app.routers import ask, auth, events, outlooks, scenarios, intelligence, stories
from app.services.auth import hash_password
from app.services.intelligence import seed_demo_sources


def _seed_demo_data(session_factory) -> None:
    """Create demo user, sources, events, stories, and full workflow data."""
    with session_factory() as db:
        # Check if demo user exists
        analyst = db.query(Analyst).filter(Analyst.email == "demo@analyst-lens.local").first()
        if not analyst:
            analyst = Analyst(
                email="demo@analyst-lens.local",
                hashed_password=hash_password("demo123"),
                full_name="Demo Analyst",
                role="admin",
                is_active=True,
            )
            db.add(analyst)
            db.commit()
            db.refresh(analyst)

        # Seed demo intelligence sources
        seed_demo_sources(db)

        # Check if demo stories already exist
        if db.query(NewsStory).count() > 0:
            return

        # Create tags
        tag_names = ["shipping", "energy", "sanctions", "conflict", "cyber", "elections", "trade"]
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

        # Event 1: Red Sea Shipping (Verified)
        event1 = Event(
            title="Houthi forces target commercial vessel in Red Sea",
            summary="A commercial cargo vessel was targeted by Houthi forces while transiting the Bab el-Mandeb strait. The vessel sustained minor damage but continued to its destination. This marks the fifth incident this week.",
            region="Middle East",
            country="Yemen",
            theme="shipping",
            sector="shipping",
            risk_type="operational",
            severity=4,
            confidence=0.85,
            occurred_at=now - timedelta(hours=6),
            fingerprint="demo_redsea_001",
            owner_id=analyst.id
        )
        event1.tags = [tags.get("shipping"), tags.get("conflict")]
        event1.tags = [t for t in event1.tags if t]
        db.add(event1)
        db.flush()

        source1a = Source(name="Reuters Maritime", url="https://reuters.com/maritime", reliability=0.9, event_id=event1.id, verification_status="verified")
        db.add(source1a)
        db.flush()
        db.add(SourceVerification(source_id=source1a.id, status="verified", verification_method="cross-reference", verification_notes="Confirmed by Lloyd's List", verified_at=now - timedelta(hours=4), verified_by_id=analyst.id))

        source1b = Source(name="UKMTO Statement", url="https://ukmto.gov.uk", reliability=0.95, event_id=event1.id, verification_status="verified")
        db.add(source1b)
        db.flush()
        db.add(SourceVerification(source_id=source1b.id, status="verified", verification_method="official_confirmation", verification_notes="Official UK Maritime statement", verified_at=now - timedelta(hours=3), verified_by_id=analyst.id))

        db.add(EventTimelineEntry(event_id=event1.id, description="Event created from monitoring", entry_type="manual"))
        db.add(EventTimelineEntry(event_id=event1.id, description="Sources verified", entry_type="source_update", recorded_at=now - timedelta(hours=3)))

        # Event 2: EU Sanctions (Verified, Published)
        event2 = Event(
            title="EU announces 14th sanctions package targeting Russian energy",
            summary="The European Union has announced new restrictions on Russian LNG transshipments and shadow fleet operations. Measures expected to impact global energy markets.",
            region="Europe",
            country="Multi-country",
            theme="sanctions",
            sector="energy",
            risk_type="regulatory",
            severity=4,
            confidence=0.92,
            occurred_at=now - timedelta(days=1),
            fingerprint="demo_eu_sanc_001",
            owner_id=analyst.id,
            is_published=True,
            published_at=now - timedelta(hours=20)
        )
        event2.tags = [tags.get("sanctions"), tags.get("energy")]
        event2.tags = [t for t in event2.tags if t]
        db.add(event2)
        db.flush()

        source2a = Source(name="European Commission", url="https://ec.europa.eu/sanctions", reliability=0.98, event_id=event2.id, verification_status="verified")
        db.add(source2a)
        db.flush()
        db.add(SourceVerification(source_id=source2a.id, status="verified", verification_method="official_confirmation", verification_notes="Official EC release", verified_at=now - timedelta(hours=22), verified_by_id=analyst.id))

        # Event 3: Taiwan (Mixed verification)
        event3 = Event(
            title="PLA conducts exercises near Taiwan Strait",
            summary="Large-scale military exercises including live-fire drills near Taiwan. Regional alert levels elevated.",
            region="Asia Pacific",
            country="China",
            theme="conflict",
            sector="defense",
            severity=5,
            confidence=0.78,
            occurred_at=now - timedelta(hours=12),
            fingerprint="demo_taiwan_001",
            owner_id=analyst.id
        )
        event3.tags = [tags.get("conflict")]
        event3.tags = [t for t in event3.tags if t]
        db.add(event3)
        db.flush()

        source3a = Source(name="Taiwan MOD", url="https://mnd.gov.tw", reliability=0.88, event_id=event3.id, verification_status="verified")
        db.add(source3a)
        db.flush()
        db.add(SourceVerification(source_id=source3a.id, status="verified", verification_method="official_confirmation", verification_notes="Official Taiwan statement", verified_at=now - timedelta(hours=10), verified_by_id=analyst.id))

        source3b = Source(name="Social Media Reports", url="https://twitter.com", reliability=0.4, event_id=event3.id, verification_status="unverified")
        db.add(source3b)

        # Event 4: Cyber Attack (Disputed source)
        event4 = Event(
            title="Cyberattack disrupts European port infrastructure",
            summary="Multiple European ports report coordinated IT disruptions. Investigation ongoing.",
            region="Europe",
            country="Netherlands",
            theme="cyber",
            sector="shipping",
            severity=4,
            confidence=0.65,
            occurred_at=now - timedelta(hours=3),
            fingerprint="demo_cyber_001",
            owner_id=analyst.id,
            is_ai_generated=True
        )
        event4.tags = [tags.get("cyber"), tags.get("shipping")]
        event4.tags = [t for t in event4.tags if t]
        db.add(event4)
        db.flush()

        source4a = Source(name="Port of Rotterdam", url="https://portofrotterdam.com", reliability=0.85, event_id=event4.id, verification_status="verified")
        db.add(source4a)
        db.flush()
        db.add(SourceVerification(source_id=source4a.id, status="verified", verification_method="official_confirmation", verification_notes="Port confirmed disruption", verified_at=now - timedelta(hours=2), verified_by_id=analyst.id))

        source4b = Source(name="Anonymous Telegram", url="https://t.me/anon", reliability=0.2, event_id=event4.id, verification_status="disputed")
        db.add(source4b)
        db.flush()
        db.add(SourceVerification(source_id=source4b.id, status="disputed", verification_method="cross-reference", verification_notes="Attribution claims cannot be verified", verified_at=now - timedelta(hours=1), verified_by_id=analyst.id))

        db.flush()

        # NEWS STORIES - Banking focused content
        # Published story
        db.add(NewsStory(
            headline="Red Sea Shipping Disruptions: Trade Finance Implications",
            subheadline="Banking sector alert: Fifth incident this week impacts trade finance operations",
            body="""Commercial shipping through the Red Sea faces severe operational risks as Houthi forces continue targeting vessels in the Bab el-Mandeb strait.

For banking operations, this escalation has direct implications for trade finance portfolios. Letters of credit for Asia-Europe routes face potential delays of 10-14 days as carriers reroute around the Cape of Good Hope. Shipping rates have increased by approximately 200%, affecting the economics of outstanding trade finance transactions.

Dutch financial institutions with significant trade finance exposure to Asia-Europe corridors should review their portfolios. The Port of Rotterdam, as Europe's largest port, may see cascading delays affecting documentary collection processing and cargo insurance claims.

Risk management teams should update country risk assessments for Yemen and surrounding Gulf states. Correspondent banking relationships with institutions in affected regions warrant enhanced monitoring.""",
            executive_summary="Houthi attacks on Red Sea shipping create direct implications for trade finance operations, with 10-14 day delays and 200% cost increases affecting outstanding letters of credit and documentary collections.",
            region="Middle East", theme="shipping", sector="finance",
            impact_level="high",
            business_implications="1) Trade Finance: Review all L/Cs for Asia-Europe shipping routes. 2) Documentary Collections: Prepare for processing delays. 3) Insurance Claims: Cargo damage claims may increase. 4) Client Advisory: Proactive outreach to shipping/trading clients. 5) Correspondent Banking: Monitor relationships with Gulf region banks.",
            recommended_actions="Immediate: 1) Trade Finance desk to flag affected transactions. 2) Client communication on potential delays. 3) Brief Risk Committee. 4) Update shipping sector risk appetite. 5) Coordinate with Rotterdam port authorities on timeline.",
            source_event_ids=json.dumps([event1.id]),
            all_sources_verified=True, verification_summary="2/2 sources verified",
            status="published", published_at=now - timedelta(hours=2), author_id=analyst.id
        ))

        # Approved story
        db.add(NewsStory(
            headline="EU Sanctions Package: Critical Compliance Review Required",
            subheadline="14th sanctions package demands immediate Dutch banking sector response",
            body="""The European Union's 14th sanctions package against Russia introduces significant new compliance obligations for Dutch financial institutions.

Key measures requiring immediate attention include the prohibition on transshipment of Russian LNG through EU ports, which directly affects the Port of Rotterdam's energy hub operations. Enhanced targeting of shadow fleet vessels will require banks to strengthen vessel screening procedures for ship financing and trade finance involving tanker movements.

For Dutch banks, the new provisions create immediate obligations for: sanctions screening updates, review of existing client relationships with any Russian energy nexus, enhanced due diligence on shipping counterparties, and potential transaction blocking for non-compliant activities.

Implementation timelines of 30-60 days require rapid compliance response. The Dutch Central Bank (DNB) is expected to issue supplementary guidance.""",
            executive_summary="EU's 14th sanctions package requires immediate compliance review by Dutch banks. New restrictions on Russian LNG transshipments and shadow fleet targeting create direct obligations for trade finance and correspondent banking operations.",
            region="Europe", theme="sanctions", sector="finance",
            impact_level="high",
            business_implications="1) Sanctions Compliance: Immediate screening list updates required. 2) Trade Finance: Review all Russian energy-related transactions. 3) Correspondent Banking: Assess secondary sanctions exposure. 4) KYC Updates: Enhanced due diligence on energy sector clients. 5) Regulatory: Prepare for DNB guidance and reporting requirements.",
            recommended_actions="Immediate: 1) Brief Compliance Committee. 2) Update sanctions screening systems. 3) Review pending transactions for affected goods. 4) Client outreach on new restrictions. 5) Prepare regulatory notification to DNB. 6) Legal review of existing energy sector commitments.",
            source_event_ids=json.dumps([event2.id]),
            all_sources_verified=True, verification_summary="1/1 sources verified",
            status="approved", approved_at=now - timedelta(hours=1), author_id=analyst.id
        ))

        # In review story
        db.add(NewsStory(
            headline="Taiwan Strait Crisis: Banking Sector Exposure Assessment",
            subheadline="Elevated military tensions prompt review of semiconductor supply chain financing",
            body="""Escalating military exercises in the Taiwan Strait demand urgent assessment of Dutch banking exposure to Taiwan-related supply chains.

Taiwan's critical role in global semiconductor manufacturing creates concentrated risk for technology sector financing. Dutch banks with exposure to semiconductor supply chains, including ASML-related trade finance, should activate enhanced monitoring protocols.

Country risk ratings for Taiwan require immediate review. Credit exposure to Taiwanese corporates and any guarantee facilities linked to Taiwan operations warrant reassessment of risk appetite.

Regional tension escalation could trigger capital flight and currency volatility affecting Taiwanese banking counterparties.""",
            executive_summary="PLA military exercises near Taiwan create banking sector exposure concerns for semiconductor supply chain financing and Taiwanese counterparty risk.",
            region="Asia Pacific", theme="conflict", sector="finance",
            impact_level="critical",
            business_implications="1) Country Risk: Immediate Taiwan rating review required. 2) Credit Exposure: Assess all Taiwan corporate lending. 3) Trade Finance: Review semiconductor/ASML-related facilities. 4) Correspondent Banking: Monitor Taiwanese bank relationships. 5) FX Exposure: Assess TWD currency risk positions.",
            recommended_actions="1) Convene Regional Risk Committee. 2) Run Taiwan stress test scenarios. 3) Client outreach to tech sector borrowers. 4) Update Taiwan country limit. 5) Brief Board Risk Committee on exposure. Pending: Verify all sources before publishing.",
            source_event_ids=json.dumps([event3.id]),
            all_sources_verified=False, verification_summary="1/2 verified. Unverified: Social Media",
            status="review", reviewed_at=now - timedelta(minutes=30), author_id=analyst.id,
            reviewer_notes="Verify or remove social media source before publishing. Consider adding ASML exposure analysis."
        ))

        # Draft story
        db.add(NewsStory(
            headline="Dutch Port Cyberattack: Banking IT Security Alert",
            subheadline="Rotterdam infrastructure breach triggers financial sector security review",
            body="""A coordinated cyberattack on European ports including Rotterdam raises immediate concerns for Dutch banking IT infrastructure and operational resilience.

The Port of Rotterdam disruption has direct implications for trade finance processing, as documentary workflows depend on port systems connectivity. Dutch banks should verify isolation of their systems from affected port infrastructure and review any API connections to maritime logistics platforms.

Third-party vendor assessment is critical. Banks using port-connected services for trade documentation should activate contingency protocols. Business continuity plans for trade finance operations warrant immediate review given Rotterdam's role as Europe's primary port.

Attribution remains unclear, with unverified claims of state-sponsored actors. Regardless of attribution, the incident demonstrates vulnerability of critical financial infrastructure supporting trade operations.""",
            executive_summary="Cyberattack on Rotterdam port infrastructure triggers review of Dutch banking IT security posture and trade finance operational resilience.",
            region="Europe", theme="cyber", sector="finance",
            impact_level="high",
            business_implications="1) IT Security: Review all port/maritime system connections. 2) Third Parties: Assess vendor exposure to affected infrastructure. 3) Trade Finance: Documentary processing contingency plans. 4) Business Continuity: Verify alternative processing capabilities. 5) Incident Response: Prepare for potential secondary attacks on financial sector.",
            recommended_actions="1) IT Security team to verify system isolation from port infrastructure. 2) Review API connections to maritime platforms. 3) Brief CISO and activate enhanced monitoring. 4) Prepare client advisory if services affected. 5) Coordinate with DNB on sector-wide response. Note: Do not publish until attribution claims verified.",
            source_event_ids=json.dumps([event4.id]),
            all_sources_verified=False, verification_summary="1/2 verified. Disputed: Anonymous Telegram",
            status="draft", author_id=analyst.id
        ))

        # SIGNALS - Banking focused
        db.add(Signal(
            title="Trade Finance Stress: Red Sea Disruptions",
            description="Escalating shipping disruptions in Red Sea corridor creating material impact on trade finance operations. Dutch banks with Asia-Europe trade exposure should monitor closely.",
            signal_type="escalation", severity="high", confidence=0.82,
            region="Middle East",
            countries=json.dumps(["Yemen", "Saudi Arabia"]),
            themes=json.dumps(["shipping", "trade"]),
            supporting_event_ids=json.dumps([event1.id]),
            evidence_summary="5 incidents this week vs 2 last week. 200% shipping cost increase. 10-14 day delays affecting L/C processing timelines.",
            key_indicators="L/C amendment requests, shipping delays, insurance claims, client inquiries",
            watch_for="Major carrier withdrawal, insurance coverage changes, trade finance default indicators",
            is_active=True, is_acknowledged=False
        ))

        db.add(Signal(
            title="Dutch Financial Infrastructure Cyber Threat",
            description="Coordinated cyberattack on Rotterdam port infrastructure signals elevated threat to Dutch financial sector critical systems.",
            signal_type="emerging_trend", severity="medium", confidence=0.65,
            region="Europe",
            countries=json.dumps(["Netherlands", "Germany", "Belgium"]),
            themes=json.dumps(["cyber", "finance"]),
            supporting_event_ids=json.dumps([event4.id]),
            evidence_summary="First coordinated attack on Dutch critical infrastructure. Port of Rotterdam systems affected. Potential state-sponsored methodology.",
            key_indicators="Attack vector analysis, target selection patterns, DNB advisories, NCSC alerts",
            watch_for="Financial sector targeting, secondary attacks, DNB emergency guidance",
            is_active=True, is_acknowledged=True, acknowledged_by_id=analyst.id,
            analyst_notes="Briefed IT Security and CISO. Enhanced monitoring activated. Coordinating with DNB on sector response."
        ))

        # OUTLOOKS - Banking focused
        db.add(Outlook(
            horizon_hours=24, region="Middle East", theme="shipping",
            executive_summary="Red Sea disruptions expected to persist with direct implications for trade finance operations. L/C processing delays of 10-14 days becoming standard.",
            expected_developments="Continued Houthi activity likely. Shipping industry guidance updates expected. Insurance market adjustments. Trade finance clients requesting timeline extensions.",
            key_indicators="UKMTO advisories, shipping rate indices, L/C amendment requests, insurance claim volumes",
            implications="Trade Finance: Expect increased amendment requests. Credit Risk: Monitor shipping sector client stress. Operations: Documentary processing backlogs likely.",
            confidence=0.75, rationale="Attack pattern analysis shows no de-escalation. Banking sector impacts crystallizing.",
            sentiment="negative", risk_direction="increasing",
            source_event_ids=json.dumps([event1.id]),
            status="published", published_at=now - timedelta(hours=4), owner_id=analyst.id
        ))

        db.add(Outlook(
            horizon_hours=48, region="Europe", theme="cyber",
            executive_summary="Dutch financial infrastructure on heightened alert following Rotterdam port cyberattack. DNB expected to issue sector guidance.",
            expected_developments="Attribution analysis may emerge. Port operations restoring. DNB and NCSC coordination on financial sector protection. Enhanced banking sector monitoring protocols likely.",
            key_indicators="DNB communications, NCSC threat level, port restoration timeline, secondary attack indicators",
            implications="IT Security: Maintain enhanced monitoring. Operations: Trade finance processing delays at Rotterdam. Compliance: Potential regulatory reporting obligations.",
            confidence=0.6, rationale="Limited attribution clarity. Potential for escalation to financial sector targets.",
            sentiment="negative", risk_direction="stable",
            source_event_ids=json.dumps([event4.id]),
            status="reviewed", reviewed_at=now - timedelta(hours=1), owner_id=analyst.id,
            reviewer_notes="Good banking focus. Add DNB liaison update before publishing."
        ))

        # SCENARIOS - Banking focused
        db.add(Scenario(
            name="Trade Finance Stress - Baseline", case_type="baseline",
            region="Middle East", theme="shipping",
            description="Continued Red Sea disruptions with gradual banking sector adaptation. Trade finance portfolio stress manageable.",
            triggers="Sustained militia capability, limited military intervention, shipping industry adaptation",
            warning_indicators="L/C amendment rates stable at elevated levels, no major client defaults, insurance coverage maintained",
            impacts="Trade Finance: 15-20% increase in processing complexity. Credit Risk: Shipping sector watchlist expansion.",
            operational_impacts="Documentary processing backlogs. Client service demands increase. Enhanced monitoring resources.",
            market_impacts="Shipping sector credit spreads widen 50-100bps. Trade finance pricing adjustments.",
            time_horizon_hours=720, probability=0.55, owner_id=analyst.id
        ))

        db.add(Scenario(
            name="Trade Finance Crisis - Downside", case_type="downside",
            region="Middle East", theme="shipping",
            description="Major escalation closes Red Sea corridor. Significant trade finance portfolio stress and potential defaults.",
            triggers="Attack causing vessel loss, direct military escalation, major carrier withdrawal",
            warning_indicators="Multiple L/C defaults, insurance coverage withdrawal, major client distress",
            impacts="Trade Finance: Portfolio stress requiring provisions. Credit Risk: Shipping sector downgrades.",
            operational_impacts="Crisis management activation. Client triage required. Regulatory engagement.",
            market_impacts="Shipping sector credit event. Trade finance disruption. Commodity collateral stress.",
            time_horizon_hours=720, probability=0.15, owner_id=analyst.id
        ))

        db.commit()
        print("Demo data seeded: 4 events, 4 stories, 2 signals, 2 outlooks, 2 scenarios")


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    final_database_url = database_url or settings.database_url

    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="AI-powered geopolitical intelligence platform"
    )

    # CORS for frontend
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = build_engine(final_database_url)
    Base.metadata.create_all(bind=engine)
    session_factory = build_session_factory(engine)
    application.state.session_factory = session_factory

    # Seed demo data for development
    _seed_demo_data(session_factory)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(auth.router, prefix=settings.api_prefix)
    application.include_router(events.router, prefix=settings.api_prefix)
    application.include_router(outlooks.router, prefix=settings.api_prefix)
    application.include_router(scenarios.router, prefix=settings.api_prefix)
    application.include_router(ask.router, prefix=settings.api_prefix)
    application.include_router(intelligence.router, prefix=settings.api_prefix)
    application.include_router(stories.router, prefix=settings.api_prefix)
    return application


def get_app() -> FastAPI:
    return create_app()


app = get_app

