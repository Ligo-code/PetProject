"""
Silicon Valley Trail — FastAPI web layer.

Exposes the simulation engine as an HTTP service.
The game logic is untouched — this layer only wraps it.
"""

from fastapi import FastAPI

from silicon_valley_trail.models.game_state import GameState
from silicon_valley_trail.engine.actions import travel
from silicon_valley_trail.engine.events import EventRegistry
from silicon_valley_trail.services.weather_api import get_weather
from silicon_valley_trail.services.hn_api import get_trending_keyword

app = FastAPI(
    title="Silicon Valley Trail",
    description=(
        "A state-driven startup simulation engine with real-time weather and "
        "Hacker News inputs. Built to demonstrate clean architecture, "
        "rule-based event systems, and graceful API failure handling."
    ),
    version="1.0.0",
)

registry = EventRegistry()


def _state_snapshot(state: GameState) -> dict:
    return {
        "location": state.current_location.name,
        "day": state.day,
        "cash": state.cash,
        "morale": state.morale,
        "coffee": state.coffee,
        "hype": state.hype,
        "bugs": state.bugs,
        "team": [
            {
                "name": m.name,
                "role": m.role.value,
                "active": m.is_active,
            }
            for m in state.team
        ],
    }


@app.get("/")
def root():
    return {
        "project": "Silicon Valley Trail",
        "description": (
            "A state-driven startup simulation engine. "
            "Manage cash, morale, coffee, hype, and bugs "
            "as your team travels from San Jose to San Francisco."
        ),
        "endpoints": {
            "GET  /health": "Service health check",
            "POST /play-demo": (
                "Run one demo turn with live weather and HN data. "
                "Returns state before and after the action."
            ),
            "GET  /docs": "Interactive API documentation",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/play-demo")
def play_demo():
    """
    Run a single deterministic demo turn of the simulation.

    This endpoint is intended for portfolio/interview review and does not
    persist session state between requests.
    """
    state = GameState()
    loc = state.current_location

    weather_context = {
        "weather": "unavailable",
        "weather_is_rainy": False,
        "weather_is_hot": False,
    }

    try:
        weather = get_weather(loc.lat, loc.lon)
        state.weather_description = weather.description
        state.weather_is_rainy = weather.is_rainy
        state.weather_is_hot = weather.is_hot
        weather_context = {
            "weather": state.weather_description,
            "weather_is_rainy": state.weather_is_rainy,
            "weather_is_hot": state.weather_is_hot,
        }
    except Exception:
        state.weather_description = "Weather unavailable"
        state.weather_is_rainy = False
        state.weather_is_hot = False

    try:
        state.hn_trending_keyword = get_trending_keyword()
    except Exception:
        state.hn_trending_keyword = "unavailable"

    state_before = _state_snapshot(state)

    action_message = travel(state)

    event_message = None
    event = registry.pick_from_pool(state.current_location.event_pool, state)
    if event:
        if event.is_automatic:
            event_message = f"[{event.title}] {event.auto_effect(state)}"
        else:
            choices = event.available_choices(state)
            if choices:
                result = choices[0].effect(state)
                event_message = f"[{event.title}] {result}"

    state.tick_day()
    state_after = _state_snapshot(state)

    return {
        "external_context": {
            **weather_context,
            "hn_trending_keyword": state.hn_trending_keyword,
        },
        "state_before": state_before,
        "action": action_message,
        "event": event_message,
        "state_after": state_after,
    }