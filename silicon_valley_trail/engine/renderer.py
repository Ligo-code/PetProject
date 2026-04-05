"""
Renderer (View layer) for Silicon Valley Trail.

Responsibilities:
- All terminal output: status, actions, events, win/lose screens
- No game logic, no input handling, no state mutation

Controller (game_loop.py) decides WHAT to show.
Renderer decides HOW to show it.
"""

from ..models.game_state import GameState
from ..models.team import TeamRole
from ..leaderboard import get_performance_message, format_leaderboard, load_scores

DISPLAY_WIDTH = 60


def display_status(state: GameState) -> None:
    loc = state.current_location
    active_names = ", ".join(m.name for m in state.active_team)

    print()
    print("=" * DISPLAY_WIDTH)
    print(f"Day {state.day} | {loc.name}")
    print(loc.description)
    print("=" * DISPLAY_WIDTH)
    print(f"Cash: ${state.cash:,}  |  Morale: {state.morale}/100  |  Coffee: {state.coffee}")
    print(f"Hype: {state.hype}/100  |  Bugs: {state.bugs}")
    print(f"Progress: {state.progress_percent}% to San Francisco")
    print("=" * DISPLAY_WIDTH)
    print(f"Weather: {state.weather_description}")
    if state.hn_trending_keyword:
        print(f"HN Trending: \"{state.hn_trending_keyword}\"  ->  +hype opportunity")
    if state.coffee == 0 and state.days_without_coffee == 1:
        print("WARNING: Day 2 without coffee means game over!")
    elif state.coffee == 0:
        print("WARNING: No coffee left!")
    if state.next_fix_bugs_boosted:
        print("Bug fix boost: ACTIVE (next fix will be 2x effective)")
    print(f"Team: {active_names}")
    print("-" * DISPLAY_WIDTH)
    print(f"Score: {state.calc_score()}")


def display_actions(state: GameState) -> None:
    print("\nWhat will you do?")
    print("-" * DISPLAY_WIDTH)
    print("1. Travel to next location")
    print("2. Rest and recover")
    print("3. Fix bugs")
    print("4. Marketing push")
    if state.has_role_active(TeamRole.PRODUCT):
        print("5. Knowledge share (Leo)")
    else:
        print("5. Knowledge share (Leo unavailable)")
    print("6. Buy supplies ($3,000)")
    print("7. Save game")
    print("8. Quit to menu")


def show_event(event, choices: list) -> None:
    """Render event header, description, and available choices."""
    print()
    print("!" * DISPLAY_WIDTH)
    print(f"  EVENT: {event.title}")
    print("!" * DISPLAY_WIDTH)
    if event.description:
        print(f"\n{event.description}\n")
    for i, choice in enumerate(choices, 1):
        print(f"{i}. {choice.text}")


def show_message(text: str) -> None:
    print(f"\n{text}")


def _show_score_and_leaderboard(state: GameState) -> None:
    """Shared end-of-game score display and leaderboard."""
    score = state.calc_score()
    print(f"\nFinal Score: {score}")
    print(get_performance_message(score))
    print()
    print("Top Players:")
    print(format_leaderboard(load_scores()))
    print("=" * DISPLAY_WIDTH)


def show_win(state: GameState) -> None:
    print()
    print("=" * DISPLAY_WIDTH)
    print("CONGRATULATIONS!")
    print("=" * DISPLAY_WIDTH)
    print(f"You reached San Francisco in {state.day} days!")
    print("Series A pitch: SUCCESS")
    print()
    print("Final stats:")
    print(f"  Cash:   ${state.cash:,}")
    print(f"  Morale: {state.morale}/100")
    print(f"  Hype:   {state.hype}/100")
    print(f"  Bugs:   {state.bugs}")
    print(f"  Hackathon won: {'Yes!' if state.hackathon_won else 'No'}")
    active = [m.name for m in state.active_team]
    print(f"  Team at finish: {', '.join(active)}")
    _show_score_and_leaderboard(state)


def show_lose(state: GameState) -> None:
    print()
    print("=" * DISPLAY_WIDTH)
    print("GAME OVER")
    print("=" * DISPLAY_WIDTH)
    print(state.lose_reason)
    print(f"You made it to: {state.current_location.name} (Day {state.day})")
    _show_score_and_leaderboard(state)


