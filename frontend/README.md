# Analyst Lens - Streamlit Frontend

Interactive dashboard for the Analyst Lens geopolitical intelligence platform.

## Features

- **Dashboard**: Overview metrics, event distribution charts by region/theme/severity
- **Events**: Browse, create, and annotate intelligence events with timeline tracking
- **Outlooks**: Generate and review 24/48/72-hour trend briefs
- **Scenarios**: Build baseline/upside/downside scenario cases

## Quick Start

### Prerequisites
- Python 3.11+
- Backend API running at `http://localhost:8000`

### Install and Run

```zsh
cd frontend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ensure backend is running first
streamlit run app.py
```

The app opens at `http://localhost:8501`

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

Example:
```zsh
API_BASE_URL=http://api.example.com streamlit run app.py
```

## Usage

1. **Register/Login**: Create an analyst account or login with existing credentials
2. **Dashboard**: View aggregate statistics and visualizations
3. **Events**: Ingest new intelligence events with structured tagging
4. **Outlooks**: Generate AI-assisted trend briefs for analyst review
5. **Scenarios**: Build structured scenario cases with triggers and impacts

## Screenshots

The UI provides:
- Pie charts for regional event distribution
- Bar charts for theme and severity breakdown
- Expandable event cards with timeline history
- Form-based event/scenario creation
- Status indicators for outlook review workflow

