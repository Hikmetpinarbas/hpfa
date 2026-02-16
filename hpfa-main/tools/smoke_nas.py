#!/usr/bin/env python3
from hpfa.analytics.nas import NASDetector

def e(ts, zone=1, outcome="FAIL", phase="DEFENSIVE", state="CONTROLLED", r3=False, r4=False):
    return {
        "event_start_time": ts,
        "phase": phase,
        "state_id": state,
        "action_type": "X",
        "outcome": outcome,
        "zone_id": zone,
        "pressure_level": 5.0,
        "hsr_flags": {"ring3_dead_ball_veto": r3, "ring4_physics_veto": r4},
    }

def main():
    nas = NASDetector()
    res = nas.evaluate([e(0.0), e(0.2), e(0.4)])
    assert res.status == "PASS" and res.nas_sequence_count == 1
    print("PASS: NAS triggered")

    res = nas.evaluate([e(0.0), e(0.2, r4=True), e(0.4)])
    assert res.status == "PASS" and res.nas_sequence_count == 0
    print("PASS: NAS non-trigger")

if __name__ == "__main__":
    main()
