from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class StatcastAggregate(Base):
    __tablename__ = "statcast_aggregates"
    __table_args__ = (UniqueConstraint("player_id", "season", name="uq_statcast_player_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)

    # Batted ball quality
    avg_exit_velocity: Mapped[float | None] = mapped_column(Float)
    max_exit_velocity: Mapped[float | None] = mapped_column(Float)
    avg_launch_angle: Mapped[float | None] = mapped_column(Float)
    barrel_pct: Mapped[float | None] = mapped_column(Float)
    sweet_spot_pct: Mapped[float | None] = mapped_column(Float)
    hard_hit_pct: Mapped[float | None] = mapped_column(Float)

    # Pitch quality (pitchers)
    avg_spin_rate: Mapped[float | None] = mapped_column(Float)
    avg_fastball_velo: Mapped[float | None] = mapped_column(Float)

    # Expected stats
    xba: Mapped[float | None] = mapped_column(Float)
    xslg: Mapped[float | None] = mapped_column(Float)
    xwoba: Mapped[float | None] = mapped_column(Float)
    xera: Mapped[float | None] = mapped_column(Float)

    # Player type (batter or pitcher context)
    player_type: Mapped[str | None] = mapped_column(default="batter")

    player: Mapped["Player"] = relationship(back_populates="statcast_aggregates")  # noqa: F821
