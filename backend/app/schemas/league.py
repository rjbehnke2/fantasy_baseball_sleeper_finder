"""Pydantic schemas for league settings."""

from pydantic import BaseModel


class LeagueSettingsCreate(BaseModel):
    name: str
    scoring_type: str = "h2h_categories"
    league_format: str = "dynasty"
    roster_slots: dict | None = None
    stat_categories: dict | None = None
    auction_budget: float = 260.0
    roster_size: int = 25
    num_teams: int = 12
    keeper_rules: dict | None = None


class LeagueSettingsResponse(BaseModel):
    id: int
    name: str
    scoring_type: str
    league_format: str
    roster_slots: dict | None = None
    stat_categories: dict | None = None
    auction_budget: float
    roster_size: int
    num_teams: int
    keeper_rules: dict | None = None

    model_config = {"from_attributes": True}
