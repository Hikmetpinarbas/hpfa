from __future__ import annotations

from typing import Any, Optional


MISSING_TOKENS = {"", "-", "nan", "NaN", "NAN", "NULL", "null", "None", "none"}


def parse_percent(value: Any) -> Optional[float]:
    """
    Scale-safe percent parser.
    - None / missing tokens => None
    - If 0..1 => keep
    - If 1..100 => /100
    - Else => ValueError (caller should fail-closed)
    """
    if value is None:
        return None

    if isinstance(value, str):
        v = value.strip()
        if v in MISSING_TOKENS:
            return None
        v = v.replace("%", "").strip()
        if v in MISSING_TOKENS:
            return None
        try:
            x = float(v)
        except ValueError as e:
            raise ValueError(f"percent parse failed for '{value}'") from e
    else:
        try:
            x = float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"percent parse failed for '{value}'") from e

    if 0.0 <= x <= 1.0:
        return x
    if 1.0 < x <= 100.0:
        return x / 100.0

    raise ValueError(f"percent out of range: {x}")
