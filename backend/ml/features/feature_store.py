"""Central feature definitions and metadata.

Defines which features are used by each model, their types, and default values.
This serves as the single source of truth for feature columns across training
and inference.
"""

# All feature categories with metadata
BATTER_FEATURES = {
    # Differential features
    "differentials": [
        "woba_minus_xwoba", "ba_minus_xba", "slg_minus_xslg", "babip_minus_league",
    ],
    # Year-over-year trends
    "yoy_trends": [
        "barrel_pct_yoy_delta", "hard_hit_pct_yoy_delta", "k_pct_yoy_delta",
        "bb_pct_yoy_delta", "avg_exit_velocity_yoy_delta",
        "woba_yoy_delta", "xwoba_yoy_delta", "iso_yoy_delta",
        "sprint_speed_yoy_delta", "wrc_plus_yoy_delta", "pa_yoy_delta",
    ],
    # Multi-year trends
    "multi_year_trends": [
        "barrel_pct_2yr_trend", "barrel_pct_3yr_trend",
        "hard_hit_pct_2yr_trend", "hard_hit_pct_3yr_trend",
        "k_pct_2yr_trend", "k_pct_3yr_trend",
        "bb_pct_2yr_trend", "bb_pct_3yr_trend",
        "avg_exit_velocity_2yr_trend", "avg_exit_velocity_3yr_trend",
        "woba_2yr_trend", "woba_3yr_trend",
        "xwoba_2yr_trend", "xwoba_3yr_trend",
        "iso_2yr_trend", "iso_3yr_trend",
        "sprint_speed_2yr_trend", "sprint_speed_3yr_trend",
        "wrc_plus_2yr_trend", "wrc_plus_3yr_trend",
    ],
    # Age curve
    "age_features": [
        "age", "years_from_peak", "age_bucket", "pre_peak",
    ],
    # Latest stat snapshot
    "latest_stats": [
        "latest_barrel_pct", "latest_hard_hit_pct", "latest_k_pct", "latest_bb_pct",
        "latest_avg_exit_velocity", "latest_sprint_speed", "latest_woba", "latest_xwoba",
        "latest_iso", "latest_babip", "latest_war", "latest_gb_pct", "latest_fb_pct",
        "latest_ld_pct",
    ],
    # Context
    "context": [
        "pa_latest", "seasons_available",
    ],
}

PITCHER_FEATURES = {
    "differentials": [
        "era_minus_fip", "era_minus_xera", "fip_minus_xfip",
        "babip_minus_league", "lob_pct_minus_league", "hr_fb_pct_minus_league",
    ],
    "yoy_trends": [
        "k_pct_yoy_delta", "bb_pct_yoy_delta", "k_bb_pct_yoy_delta",
        "swstr_pct_yoy_delta", "csw_pct_yoy_delta",
        "barrel_pct_against_yoy_delta", "hard_hit_pct_against_yoy_delta",
        "gb_pct_yoy_delta", "era_yoy_delta", "fip_yoy_delta",
        "siera_yoy_delta", "whip_yoy_delta", "ip_yoy_delta",
    ],
    "multi_year_trends": [
        "k_pct_2yr_trend", "k_pct_3yr_trend",
        "bb_pct_2yr_trend", "bb_pct_3yr_trend",
        "k_bb_pct_2yr_trend", "k_bb_pct_3yr_trend",
        "swstr_pct_2yr_trend", "swstr_pct_3yr_trend",
        "csw_pct_2yr_trend", "csw_pct_3yr_trend",
        "barrel_pct_against_2yr_trend", "barrel_pct_against_3yr_trend",
        "hard_hit_pct_against_2yr_trend", "hard_hit_pct_against_3yr_trend",
        "gb_pct_2yr_trend", "gb_pct_3yr_trend",
        "era_2yr_trend", "era_3yr_trend",
        "fip_2yr_trend", "fip_3yr_trend",
        "siera_2yr_trend", "siera_3yr_trend",
        "whip_2yr_trend", "whip_3yr_trend",
    ],
    "age_features": [
        "age", "years_from_peak", "age_bucket", "pre_peak",
    ],
    "latest_stats": [
        "latest_k_pct", "latest_bb_pct", "latest_k_bb_pct",
        "latest_swstr_pct", "latest_csw_pct",
        "latest_era", "latest_fip", "latest_xfip", "latest_siera", "latest_xera",
        "latest_whip", "latest_war",
        "latest_barrel_pct_against", "latest_hard_hit_pct_against",
        "latest_gb_pct", "latest_lob_pct", "latest_hr_fb_pct", "latest_stuff_plus",
    ],
    "context": [
        "is_starter", "ip_latest", "seasons_available",
    ],
}


def get_all_features(player_type: str = "batter") -> list[str]:
    """Get flat list of all feature column names for a player type."""
    features = BATTER_FEATURES if player_type == "batter" else PITCHER_FEATURES
    all_cols = []
    for category_cols in features.values():
        all_cols.extend(category_cols)
    return all_cols
