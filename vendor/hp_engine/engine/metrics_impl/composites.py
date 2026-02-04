from __future__ import annotations
from typing import Optional


def compute_finishing_skill_psxg_minus_xg(xg: Optional[float], psxg: Optional[float]) -> Optional[float]:
    if xg is None or psxg is None:
        return None
    return float(psxg) - float(xg)


def compute_progression_value_progressive_passes_plus_possession_value(
    progressive_passes: Optional[float], possession_value: Optional[float]
) -> Optional[float]:
    if progressive_passes is None or possession_value is None:
        return None
    return float(progressive_passes) + float(possession_value)


def compute_press_aggression_inverse_ppda(ppda: Optional[float]) -> Optional[float]:
    if ppda is None:
        return None
    ppda_f = float(ppda)
    if ppda_f <= 0:
        return None
    return 1.0 / ppda_f