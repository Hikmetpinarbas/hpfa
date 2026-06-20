"""HPFA Metric Contract Registry loader.

Candidate stub only. Not production-bound.
Runtime rule: do not read Google Drive or Dropbox.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MetricRegistryError(ValueError):
    """Raised when a metric registry cannot be loaded safely."""


REQUIRED_FIELDS = {
    "id",
    "layer",
    "definition",
    "required_columns",
    "status_policy",
    "definition_confidence",
}


def load_metric_registry(path: str | Path) -> list[dict[str, Any]]:
    """Load a local metric registry file.

    The file must be packaged locally. External connector paths are not accepted.
    """
    registry_path = Path(path)
    if not registry_path.exists():
        raise MetricRegistryError(f"registry file not found: {registry_path}")
    if registry_path.is_dir():
        raise MetricRegistryError(f"registry path is a directory: {registry_path}")

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    metrics = data.get("metrics") if isinstance(data, dict) else data
    if not isinstance(metrics, list):
        raise MetricRegistryError("registry must contain a metrics list")

    for idx, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            raise MetricRegistryError(f"metric at index {idx} is not an object")
        missing = sorted(REQUIRED_FIELDS - set(metric))
        if missing:
            raise MetricRegistryError(
                f"metric {metric.get('id', idx)} missing required fields: {missing}"
            )
    return metrics


def index_metrics(metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return a metric-id keyed registry and fail on duplicates."""
    indexed: dict[str, dict[str, Any]] = {}
    for metric in metrics:
        metric_id = str(metric["id"])
        if metric_id in indexed:
            raise MetricRegistryError(f"duplicate metric id: {metric_id}")
        indexed[metric_id] = metric
    return indexed
