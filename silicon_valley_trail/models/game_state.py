from dataclasses import dataclass, field
from .team import TeamMember, TeamRole, DEFAULT_TEAM
from .location import LOCATIONS
import copy


@dataclass
class GameState:
    # Core resources
    cash: int = 50_000
    morale: int = 100
    coffee: int = 50
    hype: int = 50
    bugs: int = 0

    # Progress
    day: int = 1
    current_location_index: int = 0
    days_without_coffee: int = 0

    # Team
    team: list[TeamMember] = field(default_factory=lambda: copy.deepcopy(DEFAULT_TEAM))

    # Flags
    game_over: bool = False
    won: bool = False
    hackathon_won: bool = False
    next_fix_bugs_boosted: bool = False

    # API data (refreshed each turn)
    weather_description: str = "Unknown"
    weather_is_rainy: bool = False
    weather_is_hot: bool = False
    hn_trending_keyword: str | None = None

    # Lose reason (set when game_over becomes True)
    lose_reason: str = ""

    # --- Properties ---

    @property
    def current_location(self):
        return LOCATIONS[self.current_location_index]

    @property
    def active_team(self) -> list[TeamMember]:
        return [m for m in self.team if m.is_active]

    @property
    def progress_percent(self) -> int:
        return round(self.current_location_index / (len(LOCATIONS) - 1) * 100)

    def has_role_active(self, role: TeamRole) -> bool:
        return any(m.role == role and m.is_active for m in self.team)

    # --- Core methods ---

    def apply_effects(
        self,
        cash: int = 0,
        morale: int = 0,
        coffee: int = 0,
        hype: int = 0,
        bugs: int = 0,
    ) -> None:
        """Single entry point for applying resource changes. Clamps after."""
        self.cash += cash
        self.morale += morale
        self.coffee += coffee
        self.hype += hype
        self.bugs += bugs
        self._clamp_stats()

    def _clamp_stats(self) -> None:
        self.cash = max(0, self.cash)
        self.morale = max(0, min(100, self.morale))
        self.coffee = max(0, self.coffee)
        self.hype = max(0, min(100, self.hype))
        self.bugs = max(0, self.bugs)

    def tick_day(self) -> None:
        """Advance one day: update coffee streak and inactive members."""
        self.day += 1
        if self.coffee == 0:
            self.days_without_coffee += 1
        else:
            self.days_without_coffee = 0
        self._tick_inactive_members()

    def _tick_inactive_members(self) -> None:
        for member in self.team:
            if not member.is_active and member.inactive_days_remaining > 0:
                member.inactive_days_remaining -= 1
                if member.inactive_days_remaining == 0:
                    member.is_active = True

    def check_lose_condition(self) -> tuple[bool, str]:
        if self.cash <= 0:
            return True, "You ran out of cash. The startup is dead."
        if self.morale <= 0:
            return True, "Team morale collapsed. Everyone quit."
        if self.bugs >= 20:
            return True, "The codebase is unrecoverable. 20 bugs. Investors ran."
        if self.days_without_coffee >= 2:
            return True, "Two days without coffee. The team cannot function."
        return False, ""
