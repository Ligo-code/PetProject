from dataclasses import dataclass, field
from .team import TeamMember, TeamRole, DEFAULT_TEAM
from .location import LOCATIONS, Location
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
    def current_location(self) -> Location:
        return LOCATIONS[self.current_location_index]

    @property
    def active_team(self) -> list[TeamMember]:
        return [m for m in self.team if m.is_active]

    @property
    def progress_percent(self) -> int:
        if len(LOCATIONS) <= 1:
            return 100
        return round(self.current_location_index / (len(LOCATIONS) - 1) * 100)

    def has_role_active(self, role: TeamRole) -> bool:
        return any(m.role == role and m.is_active for m in self.team)

    # --- Resource effects ---

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

    def apply_member_morale_change(self, role: TeamRole, amount: int) -> None:
        """Apply morale change to a specific team member by role."""
        for member in self.team:
            if member.role == role:
                if amount < 0:
                    member.reduce_morale(abs(amount))
                else:
                    member.restore_morale(amount)

    def _clamp_stats(self) -> None:
        self.cash = max(0, self.cash)
        self.morale = max(0, min(100, self.morale))
        self.coffee = max(0, self.coffee)
        self.hype = max(0, min(100, self.hype))
        self.bugs = max(0, self.bugs)

    # --- Progress ---

    def advance_location(self, steps: int = 1) -> None:
        self.current_location_index = min(
            self.current_location_index + steps,
            len(LOCATIONS) - 1,
        )

    # --- Turn lifecycle ---

    def tick_day(self) -> None:
        """Advance one day. Call AFTER showing the player any messages."""
        self.day += 1
        if self.coffee == 0:
            self.days_without_coffee += 1
        else:
            self.days_without_coffee = 0
        self._tick_inactive_members()

    def _tick_inactive_members(self) -> None:
        for member in self.team:
            member.apply_inactive_day()

    # --- Win / Lose ---

    def check_lose_condition(self) -> bool:
        """Check lose conditions. Sets game_over and lose_reason if triggered."""
        if self.cash <= 0:
            self.game_over = True
            self.lose_reason = "You ran out of cash. The startup is dead."
            return True
        if self.morale <= 0:
            self.game_over = True
            self.lose_reason = "Team morale collapsed. Everyone quit."
            return True
        if self.bugs >= 20:
            self.game_over = True
            self.lose_reason = "The codebase is unrecoverable. 20 bugs. Investors ran."
            return True
        if self.days_without_coffee >= 2:
            self.game_over = True
            self.lose_reason = "Two days without coffee. The team cannot function."
            return True
        if not self.active_team:
            self.game_over = True
            self.lose_reason = "No one is left to keep the startup running."
            return True
        return False

    def check_win_condition(self) -> bool:
        """Check win condition. Sets won and game_over if triggered."""
        if self.game_over:
            return False
        if self.current_location_index >= len(LOCATIONS) - 1:
            self.won = True
            self.game_over = True
            return True
        return False

    def check_game_status(self) -> None:
        """Single call for engine: checks lose first, then win."""
        if self.check_lose_condition():
            return
        self.check_win_condition()
