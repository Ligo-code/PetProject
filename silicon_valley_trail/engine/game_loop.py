"""
Core game loop for Silicon Valley Trail.

Responsibilities:
- Present the current state to the player
- Handle action selection
- Trigger events after travel
- Trigger overnight events after rest
- Call tick_day() after every turn
- Check win/lose after every turn

Services (weather, HN) are called here and inject data into GameState.
If a service fails, GameState retains its previous/default values — game continues.
"""

import random

from ..models.game_state import GameState
from ..models.location import LOCATIONS
from ..models.team import TeamRole
from ..engine.actions import (
    travel, rest, fix_bugs, marketing_push, knowledge_share, buy_supplies,
)
from ..engine.events import EventRegistry

OVERNIGHT_EVENT_CHANCE = 0.45   # 45% chance of an overnight event after rest

registry = EventRegistry()

# Always-available events used as fallback when location pool yields nothing
FALLBACK_EVENT_KEYS = ["press_coverage", "recruiter_dm", "coffee_shortage"]


# ---------------------------------------------------------------------------
# Service injection (with fallback)
# ---------------------------------------------------------------------------

def _refresh_weather(state: GameState) -> None:
    """Fetch weather for current location and update state. Silent on failure."""
    try:
        from ..services.weather_api import get_weather
        loc = state.current_location
        data = get_weather(loc.lat, loc.lon)
        state.weather_description = data.description
        state.weather_is_rainy = data.is_rainy
        state.weather_is_hot = data.is_hot
    except Exception:
        pass  # keep previous weather data, game continues


def _refresh_hn(state: GameState) -> None:
    """Fetch HN trending keyword. Only called once at game start."""
    try:
        from ..services.hn_api import get_trending_keyword
        state.hn_trending_keyword = get_trending_keyword()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Event resolution
# ---------------------------------------------------------------------------

def _resolve_event(state: GameState, event) -> None:
    """Present an event to the player and apply the chosen effect."""
    print()
    print("!" * 60)
    print(f"  EVENT: {event.title}")
    print("!" * 60)
    if event.description:
        print(f"\n{event.description}\n")

    if event.is_automatic:
        msg = event.auto_effect(state)
        print(msg)
        return

    choices = event.available_choices(state)
    if not choices:
        return

    for i, choice in enumerate(choices, 1):
        print(f"{i}. {choice.text}")

    choice = _get_choice(len(choices))
    msg = choices[choice - 1].effect(state)
    print(f"\n{msg}")


def _maybe_trigger_overnight_event(state: GameState) -> None:
    """After rest, roll for an overnight event."""
    if random.random() < OVERNIGHT_EVENT_CHANCE:
        event = registry.pick_overnight(state)
        if event:
            _resolve_event(state, event)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _display_status(state: GameState) -> None:
    loc = state.current_location
    active_names = ", ".join(m.name for m in state.active_team)

    print()
    print("=" * 60)
    print(f"Day {state.day} | {loc.name}")
    print(loc.description)
    print("=" * 60)
    print(f"Cash: ${state.cash:,}  |  Morale: {state.morale}/100  |  Coffee: {state.coffee}")
    print(f"Hype: {state.hype}/100  |  Bugs: {state.bugs}")
    print(f"Progress: {state.progress_percent}% to San Francisco")
    print("=" * 60)
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
    print("-" * 60)


def _display_actions(state: GameState) -> None:
    print("\nWhat will you do?")
    print("-" * 60)
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


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def _get_choice(max_option: int) -> int:
    while True:
        try:
            raw = input(f"\nEnter choice (1-{max_option}): ").strip()
            value = int(raw)
            if 1 <= value <= max_option:
                return value
        except (ValueError, EOFError):
            pass
        print(f"Please enter a number between 1 and {max_option}.")


def _press_enter() -> None:
    try:
        input("\nPress Enter to continue...")
    except EOFError:
        pass


# ---------------------------------------------------------------------------
# Win / Lose screens
# ---------------------------------------------------------------------------

def _show_win(state: GameState) -> None:
    print()
    print("=" * 60)
    print("CONGRATULATIONS!")
    print("=" * 60)
    print(f"You reached San Francisco in {state.day} days!")
    print("Series A pitch: SUCCESS")
    print()
    print(f"Final stats:")
    print(f"  Cash:   ${state.cash:,}")
    print(f"  Morale: {state.morale}/100")
    print(f"  Hype:   {state.hype}/100")
    print(f"  Bugs:   {state.bugs}")
    print(f"  Hackathon won: {'Yes!' if state.hackathon_won else 'No'}")
    active = [m.name for m in state.active_team]
    print(f"  Team at finish: {', '.join(active)}")
    print("=" * 60)


def _show_lose(state: GameState) -> None:
    print()
    print("=" * 60)
    print("GAME OVER")
    print("=" * 60)
    print(state.lose_reason)
    print(f"You made it to: {state.current_location.name} (Day {state.day})")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

def run_game(state: GameState, save_callback, quit_callback) -> None:
    """
    Run the game loop until win, lose, or quit.

    Args:
        state:          current GameState (new or loaded)
        save_callback:  callable(state) -> None
        quit_callback:  callable() -> None  (returns to main menu)
    """
    _refresh_hn(state)

    while not state.game_over:
        _refresh_weather(state)
        _display_status(state)
        _display_actions(state)

        choice = _get_choice(8)

        if choice == 1:
            if state.current_location_index == len(LOCATIONS) - 1:
                print("You're already in San Francisco!")
                _press_enter()
                continue
            msg = travel(state)
            print(f"\n{msg}")
            # Trigger a location event after arriving — fallback ensures one always fires
            event = registry.pick_from_pool(state.current_location.event_pool, state)
            if not event:
                event = registry.pick_from_pool(FALLBACK_EVENT_KEYS, state)
            if event:
                _resolve_event(state, event)

        elif choice == 2:
            msg = rest(state)
            print(f"\n{msg}")
            _maybe_trigger_overnight_event(state)

        elif choice == 3:
            msg = fix_bugs(state)
            print(f"\n{msg}")

        elif choice == 4:
            msg = marketing_push(state)
            print(f"\n{msg}")

        elif choice == 5:
            msg = knowledge_share(state)
            print(f"\n{msg}")

        elif choice == 6:
            msg = buy_supplies(state)
            print(f"\n{msg}")

        elif choice == 7:
            save_callback(state)
            print("\nGame saved!")
            _press_enter()
            continue

        elif choice == 8:
            quit_callback()
            return

        # End of turn
        state.tick_day()
        print(f"\nDaily upkeep: -{state.DAILY_COFFEE_DRAIN} coffee.")
        state.check_game_status()
        _press_enter()

    if state.won:
        _show_win(state)
    else:
        _show_lose(state)
    _press_enter()
