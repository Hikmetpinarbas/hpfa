from __future__ import annotations

from typing import Any, Dict

def compute_shot_goals_added(context: Dict[str, Any]) -> Dict[str, float]:
    """
    SGA = PSxG - xG

    Expected context keys:
      - psxg
      - xg
    """
    psxg = float(context.get("psxg", 0.0) or 0.0)
    xg = float(context.get("xg", 0.0) or 0.0)
    return {"shot_goals_added": psxg - xg}