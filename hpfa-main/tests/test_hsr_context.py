import pytest
from hpfa.security.hsr_context import validate_context

# --- helpers ---

def _ev(ts=1.0, prev_ts=0.0, state="CONTROLLED", prev_state="DEAD_BALL",
        effect="START", event_type="RESTART_KICKOFF"):
    return {
        "event_start_time": ts,
        "prev_event_time": prev_ts,
        "state_id": state,
        "prev_state_id": prev_state,
        "possession_effect": effect,
        "event_type": event_type,
    }


# --- START landing invariant (canon: possession_state_machine.md lines 36-41) ---

def test_start_from_dead_ball_restart_is_valid():
    # DEAD_BALL + RESTART_* → CONTROLLED START
    validate_context(_ev(prev_state="DEAD_BALL", state="CONTROLLED", effect="START", event_type="RESTART_KICKOFF"))


def test_start_from_controlled_interception_is_valid():
    # CONTROLLED + INTERCEPTION → CONTROLLED START (canon line 40)
    validate_context(_ev(prev_state="CONTROLLED", state="CONTROLLED", effect="START", event_type="INTERCEPTION"))


def test_start_from_contested_interception_is_valid():
    # CONTESTED + INTERCEPTION → CONTROLLED START (canon line 41)
    validate_context(_ev(prev_state="CONTESTED", state="CONTROLLED", effect="START", event_type="INTERCEPTION"))


def test_start_landing_non_controlled_is_vetoed():
    # START must always land in CONTROLLED; any other destination is invalid
    with pytest.raises(ValueError) as exc:
        validate_context(_ev(prev_state="DEAD_BALL", state="DEAD_BALL", effect="START"))
    assert "HSR_CONTEXT_VIOLATION:start_must_land_controlled" in str(exc.value)


def test_start_landing_contested_is_vetoed():
    with pytest.raises(ValueError) as exc:
        validate_context(_ev(prev_state="DEAD_BALL", state="CONTESTED", effect="START"))
    assert "HSR_CONTEXT_VIOLATION:start_must_land_controlled" in str(exc.value)


# --- Temporal monotonicity ---

def test_time_non_monotonic_is_vetoed():
    ev = _ev(ts=0.5, prev_ts=1.0, effect="NEUTRAL", prev_state="CONTROLLED", state="CONTROLLED")
    with pytest.raises(ValueError) as exc:
        validate_context(ev)
    assert "HSR_CONTEXT_VIOLATION:time_non_monotonic" in str(exc.value)


def test_equal_timestamps_are_valid():
    # same ts is monotone (>=), not a violation
    validate_context(_ev(ts=1.0, prev_ts=1.0, effect="NEUTRAL", prev_state="CONTROLLED", state="CONTROLLED"))


# --- Cooldown breach ---

def test_cooldown_breach_tackle_after_dead_ball():
    ev = _ev(ts=1.0, prev_ts=0.0, prev_state="DEAD_BALL", state="CONTESTED",
             effect="NEUTRAL", event_type="TACKLE")
    # dt = 1.0s > COOLDOWN_S (0.3s)
    with pytest.raises(ValueError) as exc:
        validate_context(ev)
    assert "HSR_CONTEXT_VIOLATION:cooldown_breach" in str(exc.value)


def test_cooldown_within_window_is_valid():
    ev = _ev(ts=0.2, prev_ts=0.0, prev_state="DEAD_BALL", state="CONTESTED",
             effect="NEUTRAL", event_type="TACKLE")
    # dt = 0.2s <= COOLDOWN_S (0.3s): OK
    validate_context(ev)


# --- Fail-closed: missing fields ---

def test_missing_ts_raises_fail_closed():
    ev = _ev()
    del ev["event_start_time"]
    with pytest.raises(ValueError) as exc:
        validate_context(ev)
    assert "HSR_FAIL_CLOSED:context:missing_fields" in str(exc.value)


def test_missing_prev_state_raises_fail_closed():
    ev = _ev()
    del ev["prev_state_id"]
    with pytest.raises(ValueError) as exc:
        validate_context(ev)
    assert "HSR_FAIL_CLOSED:context:missing_fields" in str(exc.value)


def test_non_dict_event_raises_fail_closed():
    with pytest.raises(ValueError) as exc:
        validate_context("not_a_dict")
    assert "HSR_FAIL_CLOSED:context:event_not_dict" in str(exc.value)
