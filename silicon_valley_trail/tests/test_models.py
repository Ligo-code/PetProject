"""
Tests for GameState and TeamMember core logic.
Covers: clamping, morale transitions, burnout, active_team, win/lose conditions.
"""

import copy
import pytest

from silicon_valley_trail.models.game_state import GameState
from silicon_valley_trail.models.team import TeamMember, TeamRole, DEFAULT_TEAM
from silicon_valley_trail.engine.events import PERMANENT_LEAVE, BURNOUT_LEAVE_DAYS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(**kwargs) -> GameState:
    """Create a GameState with defaults overridden by kwargs."""
    return GameState(**kwargs)


def active_member(role: TeamRole) -> TeamMember:
    return next(m for m in copy.deepcopy(DEFAULT_TEAM) if m.role == role)


# ---------------------------------------------------------------------------
# GameState — clamping
# ---------------------------------------------------------------------------

class TestClamping:
    def test_morale_does_not_go_below_zero(self):
        state = make_state(morale=5)
        state.apply_effects(morale=-100)
        assert state.morale == 0

    def test_morale_does_not_exceed_100(self):
        state = make_state(morale=90)
        state.apply_effects(morale=50)
        assert state.morale == 100

    def test_cash_does_not_go_below_zero(self):
        state = make_state(cash=100)
        state.apply_effects(cash=-999)
        assert state.cash == 0

    def test_hype_clamped_between_0_and_100(self):
        state = make_state(hype=95)
        state.apply_effects(hype=20)
        assert state.hype == 100

    def test_bugs_do_not_go_below_zero(self):
        state = make_state(bugs=2)
        state.apply_effects(bugs=-10)
        assert state.bugs == 0


# ---------------------------------------------------------------------------
# TeamMember — morale & burnout
# ---------------------------------------------------------------------------

class TestTeamMemberMorale:
    def test_reduce_morale_clamps_at_zero(self):
        m = active_member(TeamRole.FRONTEND)
        m.reduce_morale(200)
        assert m.morale == 0

    def test_restore_morale_clamps_at_100(self):
        m = active_member(TeamRole.FRONTEND)
        m.morale = 80
        m.restore_morale(50)
        assert m.morale == 100

    def test_product_burns_out_at_or_below_25(self):
        m = active_member(TeamRole.PRODUCT)
        m.morale = 30
        m.reduce_morale(10)  # lands at 20, triggers burnout
        assert not m.is_active
        assert m.inactive_days_remaining == BURNOUT_LEAVE_DAYS

    def test_frontend_burns_out_at_or_below_10(self):
        m = active_member(TeamRole.FRONTEND)
        m.morale = 15
        m.reduce_morale(10)  # lands at 5, triggers burnout
        assert not m.is_active

    def test_backend_never_burns_out(self):
        m = active_member(TeamRole.BACKEND)
        m.reduce_morale(200)  # morale hits 0
        assert m.is_active  # should_burnout returns False for BACKEND

    def test_restore_morale_reactivates_when_leave_timer_expired(self):
        # Leave timer must reach 0 before restore_morale can reactivate
        m = active_member(TeamRole.FRONTEND)
        m.is_active = False
        m.inactive_days_remaining = 0
        m.restore_morale(30)
        assert m.is_active

    def test_restore_morale_does_not_reactivate_while_on_leave(self):
        # If inactive_days_remaining > 0, the timer takes priority
        m = active_member(TeamRole.FRONTEND)
        m.is_active = False
        m.inactive_days_remaining = 1
        m.restore_morale(30)
        assert not m.is_active  # still on leave, timer hasn't expired

    def test_apply_inactive_day_counts_down(self):
        m = active_member(TeamRole.FRONTEND)
        m.is_active = False
        m.inactive_days_remaining = 2
        m.apply_inactive_day()
        assert m.inactive_days_remaining == 1
        assert not m.is_active

    def test_apply_inactive_day_reactivates_at_zero(self):
        m = active_member(TeamRole.FRONTEND)
        m.is_active = False
        m.morale = 50
        m.inactive_days_remaining = 1
        m.apply_inactive_day()
        assert m.is_active

    def test_apply_inactive_day_skips_permanent_leave(self):
        m = active_member(TeamRole.PRODUCT)
        m.is_active = False
        m.inactive_days_remaining = PERMANENT_LEAVE
        m.apply_inactive_day()
        assert m.inactive_days_remaining == PERMANENT_LEAVE
        assert not m.is_active


# ---------------------------------------------------------------------------
# TeamMember — poaching logic
# ---------------------------------------------------------------------------

class TestPoaching:
    def test_backend_cannot_be_poached(self):
        m = active_member(TeamRole.BACKEND)
        assert not m.can_be_poached(hype=100)

    def test_frontend_can_always_be_poached(self):
        m = active_member(TeamRole.FRONTEND)
        assert m.can_be_poached(hype=0)

    def test_product_poached_only_when_hype_above_70(self):
        m = active_member(TeamRole.PRODUCT)
        assert not m.can_be_poached(hype=70)
        assert m.can_be_poached(hype=71)


# ---------------------------------------------------------------------------
# GameState — team queries
# ---------------------------------------------------------------------------

class TestTeamQueries:
    def test_has_role_active_true(self):
        state = make_state()
        assert state.has_role_active(TeamRole.BACKEND)

    def test_has_role_active_false_when_inactive(self):
        state = make_state()
        kay = next(m for m in state.team if m.role == TeamRole.BACKEND)
        kay.is_active = False
        assert not state.has_role_active(TeamRole.BACKEND)

    def test_active_team_excludes_inactive_members(self):
        state = make_state()
        state.team[1].is_active = False  # Hanna
        assert len(state.active_team) == 2

    def test_progress_percent_at_start(self):
        state = make_state()
        assert state.progress_percent == 0

    def test_progress_percent_at_end(self):
        from silicon_valley_trail.models.location import LOCATIONS
        state = make_state(current_location_index=len(LOCATIONS) - 1)
        assert state.progress_percent == 100


# ---------------------------------------------------------------------------
# GameState — win / lose
# ---------------------------------------------------------------------------

class TestWinLose:
    def test_lose_on_zero_cash(self):
        state = make_state(cash=0)
        assert state.check_lose_condition()
        assert "cash" in state.lose_reason.lower()

    def test_lose_on_zero_morale(self):
        state = make_state(morale=0)
        assert state.check_lose_condition()

    def test_lose_on_too_many_bugs(self):
        state = make_state(bugs=20)
        assert state.check_lose_condition()

    def test_lose_on_coffee_drought(self):
        state = make_state(days_without_coffee=2)
        assert state.check_lose_condition()

    def test_lose_when_no_active_team(self):
        state = make_state()
        for m in state.team:
            m.is_active = False
        assert state.check_lose_condition()

    def test_no_loss_with_healthy_state(self):
        state = make_state()
        assert not state.check_lose_condition()

    def test_win_at_final_location(self):
        from silicon_valley_trail.models.location import LOCATIONS
        state = make_state(current_location_index=len(LOCATIONS) - 1)
        assert state.check_win_condition()
        assert state.won
        assert state.game_over

    def test_win_does_not_trigger_if_already_lost(self):
        from silicon_valley_trail.models.location import LOCATIONS
        state = make_state(
            current_location_index=len(LOCATIONS) - 1,
            game_over=True,
            won=False,
        )
        result = state.check_win_condition()
        assert not result
        assert not state.won

    def test_tick_day_increments_coffee_drought(self):
        state = make_state(coffee=0, days_without_coffee=0)
        state.tick_day()
        assert state.days_without_coffee == 1

    def test_tick_day_resets_coffee_drought_when_coffee_available(self):
        state = make_state(coffee=10, days_without_coffee=1)
        state.tick_day()
        assert state.days_without_coffee == 0
