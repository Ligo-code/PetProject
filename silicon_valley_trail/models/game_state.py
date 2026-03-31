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
    cloud_bill_fixed: bool = False  # server_bill event becomes unavailable after paying

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

    RESOURCE_FIELDS = ("cash", "morale", "coffee", "hype", "bugs")

    def apply_effects(
        self,
        cash: int = 0,
        morale: int = 0,
        coffee: int = 0,
        hype: int = 0,
        bugs: int = 0,
    ) -> dict[str, int]:
        """
        Apply resource changes, clamp, and return actual deltas.
        Only resource fields are tracked — not flags or progress fields.
        Zero-delta fields are included (caller decides whether to show them).
        """
        before = {f: getattr(self, f) for f in self.RESOURCE_FIELDS}
        self.cash += cash
        self.morale += morale
        self.coffee += coffee
        self.hype += hype
        self.bugs += bugs
        self._clamp_stats()
        return {f: getattr(self, f) - before[f] for f in self.RESOURCE_FIELDS}

    @staticmethod
    def format_deltas(deltas: dict[str, int]) -> str:
        """Return a human-readable string of non-zero resource changes."""
        parts = []
        for field, delta in deltas.items():
            if delta == 0:
                continue
            sign = "+" if delta > 0 else ""
            if field == "cash":
                parts.append(f"{sign}${delta:,}")
            else:
                parts.append(f"{sign}{delta} {field}")
        return ", ".join(parts) if parts else "no change"

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

    DAILY_COFFEE_DRAIN = 1      # passive coffee consumption per day
    BUG_GROWTH_INTERVAL = 3    # bugs grow by 1 every N days if not fixed
    LOW_COFFEE_THRESHOLD = 15  # below this, team morale starts to slip

    def tick_day(self) -> None:
        """Advance one day. Call AFTER showing the player any messages."""
        self.day += 1

        # Passive coffee drain
        self.coffee = max(0, self.coffee - self.DAILY_COFFEE_DRAIN)

        if self.coffee == 0:
            self.days_without_coffee += 1
        else:
            self.days_without_coffee = 0

        # Passive bug growth every N days
        if self.day % self.BUG_GROWTH_INTERVAL == 0:
            self.bugs += 1

        # Low coffee drains morale — team is running on fumes
        if self.coffee < self.LOW_COFFEE_THRESHOLD:
            self.morale = max(0, self.morale - 1)

        self._tick_inactive_members()

    def _tick_inactive_members(self) -> None:
        for member in self.team:
            member.apply_inactive_day()

    # --- Win / Lose ---

    def check_lose_condition(self) -> bool:
        """Check lose conditions. Sets game_over and lose_reason if triggered.

        Order reflects priority: most concrete/final cause first.
        """
        if not self.active_team:
            self.game_over = True
            self.lose_reason = "No one is left to keep the startup alive."
            return True
        if self.days_without_coffee >= 2:
            self.game_over = True
            self.lose_reason = "Two days without coffee. The team could not keep going."
            return True
        if self.morale <= 0:
            self.game_over = True
            self.lose_reason = "Team morale collapsed. Everyone quit."
            return True
        if self.cash <= 0:
            self.game_over = True
            self.lose_reason = "You ran out of cash. The startup shut down."
            return True
        if self.bugs >= 20:
            self.game_over = True
            self.lose_reason = f"The codebase became unrecoverable ({self.bugs} bugs). Investors lost confidence."
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
        """Win takes priority: if player reached SF, it's a win even on a bad day."""
        if self.check_win_condition():
            return
        self.check_lose_condition()
