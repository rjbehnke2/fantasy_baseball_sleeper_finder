from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class LeagueSettings(Base):
    __tablename__ = "league_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    scoring_type: Mapped[str] = mapped_column(
        String(20), default="h2h_categories"
    )  # roto, h2h_categories, h2h_points
    league_format: Mapped[str] = mapped_column(
        String(20), default="dynasty"
    )  # redraft, keeper, dynasty
    roster_slots: Mapped[dict | None] = mapped_column(JSONB)
    stat_categories: Mapped[dict | None] = mapped_column(JSONB)
    auction_budget: Mapped[float] = mapped_column(Float, default=260.0)
    roster_size: Mapped[int] = mapped_column(Integer, default=25)
    keeper_rules: Mapped[dict | None] = mapped_column(JSONB)
    num_teams: Mapped[int] = mapped_column(Integer, default=12)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
