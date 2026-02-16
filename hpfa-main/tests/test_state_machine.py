import pytest

from hpfa.core.state_machine import PossessionStateMachine


def test_restart_starts_controlled_with_start_effect():
    sm = PossessionStateMachine()
    out, res = sm.update({"event_type": "RESTART_KICKOFF", "team_id": 1, "event_start_time": 0.0})
    assert out["state_id"] == "CONTROLLED"
    assert out["possession_effect"] == "START"
    assert out["possession_id"] is not None


def test_pass_success_continues_controlled():
    sm = PossessionStateMachine()
    sm.update({"event_type": "RESTART_KICKOFF", "team_id": 1, "event_start_time": 0.0})
    out, res = sm.update({"event_type": "PASS", "team_id": 1, "event_start_time": 1.0, "outcome": "success"})
    assert out["state_id"] == "CONTROLLED"
    assert out["possession_effect"] == "CONTINUE"
    assert out["possession_id"] is not None


def test_fail_closed_on_pass_without_success_is_unvalidated():
    """
    Canon v1.0.0 policy:
    - PASS/DRIBBLE fail or missing outcome is NOT defined in transition table.
    - Therefore system marks it UNVALIDATED (fail-closed, no speculation).
    """
    sm = PossessionStateMachine()
    sm.update({"event_type": "RESTART_KICKOFF", "team_id": 1, "event_start_time": 0.0})
    out, res = sm.update({"event_type": "PASS", "team_id": 1, "event_start_time": 1.0})
    assert out["state_id"] == "UNVALIDATED"
    assert out["possession_effect"] == "NEUTRAL"


def test_fail_closed_on_dribble_without_success_is_unvalidated():
    sm = PossessionStateMachine()
    sm.update({"event_type": "RESTART_KICKOFF", "team_id": 1, "event_start_time": 0.0})
    out, res = sm.update({"event_type": "DRIBBLE", "team_id": 1, "event_start_time": 1.0})
    assert out["state_id"] == "UNVALIDATED"
    assert out["possession_effect"] == "NEUTRAL"


def test_out_ends_dead_ball_and_clears_possession():
    sm = PossessionStateMachine()
    sm.update({"event_type": "RESTART_KICKOFF", "team_id": 1, "event_start_time": 0.0})
    out, res = sm.update({"event_type": "OUT", "team_id": 1, "event_start_time": 2.0})
    assert out["state_id"] == "DEAD_BALL"
    assert out["possession_effect"] == "END"
    assert out["possession_id"] is None


def test_tackle_from_controlled_to_contested_neutral():
    sm = PossessionStateMachine()
    sm.update({"event_type": "RESTART_KICKOFF", "team_id": "A", "event_start_time": 0.0})
    out, res = sm.update({"event_type": "TACKLE", "team_id": "A", "event_start_time": 1.0})
    assert out["state_id"] == "CONTESTED"
    assert out["possession_effect"] == "NEUTRAL"


def test_unknown_event_is_unvalidated():
    sm = PossessionStateMachine()
    sm.update({"event_type": "RESTART_KICKOFF", "team_id": "A", "event_start_time": 0.0})
    out, res = sm.update({"event_type": "WTF_EVENT", "team_id": "A", "event_start_time": 1.0})
    assert out["state_id"] == "UNVALIDATED"
    assert out["possession_effect"] == "NEUTRAL"
