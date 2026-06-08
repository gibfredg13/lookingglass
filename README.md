<<<<<<< HEAD
# lookingglass
=======
# The Analyst Lens

AI-Powered Geopolitical Intelligence Platform for Banking

## Overview

The Analyst Lens is an AI-enabled geopolitical intelligence platform designed for Dutch banking sector risk management. The platform:
- Monitors global events with specific focus on banking sector implications
- Analyzes impact on trade finance, sanctions compliance, and correspondent banking
- Emphasizes relevance to Netherlands and European financial operations
- Produces intelligence briefs tailored for banking leadership
- Supports risk scenarios for credit, operational, and compliance risk

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        ANALYST LENS                               │
├──────────────────────────────────────────────────────────────────┤
│  Frontend (Streamlit)                                             │
│  ┌─────────┬─────────┬────────┬─────────┬──────────┬──────────┐ │
│  │Dashboard│ Monitor │ Inbox  │ Events  │ Signals  │ Outlooks │ │
│  └─────────┴─────────┴────────┴─────────┴──────────┴──────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI)                                                │
│  ┌─────────────┬──────────────┬──────────────┬─────────────────┐ │
│  │ Intelligence│    Events    │   Outlooks   │   Scenarios     │ │
│  │  Ingestion  │   Management │   Engine     │    Builder      │ │
│  └─────────────┴──────────────┴──────────────┴─────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  AI Services                                                      │
│  ┌─────────────┬──────────────┬──────────────┬─────────────────┐ │
│  │   Content   │    Signal    │   Outlook    │  Ask Anything   │ │
│  │  Analyzer   │   Detector   │  Generator   │     Q&A         │ │
│  └─────────────┴──────────────┴──────────────┴─────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  Database (PostgreSQL/SQLite)                                     │
│  Sources │ Raw Items │ Events │ Signals │ Outlooks │ Scenarios  │
└──────────────────────────────────────────────────────────────────┘
```

## Workflow

### 1. Monitor (Intelligence Ingestion)
- Configure intelligence sources (RSS feeds, APIs)
- Auto-fetch news from Reuters, BBC, Al Jazeera, etc.
- Sources are checked periodically for new content

### 2. Inbox (AI Processing)
- Raw items are analyzed by AI (GPT-4 or heuristics fallback)
- AI extracts: region, country, theme, sector, severity, tags
- Items are scored for relevance and duplicates detected
- Relevant items can be promoted to Events

### 3. Events
- Central repository of intelligence events
- Each event has: title, summary, classification, sources, timeline
- Events can be tagged, edited, and published to stakeholders
- Duplicate detection via content fingerprinting

### 4. Stories (Distribution)
- Generate news stories from verified events
- Source verification workflow: unverified → verified/disputed/retracted
- Story workflow: Draft → Review → Approved → Published
- **Stories cannot be published unless ALL sources are verified**
- Public feed for stakeholder distribution

### 5. Signals (Early Warning)
- AI analyzes event patterns to detect emerging trends
- Signal types: escalation, de-escalation, emerging trend, inflection point
- Signals include: evidence, key indicators, what to watch for
- Analysts acknowledge and annotate signals

### 6. Outlooks (Trend Briefs)
- AI-generated 24/48/72 hour forecasts
- Based on recent events in a region/theme
- Includes: expected developments, key indicators, implications
- Review workflow: Draft → Reviewed → Published

### 7. Scenarios
- Build baseline, upside, and downside scenarios
- Define triggers, warning indicators, impacts
- Track probability and time horizons
- Templates for consistent scenario development

### 8. Ask Anything
- Natural language Q&A over intelligence data
- Answers with citations and confidence levels
- Includes sentiment and risk assessment

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Run tests (uses SQLite, no Postgres needed)
pytest

# 3. Start API server
uvicorn app.main:get_app --factory --reload

# 4. Start frontend
cd frontend && streamlit run app.py
```

### With Docker

```bash
# Start full stack
docker compose up -d

# API: http://localhost:8000
# Frontend: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

## Demo Credentials

- **Email:** demo@analyst-lens.local
- **Password:** demo123

## Demo Data

The application comes pre-seeded with demonstration data showing the complete workflow:

**Events (4):**
- Red Sea Houthi Attack (fully verified, 2 sources)
- EU Sanctions Package (published, verified)
- Taiwan Strait Exercises (mixed verification)
- European Port Cyberattack (disputed source)

**News Stories (4):**
- Published: Red Sea Shipping story (all sources verified)
- Approved: EU Sanctions story (ready to publish)
- In Review: Taiwan story (needs source verification)
- Draft: Cyberattack story (disputed source)

**Signals (2):**
- High: Red Sea escalation (unacknowledged)
- Medium: European cyber threats (acknowledged)

**Outlooks (2):**
- 24h Middle East/Shipping outlook (published)
- 48h Europe/Cyber outlook (reviewed)

**Scenarios (2):**
- Red Sea Baseline scenario
- Red Sea Downside scenario

### Demo Workflow

1. **Login** with demo credentials
2. **Dashboard** shows overview of all intelligence
3. **Events** - View events and their sources
4. **Stories** - See stories in different workflow states:
   - Published story (all sources verified)
   - Approved story ready for publishing
   - Story in review (needs source verification)
   - Draft story with disputed source
5. **Verify Sources** - In Stories tab, use "Verify Sources" to check/verify event sources
6. **Publish** - Only stories with all sources verified can be published

## Environment Variables

Create `.env` file:

```bash
AL_DATABASE_URL=postgresql://user:pass@localhost:5432/analyst_lens
AL_SECRET_KEY=your-secret-key-change-in-production
OPENAI_API_KEY=sk-...  # Optional: for AI-powered analysis
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register analyst
- `POST /api/v1/auth/login` - Login (returns JWT)
- `GET /api/v1/auth/me` - Get current analyst

### Intelligence
- `GET /api/v1/intelligence/sources` - List sources
- `POST /api/v1/intelligence/sources` - Add source
- `POST /api/v1/intelligence/sources/{id}/fetch` - Fetch from source
- `GET /api/v1/intelligence/items` - List raw items
- `POST /api/v1/intelligence/items/{id}/process` - AI analyze
- `POST /api/v1/intelligence/items/{id}/promote` - Create event
- `GET /api/v1/intelligence/signals` - List signals
- `POST /api/v1/intelligence/signals/detect` - Run detection

### Events
- `GET /api/v1/events` - List events (analyst workspace)
- `POST /api/v1/events` - Create event
- `GET /api/v1/events/{id}` - Get event with timeline
- `PATCH /api/v1/events/{id}/publish` - Publish/unpublish
- `POST /api/v1/events/{id}/timeline` - Add timeline entry

### Outlooks
- `GET /api/v1/outlooks` - List outlooks
- `POST /api/v1/outlooks/generate` - Generate outlooks

### Scenarios
- `GET /api/v1/scenarios` - List scenarios
- `POST /api/v1/scenarios` - Create scenario

### Ask Anything
- `POST /api/v1/ask` - Ask question
- `GET /api/v1/ask/history` - Q&A history

### News Stories
- `GET /api/v1/stories` - List stories
- `POST /api/v1/stories` - Create story
- `POST /api/v1/stories/generate` - AI-generate story from events
- `GET /api/v1/stories/published` - Public feed
- `PATCH /api/v1/stories/{id}/status` - Update workflow status
- `POST /api/v1/stories/sources/{id}/verify` - Verify a source
- `GET /api/v1/stories/events/{id}/sources` - Get sources with verification
- `GET /api/v1/stories/verification-status` - Check if all sources verified

## Priority Monitoring Areas

The platform is designed for Dutch banking sector risk monitoring:
- **Regions:** Netherlands, Europe, Middle East, Gulf, China, Taiwan, US, Russia
- **Themes:** Sanctions, Trade, Cyber, Conflict, Energy, Shipping, Financial Regulation
- **Banking Focus:** Trade finance, Correspondent banking, Sanctions compliance, Credit risk, Operational risk
- **Key Concerns:** DNB regulatory compliance, ECB guidance, SWIFT restrictions, KYC/AML implications

## Development

```bash
# Run tests
pytest

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** Streamlit, Plotly
- **AI:** OpenAI GPT-4 (with heuristic fallback)
- **Auth:** JWT tokens, bcrypt password hashing

## License

Internal use only - ING Bank

>>>>>>> 28cfc65 (Initial commit)
