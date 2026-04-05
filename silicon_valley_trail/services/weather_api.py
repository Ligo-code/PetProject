"""
Weather service using Open-Meteo API.
No API key required.
"""

import os
from dataclasses import dataclass
from enum import Enum

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

class WeatherCode(Enum):
    """
    Maps WMO weather codes to gameplay-relevant data.
    Each member bundles a display description and an is_rainy flag together,
    so adding a new weather type only requires one line here — not changes
    across multiple functions.
    """
    CLEAR        = ("Clear sky",     False)
    PARTLY_CLOUDY = ("Partly cloudy", False)
    FOG          = ("Foggy",         False)
    RAIN         = ("Rainy",         True)
    SNOW         = ("Snowy",         True)   # treated as rainy for gameplay
    SHOWERS      = ("Showers",       True)
    THUNDERSTORM = ("Thunderstorm",  True)

    def __init__(self, description: str, is_rainy: bool):
        self.description = description
        self.is_rainy = is_rainy


def _parse_weather_code(code: int) -> tuple[str, bool]:
    """
    Translate a WMO weather code into a WeatherCode enum member,
    then return its description and is_rainy flag.

    Returning enum attributes instead of raw strings keeps description
    and is_rainy coupled at the source — WeatherCode owns both values.

    WMO code ranges:
      0        — Clear sky
      1–3      — Partly cloudy
      45–48    — Fog
      51–67    — Drizzle / Rain      → is_rainy = True
      71–77    — Snow                → is_rainy = True
      80–82    — Showers             → is_rainy = True
      95–99    — Thunderstorm        → is_rainy = True
    """
    if code == 0:
        weather = WeatherCode.CLEAR
    elif code <= 3:
        weather = WeatherCode.PARTLY_CLOUDY
    elif code <= 48:
        weather = WeatherCode.FOG
    elif code <= 67:
        weather = WeatherCode.RAIN
    elif code <= 77:
        weather = WeatherCode.SNOW
    elif code <= 82:
        weather = WeatherCode.SHOWERS
    else:
        # covers 83–99 (thunderstorm) and any unknown future codes
        weather = WeatherCode.THUNDERSTORM

    return weather.description, weather.is_rainy


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
