from __future__ import annotations
from typing import Any, Dict, List

LAYERS = ["micro", "mezzo", "macro"]

def build_phase_layer_matrix(events: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """
    Lite matrix:
      phase -> layer -> count
    Şimdilik micro = event count,
    mezzo/macro ileride genişletilecek (0 bırakılır).
    """
    matrix: Dict[str, Dict[str, int]] = {}
    for e in events:
        ph = e.get("phase", "UNKNOWN")
        matrix.setdefault(ph, {l: 0 for l in LAYERS})
        matrix[ph]["micro"] += 1
    return matrix
