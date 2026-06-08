# Feature Status - Analyst Lens v1.1

## Core Features

### Authentication & Authorization
- [x] User registration/login with JWT
- [x] Role-based access (analyst, senior_analyst, admin)
- [x] Per-analyst workspace isolation

### Intelligence Ingestion
- [x] Intelligence source configuration (RSS, API)
- [x] Demo sources: Reuters, BBC, Al Jazeera
- [x] Raw item fetching from sources
- [x] AI content analysis (GPT-4 with heuristic fallback)
- [x] Automatic tagging and classification
- [x] Duplicate detection via fingerprinting
- [x] Promotion to events workflow

### Events Management
- [x] CRUD operations
- [x] Structured tagging (region, country, theme, sector)
- [x] Severity and confidence scoring
- [x] Event timeline with audit entries
- [x] AI-generated vs manual event tracking
- [x] Publish to stakeholder feed
- [x] Source tracking with reliability scores

### Source Verification (NEW)
- [x] Per-source verification status (unverified, verified, disputed, retracted)
- [x] Verification method tracking (cross-reference, official, multiple sources)
- [x] Verification notes and evidence URLs
- [x] Audit trail of verification actions
- [x] Verification status aggregation for events

### News Stories (NEW)
- [x] Generate redistributable stories from verified events
- [x] AI-powered headline and body generation
- [x] Business implications and recommended actions
- [x] Impact level assessment (low, medium, high, critical)
- [x] Source verification requirement for publishing
- [x] Workflow: draft -> review -> approved -> published
- [x] Public published stories feed
- [x] Distribution channel tracking

### Signal Detection
- [x] AI pattern analysis on event clusters
- [x] Escalation/de-escalation detection
- [x] Signal severity classification
- [x] Key indicators and watch items
- [x] Analyst acknowledgement workflow

### Outlooks (24/48/72h)
- [x] AI-generated trend briefs
- [x] Expected developments
- [x] Key indicators/signposts
- [x] Implications analysis
- [x] Sentiment and risk direction
- [x] Review workflow (draft -> reviewed -> published)

### Scenarios
- [x] Baseline/upside/downside cases
- [x] Triggers and warning indicators
- [x] Impact assessment (general, operational, market)
- [x] Template support for reuse

### Ask Anything
- [x] Natural language Q&A interface
- [x] Source-based citations
- [x] Confidence scoring
- [x] Sentiment analysis
- [x] Query history

### Frontend (Streamlit)
- [x] Dashboard with metrics overview
- [x] Monitor page (source management)
- [x] Inbox page (AI processing pipeline)
- [x] Events page (CRUD + timeline + sources)
- [x] Stories page (generate, verify, publish) (NEW)
- [x] Signals page (early warnings)
- [x] Outlooks page (trend briefs)
- [x] Scenarios page (scenario builder)
- [x] Ask page (Q&A interface)

## Complete Application Flow

```
INGESTION                    PROCESSING                   VERIFICATION                 DISTRIBUTION
==========                   ==========                   ============                 ============

┌─────────────┐              ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
│   RSS/API   │              │   AI        │              │   Source    │              │   News      │
│   Sources   │─────────────▶│   Analysis  │─────────────▶│   Verify    │─────────────▶│   Stories   │
│             │              │             │              │             │              │             │
└─────────────┘              └─────────────┘              └─────────────┘              └─────────────┘
      │                            │                            │                            │
      │                            │                            │                            │
      │                            ▼                            ▼                            ▼
      │                      ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
      │                      │   Events    │              │   Status:   │              │   Publish   │
      │                      │   Created   │              │   verified  │              │   to Feed   │
      │                      │             │              │   disputed  │              │             │
      │                      └──────┬──────┘              │   retracted │              └─────────────┘
      │                             │                     └─────────────┘
      │                             │
      │         ┌───────────────────┼───────────────────┐
      │         │                   │                   │
      │         ▼                   ▼                   ▼
      │   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
      │   │   Signals   │     │  Outlooks   │     │  Scenarios  │
      │   │  Detection  │     │ (24/48/72h) │     │  Builder    │
      │   └─────────────┘     └─────────────┘     └─────────────┘
      │
      └──────────────────────────────────────────────────────────────────▶ Ask Anything Q&A


VERIFICATION WORKFLOW:
1. Event created from source
2. Each source attached has verification_status = "unverified"
3. Analyst reviews source, adds verification record
4. Source marked as: verified | disputed | retracted
5. News Stories can only be published when ALL sources verified
```

## Data Models

### New Models (v1.1)
- `SourceVerification` - Verification records with evidence
- `NewsStory` - Redistributable news content from events

### Previous Models (v1.0)
- `IntelligenceSource` - RSS/API feed configuration
- `RawIntelItem` - Ingested items with AI analysis
- `Signal` - AI-detected emerging trends
- `MarketIndicator` - Economic data tracking (future)
- `PredictionMarket` - Polymarket-style signals (future)
- `PriorityArea` - Analyst monitoring focus areas

### Updated Models
- `Event` - Added `is_ai_generated`, `ai_source_id`
- `Source` - Added `verification_status` field
- `EventTimelineEntry` - Added `entry_type` for audit
- `Tag` - Added `category` for classification
- `Outlook` - Added `region`, `theme`, `sentiment`, `risk_direction`
- `Scenario` - Added `warning_indicators`, `operational_impacts`, `market_impacts`

## Priority Monitoring Areas

Pre-configured for:
- **Regions:** Middle East, Gulf, China, Taiwan, US, South America, Europe
- **Themes:** Conflict, Sanctions, Elections, Terrorism, Cyber, Shipping, Energy, Tariffs
- **Sectors:** Energy, Shipping, Finance, Technology, Manufacturing

## API Endpoints

### News Stories (`/api/v1/stories`)
- `POST /` - Create news story manually
- `POST /generate` - AI-generate story from events
- `GET /` - List stories (with filters)
- `GET /published` - Public feed of published stories
- `GET /{id}` - Get single story
- `PATCH /{id}` - Update story content
- `PATCH /{id}/status` - Update workflow status
- `DELETE /{id}` - Delete draft story

### Source Verification (`/api/v1/stories`)
- `POST /sources/{id}/verify` - Add verification record
- `GET /events/{id}/sources` - Get event sources with verification
- `GET /verification-status?event_ids=` - Check verification status

## Future Enhancements

- [ ] Market indicators integration (oil prices, currencies)
- [ ] Prediction market signals (Polymarket, Metaculus)
- [ ] Visual analytics (heat maps, geographic visualization)
- [ ] Background job scheduler for auto-fetch
- [ ] Email/Teams notifications
- [ ] Internal ING data integration
- [ ] Country risk framework linkage
- [ ] Automated story generation triggers
