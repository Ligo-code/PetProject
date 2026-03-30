"""
Tests for player actions.
Focus: deterministic effects, role bonuses, guard conditions.
"""

import pytest

from silicon_valley_trail.models.game_state import GameState
from silicon_valley_trail.models.team import TeamRole
from silicon_valley_trail.engine.actions import (
    fix_bugs,
    marketing_push,
    knowledge_share,
    buy_supplies,
    rest,
    FIX_BUGS_BASE,
    FIX_BUGS_BACKEND_BONUS,
    FIX_BUGS_COFFEE_COST,
    MARKETING_CASH_BASE,
    MARKETING_HYPE_BASE,
    MARKETING_HYPE_FRONTEND_BONUS,
    MARKETING_HN_BONUS,
    SUPPLIES_CASH_COST,
    SUPPLIES_COFFEE_GAIN,
    REST_MORALE_RESTORE,
    REST_PRODUCT_MORALE_BONUS,
    KNOWLEDGE_SHARE_MORALE_RESTORE,
)


def make_state(**kwargs) -> GameState:
    return GameState(**kwargs)


def deactivate_role(state: GameState, role: TeamRole) -> None:
    for m in state.team:
        if m.role == role:
            m.is_active = False


# ---------------------------------------------------------------------------
# fix_bugs
# ---------------------------------------------------------------------------

class TestFixBugs:
    def test_base_reduction_without_backend(self):
        state = make_state(bugs=10, coffee=20, morale=50)
        deactivate_role(state, TeamRole.BACKEND)
        fix_bugs(state)
        assert state.bugs == 10 - FIX_BUGS_BASE

    def test_backend_bonus_increases_reduction(self):
        state = make_state(bugs=10, coffee=20, morale=50)
        fix_bugs(state)
        assert state.bugs == 10 - (FIX_BUGS_BASE + FIX_BUGS_BACKEND_BONUS)

    def test_costs_coffee(self):
        state = make_state(bugs=10, coffee=20, morale=50)
        fix_bugs(state)
        assert state.coffee == 20 - FIX_BUGS_COFFEE_COST

    def test_costs_morale(self):
        state = make_state(bugs=10, coffee=20, morale=50)
        fix_bugs(state)
        assert state.morale == 45  # -5

    def test_knowledge_share_boost_doubles_reduction(self):
        state = make_state(bugs=16, coffee=20, morale=50, next_fix_bugs_boosted=True)
        fix_bugs(state)
        expected = 16 - (FIX_BUGS_BASE + FIX_BUGS_BACKEND_BONUS) * 2
        assert state.bugs == expected

    def test_boost_flag_reset_after_use(self):
        state = make_state(bugs=10, coffee=20, morale=50, next_fix_bugs_boosted=True)
        fix_bugs(state)
        assert not state.next_fix_bugs_boosted

    def test_bugs_do_not_go_below_zero(self):
        state = make_state(bugs=2, coffee=20, morale=50)
        fix_bugs(state)
        assert state.bugs == 0


# ---------------------------------------------------------------------------
# marketing_push
# ---------------------------------------------------------------------------

class TestMarketingPush:
    def test_base_hype_and_cost_without_frontend(self):
        state = make_state(cash=10_000, hype=30)
        deactivate_role(state, TeamRole.FRONTEND)
        marketing_push(state)
        assert state.hype == 30 + MARKETING_HYPE_BASE
        assert state.cash == 10_000 - MARKETING_CASH_BASE

    def test_frontend_adds_hype_bonus_and_discount(self):
        state = make_state(cash=10_000, hype=30)
        marketing_push(state)
        assert state.hype == 30 + MARKETING_HYPE_BASE + MARKETING_HYPE_FRONTEND_BONUS
        expected_cost = int(MARKETING_CASH_BASE * 0.8)
        assert state.cash == 10_000 - expected_cost

    def test_hn_trending_adds_extra_hype(self):
        state = make_state(cash=10_000, hype=30, hn_trending_keyword="AI")
        deactivate_role(state, TeamRole.FRONTEND)
        marketing_push(state)
        assert state.hype == 30 + MARKETING_HYPE_BASE + MARKETING_HN_BONUS

    def test_hype_capped_at_100(self):
        state = make_state(cash=10_000, hype=95)
        marketing_push(state)
        assert state.hype == 100


# ---------------------------------------------------------------------------
# knowledge_share
# ---------------------------------------------------------------------------

class TestKnowledgeShare:
    def test_sets_boost_flag(self):
        state = make_state()
        knowledge_share(state)
        assert state.next_fix_bugs_boosted

    def test_restores_morale(self):
        state = make_state(morale=60)
        knowledge_share(state)
        assert state.morale == 60 + KNOWLEDGE_SHARE_MORALE_RESTORE

    def test_unavailable_without_product(self):
        state = make_state()
        deactivate_role(state, TeamRole.PRODUCT)
        msg = knowledge_share(state)
        assert not state.next_fix_bugs_boosted
        assert "not available" in msg.lower()


# ---------------------------------------------------------------------------
# buy_supplies
# ---------------------------------------------------------------------------

class TestBuySupplies:
    def test_increases_coffee(self):
        state = make_state(cash=10_000, coffee=10)
        buy_supplies(state)
        assert state.coffee == 10 + SUPPLIES_COFFEE_GAIN

    def test_costs_cash(self):
        state = make_state(cash=10_000)
        buy_supplies(state)
        assert state.cash == 10_000 - SUPPLIES_CASH_COST

    def test_guard_when_insufficient_cash(self):
        state = make_state(cash=100, coffee=10)
        msg = buy_supplies(state)
        assert state.coffee == 10           # unchanged
        assert state.cash == 100            # unchanged
        assert "not enough" in msg.lower()


# ---------------------------------------------------------------------------
# rest
# ---------------------------------------------------------------------------

class TestRest:
    def test_restores_base_morale(self):
        state = make_state(morale=50, coffee=20)
        deactivate_role(state, TeamRole.PRODUCT)
        rest(state)
        assert state.morale == 50 + REST_MORALE_RESTORE

    def test_product_active_adds_morale_bonus(self):
        state = make_state(morale=50, coffee=20)
        rest(state)
        assert state.morale == 50 + REST_MORALE_RESTORE + REST_PRODUCT_MORALE_BONUS

    def test_morale_capped_at_100(self):
        state = make_state(morale=98, coffee=20)
        rest(state)
        assert state.morale == 100
