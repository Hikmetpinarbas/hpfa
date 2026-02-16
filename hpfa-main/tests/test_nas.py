import pytest

from hpfa.analytics.nas import NASDetector


def _e(ts, phase="DEFENSIVE", state="CONTROLLED", action="X", outcome="FAIL", zone=1, p=5.0, r3=False, r4=False, eid=None):
    d = {
        "event_start_time": ts,
        "phase": phase,
        "state_id": state,
        "action_type": action,
        "outcome": outcome,
        "zone_id": zone,
        "pressure_level": p,
        "hsr_flags": {"ring3_dead_ball_veto": r3, "ring4_physics_veto": r4},
    }
    if eid is not None:
        d["event_id"] = eid
    return d


def test_nas_three_failures_same_zone_within_0_5s_should_count_one_sequence():
    nas = NASDetector(max_dt_s=0.5, min_fail_count=3)
    events = [_e(10.0), _e(10.3), _e(10.7)]
    res = nas.evaluate(events)
    assert res.status == "PASS"
    assert res.nas_sequence_count == 1
    seq = res.sequences[0]
    assert seq.fail_count == 3
    assert seq.zone_id == "1"


def test_nas_dead_ball_state_should_not_increment_sequence_count_ring3_veto():
    nas = NASDetector()
    events = [_e(10.0, state="DEAD_BALL"), _e(10.3), _e(10.6)]
    res = nas.evaluate(events)
    assert res.status == "PASS"
    assert res.nas_sequence_count == 0


def test_nas_physics_veto_events_should_be_excluded_ring4_veto():
    nas = NASDetector()
    events = [_e(10.0), _e(10.3, r4=True), _e(10.6)]
    res = nas.evaluate(events)
    assert res.status == "PASS"
    assert res.nas_sequence_count == 0


def test_nas_missing_required_fields_should_fail_closed_unvalidated():
    nas = NASDetector()
    events = [_e(10.0)]
    del events[0]["zone_id"]
    res = nas.evaluate(events)
    assert res.status == "UNVALIDATED"
    assert "NAS_FAIL_CLOSED:missing_zone_id" in res.reason


def test_nas_time_gap_over_0_5s_should_break_sequence_no_count():
    nas = NASDetector()
    events = [_e(10.0), _e(10.3), _e(11.0)]
    res = nas.evaluate(events)
    assert res.status == "PASS"
    assert res.nas_sequence_count == 0


def test_nas_zone_change_should_break_sequence_no_count():
    nas = NASDetector()
    events = [_e(10.0, zone=1), _e(10.3, zone=2), _e(10.6, zone=2)]
    res = nas.evaluate(events)
    assert res.status == "PASS"
    assert res.nas_sequence_count == 0


def test_nas_non_defensive_phases_should_be_ignored():
    nas = NASDetector()
    events = [_e(10.0, phase="ATTACK"), _e(10.3, phase="ATTACK"), _e(10.6, phase="ATTACK")]
    res = nas.evaluate(events)
    assert res.status == "PASS"
    assert res.nas_sequence_count == 0


def test_nas_extended_failure_chain_should_count_as_single_sequence():
    nas = NASDetector()
    events = [_e(10.0), _e(10.2), _e(10.4), _e(10.6), _e(10.8)]
    res = nas.evaluate(events)
    assert res.status == "PASS"
    assert res.nas_sequence_count == 1
    assert res.sequences[0].fail_count == 5
