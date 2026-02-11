"""Stat context formatters — converts structured player data into prompt-ready documents.

Assembles biographical info, stats, model scores, trends, and auction context into
a structured text document that the LLM can use to generate grounded scouting reports.
"""

from typing import Any


def format_player_context(
    player: dict,
    stats: list[dict],
    scores: dict,
    league_averages: dict | None = None,
) -> str:
    """Format a complete player context document for LLM prompt injection.

    Args:
        player: Player biographical info (name, age, team, position, etc.)
        stats: List of season stat dicts (most recent first).
        scores: Model scores dict (sleeper_score, bust_score, etc.)
        league_averages: Optional league average stats for comparison.

    Returns:
        Formatted text string ready for prompt template insertion.
    """
    sections = []

    # --- Bio section ---
    sections.append(_format_bio(player))

    # --- Current season stats with league comparisons ---
    if stats:
        sections.append(_format_current_stats(stats[0], league_averages))

    # --- 3-year trends ---
    if len(stats) >= 2:
        sections.append(_format_trends(stats))

    # --- Model scores ---
    sections.append(_format_model_scores(scores))

    # --- Skills trajectory (improvement breakdown) ---
    if scores.get("stat_improvement_breakdown"):
        sections.append(_format_improvement_breakdown(scores["stat_improvement_breakdown"]))

    # --- Consistency breakdown ---
    if scores.get("stat_consistency_breakdown"):
        sections.append(_format_consistency_breakdown(scores["stat_consistency_breakdown"]))

    # --- Differentials (luck gap) ---
    if stats:
        sections.append(_format_differentials(stats[0]))

    # --- Dynasty context ---
    sections.append(_format_dynasty_context(player, scores))

    # --- Auction context ---
    sections.append(_format_auction_context(scores))

    return "\n\n".join(s for s in sections if s)


def _format_bio(player: dict) -> str:
    """Format player biographical information."""
    lines = ["### Player Profile"]
    lines.append(f"- **Name:** {player.get('full_name', 'Unknown')}")
    lines.append(f"- **Age:** {player.get('age', 'Unknown')}")
    lines.append(f"- **Team:** {player.get('team', 'Unknown')}")
    lines.append(f"- **Position:** {player.get('position', 'Unknown')}")

    if player.get("prospect_rank"):
        lines.append(f"- **Historical Prospect Rank:** #{player['prospect_rank']}")
    if player.get("mlb_service_time"):
        lines.append(f"- **Service Time:** {player['mlb_service_time']}")

    return "\n".join(lines)


def _format_current_stats(stats: dict, league_avgs: dict | None) -> str:
    """Format current season stats with league-average comparisons."""
    lines = [f"### {stats.get('season', 'Current')} Season Stats"]

    stat_display = _get_display_stats(stats)
    for stat_name, value in stat_display.items():
        if value is None:
            continue
        line = f"- **{stat_name}:** {_fmt_stat(value)}"
        if league_avgs and stat_name.lower().replace(" ", "_") in league_avgs:
            lg_avg = league_avgs[stat_name.lower().replace(" ", "_")]
            diff = value - lg_avg
            direction = "above" if diff > 0 else "below"
            line += f" (league avg: {_fmt_stat(lg_avg)}, {abs(diff):.3f} {direction})"
        lines.append(line)

    return "\n".join(lines)


def _format_trends(stats: list[dict]) -> str:
    """Format year-over-year stat trends."""
    lines = ["### Year-over-Year Trends"]

    # Determine which stats to show based on player type
    is_pitcher = "era" in stats[0] and stats[0].get("era") is not None
    trend_stats = _get_trend_stat_names(is_pitcher)

    for display_name, col_name in trend_stats:
        values = []
        for s in reversed(stats[:3]):  # Oldest first
            val = s.get(col_name)
            if val is not None:
                values.append(f"{s.get('season', '?')}: {_fmt_stat(val)}")
        if len(values) >= 2:
            trend_dir = _trend_direction(stats, col_name, is_pitcher)
            lines.append(f"- **{display_name}:** {' → '.join(values)} {trend_dir}")

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_model_scores(scores: dict) -> str:
    """Format model prediction scores."""
    lines = ["### AI Model Scores"]

    score_display = [
        ("AI Value Score", "ai_value_score", "/100"),
        ("Sleeper Score", "sleeper_score", "/100"),
        ("Bust Score", "bust_score", "/100"),
        ("Consistency Score", "consistency_score", "/100"),
        ("Improvement Score", "improvement_score", "(-100 to 100)"),
        ("Regression Direction", "regression_direction", "(positive = improving)"),
    ]

    for display_name, key, suffix in score_display:
        val = scores.get(key)
        if val is not None:
            lines.append(f"- **{display_name}:** {val:.1f} {suffix}")

    return "\n".join(lines)


def _format_improvement_breakdown(breakdown: dict) -> str:
    """Format per-stat improvement trends."""
    lines = ["### Skills Trajectory (Improvement Breakdown)"]

    for stat, details in breakdown.items():
        if isinstance(details, dict):
            direction = details.get("direction", "flat")
            r_sq = details.get("r_squared", 0)
            values = details.get("values", [])
            val_str = " → ".join(f"{v:.3f}" for v in values) if values else "N/A"
            lines.append(
                f"- **{stat}:** {val_str} | Direction: {direction} | "
                f"Trend fit (r²): {r_sq:.2f}"
            )

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_consistency_breakdown(breakdown: dict) -> str:
    """Format per-stat consistency details."""
    lines = ["### Consistency Breakdown"]

    for stat, details in breakdown.items():
        if isinstance(details, dict):
            consistency = details.get("consistency", 0)
            cv = details.get("cv", 0)
            lines.append(
                f"- **{stat}:** Consistency {consistency:.2f} (CV: {cv:.3f})"
            )

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_differentials(stats: dict) -> str:
    """Format actual vs. expected stat differentials."""
    lines = ["### Performance vs. Expected (Luck Gap)"]

    diffs = [
        ("wOBA vs xwOBA", "woba", "xwoba"),
        ("BA vs xBA", "avg", "xba"),
        ("SLG vs xSLG", "slg", "xslg"),
        ("ERA vs xERA", "era", "xera"),
        ("ERA vs FIP", "era", "fip"),
    ]

    for display_name, actual_key, expected_key in diffs:
        actual = stats.get(actual_key)
        expected = stats.get(expected_key)
        if actual is not None and expected is not None:
            diff = actual - expected
            label = "overperforming" if diff > 0.01 else (
                "underperforming" if diff < -0.01 else "in line"
            )
            # For ERA-type stats, flip the labeling
            if actual_key in ("era",):
                label = "overperforming" if diff < -0.01 else (
                    "underperforming" if diff > 0.01 else "in line"
                )
            lines.append(
                f"- **{display_name}:** {_fmt_stat(actual)} vs {_fmt_stat(expected)} "
                f"(gap: {diff:+.3f}, {label})"
            )

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_dynasty_context(player: dict, scores: dict) -> str:
    """Format dynasty-specific context."""
    lines = ["### Dynasty Context"]

    age = player.get("age")
    if age:
        if age < 25:
            arc = "Early development phase — significant growth potential"
        elif age < 27:
            arc = "Pre-peak — approaching prime years"
        elif age <= 29:
            arc = "Peak production window"
        elif age <= 32:
            arc = "Early decline phase — still productive but monitor trends"
        else:
            arc = "Late career — declining trajectory expected"
        lines.append(f"- **Career Arc:** {arc}")

    dynasty_val = scores.get("dynasty_value")
    if dynasty_val is not None:
        lines.append(f"- **Dynasty Value Score:** {dynasty_val:.1f}/100")

    keep_cut = scores.get("keep_cut_horizon")
    if keep_cut is not None:
        lines.append(f"- **Keep/Cut Horizon:** {keep_cut} years before cost exceeds value")

    return "\n".join(lines)


def _format_auction_context(scores: dict) -> str:
    """Format auction valuation context."""
    lines = ["### Auction Valuation"]

    auction_val = scores.get("auction_value")
    if auction_val is not None:
        lines.append(f"- **Projected Dollar Value:** ${auction_val:.1f}")

    expected_cost = scores.get("expected_cost")
    if expected_cost is not None:
        lines.append(f"- **Expected Auction Cost:** ${expected_cost:.1f}")

    surplus = scores.get("surplus_value")
    if surplus is not None:
        label = "surplus" if surplus > 0 else "deficit"
        lines.append(f"- **Surplus Value:** ${surplus:+.1f} ({label})")

    return "\n".join(lines)


def _get_display_stats(stats: dict) -> dict[str, Any]:
    """Get displayable stat name -> value mapping based on player type."""
    is_pitcher = stats.get("era") is not None

    if is_pitcher:
        return {
            "ERA": stats.get("era"),
            "WHIP": stats.get("whip"),
            "FIP": stats.get("fip"),
            "xFIP": stats.get("xfip"),
            "SIERA": stats.get("siera"),
            "K%": stats.get("k_pct"),
            "BB%": stats.get("bb_pct"),
            "K-BB%": stats.get("k_bb_pct"),
            "SwStr%": stats.get("swstr_pct"),
            "CSW%": stats.get("csw_pct"),
            "Barrel% Against": stats.get("barrel_pct_against"),
            "Hard Hit% Against": stats.get("hard_hit_pct_against"),
            "GB%": stats.get("gb_pct"),
            "HR/FB%": stats.get("hr_fb_pct"),
            "LOB%": stats.get("lob_pct"),
            "WAR": stats.get("war"),
            "IP": stats.get("ip"),
        }
    else:
        return {
            "AVG": stats.get("avg"),
            "OBP": stats.get("obp"),
            "SLG": stats.get("slg"),
            "wOBA": stats.get("woba"),
            "xwOBA": stats.get("xwoba"),
            "wRC+": stats.get("wrc_plus"),
            "ISO": stats.get("iso"),
            "BABIP": stats.get("babip"),
            "K%": stats.get("k_pct"),
            "BB%": stats.get("bb_pct"),
            "Barrel%": stats.get("barrel_pct"),
            "Hard Hit%": stats.get("hard_hit_pct"),
            "Avg Exit Velocity": stats.get("avg_exit_velocity"),
            "Sprint Speed": stats.get("sprint_speed"),
            "WAR": stats.get("war"),
            "PA": stats.get("pa"),
        }


def _get_trend_stat_names(is_pitcher: bool) -> list[tuple[str, str]]:
    """Get (display_name, column_name) pairs for trend tracking."""
    if is_pitcher:
        return [
            ("K%", "k_pct"), ("BB%", "bb_pct"), ("K-BB%", "k_bb_pct"),
            ("SwStr%", "swstr_pct"), ("ERA", "era"), ("FIP", "fip"),
            ("SIERA", "siera"), ("Barrel% Against", "barrel_pct_against"),
        ]
    else:
        return [
            ("K%", "k_pct"), ("BB%", "bb_pct"), ("Barrel%", "barrel_pct"),
            ("Hard Hit%", "hard_hit_pct"), ("Exit Velocity", "avg_exit_velocity"),
            ("wOBA", "woba"), ("xwOBA", "xwoba"), ("ISO", "iso"),
        ]


def _trend_direction(stats: list[dict], col: str, is_pitcher: bool) -> str:
    """Determine trend direction emoji/label."""
    if len(stats) < 2:
        return ""
    curr = stats[0].get(col)
    prev = stats[1].get(col)
    if curr is None or prev is None:
        return ""

    diff = curr - prev
    # For pitcher ERA/FIP/WHIP, lower is better
    lower_is_better = is_pitcher and col in ("era", "fip", "xfip", "siera", "whip", "bb_pct")

    if abs(diff) < 0.005:
        return "(stable)"
    if lower_is_better:
        return "(improving)" if diff < 0 else "(declining)"
    return "(improving)" if diff > 0 else "(declining)"


def _fmt_stat(val: Any) -> str:
    """Format a stat value for display."""
    if val is None:
        return "N/A"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if abs(val) >= 10:
            return f"{val:.1f}"
        return f"{val:.3f}"
    return str(val)
