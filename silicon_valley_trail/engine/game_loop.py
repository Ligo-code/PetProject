"""
Game loop (Controller) for Silicon Valley Trail.

Responsibilities:
- Handle player input
- Orchestrate actions, events, and turn lifecycle
- Inject external API data into GameState
- Delegate all terminal output to renderer (View)

Services (weather, HN) are called here and inject data into GameState.
If a service fails, GameState retains its previous/default values — game continues.
"""

import random
from enum import IntEnum

from ..models.game_state import GameState
from ..models.location import LOCATIONS
from ..engine.actions import (
    travel, rest, fix_bugs, marketing_push, knowledge_share, buy_supplies,
)
from ..engine.events import EventRegistry
from ..engine import renderer
from ..leaderboard import save_score, ScoreEntry

OVERNIGHT_EVENT_CHANCE = 0.45   # 45% chance of an overnight event after rest


class Action(IntEnum):
    TRAVEL          = 1
    REST            = 2
    FIX_BUGS        = 3
    MARKETING_PUSH  = 4
    KNOWLEDGE_SHARE = 5
    BUY_SUPPLIES    = 6
    SAVE            = 7
    QUIT            = 8


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
# Event resolution
# ---------------------------------------------------------------------------

def _resolve_event(state: GameState, event) -> None:
    """Apply event logic: delegate display to renderer, handle input and effects here."""
    if event.is_automatic:
        renderer.show_event(event, [])
        msg = event.auto_effect(state)
        renderer.show_message(msg)
        return

    choices = event.available_choices(state)
    if not choices:
        return

    renderer.show_event(event, choices)
    choice = _get_choice(len(choices))
    msg = choices[choice - 1].effect(state)
    renderer.show_message(msg)


def _build_score_entry(state: GameState) -> ScoreEntry:
    """Build a leaderboard entry from the completed game state."""
    return ScoreEntry(
        name=state.player_name,
        score=state.calc_score(),
        won=state.won,
        day=state.day,
        hackathon_won=state.hackathon_won,
    )


def _maybe_trigger_overnight_event(state: GameState) -> None:
    """After rest, roll for an overnight event."""
    if random.random() < OVERNIGHT_EVENT_CHANCE:
        event = registry.pick_overnight(state)
        if event:
            _resolve_event(state, event)


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
        renderer.display_status(state)
        renderer.display_actions(state)

        choice = Action(_get_choice(len(Action)))

        if choice == Action.TRAVEL:
            if state.current_location_index == len(LOCATIONS) - 1:
                renderer.show_message("You're already in San Francisco!")
                _press_enter()
                continue
            msg = travel(state)
            renderer.show_message(msg)
            # Trigger a location event after arriving — fallback ensures one always fires
            event = registry.pick_from_pool(state.current_location.event_pool, state)
            if not event:
                event = registry.pick_from_pool(FALLBACK_EVENT_KEYS, state)
            if event:
                _resolve_event(state, event)

        elif choice == Action.REST:
            msg = rest(state)
            renderer.show_message(msg)
            _maybe_trigger_overnight_event(state)

        elif choice == Action.FIX_BUGS:
            msg = fix_bugs(state)
            renderer.show_message(msg)

        elif choice == Action.MARKETING_PUSH:
            msg = marketing_push(state)
            renderer.show_message(msg)

        elif choice == Action.KNOWLEDGE_SHARE:
            msg = knowledge_share(state)
            renderer.show_message(msg)

        elif choice == Action.BUY_SUPPLIES:
            msg = buy_supplies(state)
            renderer.show_message(msg)

        elif choice == Action.SAVE:
            save_callback(state)
            renderer.show_message("Game saved!")
            _press_enter()
            continue

        elif choice == Action.QUIT:
            quit_callback()
            return

        # End of turn
        state.tick_day()
        renderer.show_message(f"Daily upkeep: -{state.DAILY_COFFEE_DRAIN} coffee.")
        state.check_game_status()
        _press_enter()

    save_score(_build_score_entry(state))
    if state.won:
        renderer.show_win(state)
    else:
        renderer.show_lose(state)
    _press_enter()
