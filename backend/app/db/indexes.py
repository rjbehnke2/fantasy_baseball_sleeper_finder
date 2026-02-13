"""Database performance indexes.

Defines additional indexes beyond the ORM defaults for common query patterns.
Run via Alembic migration or directly against the database.
"""

# SQL statements for performance indexes
INDEXES = [
    # Player lookups by name (search)
    "CREATE INDEX IF NOT EXISTS ix_players_name_trgm ON players USING gin (full_name gin_trgm_ops);",

    # Batting seasons: common query patterns
    "CREATE INDEX IF NOT EXISTS ix_batting_player_season_desc ON batting_seasons (player_id, season DESC);",
    "CREATE INDEX IF NOT EXISTS ix_batting_season ON batting_seasons (season);",

    # Pitching seasons: common query patterns
    "CREATE INDEX IF NOT EXISTS ix_pitching_player_season_desc ON pitching_seasons (player_id, season DESC);",
    "CREATE INDEX IF NOT EXISTS ix_pitching_season ON pitching_seasons (season);",

    # Projections: latest per player (most common query)
    "CREATE INDEX IF NOT EXISTS ix_projections_player_date_desc ON projections (player_id, run_date DESC);",
    "CREATE INDEX IF NOT EXISTS ix_projections_ai_value ON projections (ai_value_score DESC NULLS LAST);",
    "CREATE INDEX IF NOT EXISTS ix_projections_sleeper ON projections (sleeper_score DESC NULLS LAST);",
    "CREATE INDEX IF NOT EXISTS ix_projections_bust ON projections (bust_score DESC NULLS LAST);",
    "CREATE INDEX IF NOT EXISTS ix_projections_dynasty ON projections (dynasty_value DESC NULLS LAST);",

    # Scouting reports: lookup by player + type
    "CREATE INDEX IF NOT EXISTS ix_scouting_player_type_date ON scouting_reports (player_id, report_type, generated_at DESC);",
    "CREATE INDEX IF NOT EXISTS ix_scouting_stale ON scouting_reports (stale) WHERE stale = true;",

    # Statcast aggregates
    "CREATE INDEX IF NOT EXISTS ix_statcast_player_season ON statcast_aggregates (player_id, season DESC);",
]


def get_index_sql() -> str:
    """Get all index creation statements as a single SQL string."""
    # Trigram extension needed for name search
    preamble = "CREATE EXTENSION IF NOT EXISTS pg_trgm;\n"
    return preamble + "\n".join(INDEXES)
