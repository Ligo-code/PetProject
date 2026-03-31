"""
Integration tests for core game flow.
Tests full turn cycles: action → tick_day → check_game_status.
No mocking of game internals — these test real state transitions.
"""

from silicon_valley_trail.models.game_state import GameState
from silicon_valley_trail.models.location import LOCATIONS
from silicon_valley_trail.engine.actions import (
    travel, fix_bugs, knowledge_share, buy_supplies,
    TRAVEL_COFFEE_COST, FIX_BUGS_BASE, FIX_BUGS_BACKEND_BONUS,
)


# ---------------------------------------------------------------------------
# Full turn cycle
# ---------------------------------------------------------------------------

class TestTurnCycle:
    def test_travel_advances_location_and_costs_coffee(self):
        state = GameState()
        coffee_before = state.coffee
        travel(state)
        state.tick_day()

        assert state.current_location_index == 1
        assert state.day == 2
        assert state.coffee == coffee_before - TRAVEL_COFFEE_COST - state.DAILY_COFFEE_DRAIN

    def test_tick_day_applies_passive_drain(self):
        state = GameState(coffee=20)
        state.tick_day()
        assert state.coffee == 20 - state.DAILY_COFFEE_DRAIN

    def test_tick_day_grows_bugs_by_exactly_1_on_interval(self):
        state = GameState(bugs=0)
        for _ in range(state.BUG_GROWTH_INTERVAL):
            state.tick_day()
        assert state.bugs == 1

    def test_morale_drains_when_coffee_low(self):
        state = GameState(coffee=5, morale=80)  # below LOW_COFFEE_THRESHOLD
        state.tick_day()
        assert state.morale == 79

    def test_morale_stable_when_coffee_sufficient(self):
        state = GameState(coffee=30, morale=80)
        state.tick_day()
        assert state.morale == 80


# ---------------------------------------------------------------------------
# Knowledge share → fix bugs combo
# ---------------------------------------------------------------------------

class TestKnowledgeShareCombo:
    def test_knowledge_share_then_fix_bugs_doubles_reduction(self):
        state = GameState(bugs=20, coffee=40, morale=80)
        knowledge_share(state)
        assert state.next_fix_bugs_boosted

        bugs_before = state.bugs
        fix_bugs(state)

        assert not state.next_fix_bugs_boosted
        expected_reduction = (FIX_BUGS_BASE + FIX_BUGS_BACKEND_BONUS) * 2
        assert state.bugs == max(0, bugs_before - expected_reduction)


# ---------------------------------------------------------------------------
# Win / lose via check_game_status
# ---------------------------------------------------------------------------

class TestGameStatusIntegration:
    def test_win_when_reaching_final_location(self):
        state = GameState()
        state.current_location_index = len(LOCATIONS) - 1
        state.check_game_status()
        assert state.won
        assert state.game_over

    def test_win_takes_priority_over_simultaneous_lose(self):
        """If player reaches SF on the same turn cash hits 0 — win should take priority."""
        state = GameState(cash=0)
        state.current_location_index = len(LOCATIONS) - 1
        state.check_game_status()
        assert state.won
        assert not state.lose_reason

    def test_full_lose_cycle_no_cash(self):
        state = GameState(cash=100)
        state.apply_effects(cash=-100)
        state.check_game_status()
        assert state.game_over
        assert not state.won
        assert "cash" in state.lose_reason.lower()

    def test_reaching_final_location_sets_win(self):
        """Advancing location index to the last stop triggers win condition."""
        state = GameState()
        state.current_location_index = len(LOCATIONS) - 1
        state.check_game_status()
        assert state.won

    def test_travel_cannot_go_past_final_location(self):
        """travel() should never push location index beyond the last stop."""
        state = GameState(coffee=999)
        state.current_location_index = len(LOCATIONS) - 1
        travel(state)
        assert state.current_location_index == len(LOCATIONS) - 1

    def test_coffee_drought_game_over_after_two_days(self):
        """Two consecutive days with coffee=0 triggers game over."""
        state = GameState(coffee=0)
        state.tick_day()
        assert state.days_without_coffee == 1
        assert not state.game_over
        state.tick_day()
        assert state.days_without_coffee == 2
        state.check_game_status()
        assert state.game_over
        assert not state.won

    def test_burnout_triggers_inactive_and_lose_if_all_gone(self):
        """If all non-backend members burn out and backend goes inactive, game ends."""
        state = GameState()
        for m in state.team:
            m.is_active = False
            m.inactive_days_remaining = -1  # permanently gone
        state.check_game_status()
        assert state.game_over
        assert not state.won

    def test_buy_supplies_clamps_at_resource_cap(self):
        """buy_supplies with near-full morale returns actual delta, not nominal."""
        state = GameState(cash=10_000, coffee=10, morale=95)
        deltas = state.apply_effects(morale=10, coffee=30, cash=-3_000)
        assert state.morale == 100             # clamped
        assert deltas["morale"] == 5          # actual gain, not 10
        assert deltas["coffee"] == 30         # no cap on coffee
