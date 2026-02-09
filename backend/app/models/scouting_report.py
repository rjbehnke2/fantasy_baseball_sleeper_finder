from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ScoutingReport(Base):
    __tablename__ = "scouting_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    report_type: Mapped[str] = mapped_column(
        String(30), index=True
    )  # full, sleeper_spotlight, bust_warning, dynasty_outlook
    content: Mapped[str] = mapped_column(Text)
    model_scores_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    llm_model_version: Mapped[str | None] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    stale: Mapped[bool] = mapped_column(Boolean, default=False)

    player: Mapped["Player"] = relationship(back_populates="scouting_reports")  # noqa: F821
