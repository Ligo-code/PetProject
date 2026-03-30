"""
Save / load game state to a JSON file in the user's home directory.

We manually serialize/deserialize dataclasses to avoid third-party deps.
TeamMember.role is a str Enum so it round-trips cleanly through JSON.
"""

import json
import copy
from pathlib import Path

from .models.game_state import GameState
from .models.team import TeamMember, TeamRole, DEFAULT_TEAM
from .models.location import LOCATIONS

SAVE_FILE = Path.home() / ".silicon_valley_trail_save.json"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _team_to_dict(team: list[TeamMember]) -> list[dict]:
    return [
        {
            "name": m.name,
            "role": m.role.value,
            "specialty": m.specialty,
            "morale": m.morale,
            "is_active": m.is_active,
            "inactive_days_remaining": m.inactive_days_remaining,
        }
        for m in team
    ]


def _team_from_dict(data: list[dict]) -> list[TeamMember]:
    return [
        TeamMember(
            name=d["name"],
            role=TeamRole(d["role"]),
            specialty=d["specialty"],
            morale=d["morale"],
            is_active=d["is_active"],
            inactive_days_remaining=d["inactive_days_remaining"],
        )
        for d in data
    ]


def _state_to_dict(state: GameState) -> dict:
    return {
        "cash": state.cash,
        "morale": state.morale,
        "coffee": state.coffee,
        "hype": state.hype,
        "bugs": state.bugs,
        "day": state.day,
        "current_location_index": state.current_location_index,
        "days_without_coffee": state.days_without_coffee,
        "hackathon_won": state.hackathon_won,
        "next_fix_bugs_boosted": state.next_fix_bugs_boosted,
        "team": _team_to_dict(state.team),
    }


def _state_from_dict(data: dict) -> GameState:
    return GameState(
        cash=data["cash"],
        morale=data["morale"],
        coffee=data["coffee"],
        hype=data["hype"],
        bugs=data["bugs"],
        day=data["day"],
        current_location_index=data["current_location_index"],
        days_without_coffee=data["days_without_coffee"],
        hackathon_won=data["hackathon_won"],
        next_fix_bugs_boosted=data["next_fix_bugs_boosted"],
        team=_team_from_dict(data["team"]),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_game(state: GameState) -> None:
    """Persist current game state to disk."""
    SAVE_FILE.write_text(
        json.dumps(_state_to_dict(state), indent=2),
        encoding="utf-8",
    )


def load_game() -> GameState | None:
    """Load saved game state. Returns None if no save exists or file is corrupt."""
    if not SAVE_FILE.exists():
        return None
    try:
        data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        return _state_from_dict(data)
    except Exception:
        return None


def delete_save() -> None:
    """Remove save file after game ends."""
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()
