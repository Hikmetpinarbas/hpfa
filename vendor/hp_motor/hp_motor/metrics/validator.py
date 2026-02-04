from __future__ import annotations
from typing import Any, Dict, List, Tuple

from hp_motor.library.loader import load_registry

Status = str  # OK | DEGRADED | UNKNOWN


def _has_columns(events_meta: Dict[str, Any], required: List[str]) -> bool:
    cols = set(events_meta.get("columns_present", []))
    return all(c in cols for c in required)


def validate_metrics(
    metrics_raw: Dict[str, Any],
    events_meta: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate raw metrics against metric_registry contract.
    Returns:
      validated_metrics_raw, validation_flags
    """
    registry, reg_health = load_registry()
    contract = {m["id"]: m for m in registry.get("metrics", [])}

    validated = {"meta": dict(metrics_raw.get("meta", {})), "metrics": {}}
    flags: List[str] = []

    for mid, payload in metrics_raw.get("metrics", {}).items():
        spec = contract.get(mid)
        value = payload.get("value")

        if spec is None:
            validated["metrics"][mid] = {
                "value": value,
                "status": "UNKNOWN",
                "reason": "metric_not_in_registry",
            }
            flags.append(f"metric_unknown:{mid}")
            continue

        required_cols = spec.get("required_columns", [])
        status_policy = spec.get("status_policy", {})

        if not required_cols:
            status: Status = "OK"
            reason = "no_required_columns"
        else:
            if _has_columns(events_meta, required_cols):
                status = "OK"
                reason = "required_columns_present"
            else:
                # If some but not all present → DEGRADED, else UNKNOWN
                present = set(events_meta.get("columns_present", []))
                overlap = present.intersection(set(required_cols))
                if overlap:
                    status = "DEGRADED"
                    reason = "partial_required_columns_present"
                else:
                    status = "UNKNOWN"
                    reason = "required_columns_missing"

        validated["metrics"][mid] = {
            "value": value,
            "status": status,
            "reason": reason,
            "contract": {
                "layer": spec.get("layer"),
                "mechanisms": spec.get("mechanisms", []),
            },
        }

        if status != "OK":
            flags.append(f"metric_status:{mid}:{status}")

    # propagate registry health
    if reg_health.status != "OK":
        flags.append("registry:" + reg_health.status)
        flags.extend(reg_health.flags)

    return validated, flags
