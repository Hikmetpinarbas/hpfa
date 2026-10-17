"""Stage B detection calibration on cached window series.

Only detection thresholds are searched; decoding is done once (`prepare`).
Calibration uses one labelled video; the chosen settings must then be
evaluated on different, held-out videos — never reported from the
calibration video itself.
"""

from __future__ import annotations

import copy
import itertools
from typing import Any

from pipeline import detect, evaluate_prepared
from stages import PipelineConfig

DEFAULT_GRID = {
    "b_stop_ratio": (0.4, 0.5, 0.6, 0.7),
    "b_min_stoppage_s": (3.0, 4.0, 6.0, 8.0),
    "restart_rise_ratio": (0.6, 0.8, 1.0),
    "goal_min_stoppage_s": (30.0, 45.0, 60.0),
}


def objective(per_event_type: dict[str, Any]) -> float:
    """F1 of SET_PIECE_RESTART, tie-broken by GOAL F1 (restart is the primary signal)."""
    restart = (per_event_type.get("SET_PIECE_RESTART") or {}).get("f1") or 0.0
    goal = (per_event_type.get("GOAL") or {}).get("f1") or 0.0
    return restart + 0.25 * goal


def calibrate(prep: dict[str, Any], reference: list[dict[str, Any]], base: PipelineConfig, grid: dict[str, tuple] | None = None) -> dict[str, Any]:
    grid = grid or DEFAULT_GRID
    keys = list(grid)
    trials = []
    best_cfg, best_score = base, -1.0
    for values in itertools.product(*(grid[k] for k in keys)):
        cfg = copy.deepcopy(base)
        for k, v in zip(keys, values):
            setattr(cfg, k, v)
        events = detect(prep, cfg)
        per = evaluate_prepared(prep, events, reference)["per_event_type"]
        score = objective(per)
        trials.append({"params": dict(zip(keys, values)), "objective": round(score, 4),
                       "restart_precision": (per.get("SET_PIECE_RESTART") or {}).get("precision"),
                       "restart_recall": (per.get("SET_PIECE_RESTART") or {}).get("recall"),
                       "goal_f1": (per.get("GOAL") or {}).get("f1")})
        if score > best_score:
            best_cfg, best_score = cfg, score
    trials.sort(key=lambda x: -x["objective"])
    return {
        "best_params": {k: getattr(best_cfg, k) for k in keys},
        "best_objective_in_sample": round(best_score, 4),
        "trials": trials,
        "trial_count": len(trials),
        "note": "In-sample objective on the calibration video; optimistic by construction.",
        "config": best_cfg,
    }
