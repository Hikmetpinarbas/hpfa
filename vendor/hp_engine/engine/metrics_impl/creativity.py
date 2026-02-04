from __future__ import annotations

from typing import Any, Dict

def compute_creative_diff(context: Dict[str, Any]) -> Dict[str, float]:
    """
    CreativeDiff = Assists - xA

    Expected context keys:
      - assists
      - xa
    """
    assists = float(context.get("assists", 0.0) or 0.0)
    xa = float(context.get("xa", 0.0) or 0.0)
    return {"creative_diff": assists - xa}