"""
Event system for Silicon Valley Trail.

Structure:
- EventChoice: one option the player can pick (text + effect + optional condition)
- Event: a game event with 1+ choices (or automatic if choices is empty)
- EventRegistry: holds all events, picks weighted-random from a location pool

Effect functions take GameState, mutate it in place, return a message string.
"""

import random
from dataclasses import dataclass, field
from typing import Callable

from ..models.game_state import GameState
from ..models.team import TeamRole

# Days a team member is on leave after burnout (temporary)
BURNOUT_LEAVE_DAYS = 3
# Sentinel: member left the team permanently (poached, not coming back)
PERMANENT_LEAVE = -1


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class EventChoice:
    text: str
    effect: Callable[[GameState], str]
    condition: Callable[[GameState], bool] = field(default_factory=lambda: lambda _: True)


@dataclass
class Event:
    key: str
    title: str
    description: str
    choices: list[EventChoice]          # empty = automatic (no player input)
    weight: int = 10                    # higher = more common in weighted draw
    condition: Callable[[GameState], bool] = field(default_factory=lambda: lambda _: True)
    is_overnight: bool = False          # triggered after "rest" action
    auto_effect: Callable[[GameState], str] | None = None  # used when choices is empty

    def available_choices(self, state: GameState) -> list[EventChoice]:
        """Return only choices whose condition is met in the current state."""
        return [c for c in self.choices if c.condition(state)]

    @property
    def is_automatic(self) -> bool:
        return not self.choices and self.auto_effect is not None


# ---------------------------------------------------------------------------
# Effect helpers
# ---------------------------------------------------------------------------

def _poachable_member(state: GameState):
    """Return a random active member that can be poached, or None."""
    targets = [m for m in state.active_team if m.can_be_poached(state.hype)]
    return random.choice(targets) if targets else None


# ---------------------------------------------------------------------------
# Effect functions — vc_pitch
# ---------------------------------------------------------------------------

def _vc_pitch_accept(state: GameState) -> str:
    state.apply_effects(cash=-2_000, coffee=-10)
    if state.hype >= 60:
        state.apply_effects(cash=10_000, hype=15)
        return "Great pitch! They want to set up a follow-up. +$10,000 cash, +15 hype."
    else:
        state.apply_effects(cash=3_000, hype=5)
        return "Decent interest. They'll think about it. +$3,000 cash."


def _vc_pitch_decline(state: GameState) -> str:
    return "You decided you're not ready yet. Maybe next time."


# ---------------------------------------------------------------------------
# Effect functions — hackathon
# ---------------------------------------------------------------------------

def _hackathon_enter(state: GameState) -> str:
    state.apply_effects(coffee=-15, morale=-10)
    if state.has_role_active(TeamRole.PRODUCT) and state.morale >= 50:
        state.apply_effects(cash=5_000, hype=30)
        state.hackathon_won = True
        return "You won the hackathon! +$5,000, +30 hype. The team is exhausted but proud."
    else:
        state.apply_effects(hype=10)
        return "Good effort — you didn't place, but made some connections. +10 hype."


def _hackathon_skip(state: GameState) -> str:
    return "You skipped the hackathon. The team gets a quiet day."


# ---------------------------------------------------------------------------
# Effect functions — press_coverage
# ---------------------------------------------------------------------------

def _press_accept(state: GameState) -> str:
    state.apply_effects(hype=20)
    return "Great interview! The article goes live tomorrow. +20 hype."


def _press_decline(state: GameState) -> str:
    return "Too busy right now. You pass on the interview."


# ---------------------------------------------------------------------------
# Effect functions — angel_investor
# ---------------------------------------------------------------------------

def _angel_chat(state: GameState) -> str:
    state.apply_effects(cash=8_000, hype=10)
    return "Turns out she just sold her last startup. She's in. +$8,000, +10 hype."


def _angel_ignore(state: GameState) -> str:
    return "You keep your head down. Probably just another tourist."


# ---------------------------------------------------------------------------
# Effect functions — server_bill
# ---------------------------------------------------------------------------

def _server_pay(state: GameState) -> str:
    state.apply_effects(cash=-2_000)
    return "Ouch. Paid. Someone set up a billing alert this time. -$2,000."


def _server_dispute(state: GameState) -> str:
    if random.random() < 0.5:
        return "Dispute accepted! No charge this time. Lucky."
    else:
        state.apply_effects(cash=-4_000, bugs=5)
        return "Dispute denied. Late fee added. The stress introduced new bugs. -$4,000, +5 bugs."


# ---------------------------------------------------------------------------
# Effect functions — idea_leaked
# ---------------------------------------------------------------------------

def _idea_pivot(state: GameState) -> str:
    state.apply_effects(cash=-1_500, bugs=5)
    state.apply_effects(hype=10)
    return "You pivot the feature fast. Differentiated! -$1,500, +5 bugs, +10 hype."


def _idea_ignore(state: GameState) -> str:
    state.apply_effects(hype=-15)
    return "You ignore it. The narrative shifts to them. -15 hype."


# ---------------------------------------------------------------------------
# Effect functions — key_dev_poached
# ---------------------------------------------------------------------------

def _poach_counter_offer(state: GameState) -> str:
    member = _poachable_member(state)
    if member is None:
        return "Somehow nobody's being poached today."
    state.apply_effects(cash=-5_000)
    member.restore_morale(20)
    return (
        f"{member.name} almost left for a FAANG offer. "
        f"You matched it. -$5,000. {member.name} stays."
    )


def _poach_let_go(state: GameState) -> str:
    member = _poachable_member(state)
    if member is None:
        return "Somehow nobody left today."
    member.is_active = False
    member.inactive_days_remaining = PERMANENT_LEAVE
    state.apply_effects(morale=-20)
    return (
        f"{member.name}: \"I got an offer I can't refuse. I'll miss you all.\"\n"
        f"{member.name} has left the team. -20 morale."
    )


# ---------------------------------------------------------------------------
# Effect functions — burnout_warning
# ---------------------------------------------------------------------------

def _burnout_wellness_day(state: GameState) -> str:
    state.apply_effects(cash=-1_000, morale=20)
    return "Team takes a wellness day. Everyone breathes. -$1,000, +20 morale."


def _burnout_push_through(state: GameState) -> str:
    if random.random() < 0.5:
        return "Somehow the team holds together. For now."
    else:
        at_risk = [m for m in state.active_team if m.is_burnout_risk()]
        if at_risk:
            victim = random.choice(at_risk)
            victim.is_active = False
            victim.inactive_days_remaining = BURNOUT_LEAVE_DAYS
            return (
                f"{victim.name} hit a wall and needs a few days off. "
                f"{victim.name} is on leave for 3 days."
            )
        return "The team is tired but nobody breaks. Barely."


# ---------------------------------------------------------------------------
# Effect functions — coffee_shortage
# ---------------------------------------------------------------------------

def _coffee_buy_machine(state: GameState) -> str:
    state.apply_effects(cash=-500)
    return "New machine installed. Crisis averted. -$500."


def _coffee_instant(state: GameState) -> str:
    state.apply_effects(morale=-15)
    return "Instant coffee. The team is disappointed. -15 morale."


# ---------------------------------------------------------------------------
# Effect functions — conference_invite
# ---------------------------------------------------------------------------

def _conference_attend(state: GameState) -> str:
    state.apply_effects(cash=-500, morale=15, hype=10)
    return "Inspiring talks, new connections. -$500, +15 morale, +10 hype."


def _conference_skip(state: GameState) -> str:
    return "Too much on your plate. You skip it."


# ---------------------------------------------------------------------------
# Effect functions — automatic events
# ---------------------------------------------------------------------------

def _tech_debt_auto(state: GameState) -> str:
    state.apply_effects(bugs=5, morale=-10)
    return "Tech debt is biting back. +5 bugs, -10 morale."


def _hype_spike_auto(state: GameState) -> str:
    keyword = state.hn_trending_keyword or "your startup"
    state.apply_effects(hype=25, morale=5)
    return f"\"{keyword}\" is trending on Hacker News. The internet found you. +25 hype, +5 morale."


def _aircraft_supply_drop_auto(state: GameState) -> str:
    state.apply_effects(coffee=20, cash=2_000)
    return "A supply drop lands nearby — someone arranged a delivery. +20 coffee, +$2,000."


# ---------------------------------------------------------------------------
# Overnight effect functions
# ---------------------------------------------------------------------------

def _overnight_repo_hijack(state: GameState) -> str:
    state.apply_effects(hype=-20)
    return (
        "While your team slept...\n"
        "Someone forked your repo and published it as their own. -20 hype."
    )


def _overnight_server_bill(state: GameState) -> str:
    state.apply_effects(cash=-1_500)
    return (
        "While your team slept...\n"
        "A dev instance nobody shut down ran all night. -$1,500."
    )


def _overnight_laptop_stolen(state: GameState) -> str:
    state.apply_effects(cash=-2_500, bugs=3)
    return (
        "While your team slept...\n"
        "A laptop was stolen at the café where someone stayed late. -$2,500, +3 bugs."
    )


# ---------------------------------------------------------------------------
# Event registry
# ---------------------------------------------------------------------------

class EventRegistry:
    def __init__(self) -> None:
        self._events: dict[str, Event] = {}
        self._register_all()

    def _register(self, event: Event) -> None:
        self._events[event.key] = event

    def get(self, key: str) -> Event | None:
        return self._events.get(key)

    def pick_from_pool(self, pool: list[str], state: GameState) -> Event | None:
        """Pick a weighted-random eligible event from a location's event pool."""
        eligible = [
            self._events[key]
            for key in pool
            if key in self._events and self._events[key].condition(state)
        ]
        if not eligible:
            return None
        weights = [e.weight for e in eligible]
        return random.choices(eligible, weights=weights, k=1)[0]

    def pick_overnight(self, state: GameState) -> Event | None:
        """Pick a random overnight event."""
        candidates = [
            e for e in self._events.values()
            if e.is_overnight and e.condition(state)
        ]
        if not candidates:
            return None
        weights = [e.weight for e in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def _register_all(self) -> None:
        # --- Regular events ---

        self._register(Event(
            key="vc_pitch",
            title="VC Pitch Opportunity",
            description="A VC firm on Sand Hill Road wants to hear your pitch!",
            choices=[
                EventChoice("Prepare and pitch ($2,000, -10 coffee)", _vc_pitch_accept),
                EventChoice("Not ready yet, decline", _vc_pitch_decline),
            ],
            weight=8,
        ))

        self._register(Event(
            key="hackathon",
            title="Local Hackathon!",
            description="A 48-hour hackathon is happening this weekend.",
            choices=[
                EventChoice("Enter the hackathon (-15 coffee, -10 morale)", _hackathon_enter),
                EventChoice("Skip it, focus on the journey", _hackathon_skip),
            ],
            weight=5,
            condition=lambda s: s.has_role_active(TeamRole.PRODUCT),
        ))

        self._register(Event(
            key="press_coverage",
            title="Tech Blog Wants an Interview",
            description="A popular tech blog reached out. Could be good exposure.",
            choices=[
                EventChoice("Do the interview (free)", _press_accept),
                EventChoice("Too busy right now", _press_decline),
            ],
            weight=9,
        ))

        self._register(Event(
            key="angel_investor",
            title="Angel Investor at the Coffee Shop",
            description="Someone at the next table is clearly reading your pitch deck over your shoulder.",
            choices=[
                EventChoice("Strike up a conversation", _angel_chat),
                EventChoice("Ignore, probably a tourist", _angel_ignore),
            ],
            weight=7,
        ))

        self._register(Event(
            key="server_bill",
            title="Surprise Cloud Bill!",
            description="Someone left a dev instance running all week.",
            choices=[
                EventChoice("Pay the bill (-$2,000)", _server_pay),
                EventChoice("Dispute it (50/50: free or -$4,000 +5 bugs)", _server_dispute),
            ],
            weight=10,
        ))

        self._register(Event(
            key="idea_leaked",
            title="Competitor Copied Your Idea",
            description="A well-funded startup just announced a suspiciously familiar product.",
            choices=[
                EventChoice("Pivot the feature fast (-$1,500, +5 bugs, +10 hype)", _idea_pivot),
                EventChoice("Ignore it (-15 hype)", _idea_ignore),
            ],
            weight=7,
        ))

        self._register(Event(
            key="key_dev_poached",
            title="FAANG Offer Incoming",
            description="One of your team got a recruiter DM last night. Now there's an offer on the table.",
            choices=[
                EventChoice("Counter-offer to keep them (-$5,000)", _poach_counter_offer),
                EventChoice("Let them go (-20 morale)", _poach_let_go),
            ],
            weight=4,
            condition=lambda s: any(m.can_be_poached(s.hype) for m in s.active_team),
        ))

        self._register(Event(
            key="burnout_warning",
            title="Burnout Warning",
            description="The team is running on empty. Someone's about to hit a wall.",
            choices=[
                EventChoice("Take a wellness day (-$1,000, +20 morale)", _burnout_wellness_day),
                EventChoice("Push through (50/50: fine or someone goes on leave)", _burnout_push_through),
            ],
            weight=6,
            condition=lambda s: any(m.is_burnout_risk() for m in s.active_team),
        ))

        self._register(Event(
            key="coffee_shortage",
            title="Coffee Machine Broke",
            description="The office coffee machine made a terrible sound and stopped working.",
            choices=[
                EventChoice("Buy a new one (-$500)", _coffee_buy_machine),
                EventChoice("Switch to instant coffee (-15 morale)", _coffee_instant),
            ],
            weight=9,
        ))

        self._register(Event(
            key="conference_invite",
            title="Conference Invite",
            description="You got a last-minute invite to speak at a local tech meetup.",
            choices=[
                EventChoice("Attend (-$500, +15 morale, +10 hype)", _conference_attend),
                EventChoice("Skip it", _conference_skip),
            ],
            weight=7,
        ))

        # --- Automatic events (no choices) ---

        self._register(Event(
            key="tech_debt_crisis",
            title="Tech Debt Biting Back",
            description="The shortcuts from last sprint are catching up with you.",
            choices=[],
            weight=8,
            condition=lambda s: s.bugs >= 10,
            auto_effect=_tech_debt_auto,
        ))

        self._register(Event(
            key="hype_spike",
            title="You're on the Front Page of HN!",
            description="Someone posted about your startup and it took off.",
            choices=[],
            weight=10,
            condition=lambda s: s.hn_trending_keyword is not None,
            auto_effect=_hype_spike_auto,
        ))

        self._register(Event(
            key="aircraft_supply_drop",
            title="Supply Drop!",
            description="A nearby aircraft delivered supplies arranged by a remote advisor.",
            choices=[],
            weight=5,
            auto_effect=_aircraft_supply_drop_auto,
        ))

        # --- Overnight events ---

        self._register(Event(
            key="overnight_repo_hijack",
            title="Repo Hijacked",
            description="",
            choices=[],
            weight=6,
            is_overnight=True,
            auto_effect=_overnight_repo_hijack,
        ))

        self._register(Event(
            key="overnight_server_bill",
            title="Overnight Server Bill",
            description="",
            choices=[],
            weight=8,
            is_overnight=True,
            auto_effect=_overnight_server_bill,
        ))

        self._register(Event(
            key="overnight_laptop_stolen",
            title="Laptop Stolen",
            description="",
            choices=[],
            weight=5,
            is_overnight=True,
            auto_effect=_overnight_laptop_stolen,
        ))
