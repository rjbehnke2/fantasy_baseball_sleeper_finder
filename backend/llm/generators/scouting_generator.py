"""Scouting report generation orchestrator.

Handles batch generation for top players and on-demand generation for individual
players. Coordinates context assembly, prompt selection, and LLM calls.
"""

import asyncio
import logging
from datetime import datetime

from backend.llm.client import generate_text
from backend.llm.prompts.formatters import format_player_context
from backend.llm.prompts.scouting_report import REPORT_TEMPLATES, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Concurrency limit for on-demand generation
MAX_CONCURRENT_REQUESTS = 10
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


def generate_scouting_report(
    player: dict,
    stats: list[dict],
    scores: dict,
    report_type: str = "full",
    league_averages: dict | None = None,
) -> dict:
    """Generate a single scouting report for a player.

    Args:
        player: Player biographical info dict.
        stats: List of season stat dicts (most recent first).
        scores: Model scores dict.
        report_type: One of "full", "sleeper_spotlight", "bust_warning", "dynasty_outlook".
        league_averages: Optional league averages for comparison.

    Returns:
        Dict with 'content', 'report_type', 'model_scores_snapshot', 'generated_at'.
    """
    template = REPORT_TEMPLATES.get(report_type, REPORT_TEMPLATES["full"])

    # Assemble structured context
    player_context = format_player_context(player, stats, scores, league_averages)

    # Fill template
    user_prompt = template.format(player_context=player_context)

    # Generate via Claude
    content = generate_text(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=2000 if report_type == "full" else 1200,
        temperature=0.7,
    )

    return {
        "content": content,
        "report_type": report_type,
        "model_scores_snapshot": _snapshot_scores(scores),
        "generated_at": datetime.utcnow().isoformat(),
        "llm_model_version": "claude-sonnet-4-5-20250929",
    }


def generate_batch_reports(
    players: list[dict],
    all_stats: dict[int, list[dict]],
    all_scores: dict[int, dict],
    report_type: str = "full",
    league_averages: dict | None = None,
) -> list[dict]:
    """Generate scouting reports for a batch of players.

    Args:
        players: List of player info dicts (must include 'id' or 'player_id').
        all_stats: Dict mapping player_id -> list of season stat dicts.
        all_scores: Dict mapping player_id -> model scores dict.
        report_type: Report type to generate.
        league_averages: Optional league averages.

    Returns:
        List of report dicts, each including 'player_id'.
    """
    reports = []

    for player in players:
        pid = player.get("id") or player.get("player_id")
        if pid is None:
            continue

        stats = all_stats.get(pid, [])
        scores = all_scores.get(pid, {})

        try:
            report = generate_scouting_report(
                player, stats, scores, report_type, league_averages
            )
            report["player_id"] = pid
            reports.append(report)
            logger.info(f"Generated {report_type} report for player {pid}")
        except Exception as e:
            logger.error(f"Failed to generate report for player {pid}: {e}")

    logger.info(f"Batch generation complete: {len(reports)}/{len(players)} reports")
    return reports


def _snapshot_scores(scores: dict) -> dict:
    """Create a snapshot of model scores for cache comparison."""
    keys = [
        "sleeper_score", "bust_score", "regression_direction",
        "consistency_score", "improvement_score", "ai_value_score",
        "auction_value", "dynasty_value", "surplus_value",
    ]
    return {k: scores.get(k) for k in keys if scores.get(k) is not None}
