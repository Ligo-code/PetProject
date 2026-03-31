from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .game_state import GameState


@dataclass
class EventChoice:
    text: str
    effect: Callable[["GameState"], str]
    condition: Callable[["GameState"], bool] = field(default_factory=lambda: lambda _: True)


@dataclass
class Event:
    key: str
    title: str
    description: str
    choices: list[EventChoice]          # empty = automatic (no player input)
    weight: int = 10
    condition: Callable[["GameState"], bool] = field(default_factory=lambda: lambda _: True)
    is_overnight: bool = False
    auto_effect: Callable[["GameState"], str] | None = None

    def available_choices(self, state: "GameState") -> list[EventChoice]:
        """Return only choices whose condition is met in the current state."""
        return [c for c in self.choices if c.condition(state)]

    @property
    def is_automatic(self) -> bool:
        return not self.choices and self.auto_effect is not None
