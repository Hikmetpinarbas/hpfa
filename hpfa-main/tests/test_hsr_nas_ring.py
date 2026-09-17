"""
Tests for hpfa.security.hsr_nas.NASRing (HSR Ring 6 — in-loop early-warning).

NASRing is NOT the canonical NAS analyzer; it is a per-event rolling-window
annotator. For canonical NAS see hpfa.analytics.nas.NASDetector.
"""
import pytest
from hpfa.security.hsr_nas import NASRing


# --- helpers ---

def _ev(team=1, outcome="fail", state="CONTROLLED"):
    return {"team_id": team, "outcome": outcome, "state_id": state}


# --- basic triggering ---

def test_three_consecutive_failures_trigger_nas():
    ring = NASRing(window_events=3)
    ring.update(_ev(outcome="fail"))
    ring.update(_ev(outcome="fail"))
    ev = ring.update(_ev(outcome="fail"))
    assert ev["nas_flag"] is True
    assert ev["nas_level"] == 3


def test_two_failures_do_not_trigger():
    ring = NASRing(window_events=3)
    ring.update(_ev(outcome="fail"))
    ev = ring.update(_ev(outcome="fail"))
    assert ev["nas_flag"] is False


def test_success_resets_window():
    ring = NASRing(window_events=3)
    ring.update(_ev(outcome="fail"))
    ring.update(_ev(outcome="fail"))
    ring.update(_ev(outcome="success"))   # resets
    ev = ring.update(_ev(outcome="fail"))
    assert ev["nas_flag"] is False


def test_fourth_failure_after_three_still_triggers():
    ring = NASRing(window_events=3)
    for _ in range(3):
        ring.update(_ev(outcome="fail"))
    ev = ring.update(_ev(outcome="fail"))
    assert ev["nas_flag"] is True


# --- team isolation ---

def test_failures_tracked_per_team_independently():
    ring = NASRing(window_events=3)
    for _ in range(3):
        ring.update(_ev(team=1, outcome="fail"))
    ev_t2 = ring.update(_ev(team=2, outcome="fail"))
    # team 2 only has 1 failure — no trigger
    assert ev_t2["nas_flag"] is False


def test_team_1_trigger_does_not_affect_team_2():
    ring = NASRing(window_events=3)
    for _ in range(3):
        ring.update(_ev(team=1, outcome="fail"))
    ev = ring.update(_ev(team=1, outcome="fail"))
    assert ev["nas_flag"] is True
    ev2 = ring.update(_ev(team=2, outcome="fail"))
    assert ev2["nas_flag"] is False


# --- inactive state pass-through ---

def test_dead_ball_state_passes_through_without_counting():
    ring = NASRing(window_events=3)
    ring.update(_ev(outcome="fail"))
    ring.update(_ev(outcome="fail"))
    ev = ring.update(_ev(outcome="fail", state="DEAD_BALL"))
    # state not CONTROLLED/CONTESTED → not counted
    assert ev["nas_flag"] is False


def test_mixed_active_inactive_does_not_trigger_from_inactive():
    ring = NASRing(window_events=3)
    ring.update(_ev(outcome="fail", state="CONTROLLED"))
    ring.update(_ev(outcome="fail", state="DEAD_BALL"))   # skipped
    ring.update(_ev(outcome="fail", state="DEAD_BALL"))   # skipped
    ev = ring.update(_ev(outcome="fail", state="CONTROLLED"))
    # only 2 active fails in window
    assert ev["nas_flag"] is False


# --- outcome None pass-through ---

def test_none_outcome_passes_through_without_flag():
    ring = NASRing(window_events=3)
    ev = ring.update({"team_id": 1, "outcome": None, "state_id": "CONTROLLED"})
    assert ev["nas_flag"] is False


# --- fail-closed paths ---

def test_non_dict_raises_fail_closed():
    ring = NASRing()
    with pytest.raises(ValueError) as exc:
        ring.update("not_a_dict")
    assert "NAS_FAIL_CLOSED:event_not_dict" in str(exc.value)


def test_missing_team_raises_fail_closed():
    ring = NASRing()
    with pytest.raises(ValueError) as exc:
        ring.update({"outcome": "fail", "state_id": "CONTROLLED"})
    assert "NAS_FAIL_CLOSED:missing_required_fields" in str(exc.value)


def test_missing_state_raises_fail_closed():
    ring = NASRing()
    with pytest.raises(ValueError) as exc:
        ring.update({"team_id": 1, "outcome": "fail"})
    assert "NAS_FAIL_CLOSED:missing_required_fields" in str(exc.value)


def test_invalid_outcome_raises_fail_closed():
    ring = NASRing()
    with pytest.raises(ValueError) as exc:
        ring.update({"team_id": 1, "outcome": "UNKNOWN", "state_id": "CONTROLLED"})
    assert "NAS_FAIL_CLOSED:invalid_outcome" in str(exc.value)
