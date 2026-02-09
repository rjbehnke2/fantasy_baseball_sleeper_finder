from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mlbam_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
    fangraphs_id: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    bbref_id: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), index=True)
    position: Mapped[str | None] = mapped_column(String(10))
    team: Mapped[str | None] = mapped_column(String(5))
    birth_date: Mapped[date | None] = mapped_column(Date)
    mlb_debut_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(20), default="active")
    prospect_rank: Mapped[int | None] = mapped_column(Integer)
    mlb_service_time: Mapped[str | None] = mapped_column(String(10))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    batting_seasons: Mapped[list["BattingSeason"]] = relationship(back_populates="player")  # noqa: F821
    pitching_seasons: Mapped[list["PitchingSeason"]] = relationship(back_populates="player")  # noqa: F821
    statcast_aggregates: Mapped[list["StatcastAggregate"]] = relationship(back_populates="player")  # noqa: F821
    projections: Mapped[list["Projection"]] = relationship(back_populates="player")  # noqa: F821
    scouting_reports: Mapped[list["ScoutingReport"]] = relationship(back_populates="player")  # noqa: F821

    @property
    def age(self) -> int | None:
        if self.birth_date is None:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
