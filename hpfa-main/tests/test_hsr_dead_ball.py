import pytest
from hpfa.security.hsr_dead_ball import validate_dead_ball


# --- helpers ---

def _ev(event_type="PASS", state="CONTROLLED", prev_state="CONTROLLED"):
    return {
        "event_type": event_type,
        "state_id": state,
        "prev_state_id": prev_state,
    }


# --- valid events (no veto) ---

def test_pass_in_controlled_state_is_ok():
    validate_dead_ball(_ev("PASS", "CONTROLLED", "CONTROLLED"))


def test_tackle_in_controlled_state_is_ok():
    validate_dead_ball(_ev("TACKLE", "CONTROLLED", "CONTROLLED"))


def test_interception_in_controlled_state_is_ok():
    validate_dead_ball(_ev("INTERCEPTION", "CONTROLLED", "CONTROLLED"))


def test_tackle_after_contested_is_ok():
    validate_dead_ball(_ev("TACKLE", "CONTESTED", "CONTESTED"))


# --- dead-ball veto: current state is DEAD_BALL ---

def test_tackle_in_dead_ball_state_is_vetoed():
    with pytest.raises(ValueError) as exc:
        validate_dead_ball(_ev("TACKLE", state="DEAD_BALL", prev_state="CONTROLLED"))
    assert "HSR_DEAD_BALL_VIOLATION:TACKLE" in str(exc.value)


def test_interception_in_dead_ball_state_is_vetoed():
    with pytest.raises(ValueError) as exc:
        validate_dead_ball(_ev("INTERCEPTION", state="DEAD_BALL", prev_state="CONTROLLED"))
    assert "HSR_DEAD_BALL_VIOLATION:INTERCEPTION" in str(exc.value)


# --- dead-ball veto: prev state was DEAD_BALL ---

def test_tackle_right_after_dead_ball_is_vetoed():
    with pytest.raises(ValueError) as exc:
        validate_dead_ball(_ev("TACKLE", state="CONTROLLED", prev_state="DEAD_BALL"))
    assert "HSR_DEAD_BALL_VIOLATION:TACKLE" in str(exc.value)


def test_interception_right_after_dead_ball_is_vetoed():
    with pytest.raises(ValueError) as exc:
        validate_dead_ball(_ev("INTERCEPTION", state="CONTROLLED", prev_state="DEAD_BALL"))
    assert "HSR_DEAD_BALL_VIOLATION:INTERCEPTION" in str(exc.value)


# --- non-illegal events survive dead-ball context ---

def test_pass_right_after_dead_ball_is_ok():
    # PASS is not in ILLEGAL_EVENTS, so no veto even from dead-ball context
    validate_dead_ball(_ev("PASS", state="CONTROLLED", prev_state="DEAD_BALL"))


def test_restart_in_dead_ball_state_is_ok():
    validate_dead_ball(_ev("RESTART_KICKOFF", state="CONTROLLED", prev_state="DEAD_BALL"))


# --- fail-closed paths ---

def test_non_dict_raises_fail_closed():
    with pytest.raises(ValueError) as exc:
        validate_dead_ball("not_a_dict")
    assert "HSR_FAIL_CLOSED:event_not_dict" in str(exc.value)


def test_missing_event_type_raises_fail_closed():
    ev = _ev()
    del ev["event_type"]
    with pytest.raises(ValueError) as exc:
        validate_dead_ball(ev)
    assert "HSR_FAIL_CLOSED:missing_event_type" in str(exc.value)


def test_empty_event_type_raises_fail_closed():
    ev = _ev()
    ev["event_type"] = "   "
    with pytest.raises(ValueError) as exc:
        validate_dead_ball(ev)
    assert "HSR_FAIL_CLOSED:missing_event_type" in str(exc.value)


def test_both_state_fields_missing_raises_fail_closed():
    with pytest.raises(ValueError) as exc:
        validate_dead_ball({"event_type": "TACKLE"})
    assert "HSR_FAIL_CLOSED:missing_state_fields" in str(exc.value)
