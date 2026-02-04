from __future__ import annotations

from typing import Any, Dict

def _safe_div(n: float, d: float, eps: float = 1e-9) -> float:
    if d is None or abs(d) < eps:
        return 0.0
    return float(n) / float(d)

def compute_field_tilt(context: Dict[str, Any]) -> Dict[str, float]:
    """
    FieldTilt = team_f3rd_passes / (team_f3rd_passes + opp_f3rd_passes)

    Expected context keys:
      - team_final_third_passes
      - opponent_final_third_passes
    """
    t = float(context.get("team_final_third_passes", 0.0) or 0.0)
    o = float(context.get("opponent_final_third_passes", 0.0) or 0.0)
    return {"field_tilt": _safe_div(t, (t + o))}