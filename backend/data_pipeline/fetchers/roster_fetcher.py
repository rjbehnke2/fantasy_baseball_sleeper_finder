"""Fetches roster and injury data from the MLB Stats API."""

import logging

import statsapi

logger = logging.getLogger(__name__)


def fetch_all_active_rosters() -> list[dict]:
    """Fetch current 40-man rosters for all MLB teams.

    Returns:
        List of player dicts with id, name, team, position, status.
    """
    players = []
    teams = statsapi.get("teams", {"sportId": 1})  # sportId 1 = MLB

    for team in teams.get("teams", []):
        team_id = team["id"]
        team_abbr = team.get("abbreviation", "")
        try:
            roster = statsapi.roster(team_id, rosterType="40Man")
            # Parse the text roster into structured data
            for line in roster.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                players.append({
                    "team": team_abbr,
                    "roster_line": line,
                })
        except Exception:
            logger.exception(f"Error fetching roster for team {team_abbr} ({team_id})")

    logger.info(f"Fetched roster data for {len(players)} players")
    return players


def fetch_player_info(mlbam_id: int) -> dict | None:
    """Fetch detailed info for a single player by MLBAM ID.

    Args:
        mlbam_id: The MLB Advanced Media player ID.

    Returns:
        Dict with player biographical data, or None if not found.
    """
    try:
        data = statsapi.get("people", {"personIds": mlbam_id})
        if data.get("people"):
            person = data["people"][0]
            return {
                "mlbam_id": person["id"],
                "full_name": person.get("fullName", ""),
                "position": person.get("primaryPosition", {}).get("abbreviation", ""),
                "birth_date": person.get("birthDate"),
                "mlb_debut_date": person.get("mlbDebutDate"),
                "team": person.get("currentTeam", {}).get("abbreviation", ""),
                "status": "active" if person.get("active") else "inactive",
            }
    except Exception:
        logger.exception(f"Error fetching player info for {mlbam_id}")
    return None
