"""Pydantic schemas for rankings-related API responses."""

from pydantic import BaseModel

from backend.app.schemas.player import PlayerSummary


class RankedPlayer(BaseModel):
    rank: int
    player: PlayerSummary
    value_breakdown: dict | None = None


class RankingsResponse(BaseModel):
    rankings: list[RankedPlayer]
    total: int
    ranking_type: str  # overall, dynasty, auction, sleepers, busts


class AuctionValueEntry(BaseModel):
    rank: int
    player: PlayerSummary
    auction_value: float
    surplus_value: float | None = None
    dynasty_value: float | None = None
    keep_cut_horizon: int | None = None


class AuctionValuesResponse(BaseModel):
    values: list[AuctionValueEntry]
    total: int
