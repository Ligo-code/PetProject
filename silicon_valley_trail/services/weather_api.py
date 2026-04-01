"""
Weather service using Open-Meteo API.
No API key required.

WMO weather code groups:
  0        — Clear sky
  1–3      — Partly cloudy
  45–48    — Fog
  51–67    — Drizzle / Rain
  71–77    — Snow
  80–82    — Showers
  95–99    — Thunderstorm
"""

import os
from dataclasses import dataclass

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 3
HOT_THRESHOLD_C = 28.0

USE_MOCK = os.getenv("MOCK_APIS", "false").lower() == "true"


@dataclass
class WeatherData:
    description: str
    temperature: float
    is_rainy: bool
    is_hot: bool


_MOCK_WEATHER = WeatherData(
    description="Partly cloudy, 18°C",
    temperature=18.0,
    is_rainy=False,
    is_hot=False,
)


def _parse_weather_code(code: int) -> tuple[str, bool]:
    """
    Translate a WMO weather code (returned by Open-Meteo API) into a
    human-readable description and an is_rainy flag.

    WMO code ranges:
      0        — Clear sky
      1–3      — Partly cloudy
      45–48    — Fog
      51–67    — Drizzle / Rain      → is_rainy = True
      71–77    — Snow                → is_rainy = True (treated as rain for gameplay)
      80–82    — Showers             → is_rainy = True
      95–99    — Thunderstorm        → is_rainy = True
    """
    if code == 0:
        return "Clear sky", False
    if code <= 3:
        return "Partly cloudy", False
    if code <= 48:
        return "Foggy", False
    if code <= 67:
        return "Rainy", True
    if code <= 77:
        return "Snowy", True
    if code <= 82:
        return "Showers", True
    return "Thunderstorm", True


def get_weather(lat: float, lon: float) -> WeatherData:
    """
    Fetch current weather for given coordinates.
    Falls back to mock data on any error.
    """
    if USE_MOCK:
        return _MOCK_WEATHER

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        current = response.json()["current_weather"]

        code = int(current["weathercode"])
        temp = float(current["temperature"])
        description_base, is_rainy = _parse_weather_code(code)
        description = f"{description_base}, {temp:.0f}°C"

        return WeatherData(
            description=description,
            temperature=temp,
            is_rainy=is_rainy,
            is_hot=temp >= HOT_THRESHOLD_C,
        )

    except Exception:
        return _MOCK_WEATHER
