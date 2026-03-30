"""
Tests for the event system.
Focus: available_choices filtering, event conditions, deterministic effects.
For randomised effects — seed or mock random.
"""

import random
from unittest.mock import patch

import pytest

from silicon_valley_trail.models.game_state import GameState
from silicon_valley_trail.models.team import TeamRole
from silicon_valley_trail.engine.events import (
    EventRegistry,
    EventChoice,
    Event,
    PERMANENT_LEAVE,
    _vc_pitch_accept,
    _vc_pitch_decline,
    _poach_counter_offer,
    _poach_let_go,
    _burnout_wellness_day,
    _tech_debt_auto,
    _hype_spike_auto,
)


def make_state(**kwargs) -> GameState:
    return GameState(**kwargs)


def deactivate_role(state: GameState, role: TeamRole) -> None:
    for m in state.team:
        if m.role == role:
            m.is_active = False


# ---------------------------------------------------------------------------
# available_choices
# ---------------------------------------------------------------------------

class TestAvailableChoices:
    def test_all_choices_returned_when_all_conditions_met(self):
        choice_a = EventChoice("A", lambda s: "a")
        choice_b = EventChoice("B", lambda s: "b")
        event = Event("e", "E", "desc", [choice_a, choice_b])
        state = make_state()
        assert event.available_choices(state) == [choice_a, choice_b]

    def test_choice_filtered_when_condition_false(self):
        choice_a = EventChoice("A", lambda s: "a")
        choice_b = EventChoice("B", lambda s: "b", condition=lambda s: False)
        event = Event("e", "E", "desc", [choice_a, choice_b])
        state = make_state()
        available = event.available_choices(state)
        assert available == [choice_a]

    def test_no_choices_when_all_conditions_false(self):
        choice = EventChoice("X", lambda s: "x", condition=lambda s: s.cash > 1_000_000)
        event = Event("e", "E", "desc", [choice])
        state = make_state(cash=0)
        assert event.available_choices(state) == []


# ---------------------------------------------------------------------------
# Event.is_automatic
# ---------------------------------------------------------------------------

class TestIsAutomatic:
    def test_automatic_event(self):
        event = Event("auto", "Auto", "", choices=[], auto_effect=lambda s: "")
        assert event.is_automatic

    def test_choice_event_is_not_automatic(self):
        choice = EventChoice("Go", lambda s: "")
        event = Event("choice", "Choice", "", choices=[choice])
        assert not event.is_automatic


# ---------------------------------------------------------------------------
# Event registry — conditions
# ---------------------------------------------------------------------------

class TestEventRegistryConditions:
    def setup_method(self):
        self.registry = EventRegistry()

    def test_key_dev_poached_requires_poachable_member(self):
        event = self.registry.get("key_dev_poached")
        state = make_state(hype=30)          # PRODUCT not poachable at hype 30
        deactivate_role(state, TeamRole.FRONTEND)  # FRONTEND gone too
        assert not event.condition(state)

    def test_key_dev_poached_available_when_frontend_active(self):
        event = self.registry.get("key_dev_poached")
        state = make_state()
        assert event.condition(state)        # Hanna (FRONTEND) always poachable

    def test_burnout_warning_requires_burnout_risk(self):
        event = self.registry.get("burnout_warning")
        state = make_state()                 # all members at 100 morale
        assert not event.condition(state)

    def test_burnout_warning_triggers_when_at_risk(self):
        event = self.registry.get("burnout_warning")
        state = make_state()
        state.team[1].morale = 5            # Hanna well below burnout threshold
        assert event.condition(state)

    def test_tech_debt_crisis_requires_bugs_above_10(self):
        event = self.registry.get("tech_debt_crisis")
        assert not event.condition(make_state(bugs=9))
        assert event.condition(make_state(bugs=10))

    def test_hype_spike_requires_trending_keyword(self):
        event = self.registry.get("hype_spike")
        assert not event.condition(make_state())
        assert event.condition(make_state(hn_trending_keyword="AI"))


# ---------------------------------------------------------------------------
# Effect functions — deterministic
# ---------------------------------------------------------------------------

class TestVcPitchEffects:
    def test_high_hype_pitch_gives_more_cash(self):
        state = make_state(cash=50_000, hype=70, coffee=30)
        _vc_pitch_accept(state)
        assert state.cash == 50_000 - 2_000 + 10_000

    def test_low_hype_pitch_gives_less_cash(self):
        state = make_state(cash=50_000, hype=40, coffee=30)
        _vc_pitch_accept(state)
        assert state.cash == 50_000 - 2_000 + 3_000

    def test_decline_changes_nothing(self):
        state = make_state(cash=50_000, hype=50)
        _vc_pitch_decline(state)
        assert state.cash == 50_000
        assert state.hype == 50


class TestPoachingEffects:
    def test_counter_offer_spends_cash_and_keeps_member(self):
        state = make_state(cash=20_000)
        _poach_counter_offer(state)
        assert state.cash == 15_000
        # Hanna (FRONTEND) should still be active
        hanna = next(m for m in state.team if m.role == TeamRole.FRONTEND)
        assert hanna.is_active

    def test_let_go_marks_member_as_permanently_gone(self):
        state = make_state()
        _poach_let_go(state)
        gone = [m for m in state.team if m.inactive_days_remaining == PERMANENT_LEAVE]
        assert len(gone) == 1

    def test_let_go_reduces_morale(self):
        state = make_state(morale=80)
        _poach_let_go(state)
        assert state.morale == 60


class TestAutoEffects:
    def test_tech_debt_adds_bugs_and_drops_morale(self):
        state = make_state(bugs=10, morale=60)
        _tech_debt_auto(state)
        assert state.bugs == 15
        assert state.morale == 50

    def test_hype_spike_increases_hype_and_morale(self):
        state = make_state(hype=40, morale=60, hn_trending_keyword="startup")
        _hype_spike_auto(state)
        assert state.hype == 65
        assert state.morale == 65


# ---------------------------------------------------------------------------
# Randomised effects — mocked
# ---------------------------------------------------------------------------

class TestRandomisedEffects:
    def test_server_dispute_lucky_path(self):
        from silicon_valley_trail.engine.events import _server_dispute
        state = make_state(cash=10_000, bugs=0)
        with patch("silicon_valley_trail.engine.events.random.random", return_value=0.3):
            msg = _server_dispute(state)
        assert state.cash == 10_000           # no charge
        assert "accepted" in msg.lower()

    def test_server_dispute_unlucky_path(self):
        from silicon_valley_trail.engine.events import _server_dispute
        state = make_state(cash=10_000, bugs=0)
        with patch("silicon_valley_trail.engine.events.random.random", return_value=0.7):
            msg = _server_dispute(state)
        assert state.cash == 6_000            # -4000
        assert state.bugs == 5

    def test_burnout_push_through_lucky(self):
        from silicon_valley_trail.engine.events import _burnout_push_through
        state = make_state()
        with patch("silicon_valley_trail.engine.events.random.random", return_value=0.3):
            msg = _burnout_push_through(state)
        # No member should go inactive
        assert all(m.is_active for m in state.team)

    def test_burnout_push_through_unlucky_deactivates_at_risk_member(self):
        from silicon_valley_trail.engine.events import _burnout_push_through
        state = make_state()
        state.team[1].morale = 5    # Hanna is burnout risk
        with patch("silicon_valley_trail.engine.events.random.random", return_value=0.7):
            _burnout_push_through(state)
        hanna = state.team[1]
        assert not hanna.is_active


# ---------------------------------------------------------------------------
# EventRegistry — pick_from_pool
# ---------------------------------------------------------------------------

class TestPickFromPool:
    def test_returns_none_for_empty_pool(self):
        registry = EventRegistry()
        state = make_state()
        assert registry.pick_from_pool([], state) is None

    def test_skips_events_whose_condition_fails(self):
        registry = EventRegistry()
        # tech_debt_crisis requires bugs >= 10
        state = make_state(bugs=0)
        result = registry.pick_from_pool(["tech_debt_crisis"], state)
        assert result is None

    def test_returns_eligible_event(self):
        registry = EventRegistry()
        state = make_state()
        result = registry.pick_from_pool(["press_coverage"], state)
        assert result is not None
        assert result.key == "press_coverage"
