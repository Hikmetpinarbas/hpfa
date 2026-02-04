from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set
import importlib


class Decision(str, Enum):
    ACCEPT = "ACCEPT"
    SOFT_FAIL = "SOFT_FAIL"
    HARD_FAIL = "HARD_FAIL"


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str


def _allowed_epistemic_statuses() -> Set[str]:
    """Fail-closed: allowed set MUST come from canon.epistemic_meta.EpistemicStatus."""
    try:
        mod = importlib.import_module("canon.epistemic_meta")
    except Exception as e:
        raise RuntimeError("Cannot import canon.epistemic_meta for EpistemicStatus") from e

    enum_obj = getattr(mod, "EpistemicStatus", None)
    if enum_obj is None:
        raise RuntimeError("canon.epistemic_meta.EpistemicStatus not found (fail-closed)")

    values: Set[str] = set()
    for item in enum_obj:
        v = getattr(item, "value", None)
        if isinstance(v, str) and v.strip():
            values.add(v.strip())

    if not values:
        raise RuntimeError("EpistemicStatus enum has no string values (fail-closed)")

    return values


def evaluate_epistemic_policy(
    *,
    epistemic_status: str,
    lossy_mapping: bool,
    human_override: bool,
    assumption_id: Optional[str],
) -> PolicyDecision:
    allowed = _allowed_epistemic_statuses()

    status = (epistemic_status or "").strip()
    if status not in allowed:
        return PolicyDecision(
            decision=Decision.HARD_FAIL,
            reason=f"epistemic_status '{status}' not in allowed enum: {sorted(allowed)}",
        )

    if human_override and not assumption_id:
        return PolicyDecision(
            decision=Decision.HARD_FAIL,
            reason="human_override=True requires assumption_id",
        )

    if lossy_mapping:
        if human_override:
            return PolicyDecision(
                decision=Decision.SOFT_FAIL,
                reason="lossy_mapping=True with human_override=True (override accepted, degraded mode)",
            )
        return PolicyDecision(
            decision=Decision.SOFT_FAIL,
            reason="lossy_mapping=True without human_override (degraded mode)",
        )

    return PolicyDecision(decision=Decision.ACCEPT, reason="policy OK")
