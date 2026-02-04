from __future__ import annotations
from typing import Any, Dict, List

from hp_motor.config_reader import read_spec


def compute_raw_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    spec = read_spec()
    prog_dx = float(spec.get("hp_motor", {}).get("progressive_pass_dx_threshold", 15.0))

    # column inventory
    columns_present = set()
    for e in events:
        columns_present.update(e.keys())

    pass_count = 0
    prog_pass = 0
    shot = 0
    turnover = 0
    have_xy = True

    for e in events:
        et = str(e.get("event_type", "")).lower()

        if et == "pass":
            pass_count += 1
            if "start_x" in e and "end_x" in e:
                try:
                    dx = float(e["end_x"]) - float(e["start_x"])
                    if dx >= prog_dx:
                        prog_pass += 1
                except Exception:
                    have_xy = False
            else:
                have_xy = False

        if "shot" in et:
            shot += 1

        if et in {"turnover", "dispossessed"}:
            turnover += 1
        if et == "pass" and str(e.get("outcome", "")).lower() in {"fail", "failed", "incomplete", "lost"}:
            turnover += 1
        if et in {"carry", "dribble"} and str(e.get("outcome", "")).lower() in {"fail", "failed", "lost"}:
            turnover += 1

    return {
        "meta": {
            "thresholds": {"progressive_pass_dx": prog_dx},
            "counts": {"events": len(events)},
            "columns_present": sorted(columns_present),
        },
        "metrics": {
            "M_PASS_COUNT": {"value": pass_count},
            "M_PROG_PASS_COUNT": {"value": prog_pass},
            "M_SHOT_COUNT": {"value": shot},
            "M_TURNOVER_COUNT": {"value": turnover},
        },
    }
