# AGENTS Guide

## Project overview
Backend PoC for "The Analyst Lens" geopolitical intelligence platform. Python 3.11+ / FastAPI / SQLAlchemy / PostgreSQL/SQLite.

## Key directories
- `app/` - FastAPI application (routers, services, models, schemas)
- `app/routers/` - API endpoint handlers
- `app/services/` - Business logic (AI analysis, outlook generation)
- `alembic/` - Database migrations
- `tests/` - Integration tests (pytest)
- `frontend/` - Streamlit web interface
- `scripts/` - Seed and utility scripts

## Build and test commands
```zsh
# Install
pip install -e ".[dev]"

# Run tests (uses SQLite, no Postgres needed)
pytest

# Start local Postgres (optional)
docker compose up db -d

# Apply migrations
alembic upgrade head

# Run API server (port 8000)
uvicorn app.main:get_app --factory --reload --port 8000

# Run Streamlit frontend (port 8501)
cd frontend && streamlit run app.py --server.port 8501
```

## Code conventions
- Pydantic schemas in `app/schemas.py` for all request/response DTOs.
- SQLAlchemy ORM models in `app/models.py` using `Mapped[]` type hints.
- Business logic in `app/services/`; routers only handle HTTP concerns.
- JWT authentication via `CurrentAnalyst` dependency (`app/routers/dependencies.py`).
- All protected routes require `Authorization: Bearer <token>` header.

## Data model highlights
- `Analyst` - user identity with role (analyst/senior_analyst/admin).
- `IntelligenceSource` - RSS/API feed configuration for ingestion.
- `RawIntelItem` - ingested items before AI processing.
- `Event` - intelligence item with fingerprint for duplicate detection.
- `Source` - attached to events with verification status.
- `SourceVerification` - verification records with evidence.
- `NewsStory` - redistributable content generated from verified events.
- `Signal` - AI-detected emerging trends.
- `EventTimelineEntry` - audit log entries per event.
- `Outlook` - 24/48/72h generated briefs, owned by analyst.
- `Scenario` - baseline/upside/downside cases, owned by analyst.
- All entities scoped by `owner_id` for workspace isolation.

## Application workflow
1. **Monitor** - Configure RSS/API sources to ingest intelligence
2. **Inbox** - AI processes raw items (classify, tag, summarize)
3. **Events** - Promote relevant items to events with sources
4. **Verify** - Verify each source (cross-reference, official confirmation)
5. **Stories** - Generate news stories from verified events
6. **Publish** - Publish stories for redistribution (requires all sources verified)

## Source verification statuses
- `unverified` - Default, needs analyst review
- `verified` - Confirmed via specified method
- `disputed` - Conflicting information found
- `retracted` - Source withdrawn or proven false

## News story workflow
- `draft` - Initial creation
- `review` - Submitted for senior review
- `approved` - Ready for publishing
- `published` - Public on stakeholder feed
- `archived` - No longer active

## Adding a new feature checklist
1. Add/modify ORM model in `app/models.py`.
2. Add migration: `alembic revision --autogenerate -m "description"`.
3. Add Pydantic schemas in `app/schemas.py`.
4. Add/extend router in `app/routers/`.
5. Register router in `app/main.py` if new module.
6. Add frontend page in `frontend/app.py`.
7. Add integration test in `tests/`.
8. Run `pytest` to verify.

## Environment
Copy `.env.example` to `.env` and set:
- `AL_DATABASE_URL` - Database connection (default: SQLite for dev)
- `AL_SECRET_KEY` - JWT signing secret (change in production)
- `OPENAI_API_KEY` - Optional, for AI-powered analysis

## Demo credentials
- Email: `demo@analyst-lens.local`
- Password: `demo123`

## Product scope reference
See `.idea/idea.md` for full requirements.
See `FEATURE_STATUS.md` for current implementation status.
