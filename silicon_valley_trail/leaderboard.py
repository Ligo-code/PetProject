"""
Leaderboard storage for Silicon Valley Trail.

Stores completed run results separately from save-game data.
Each entry records the player name, score, and key run stats.
"""

import json
from pathlib import Path

from .models.game_state import GameState

LEADERBOARD_FILE = Path.home() / ".silicon_valley_trail_leaderboard.json"

SCORE_MESSAGES = [
    (300, "Legendary run — you nailed it."),
    (200, "Strong finish — you built a solid startup."),
    (100, "Decent run — room to improve."),
    (0,   "Rough ride — try again."),
]


def _get_message(score: int) -> str:
    for threshold, message in SCORE_MESSAGES:
        if score >= threshold:
            return message
    return SCORE_MESSAGES[-1][1]


def save_score(state: GameState) -> None:
    """Append the completed run to the leaderboard file."""
    entries = load_scores()
    entries.append({
        "name": state.player_name,
        "score": state.calc_score(),
        "won": state.won,
        "day": state.day,
        "hackathon_won": state.hackathon_won,
    })
    LEADERBOARD_FILE.write_text(
        json.dumps(entries, indent=2),
        encoding="utf-8",
    )


def load_scores() -> list[dict]:
    """Load all leaderboard entries, sorted by score descending."""
    if not LEADERBOARD_FILE.exists():
        return []
    try:
        entries = json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
        return sorted(entries, key=lambda e: e["score"], reverse=True)
    except Exception:
        return []


def format_leaderboard(entries: list[dict]) -> str:
    """Format leaderboard entries for display."""
    if not entries:
        return "No scores yet."
    lines = []
    for i, entry in enumerate(entries[:10], 1):  # top 10
        won_marker = "✓" if entry["won"] else " "
        lines.append(
            f"{i:>2}. [{won_marker}] {entry['name']:<15} {entry['score']:>4} pts  "
            f"(Day {entry['day']})"
        )
    return "\n".join(lines)


def get_performance_message(score: int) -> str:
    return _get_message(score)
