"""Pydantic schemas for player-related API requests and responses."""

from datetime import date, datetime

from pydantic import BaseModel


class PlayerSummary(BaseModel):
    id: int
    full_name: str
    team: str | None = None
    position: str | None = None
    age: int | None = None

    # Model scores (from latest projection)
    ai_value_score: float | None = None
    sleeper_score: float | None = None
    bust_score: float | None = None
    consistency_score: float | None = None
    improvement_score: float | None = None
    auction_value: float | None = None
    surplus_value: float | None = None
    dynasty_value: float | None = None

    # Key stats (most recent season)
    key_stats: dict | None = None

    model_config = {"from_attributes": True}


class BattingSeasonSchema(BaseModel):
    season: int
    pa: int | None = None
    avg: float | None = None
    obp: float | None = None
    slg: float | None = None
    hr: int | None = None
    rbi: int | None = None
    r: int | None = None
    sb: int | None = None
    woba: float | None = None
    xwoba: float | None = None
    wrc_plus: int | None = None
    k_pct: float | None = None
    bb_pct: float | None = None
    barrel_pct: float | None = None
    hard_hit_pct: float | None = None
    avg_exit_velocity: float | None = None
    iso: float | None = None
    babip: float | None = None
    war: float | None = None

    model_config = {"from_attributes": True}


class PitchingSeasonSchema(BaseModel):
    season: int
    ip: float | None = None
    era: float | None = None
    whip: float | None = None
    fip: float | None = None
    siera: float | None = None
    so: int | None = None
    w: int | None = None
    sv: int | None = None
    k_pct: float | None = None
    bb_pct: float | None = None
    k_bb_pct: float | None = None
    swstr_pct: float | None = None
    csw_pct: float | None = None
    barrel_pct_against: float | None = None
    hard_hit_pct_against: float | None = None
    hr_fb_pct: float | None = None
    babip: float | None = None
    lob_pct: float | None = None
    war: float | None = None

    model_config = {"from_attributes": True}


class ProjectionSchema(BaseModel):
    run_date: datetime | None = None
    model_version: str | None = None
    sleeper_score: float | None = None
    bust_score: float | None = None
    regression_direction: float | None = None
    consistency_score: float | None = None
    improvement_score: float | None = None
    ai_value_score: float | None = None
    auction_value: float | None = None
    dynasty_value: float | None = None
    surplus_value: float | None = None
    marcel_projections: dict | None = None
    shap_explanations: dict | None = None
    stat_consistency_breakdown: dict | None = None
    stat_improvement_breakdown: dict | None = None

    model_config = {"from_attributes": True}


class PlayerDetail(BaseModel):
    id: int
    full_name: str
    team: str | None = None
    position: str | None = None
    age: int | None = None
    birth_date: date | None = None
    mlb_debut_date: date | None = None
    status: str | None = None
    prospect_rank: int | None = None

    batting_seasons: list[BattingSeasonSchema] = []
    pitching_seasons: list[PitchingSeasonSchema] = []
    projection: ProjectionSchema | None = None

    model_config = {"from_attributes": True}


class PlayerListResponse(BaseModel):
    players: list[PlayerSummary]
    total: int
    page: int
    per_page: int
