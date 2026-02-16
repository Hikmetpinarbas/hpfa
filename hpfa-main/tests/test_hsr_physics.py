import pytest

from hpfa.security.hsr_physics import PhysicsRing, validate_physics


def test_physics_pass_normal_speed():
    ring = PhysicsRing(max_speed_mps=12.0)

    # prime
    validate_physics({"event_start_time": 0.0, "x": 0.0, "y": 0.0}, ring)

    # 6m in 1s => 6 m/s PASS
    validate_physics({"event_start_time": 1.0, "x": 6.0, "y": 0.0}, ring)


def test_physics_violation_high_speed():
    ring = PhysicsRing(max_speed_mps=12.0)

    validate_physics({"event_start_time": 0.0, "x": 0.0, "y": 0.0}, ring)

    # 30m in 1s => 30 m/s VIOLATION
    with pytest.raises(ValueError) as e:
        validate_physics({"event_start_time": 1.0, "x": 30.0, "y": 0.0}, ring)
    assert "HSR_PHYSICS_VIOLATION" in str(e.value)


def test_physics_fail_closed_missing_xy():
    ring = PhysicsRing()
    with pytest.raises(ValueError) as e:
        validate_physics({"event_start_time": 0.0, "x": 0.0}, ring)
    assert "HSR_FAIL_CLOSED:physics:missing_xy" in str(e.value)


def test_physics_fail_closed_nonpositive_dt():
    ring = PhysicsRing()
    validate_physics({"event_start_time": 1.0, "x": 0.0, "y": 0.0}, ring)

    with pytest.raises(ValueError) as e:
        validate_physics({"event_start_time": 1.0, "x": 1.0, "y": 1.0}, ring)
    assert "HSR_FAIL_CLOSED:physics:nonpositive_dt" in str(e.value)
