"""
Leaderboard storage for Silicon Valley Trail.

Stores completed run results separately from save-game data.
Each entry records the player name, score, and key run stats.

Note: save_score() is not protected against concurrent writes.
For a CLI app this is acceptable (without over-engineering) — in production, use file locks or a database.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path


LEADERBOARD_FILE = Path.home() / ".silicon_valley_trail_leaderboard.json"
MAX_LEADERBOARD_SIZE = 100  # cap file growth

SCORE_MESSAGES = [
    (300, "Legendary run — you nailed it."),
    (200, "Strong finish — you built a solid startup."),
    (100, "Decent run — room to improve."),
    (0,   "Rough ride — try again."),
]

REQUIRED_ENTRY_FIELDS = {"name", "score", "won", "day", "hackathon_won"}


@dataclass
class ScoreEntry:
    """A single completed run recorded on the leaderboard."""
    name: str
    score: int
    won: bool
    day: int
    hackathon_won: bool


def _get_message(score: int) -> str:
    for threshold, message in SCORE_MESSAGES:
        if score >= threshold:
            return message
    return SCORE_MESSAGES[-1][1]


def _is_valid_entry(data: dict) -> bool:
    """Return True if the dict has all required fields, correct types, and sane values."""
    if not REQUIRED_ENTRY_FIELDS.issubset(data.keys()):
        return False
    return (
        isinstance(data["name"], str)
        and isinstance(data["score"], int)
        and isinstance(data["won"], bool)
        and isinstance(data["day"], int)
        and isinstance(data["hackathon_won"], bool)
        and data["name"].strip() != ""
        and data["score"] >= 0
        and data["day"] >= 1
    )


def save_score(entry: ScoreEntry) -> None:
    """
    Append a completed run entry to the leaderboard file.
    Keeps only the top MAX_LEADERBOARD_SIZE entries by score.

    Caller is responsible for building the ScoreEntry from game state —
    leaderboard has no dependency on GameState.
    """
    entries = load_scores()
    entries.append(entry)
    entries_sorted = sorted(entries, key=lambda e: e.score, reverse=True)
    top_entries = entries_sorted[:MAX_LEADERBOARD_SIZE]
    LEADERBOARD_FILE.write_text(
        json.dumps([asdict(e) for e in top_entries], indent=2),
        encoding="utf-8",
    )


def load_scores() -> list[ScoreEntry]:
    """
    Load leaderboard entries from disk, sorted by score descending.
    Skips malformed or incomplete entries silently.
    Falls back to empty list on any error, including whole-file corruption.
    """
    if not LEADERBOARD_FILE.exists():
        return []
    try:
        raw = json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        return sorted(
            [ScoreEntry(**e) for e in raw if _is_valid_entry(e)],
            key=lambda e: e.score,
            reverse=True,
        )
    except Exception:
        return []


def format_leaderboard(entries: list[ScoreEntry]) -> str:
    """Format top 10 leaderboard entries for display."""
    if not entries:
        return "No scores yet."
    lines = []
    for i, entry in enumerate(entries[:10], 1):
        won_marker = "✓" if entry.won else " "
        lines.append(
            f"{i:>2}. [{won_marker}] {entry.name:<15} {entry.score:>4} pts  "
            f"(Day {entry.day})"
        )
    return "\n".join(lines)


def get_performance_message(score: int) -> str:
    return _get_message(score)
