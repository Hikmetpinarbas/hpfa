#!/usr/bin/env python3
"""
HPFA Smoke Runner — State Machine + HSR (R3 + R4)
Fail-closed; deterministic.

Exit codes:
  0 = all PASS
  1 = at least one FAIL
  2 = runtime error (fail-closed)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from hpfa.core.state_machine import PossessionStateMachine
from hpfa.security.hsr_dead_ball import validate_dead_ball
from hpfa.security.hsr_physics import PhysicsRing, validate_physics


@dataclass
class Case:
    name: str
    events: List[Dict[str, Any]]
    expect_error_contains: Optional[str]  # None => expect PASS (no error)


def _run_sm_case(sm: PossessionStateMachine, case: Case) -> Tuple[bool, str]:
    last_evt: Optional[Dict[str, Any]] = None
    for e in case.events:
        last_evt, _ = sm.update(e)
    if last_evt is None:
        return False, "no_event_produced"

    try:
        validate_dead_ball(last_evt)
        if case.expect_error_contains is None:
            return True, (
                f"PASS (HSR ok) | last={last_evt.get('prev_state_id')}->{last_evt.get('state_id')} "
                f"{last_evt.get('event_type')} reason={last_evt.get('sm_reason')}"
            )
        return False, f"FAIL expected error containing '{case.expect_error_contains}' but got PASS"
    except ValueError as ve:
        msg = str(ve)
        if case.expect_error_contains is None:
            return False, f"FAIL unexpected error: {msg}"
        if case.expect_error_contains in msg:
            return True, f"PASS (triggered) {msg}"
        return False, f"FAIL error mismatch: got '{msg}' expected contains '{case.expect_error_contains}'"


def _run_physics_case(case: Case) -> Tuple[bool, str]:
    ring = PhysicsRing(max_speed_mps=12.0)

    try:
        for e in case.events:
            validate_physics(e, ring)

        if case.expect_error_contains is None:
            return True, "PASS (HSR ok)"
        return False, f"FAIL expected error containing '{case.expect_error_contains}' but got PASS"

    except ValueError as ve:
        msg = str(ve)
        if case.expect_error_contains is None:
            return False, f"FAIL unexpected error: {msg}"
        if case.expect_error_contains in msg:
            return True, f"PASS (triggered) {msg}"
        return False, f"FAIL error mismatch: got '{msg}' expected contains '{case.expect_error_contains}'"


def main() -> int:
    try:
        any_fail = False

        print("== HPFA SMOKE: SM + HSR (R3+R4) ==")

        # ---------------- R3 (Dead Ball) ----------------
        r3_cases: List[Case] = [
            Case(
                name="dead_ball_then_tackle_should_trigger_ring3",
                events=[{"event_type": "TACKLE", "team_id": "A", "event_start_time": 10.0}],
                expect_error_contains="HSR_DEAD_BALL_VIOLATION:TACKLE",
            ),
            Case(
                name="restart_then_tackle_should_pass_ring3",
                events=[
                    {"event_type": "RESTART_KICKOFF", "team_id": "A", "event_start_time": 1.0},
                    {"event_type": "TACKLE", "team_id": "A", "event_start_time": 2.0},
                ],
                expect_error_contains=None,
            ),
        ]

        for c in r3_cases:
            sm = PossessionStateMachine()
            ok, detail = _run_sm_case(sm, c)
            print(f"[{'PASS' if ok else 'FAIL'}] {c.name}: {detail}")
            if not ok:
                any_fail = True

        # ---------------- R4 (Physics) ----------------
        r4_cases: List[Case] = [
            Case(
                name="physics_normal_should_pass_ring4",
                events=[
                    {"event_start_time": 0.0, "x": 0.0, "y": 0.0},
                    {"event_start_time": 1.0, "x": 5.0, "y": 0.0},
                ],
                expect_error_contains=None,
            ),
            Case(
                name="physics_teleport_should_trigger_ring4",
                events=[
                    {"event_start_time": 0.0, "x": 0.0, "y": 0.0},
                    {"event_start_time": 0.1, "x": 50.0, "y": 0.0},  # 500 m/s
                ],
                expect_error_contains="HSR_PHYSICS_VIOLATION",
            ),
            Case(
                name="missing_physics_fields_fail_closed_ring4",
                events=[{"event_start_time": 0.0, "x": 0.0}],  # missing y
                expect_error_contains="HSR_FAIL_CLOSED:physics:missing_xy",
            ),
            Case(
                name="nonpositive_dt_should_trigger_ring4",
                events=[
                    {"event_start_time": 1.0, "x": 0.0, "y": 0.0},
                    {"event_start_time": 1.0, "x": 1.0, "y": 1.0},  # dt=0
                ],
                expect_error_contains="HSR_FAIL_CLOSED:physics:nonpositive_dt",
            ),
        ]

        for c in r4_cases:
            ok, detail = _run_physics_case(c)
            print(f"[{'PASS' if ok else 'FAIL'}] {c.name}: {detail}")
            if not ok:
                any_fail = True

        return 1 if any_fail else 0

    except Exception as e:
        print(f"[RUNTIME_ERROR] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
