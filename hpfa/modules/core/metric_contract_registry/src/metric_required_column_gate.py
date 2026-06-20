"""Required-column gate for HPFA metric contracts.

Candidate stub only. Produces evidence readiness status, not football claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RequiredColumnGateResult:
    metric_id: str
    status: str
    missing_columns: tuple[str, ...]
    degraded_reason: str | None = None


def evaluate_required_columns(
    metric: dict,
    available_columns: Iterable[str],
) -> RequiredColumnGateResult:
    """Evaluate whether a metric can be calculated from available columns."""
    metric_id = str(metric.get("id", "UNKNOWN_METRIC"))
    required = tuple(str(col) for col in metric.get("required_columns", []))
    available = {str(col) for col in available_columns}
    missing = tuple(col for col in required if col not in available)

    if not required:
        return RequiredColumnGateResult(
            metric_id=metric_id,
            status="DEGRADED",
            missing_columns=(),
            degraded_reason="metric has no required_columns contract",
        )

    if missing:
        return RequiredColumnGateResult(
            metric_id=metric_id,
            status="UNKNOWN",
            missing_columns=missing,
            degraded_reason="required columns missing",
        )

    return RequiredColumnGateResult(
        metric_id=metric_id,
        status="OK",
        missing_columns=(),
        degraded_reason=None,
    )
