"""Scouting report cache manager.

Handles cache invalidation logic — determines when a report is stale and
should be regenerated. Reports become stale when model scores shift significantly,
a player changes teams, or goes on/off the IL.
"""

import logging

logger = logging.getLogger(__name__)

# Thresholds for staleness detection
SCORE_CHANGE_THRESHOLD = 10.0  # Points of change before marking stale
DOLLAR_CHANGE_THRESHOLD = 5.0  # Dollar value change threshold


def is_report_stale(
    cached_snapshot: dict | None,
    current_scores: dict,
) -> bool:
    """Determine if a cached report should be marked as stale.

    Args:
        cached_snapshot: The model_scores_snapshot from when the report was generated.
        current_scores: Current model scores for the player.

    Returns:
        True if the report should be regenerated.
    """
    if cached_snapshot is None:
        return True

    # Check score-based staleness
    score_keys = [
        "sleeper_score", "bust_score", "consistency_score",
        "improvement_score", "ai_value_score",
    ]
    for key in score_keys:
        old_val = cached_snapshot.get(key)
        new_val = current_scores.get(key)
        if old_val is not None and new_val is not None:
            if abs(new_val - old_val) > SCORE_CHANGE_THRESHOLD:
                logger.debug(f"Report stale: {key} changed {old_val:.1f} -> {new_val:.1f}")
                return True

    # Check dollar value staleness
    dollar_keys = ["auction_value", "dynasty_value", "surplus_value"]
    for key in dollar_keys:
        old_val = cached_snapshot.get(key)
        new_val = current_scores.get(key)
        if old_val is not None and new_val is not None:
            if abs(new_val - old_val) > DOLLAR_CHANGE_THRESHOLD:
                logger.debug(f"Report stale: {key} changed {old_val:.1f} -> {new_val:.1f}")
                return True

    # Check regression direction flip
    old_reg = cached_snapshot.get("regression_direction", 0)
    new_reg = current_scores.get("regression_direction", 0)
    if old_reg * new_reg < 0 and abs(new_reg - old_reg) > 0.02:
        logger.debug("Report stale: regression direction flipped")
        return True

    return False


def select_batch_players(
    all_scores: dict[int, dict],
    top_n_value: int = 250,
    top_n_sleepers: int = 50,
    top_n_busts: int = 50,
) -> dict[int, list[str]]:
    """Select players for batch report generation and their report types.

    Args:
        all_scores: Dict mapping player_id -> scores dict.
        top_n_value: Number of top players by AI value to get full reports.
        top_n_sleepers: Number of top sleepers for spotlight reports.
        top_n_busts: Number of top busts for warning reports.

    Returns:
        Dict mapping player_id -> list of report types to generate.
    """
    player_reports: dict[int, list[str]] = {}

    scores_list = [(pid, s) for pid, s in all_scores.items()]

    # Top players by AI value score get full reports
    by_value = sorted(scores_list, key=lambda x: x[1].get("ai_value_score", 0), reverse=True)
    for pid, _ in by_value[:top_n_value]:
        player_reports.setdefault(pid, []).append("full")

    # Top sleepers get spotlight reports
    by_sleeper = sorted(scores_list, key=lambda x: x[1].get("sleeper_score", 0), reverse=True)
    for pid, _ in by_sleeper[:top_n_sleepers]:
        player_reports.setdefault(pid, []).append("sleeper_spotlight")

    # Top busts get warning reports
    by_bust = sorted(scores_list, key=lambda x: x[1].get("bust_score", 0), reverse=True)
    for pid, _ in by_bust[:top_n_busts]:
        player_reports.setdefault(pid, []).append("bust_warning")

    # Young players (under 26) with high value get dynasty outlook
    young_players = [
        (pid, s) for pid, s in scores_list
        if s.get("age", 30) < 26
    ]
    by_young_value = sorted(young_players, key=lambda x: x[1].get("ai_value_score", 0), reverse=True)
    for pid, _ in by_young_value[:50]:
        player_reports.setdefault(pid, []).append("dynasty_outlook")

    total_reports = sum(len(v) for v in player_reports.values())
    logger.info(
        f"Selected {len(player_reports)} players for batch generation "
        f"({total_reports} total reports)"
    )
    return player_reports
