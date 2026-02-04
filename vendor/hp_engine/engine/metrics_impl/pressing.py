from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

def _safe_div(n: float, d: float, eps: float = 1e-9) -> float:
    if d is None or abs(d) < eps:
        return 0.0
    return float(n) / float(d)

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def compute_ppda(context: Dict[str, Any]) -> Dict[str, float]:
    """
    Expected context keys:
      - opponent_passes_build (float/int)
      - defensive_actions_press (float/int)

    Returns: {"ppda": float}
    """
    opp_passes = float(context.get("opponent_passes_build", 0.0) or 0.0)
    def_actions = float(context.get("defensive_actions_press", 0.0) or 0.0)
    return {"ppda": _safe_div(opp_passes, def_actions)}

def compute_build_up_disruption(context: Dict[str, Any]) -> Dict[str, float]:
    """
    BDP = (expected_pass_pct - actual_pass_pct) / expected_pass_pct
    clipped to [-1, 1].

    Expected context keys:
      - expected_pass_pct (0..1 or 0..100; both accepted)
      - actual_pass_pct   (0..1 or 0..100; both accepted)
    """
    expv = float(context.get("expected_pass_pct", 0.0) or 0.0)
    actv = float(context.get("actual_pass_pct", 0.0) or 0.0)

    # Accept both [0..1] and [0..100]
    if expv > 1.5:
        expv = expv / 100.0
    if actv > 1.5:
        actv = actv / 100.0

    bdp = _safe_div((expv - actv), expv, eps=1e-6)
    bdp = _clip(bdp, -1.0, 1.0)
    return {"build_up_disruption": bdp}