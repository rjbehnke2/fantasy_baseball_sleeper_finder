from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Projection(Base):
    __tablename__ = "projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    run_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    model_version: Mapped[str] = mapped_column(String(50))

    # ML model scores
    sleeper_score: Mapped[float | None] = mapped_column(Float)
    bust_score: Mapped[float | None] = mapped_column(Float)
    regression_direction: Mapped[float | None] = mapped_column(Float)
    regression_magnitude: Mapped[float | None] = mapped_column(Float)
    consistency_score: Mapped[float | None] = mapped_column(Float)
    improvement_score: Mapped[float | None] = mapped_column(Float)
    ai_value_score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)

    # Explanations
    shap_explanations: Mapped[dict | None] = mapped_column(JSONB)
    stat_consistency_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    stat_improvement_breakdown: Mapped[dict | None] = mapped_column(JSONB)

    # Auction / Dynasty values
    auction_value: Mapped[float | None] = mapped_column(Float)
    dynasty_value: Mapped[float | None] = mapped_column(Float)
    surplus_value: Mapped[float | None] = mapped_column(Float)

    # Marcel baseline projections (stored for reference)
    marcel_projections: Mapped[dict | None] = mapped_column(JSONB)

    player: Mapped["Player"] = relationship(back_populates="projections")  # noqa: F821
