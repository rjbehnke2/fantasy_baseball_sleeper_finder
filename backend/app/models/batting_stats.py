from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class BattingSeason(Base):
    __tablename__ = "batting_seasons"
    __table_args__ = (UniqueConstraint("player_id", "season", name="uq_batting_player_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)

    # Counting stats
    pa: Mapped[int | None] = mapped_column(Integer)
    ab: Mapped[int | None] = mapped_column(Integer)
    h: Mapped[int | None] = mapped_column(Integer)
    hr: Mapped[int | None] = mapped_column(Integer)
    rbi: Mapped[int | None] = mapped_column(Integer)
    r: Mapped[int | None] = mapped_column(Integer)
    sb: Mapped[int | None] = mapped_column(Integer)
    cs: Mapped[int | None] = mapped_column(Integer)

    # Rate stats
    avg: Mapped[float | None] = mapped_column(Float)
    obp: Mapped[float | None] = mapped_column(Float)
    slg: Mapped[float | None] = mapped_column(Float)
    ops: Mapped[float | None] = mapped_column(Float)
    iso: Mapped[float | None] = mapped_column(Float)
    babip: Mapped[float | None] = mapped_column(Float)

    # Advanced / FanGraphs
    woba: Mapped[float | None] = mapped_column(Float)
    xwoba: Mapped[float | None] = mapped_column(Float)
    wrc_plus: Mapped[int | None] = mapped_column(Integer)
    war: Mapped[float | None] = mapped_column(Float)

    # Plate discipline
    k_pct: Mapped[float | None] = mapped_column(Float)
    bb_pct: Mapped[float | None] = mapped_column(Float)

    # Batted ball / Statcast
    barrel_pct: Mapped[float | None] = mapped_column(Float)
    hard_hit_pct: Mapped[float | None] = mapped_column(Float)
    avg_exit_velocity: Mapped[float | None] = mapped_column(Float)
    avg_launch_angle: Mapped[float | None] = mapped_column(Float)
    sprint_speed: Mapped[float | None] = mapped_column(Float)
    gb_pct: Mapped[float | None] = mapped_column(Float)
    fb_pct: Mapped[float | None] = mapped_column(Float)
    ld_pct: Mapped[float | None] = mapped_column(Float)

    # Expected stats
    xba: Mapped[float | None] = mapped_column(Float)
    xslg: Mapped[float | None] = mapped_column(Float)

    # ADP
    adp: Mapped[float | None] = mapped_column(Float)

    player: Mapped["Player"] = relationship(back_populates="batting_seasons")  # noqa: F821
