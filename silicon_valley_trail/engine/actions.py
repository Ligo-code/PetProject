"""
Player actions for Silicon Valley Trail.

Each action is a function that takes GameState, mutates it, and returns a message string.
Actions do NOT call tick_day() — that's the game loop's responsibility.

Role bonuses applied here:
- BACKEND (Kay):   fix_bugs is 40% more effective
- FRONTEND (Hanna): marketing_push costs 20% less cash, +5 extra hype
- PRODUCT (Leo):   knowledge_share unlocks; rest restores extra morale
"""

from ..models.game_state import GameState
from ..models.team import TeamRole

fmt = GameState.format_deltas  # local shorthand

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRAVEL_COFFEE_COST = 5
TRAVEL_RAIN_MORALE_PENALTY = -10
TRAVEL_RAIN_COFFEE_PENALTY = -5
TRAVEL_HEAT_BUG_PENALTY = 1

REST_MORALE_RESTORE = 15
REST_PRODUCT_MORALE_BONUS = 5       # Leo is a great mood booster when active
REST_COFFEE_COST = 8

FIX_BUGS_BASE = 5
FIX_BUGS_BACKEND_BONUS = 3         # Kay fixes 8 bugs instead of 5
FIX_BUGS_BOOSTED_MULTIPLIER = 2    # after knowledge_share
FIX_BUGS_COFFEE_COST = 10
FIX_BUGS_MORALE_COST = -5

MARKETING_CASH_BASE = 1_500
MARKETING_CASH_FRONTEND_DISCOUNT = 0.8   # Hanna cuts cost to $1,200
MARKETING_HYPE_BASE = 20
MARKETING_HYPE_FRONTEND_BONUS = 5        # Hanna adds +5 hype on top
MARKETING_HN_BONUS = 5                   # extra hype when HN trending

KNOWLEDGE_SHARE_COFFEE_COST = 5
KNOWLEDGE_SHARE_MORALE_RESTORE = 10

SUPPLIES_CASH_COST = 3_000
SUPPLIES_COFFEE_GAIN = 30
SUPPLIES_MORALE_GAIN = 10


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def travel(state: GameState) -> str:
    """Move to the next location. Weather affects cost."""
    coffee_cost = TRAVEL_COFFEE_COST
    messages: list[str] = []

    if state.weather_is_rainy:
        coffee_cost += abs(TRAVEL_RAIN_COFFEE_PENALTY)
        state.apply_effects(morale=TRAVEL_RAIN_MORALE_PENALTY)
        messages.append("Rain slows the team down.")

    if state.weather_is_hot:
        state.apply_effects(bugs=TRAVEL_HEAT_BUG_PENALTY)
        messages.append("Heat wave — everyone is distracted.")

    deltas = state.apply_effects(coffee=-coffee_cost)
    state.advance_location()

    location = state.current_location
    messages.insert(0, f"Arrived at {location.name}! ({fmt(deltas)})")
    return "\n".join(messages)


def rest(state: GameState) -> str:
    """Rest for a day. Restore morale, consume coffee."""
    morale_gain = REST_MORALE_RESTORE
    if state.has_role_active(TeamRole.PRODUCT):
        morale_gain += REST_PRODUCT_MORALE_BONUS

    deltas = state.apply_effects(morale=morale_gain, coffee=-REST_COFFEE_COST)
    return f"The team rests. {fmt(deltas)}."


def fix_bugs(state: GameState) -> str:
    """Reduce bug count. Kay (BACKEND) is more effective."""
    reduction = FIX_BUGS_BASE
    if state.has_role_active(TeamRole.BACKEND):
        reduction += FIX_BUGS_BACKEND_BONUS

    if state.next_fix_bugs_boosted:
        reduction *= FIX_BUGS_BOOSTED_MULTIPLIER
        state.next_fix_bugs_boosted = False

    deltas = state.apply_effects(
        bugs=-reduction,
        coffee=-FIX_BUGS_COFFEE_COST,
        morale=FIX_BUGS_MORALE_COST,
    )
    return f"Bugs squashed. {fmt(deltas)}."


def marketing_push(state: GameState) -> str:
    """Run a marketing campaign. Hanna (FRONTEND) makes it cheaper and more effective."""
    cash_cost = MARKETING_CASH_BASE
    hype_gain = MARKETING_HYPE_BASE

    if state.has_role_active(TeamRole.FRONTEND):
        cash_cost = int(cash_cost * MARKETING_CASH_FRONTEND_DISCOUNT)
        hype_gain += MARKETING_HYPE_FRONTEND_BONUS

    if state.hn_trending_keyword:
        hype_gain += MARKETING_HN_BONUS

    state.apply_effects(cash=-cash_cost, hype=hype_gain)
    return (
        f"Campaign launched! +{hype_gain} hype. Cost: -${cash_cost:,}."
    )


def knowledge_share(state: GameState) -> str:
    """
    Leo (PRODUCT) runs a team learning session.
    Restores morale and boosts the next fix_bugs action.
    Only available when PRODUCT member is active.
    """
    if not state.has_role_active(TeamRole.PRODUCT):
        return "Leo is not available right now. Knowledge share cancelled."

    state.apply_effects(morale=KNOWLEDGE_SHARE_MORALE_RESTORE, coffee=-KNOWLEDGE_SHARE_COFFEE_COST)
    state.next_fix_bugs_boosted = True
    return (
        f"Leo runs a learning session. "
        f"+{KNOWLEDGE_SHARE_MORALE_RESTORE} morale, -{KNOWLEDGE_SHARE_COFFEE_COST} coffee. "
        f"Next bug fix will be twice as effective."
    )


def buy_supplies(state: GameState) -> str:
    """Spend cash to restock coffee and boost morale."""
    if state.cash < SUPPLIES_CASH_COST:
        return f"Not enough cash. You need ${SUPPLIES_CASH_COST:,}."

    deltas = state.apply_effects(
        cash=-SUPPLIES_CASH_COST,
        coffee=SUPPLIES_COFFEE_GAIN,
        morale=SUPPLIES_MORALE_GAIN,
    )
    return f"Supplies restocked. {GameState.format_deltas(deltas)}."
