# Fantasy Baseball Sleeper Finder — Implementation Plan

## Vision

A web application that uses ML models trained on baseball statistics and advanced analytics to generate AI-derived player evaluations for fantasy baseball. The core differentiator is AI-powered insights: sleeper identification, bust detection, regression prediction, consistency scoring, and composite value rankings — all with explainable reasoning.

---

## 1. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Backend** | Python 3.11+ / FastAPI / Uvicorn | ML models are Python-native; FastAPI gives auto-docs, async, Pydantic validation |
| **Frontend** | Next.js (App Router) + shadcn/ui + Tailwind CSS + Recharts | Server-side rendering, production-quality components, built-in charting |
| **ML** | scikit-learn + XGBoost + LightGBM + SHAP | XGBoost/LightGBM excel on tabular baseball data; SHAP provides explainability |
| **Database** | PostgreSQL (SQLAlchemy 2.0 + Alembic) | Handles millions of Statcast rows, JSONB for flexible schemas, concurrent access |
| **Data** | pybaseball + MLB-StatsAPI | pybaseball aggregates FanGraphs/Savant/Lahman; MLB-StatsAPI for rosters/injuries |
| **Scheduling** | APScheduler | Nightly data refresh without the complexity of Celery |
| **Package Mgmt** | uv | Fast, reliable Python dependency management |
| **Infra** | Docker Compose (dev), GitHub Actions (CI/CD) | Single-command local stack, automated deploys |

---

## 2. Project Structure

```
fantasy_baseball_sleeper_finder/
├── README.md
├── PLAN.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── alembic/                      # Database migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory, lifespan events
│   │   ├── config.py                 # Pydantic BaseSettings
│   │   ├── dependencies.py
│   │   │
│   │   ├── api/v1/
│   │   │   ├── router.py             # Aggregates all v1 routers
│   │   │   ├── players.py            # Player lookup, search, detail
│   │   │   ├── rankings.py           # AI rankings endpoints
│   │   │   ├── comparisons.py        # Player comparison endpoints
│   │   │   ├── insights.py           # Sleepers, busts, regression
│   │   │   └── league.py             # League settings customization
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── player.py
│   │   │   ├── batting_stats.py
│   │   │   ├── pitching_stats.py
│   │   │   ├── statcast.py
│   │   │   ├── projections.py
│   │   │   └── league_settings.py
│   │   │
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── player.py
│   │   │   ├── rankings.py
│   │   │   ├── insights.py
│   │   │   └── league.py
│   │   │
│   │   ├── services/                 # Business logic layer
│   │   │   ├── player_service.py
│   │   │   ├── ranking_service.py
│   │   │   └── insight_service.py
│   │   │
│   │   └── db/
│   │       ├── session.py            # Async SQLAlchemy session factory
│   │       └── base.py               # Declarative base
│   │
│   ├── data_pipeline/
│   │   ├── fetchers/
│   │   │   ├── fangraphs_fetcher.py  # pybaseball batting_stats/pitching_stats
│   │   │   ├── statcast_fetcher.py   # pybaseball statcast functions
│   │   │   ├── roster_fetcher.py     # MLB-StatsAPI roster/injury data
│   │   │   └── player_id_mapper.py   # Cross-reference player IDs
│   │   │
│   │   ├── transformers/
│   │   │   ├── cleaning.py           # Data cleaning, null handling
│   │   │   ├── feature_engineering.py # Derived features (differentials, trends)
│   │   │   └── aggregations.py       # Pitch-level to season-level rollups
│   │   │
│   │   ├── loaders/
│   │   │   └── db_loader.py          # Write cleaned data to PostgreSQL
│   │   │
│   │   ├── orchestrator.py           # Pipeline scheduling logic
│   │   └── backfill.py               # One-time historical data load
│   │
│   ├── ml/
│   │   ├── features/
│   │   │   ├── feature_store.py      # Central feature definitions
│   │   │   ├── batter_features.py
│   │   │   └── pitcher_features.py
│   │   │
│   │   ├── models/
│   │   │   ├── marcel_baseline.py    # Marcel projection (baseline to beat)
│   │   │   ├── sleeper_model.py      # Sleeper detection
│   │   │   ├── bust_model.py         # Bust detection
│   │   │   ├── regression_model.py   # Regression direction prediction
│   │   │   ├── consistency_model.py  # Consistency/volatility scorer
│   │   │   ├── value_model.py        # Composite AI Value Score
│   │   │   └── trajectory_model.py   # TFT career trajectory (Phase 3)
│   │   │
│   │   ├── training/
│   │   │   ├── train_pipeline.py     # End-to-end training orchestration
│   │   │   ├── evaluation.py         # Backtesting, cross-validation
│   │   │   └── hyperparameter.py     # Optuna hyperparameter search
│   │   │
│   │   ├── inference/
│   │   │   ├── predictor.py          # Load models, generate predictions
│   │   │   └── explainer.py          # SHAP explanations
│   │   │
│   │   └── artifacts/                # Serialized models (.joblib, .xgb)
│   │       └── .gitkeep
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_api/
│       ├── test_pipeline/
│       └── test_ml/
│
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── app/
│       │   ├── layout.tsx            # Root layout with sidebar nav
│       │   ├── page.tsx              # Dashboard
│       │   ├── players/
│       │   │   ├── page.tsx          # Player rankings table
│       │   │   └── [playerId]/
│       │   │       └── page.tsx      # Player detail
│       │   ├── sleepers/page.tsx     # Sleeper picks
│       │   ├── busts/page.tsx        # Bust alerts
│       │   ├── compare/page.tsx      # Side-by-side comparison
│       │   └── settings/page.tsx     # League settings
│       │
│       ├── components/
│       │   ├── ui/                   # shadcn/ui components
│       │   ├── players/
│       │   │   ├── player-card.tsx
│       │   │   ├── player-table.tsx
│       │   │   └── player-radar.tsx
│       │   ├── insights/
│       │   │   ├── sleeper-card.tsx
│       │   │   ├── bust-alert.tsx
│       │   │   └── regression-indicator.tsx
│       │   └── charts/
│       │       ├── stat-trend.tsx
│       │       ├── value-gauge.tsx
│       │       └── consistency-heatmap.tsx
│       │
│       ├── lib/
│       │   ├── api.ts                # API client
│       │   ├── types.ts
│       │   └── utils.ts
│       │
│       └── hooks/
│           ├── use-players.ts
│           ├── use-rankings.ts
│           └── use-league-settings.ts
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_prototyping.ipynb
│   └── 04_model_evaluation.ipynb
│
└── scripts/
    ├── seed_database.py
    ├── train_models.py
    └── generate_projections.py
```

---

## 3. Data Pipeline

### 3.1 Data Sources

| Source | Library | Data Type | Historical Depth |
|---|---|---|---|
| FanGraphs | `pybaseball.batting_stats()` / `pitching_stats()` | Season-level advanced stats (wOBA, xwOBA, wRC+, SIERA, FIP, Barrel%, etc.) | 2015-present |
| Baseball Savant | `pybaseball.statcast()` | Pitch-level Statcast (EV, LA, spin rate, etc.) | 2019-present |
| Lahman Database | `pybaseball` Lahman module | Historical season stats | 1871-present |
| MLB Stats API | `MLB-StatsAPI` | Rosters, injuries, schedules | Current |

### 3.2 Fetching Strategy

**Historical Backfill** (one-time, via `scripts/seed_database.py`):
- FanGraphs batting/pitching stats: 2015-present (single call per stat type)
- Statcast aggregates: 2019-present, fetched in 7-day chunks to stay under Baseball Savant's 30K row limit
- Always enable `pybaseball.cache.enable()` before fetching

**Nightly Incremental Updates** (via APScheduler, 5:00 AM ET):
- Yesterday's Statcast data
- Re-aggregate current-season per-player Statcast summaries
- Roster changes and injury updates via MLB-StatsAPI
- Monthly full FanGraphs stats refresh

### 3.3 Player ID Mapping

Critical integration challenge. pybaseball uses MLBAM IDs, FanGraphs has its own IDs, Baseball Reference uses another. The `player_id_mapper.py` module uses `pybaseball.playerid_reverse_lookup()` to build a canonical player table with all three ID systems for reliable cross-source joins.

### 3.4 Database Schema

**`players`** — canonical player record
- `id` (PK), `mlbam_id`, `fangraphs_id`, `bbref_id`, `full_name`, `position`, `team`, `birth_date`, `mlb_debut_date`, `status`

**`batting_seasons`** — one row per player per season
- `player_id` (FK), `season`, `pa`, `ab`, `h`, `hr`, `rbi`, `sb`, `avg`, `obp`, `slg`, `woba`, `xwoba`, `wrc_plus`, `barrel_pct`, `hard_hit_pct`, `sprint_speed`, `babip`, `k_pct`, `bb_pct`, `war`, `adp`

**`pitching_seasons`** — one row per player per season
- `player_id` (FK), `season`, `ip`, `era`, `whip`, `fip`, `xfip`, `siera`, `k_pct`, `bb_pct`, `k_bb_pct`, `csw_pct`, `swstr_pct`, `barrel_pct_against`, `hard_hit_pct_against`, `stuff_plus`, `war`, `babip`, `lob_pct`, `hr_fb_pct`, `adp`

**`statcast_aggregates`** — per-player-per-season Statcast summaries
- `player_id` (FK), `season`, `avg_exit_velocity`, `max_exit_velocity`, `avg_launch_angle`, `barrel_pct`, `sweet_spot_pct`, `avg_spin_rate`, `xba`, `xslg`, `xwoba`, `xera`

**`monthly_splits`** — per-player-per-month (for consistency scoring)
- `player_id` (FK), `season`, `month`, key rate stats

**`projections`** — model outputs
- `player_id` (FK), `run_date`, `model_version`, `sleeper_score`, `bust_score`, `regression_direction`, `regression_magnitude`, `consistency_score`, `ai_value_score`, `confidence`, `shap_explanations` (JSONB)

**`league_settings`** — user-customizable league configs
- `id`, `name`, `scoring_type`, `roster_slots` (JSONB), `stat_categories` (JSONB)

### 3.5 Feature Engineering

This is the intellectual core of the pipeline — the quality of features determines the quality of all ML models.

**Differential Features (actual vs. expected):**
- `woba_minus_xwoba`: positive = overperforming (bust signal), negative = underperforming (sleeper signal)
- `ba_minus_xba`, `era_minus_xera`: same principle
- `babip_minus_league_avg`: high delta suggests regression

**Trend Features (year-over-year):**
- `barrel_pct_yoy_delta`, `k_pct_yoy_delta`, `bb_pct_yoy_delta`, `csw_pct_yoy_delta`
- 2-year and 3-year trend slopes via linear regression on seasonal values

**Age Curve Features:**
- `age`, `years_from_peak` (peak ~27 hitters, ~26 pitchers)
- `age_bucket`: pre-peak / peak / early-decline / late-decline
- `post_hype_flag`: age 26-29, former top prospect, MLB underperformer

**Consistency Features (from monthly splits):**
- `woba_cv`: coefficient of variation of monthly wOBA
- `woba_iqr`: interquartile range
- `bad_month_ratio`: fraction of months below league average
- `hot_streak_magnitude`: max monthly wOBA minus season wOBA

**Context Features:**
- `team_park_factor`, `lineup_position_avg`, `playing_time_trend`

**Marcel Baseline Features:**
- Weighted 3-year average (5/4/3 weighting)
- Regression to mean (1200 PA batters / 134 outs pitchers of league-average blended in)
- Age adjustment: +/- 0.006 per year from peak

---

## 4. ML Models (Core Differentiator)

### 4.0 Marcel Baseline — The Bar to Clear

Every ML model must demonstrably outperform the Marcel system. Marcel is implemented first and its projections also serve as input features for downstream models.

**Formula:** `projected_stat = (5 * year_N + 4 * year_N-1 + 3 * year_N-2) / 12`, regressed toward league mean proportional to playing time, age-adjusted.

### 4.1 Sleeper Finder Model

**Objective:** Identify players whose underlying quality (Statcast, expected stats) significantly exceeds their surface stats or draft cost.

**Training Target:** Binary classification. A "sleeper" = player with ADP outside top 150 who finished in the top 100 by fantasy value.

**Key Features (expected importance order):**
1. `xwoba_minus_woba` (negative = quality exceeds results)
2. `barrel_pct` + `barrel_pct_yoy_delta`
3. `hard_hit_pct` + `hard_hit_pct_yoy_delta`
4. `k_pct_yoy_delta` (declining K rate)
5. `csw_pct_yoy_delta` (pitchers: improving stuff)
6. `age_bucket` (pre-peak more likely to break out)
7. `playing_time_trend` (increasing = team trust)
8. `post_hype_flag`
9. Marcel delta (projected vs. actual)
10. `adp` (cheap + good underlying = sleeper)

**Architecture:** LightGBM + XGBoost ensemble with class-weight balancing (sleepers are ~5-10% of pool). Calibrated probabilities via `CalibratedClassifierCV`. Hyperparameter tuning with Optuna, 5-fold time-series CV.

**Output:** `sleeper_score` (0-100) + SHAP top-3 feature explanations per player.

### 4.2 Bust Detector Model

**Objective:** Flag players whose surface stats are propped up by unsustainable luck.

**Training Target:** Binary classification. A "bust" = player with ADP in top 100 who finished outside top 200 or 60+ days on IL.

**Key Features:**
1. `woba_minus_xwoba` (positive = stats exceed quality)
2. `babip_minus_league_avg` (high BABIP regresses)
3. `hr_fb_pct` vs. league average (unsustainable HR/FB)
4. `lob_pct` for pitchers (high LOB% regresses down)
5. `age_bucket` (late-decline = higher bust risk)
6. `injury_history_score` (weighted IL stints)
7. `era_minus_fip` for pitchers
8. `consistency_score` (volatile = higher bust risk)
9. `playing_time_trend` (declining = team losing faith)

**Architecture:** Same LightGBM + XGBoost ensemble. Same tuning framework.

**Output:** `bust_score` (0-100) + SHAP top-3 explanations.

### 4.3 Regression Direction Model

**Objective:** Predict whether a player will improve or decline, and by how much.

**Training Target:** Regression task. Target = `next_season_woba - current_season_woba` (batters) or `current_season_fip - next_season_fip` (pitchers, inverted for unified "improvement" metric).

**Key Features:** All differential features + Marcel deltas + YoY trends + age curve.

**Architecture:** XGBoost Regressor + LightGBM Regressor ensemble. Evaluated with MAE and directional accuracy.

**Output:** `regression_direction` (signed float), `regression_confidence` (from quantile regression prediction intervals).

### 4.4 Consistency Score

**Not an ML model** — a statistical calculation from monthly splits data.

**Formula:**
```
consistency_score = 100 - normalize(
    0.4 * coefficient_of_variation +
    0.3 * iqr_scaled +
    0.2 * bad_month_ratio +
    0.1 * max_drawdown_scaled
)
```

Multi-year smoothing: current season 60%, prior 30%, two seasons ago 10%.

**Output:** `consistency_score` (0-100) + monthly performance array for sparkline visualization.

### 4.5 AI Value Score (Composite)

**Objective:** Single 0-100 number combining all model outputs with contextual factors.

**Formula:**
```
ai_value_score = (
    w1 * projected_fantasy_value +      # Marcel + regression adjustment
    w2 * sleeper_upside +               # sleeper_score * (1 - current_value_pct)
    w3 * (100 - bust_risk) +            # Inverse bust score
    w4 * consistency_score +
    w5 * age_curve_factor +             # Bonus pre-peak, penalty late-decline
    w6 * opportunity_score              # Playing time / role security
)
```

Weights `w1-w6` calibrated via linear regression on historical seasons.

**League Customization:** `projected_fantasy_value` changes based on user's league settings (categories vs. points, roster composition). Rankings adjust accordingly.

**Output:** `ai_value_score` (0-100) + component breakdown for the UI explainer.

---

## 5. API Design

### Base URL: `/api/v1`

### Players
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/players` | Paginated search/list with filters (position, team, sort_by any score) |
| `GET` | `/players/{player_id}` | Full detail: bio, 3-year stats, all model scores, SHAP explanations, monthly splits |
| `GET` | `/players/{player_id}/stats` | Historical stats by season and stat type |

### Rankings
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/rankings` | AI-powered rankings with value breakdown per player |
| `GET` | `/rankings/sleepers` | Top sleeper candidates with reasons |
| `GET` | `/rankings/busts` | Top bust risks with reasons |
| `GET` | `/rankings/regression` | Regression candidates by direction |

### Comparisons
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/compare?player_ids=1,2,3` | Side-by-side comparison with percentile-coded stats |

### League Settings
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/league-settings` | Create league config (scoring type, categories, roster) |
| `GET` | `/league-settings/{id}` | Retrieve league config |

### Insights & Metadata
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/insights/daily` | Daily AI digest: risers, fallers, injury impacts |
| `GET` | `/model/info` | Model version, last-trained date, backtest accuracy |

---

## 6. Frontend Design

### Pages

**Dashboard (`/`)** — Landing page with:
- "Today's Top Sleepers" (top 5 with brief explanations)
- "Bust Alerts" (top 5 warnings)
- "Biggest Movers" (score changes since last update)
- Quick-search bar, model freshness indicator

**Player Rankings (`/players`)** — Full-width sortable/filterable table (Tanstack Table):
- Columns: Rank, Name, Team, Pos, Age, AI Value Score, Sleeper Score, Bust Score, Consistency, ADP, key stats
- Sidebar filters: position, team, age range, min PA/IP
- Toggle: All / Batters / Pitchers
- League settings toggle for personalized rankings

**Player Detail (`/players/[playerId]`)** — Most information-dense page:
- AI Assessment Card: value gauge (0-100, color gradient), sleeper/bust/consistency badges
- "Why This Score" section: SHAP-derived plain-English explanations
- Stat Trends: 3-year line charts (wOBA, xwOBA, Barrel%, K%)
- Monthly Splits Heatmap
- Radar Chart: percentile ranks across key metrics (Power, Contact, Speed, Discipline)
- "Compare with..." shortcut

**Sleepers (`/sleepers`)** — Card layout:
- Sleeper score (large), top 3 SHAP reasons as bullets
- Mini sparkline: xwOBA vs. wOBA over 3 seasons
- Sortable, position-filterable

**Busts (`/busts`)** — Same card layout, warning color scheme (amber/red)

**Compare (`/compare`)** — Select 2-5 players:
- Side-by-side stat table, cells color-coded by percentile
- Overlaid trend line charts
- Radar chart overlay

**Settings (`/settings`)** — League configuration form:
- Scoring type (roto/H2H categories/H2H points)
- Stat categories (checkboxes)
- Roster slots, points-per-stat values

### Design Principles
1. **Lead with "why"**: Every score has an expandable explanation
2. **Visual encoding**: Color-coded badges, sparklines, percentile bars for scanning
3. **Show confidence**: Display confidence indicators when model is less certain
4. **Make it personal**: Prominently show "Customized for your league" when settings applied

---

## 7. Development Phases

### Phase 1: Data Foundation + Marcel Baseline + Minimal API

**Goal:** A working API that returns Marcel projections and basic stats for all MLB players.

- Set up PostgreSQL via Docker Compose
- Implement data fetchers: FanGraphs stats (2015-present), Statcast aggregates (2019-present), player ID mapping
- Build data cleaning and database loading pipeline
- Run historical backfill via `scripts/seed_database.py`
- Implement Marcel baseline projections
- Implement feature engineering pipeline
- Build FastAPI with `/players` and `/rankings` endpoints (Marcel-based)
- Scaffold Next.js frontend: sidebar layout, player table, player detail (stats only)
- Connect frontend to API, verify end-to-end flow
- Write tests for fetchers, cleaning, API

**Deliverable:** Browse all MLB players, see 3-year stat history, see Marcel projections. No ML yet, but data infrastructure is solid.

### Phase 2: Core ML Models + AI-Driven UI

**Goal:** All five model outputs trained, evaluated, and served. Frontend shows AI scores with explanations.

- Train sleeper model (LightGBM + XGBoost ensemble, 2016-2023 data, validate on 2024)
- Train bust model (same ensemble approach)
- Train regression model (XGBoost + LightGBM regressors)
- Implement backtesting framework with walk-forward validation
- Implement Optuna hyperparameter tuning
- Implement consistency scoring from monthly splits
- Implement composite AI Value Score with weight calibration
- Integrate SHAP for plain-English explanations
- Build unified inference pipeline
- Add all rankings/insights/comparison API endpoints
- Add league settings CRUD endpoints
- Build full frontend: AI assessment cards, sleepers page, busts page, comparison page, settings page
- Add radar charts, stat trend charts, value gauges

**Deliverable:** Full AI value proposition visible. Users find sleepers, avoid busts, understand model reasoning. Rankings adjust to custom league settings.

### Phase 3: Polish, Advanced Models, Deployment

**Goal:** Career trajectory model, daily updates, production deployment.

- Implement Temporal Fusion Transformer for multi-season career trajectory prediction
- Integrate trajectory predictions into AI Value Score
- Add trajectory visualization to player detail page
- Implement APScheduler for nightly data refresh + weekly re-inference
- Add roster/injury monitoring with push-to-projections updates
- Implement API response caching
- Dockerize full stack (multi-stage builds)
- Set up CI/CD with GitHub Actions
- Deploy to cloud provider
- Add daily insights digest
- Performance optimization (DB indexes, frontend bundle)
- Beta testing

**Deliverable:** Production-deployed application with nightly updates, all model outputs, career trajectory projections, polished UI.
