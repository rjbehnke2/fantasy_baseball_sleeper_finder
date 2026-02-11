"""Scouting report service — retrieves cached reports or generates on demand."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.scouting_report import ScoutingReport

logger = logging.getLogger(__name__)


async def get_report(
    db: AsyncSession,
    player_id: int,
    report_type: str = "full",
) -> ScoutingReport | None:
    """Get the most recent scouting report for a player.

    Args:
        db: Database session.
        player_id: Player ID.
        report_type: Report type to retrieve.

    Returns:
        ScoutingReport or None if not cached.
    """
    stmt = (
        select(ScoutingReport)
        .where(
            ScoutingReport.player_id == player_id,
            ScoutingReport.report_type == report_type,
        )
        .order_by(ScoutingReport.generated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def save_report(
    db: AsyncSession,
    player_id: int,
    report_data: dict,
) -> ScoutingReport:
    """Save a generated scouting report to the database.

    Args:
        db: Database session.
        player_id: Player ID.
        report_data: Dict from scouting_generator.generate_scouting_report().

    Returns:
        Saved ScoutingReport instance.
    """
    report = ScoutingReport(
        player_id=player_id,
        report_type=report_data["report_type"],
        content=report_data["content"],
        model_scores_snapshot=report_data.get("model_scores_snapshot"),
        llm_model_version=report_data.get("llm_model_version"),
        generated_at=datetime.utcnow(),
        stale=False,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    logger.info(f"Saved {report.report_type} report for player {player_id}")
    return report


async def mark_stale(
    db: AsyncSession,
    player_id: int,
) -> int:
    """Mark all reports for a player as stale.

    Returns:
        Number of reports marked stale.
    """
    stmt = (
        select(ScoutingReport)
        .where(
            ScoutingReport.player_id == player_id,
            ScoutingReport.stale == False,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()

    count = 0
    for report in reports:
        report.stale = True
        count += 1

    if count > 0:
        await db.commit()
    return count


async def get_all_reports_for_player(
    db: AsyncSession,
    player_id: int,
) -> list[ScoutingReport]:
    """Get all report types for a player."""
    stmt = (
        select(ScoutingReport)
        .where(ScoutingReport.player_id == player_id)
        .order_by(ScoutingReport.generated_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
