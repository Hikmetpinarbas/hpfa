from __future__ import annotations

from typing import Any, Dict

def compute_progression_score(context: Dict[str, Any]) -> Dict[str, float]:
    """
    ProgScore = (Prog*3) + (F3rd*2) + (Box*4)

    Expected context keys:
      - prog
      - f3rd
      - box
      Optional:
      - minutes (if provided, caller can normalize per90 outside)
    """
    prog = float(context.get("prog", 0.0) or 0.0)
    f3rd = float(context.get("f3rd", 0.0) or 0.0)
    box = float(context.get("box", 0.0) or 0.0)
    score = (prog * 3.0) + (f3rd * 2.0) + (box * 4.0)
    return {"progression_score": score}