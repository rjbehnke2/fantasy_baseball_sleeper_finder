# Fantasy Baseball Sleeper Finder

AI-powered dynasty auction fantasy baseball player evaluations. Uses ML models and LLM-generated scouting reports to identify sleepers, flag bust risks, project career trajectories, and calculate auction values.

## Features

- **Sleeper Detection** — XGBoost + LightGBM ensemble identifies undervalued players poised for breakouts
- **Bust Warnings** — Flags overvalued players showing regression signals
- **Career Trajectory Projections** — Multi-season value curves with confidence bands and position-specific aging models
- **AI Scouting Reports** — Claude-generated narrative reports (full analysis, sleeper spotlight, bust warning, dynasty outlook)
- **Auction Valuations** — SGP-based dollar values calibrated to your league settings
- **Dynasty Rankings** — Long-term value rankings factoring in age, trajectory, and improvement trends
- **Daily Insights Digest** — Automated daily summary of top sleepers, bust warnings, dynasty risers, and improvement leaders
- **Consistency & Improvement Scoring** — Measures performance stability and skills trajectory over time

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | Next.js 14 (App Router), Tailwind CSS, Recharts |
| Database | PostgreSQL 16, SQLAlchemy 2.0 (async) |
| ML | scikit-learn, XGBoost, LightGBM, SHAP, Optuna |
| LLM | Anthropic Claude API |
| Data | pybaseball, MLB-StatsAPI |
| Scheduling | APScheduler |
| Infrastructure | Docker Compose |

## Quick Start (Local Development)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An [Anthropic API key](https://console.anthropic.com/) (optional — only needed for AI scouting reports)

### 1. Clone and configure

```bash
git clone https://github.com/rjbehnke2/fantasy_baseball_sleeper_finder.git
cd fantasy_baseball_sleeper_finder

# Create your .env file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (optional)
```

### 2. Start the stack

```bash
docker compose up -d
```

This starts three containers:
- **PostgreSQL** on port `5432`
- **FastAPI backend** on port `8000`
- **Next.js frontend** on port `3000`

### 3. Seed the database and generate projections

```bash
docker compose exec api python -m scripts.seed_database
```

This will:
1. Build a player ID mapping table from the Chadwick register (~25,000 players)
2. Fetch batting stats (2015–present) from FanGraphs or Baseball Reference
3. Fetch pitching stats (2015–present) from FanGraphs or Baseball Reference
4. Run the ML inference pipeline to generate projections, rankings, and auction values

The seeding process takes several minutes. Data sources are tried in order: FanGraphs API, pybaseball FanGraphs scrapers, then Baseball Reference as a fallback.

To re-run just the inference pipeline (e.g., after a data refresh):

```bash
docker compose exec api python -m scripts.run_inference
```

### 4. Open the app

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **API docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health check:** [http://localhost:8000/health](http://localhost:8000/health)

## Running Without Docker

### Backend

```bash
# Install Python dependencies
pip install -e ".[dev]"

# Start PostgreSQL (must be running on localhost:5432)
# Seed the database and run inference
python -m scripts.seed_database

# Or run them separately:
# python -m scripts.seed_database  # data only
# python -m scripts.run_inference  # projections only

# Start the API server
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/fantasy_baseball` | Async database connection string |
| `DATABASE_URL_SYNC` | `postgresql://postgres:postgres@localhost:5432/fantasy_baseball` | Sync database connection string |
| `ANTHROPIC_API_KEY` | (empty) | Anthropic API key for AI scouting reports |
| `APP_ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `BACKFILL_START_YEAR` | `2015` | Earliest season to fetch historical stats |
| `STATCAST_START_YEAR` | `2019` | Earliest season for Statcast data |

## API Endpoints

### Players
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/players` | List players (search, filter by position/team, paginated) |
| GET | `/api/v1/players/{id}` | Player detail with stats and projections |
| GET | `/api/v1/players/{id}/trajectory` | Multi-season career trajectory projection |
| GET | `/api/v1/players/{id}/scouting-report` | LLM-generated scouting report |
| GET | `/api/v1/players/{id}/scouting-reports` | All scouting report types for a player |

### Rankings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/rankings` | AI-powered overall rankings |
| GET | `/api/v1/rankings/sleepers` | Top sleeper candidates |
| GET | `/api/v1/rankings/busts` | Top bust risks |
| GET | `/api/v1/rankings/dynasty` | Dynasty-focused long-term rankings |
| GET | `/api/v1/rankings/auction-values` | Projected auction dollar values |

### League & Insights
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/league-settings` | Create league configuration |
| GET | `/api/v1/league-settings/{id}` | Get league configuration |
| GET | `/api/v1/insights/daily` | Daily AI insights digest |
| GET | `/health` | Health check |

## ML Models

| Model | Purpose |
|-------|---------|
| **Marcel Baseline** | ZiPS-style weighted projection using 3-year weighted averages with age and regression adjustments |
| **Sleeper Model** | XGBoost + LightGBM ensemble identifying undervalued breakout candidates |
| **Bust Model** | XGBoost + LightGBM ensemble flagging overvalued regression risks |
| **Regression Model** | Detects players likely to regress toward the mean |
| **Consistency Model** | Measures season-to-season and month-to-month performance stability |
| **Improvement Model** | Tracks skills trajectory to find players trending upward |
| **Trajectory Model** | Projects multi-season career value using position-specific aging curves |
| **AI Value Score** | Composite 0–100 score combining all model outputs with weighted components |

## Project Structure

```
fantasy_baseball_sleeper_finder/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # FastAPI route handlers
│   │   ├── db/               # Database session and base
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── services/         # Business logic layer
│   │   └── config.py         # Settings and env vars
│   ├── data_pipeline/
│   │   ├── fetchers/         # Data source integrations (FanGraphs, BBRef, Statcast)
│   │   ├── transformers/     # Data cleaning and feature engineering
│   │   ├── loaders/          # Database persistence
│   │   └── orchestrator.py   # APScheduler nightly/weekly jobs
│   ├── ml/
│   │   ├── models/           # ML model implementations
│   │   ├── features/         # Feature engineering
│   │   ├── inference/        # Prediction pipeline
│   │   └── training/         # Model training scripts
│   └── tests/                # pytest test suite (87 tests)
├── frontend/
│   └── src/
│       ├── app/              # Next.js pages (App Router)
│       ├── components/       # React components (charts, tables, reports)
│       └── lib/              # API client and utilities
├── deploy/                   # Production deployment configs
│   ├── docker-compose.prod.yml
│   ├── railway.toml
│   └── fly.toml
├── scripts/
│   └── seed_database.py      # One-time data backfill script
├── docker-compose.yml        # Local development stack
└── pyproject.toml            # Python project config
```

## Production Deployment

### Option 1: Docker Compose (Self-Hosted)

```bash
# Create .env with production values
echo "POSTGRES_PASSWORD=your-secure-password" >> .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

docker compose -f deploy/docker-compose.prod.yml up -d
docker compose -f deploy/docker-compose.prod.yml exec api python -m scripts.seed_database
```

The API serves on port `8080`, frontend on port `3000`.

### Option 2: Railway

```bash
# Install Railway CLI and login
railway login
railway init
railway add --plugin postgresql

# Set secrets
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set APP_ENV=production

# Deploy
railway up
```

### Option 3: Fly.io

```bash
# Install Fly CLI and login
fly auth login
fly launch
fly postgres create --name fantasy-baseball-db
fly postgres attach fantasy-baseball-db

# Set secrets
fly secrets set ANTHROPIC_API_KEY=sk-ant-...

# Deploy
fly deploy
```

## Automated Scheduling (Production)

When `APP_ENV=production`, the API starts APScheduler with these jobs:

| Schedule | Job | Description |
|----------|-----|-------------|
| Daily 5:00 AM ET | Data Refresh | Fetches latest Statcast data, roster changes, monthly FanGraphs refresh |
| Monday 6:00 AM ET | Model Inference | Runs all ML models, updates projections and value scores |
| Monday 7:00 AM ET | Report Generation | Batch-generates Claude scouting reports for top players |

## Testing

```bash
# Run all backend tests
python -m pytest backend/tests/ -v

# Run with coverage
python -m pytest backend/tests/ --cov=backend --cov-report=term-missing

# Run a specific test module
python -m pytest backend/tests/test_ml/test_trajectory.py -v
```

## Troubleshooting

**Port already in use:** If port 8000 is taken, edit `docker-compose.yml` and change `"8000:8000"` to `"8080:8000"` (or any free port).

**FanGraphs data fetch fails:** FanGraphs periodically blocks API access. The app automatically falls back to Baseball Reference. BBRef provides core stats (AVG, OBP, SLG, HR, WAR) but not advanced Statcast metrics (Barrel%, xwOBA).

**Database seeding fails with UniqueViolationError:** Wipe the database volumes and rebuild:
```bash
docker compose down -v
docker compose build --no-cache api
docker compose up -d
docker compose exec api python -m scripts.seed_database
```

**Changes not reflected after code edits:** Docker may cache old images. Rebuild with `docker compose build --no-cache`.

## License

MIT
