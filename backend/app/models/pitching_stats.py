from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class PitchingSeason(Base):
    __tablename__ = "pitching_seasons"
    __table_args__ = (UniqueConstraint("player_id", "season", name="uq_pitching_player_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)

    # Counting stats
    w: Mapped[int | None] = mapped_column(Integer)
    l: Mapped[int | None] = mapped_column(Integer)
    sv: Mapped[int | None] = mapped_column(Integer)
    hld: Mapped[int | None] = mapped_column(Integer)
    ip: Mapped[float | None] = mapped_column(Float)
    gs: Mapped[int | None] = mapped_column(Integer)
    g: Mapped[int | None] = mapped_column(Integer)
    so: Mapped[int | None] = mapped_column(Integer)
    bb: Mapped[int | None] = mapped_column(Integer)
    h: Mapped[int | None] = mapped_column(Integer)
    hr: Mapped[int | None] = mapped_column(Integer)

    # Rate stats
    era: Mapped[float | None] = mapped_column(Float)
    whip: Mapped[float | None] = mapped_column(Float)
    babip: Mapped[float | None] = mapped_column(Float)

    # Advanced / FanGraphs
    fip: Mapped[float | None] = mapped_column(Float)
    xfip: Mapped[float | None] = mapped_column(Float)
    siera: Mapped[float | None] = mapped_column(Float)
    war: Mapped[float | None] = mapped_column(Float)

    # Plate discipline
    k_pct: Mapped[float | None] = mapped_column(Float)
    bb_pct: Mapped[float | None] = mapped_column(Float)
    k_bb_pct: Mapped[float | None] = mapped_column(Float)
    swstr_pct: Mapped[float | None] = mapped_column(Float)
    csw_pct: Mapped[float | None] = mapped_column(Float)

    # Batted ball
    barrel_pct_against: Mapped[float | None] = mapped_column(Float)
    hard_hit_pct_against: Mapped[float | None] = mapped_column(Float)
    gb_pct: Mapped[float | None] = mapped_column(Float)
    fb_pct: Mapped[float | None] = mapped_column(Float)
    hr_fb_pct: Mapped[float | None] = mapped_column(Float)

    # Luck indicators
    lob_pct: Mapped[float | None] = mapped_column(Float)

    # FanGraphs advanced
    stuff_plus: Mapped[float | None] = mapped_column(Float)

    # Expected stats
    xera: Mapped[float | None] = mapped_column(Float)

    # ADP
    adp: Mapped[float | None] = mapped_column(Float)

    player: Mapped["Player"] = relationship(back_populates="pitching_seasons")  # noqa: F821
