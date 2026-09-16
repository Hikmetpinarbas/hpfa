from __future__ import annotations

from typing import Any

DIAGNOSTIC_WINDOW_ROLE = "SENSITIVITY_ONLY_NOT_PRODUCTION_CONTRACT"
CALIBRATION_REQUIRED = "CALIBRATION_REQUIRED"
UNRESOLVED_CONTRACT_KEY = "UNRESOLVED_CONSTRUCT_CONTRACT_KEY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _sorted_text(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _positive_windows(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    windows: set[float] = set()
    for item in value:
        if isinstance(item, bool):
            continue
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            windows.add(parsed)
    return sorted(windows)


def _contract_key(record: dict[str, Any]) -> str:
    """Build a role-aware construct key without claiming physical restart/action truth."""
    role = _clean(record.get("source_role")) or "SOURCE_ROLE_UNKNOWN"
    families = _sorted_text(record.get("anchor_action_family_candidates"))
    if not families:
        return UNRESOLVED_CONTRACT_KEY
    return f"{role}|{'+' .join(families)}"


def apply_construct_temporal_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Make the current global horizon grid explicitly diagnostic-only.

    The existing consequence producer still searches a fixed diagnostic grid. This adapter
    prevents that grid from being mistaken for a production-authoritative football horizon.
    It creates no family threshold, does not recalibrate from one match, and does not alter
    temporal relation admission. Each visible consequence candidate receives a role-aware
    construct contract key and remains CALIBRATION_REQUIRED until a future, separately
    admitted construct-specific temporal contract exists.
    """
    result = dict(payload)
    if result.get("status") == "FAIL_CLOSED":
        return result

    windows = _positive_windows(result.get("window_seconds"))
    records = result.get("trackable_action_consequence_candidates")
    if not isinstance(records, list):
        records = []

    adapted: list[dict[str, Any]] = []
    contract_keys: set[str] = set()
    unresolved_key_count = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        row = dict(record)
        key = _contract_key(row)
        contract_keys.add(key)
        if key == UNRESOLVED_CONTRACT_KEY:
            unresolved_key_count += 1
        row["temporal_consequence_contract_key"] = key
        row["construct_specific_temporal_contract_required"] = True
        row["temporal_consequence_contract_state"] = CALIBRATION_REQUIRED
        row["diagnostic_window_seconds"] = list(windows)
        row["diagnostic_window_role"] = DIAGNOSTIC_WINDOW_ROLE
        row["production_temporal_window_seconds"] = None
        row["diagnostic_window_can_authorize_claim"] = False
        row["diagnostic_window_can_authorize_professional_finding"] = False
        row["single_match_observed_latency_can_set_production_threshold"] = False
        row["construct_contract_is_causal_truth"] = False
        row["construct_contract_is_tactical_truth"] = False
        adapted.append(row)

    review_hits = {
        _clean(item)
        for item in (result.get("review_hits") or [])
        if _clean(item)
    }
    if adapted:
        review_hits.add("construct_specific_temporal_contract_calibration_required")
    if unresolved_key_count:
        review_hits.add("construct_temporal_contract_key_unresolved")

    result["trackable_action_consequence_candidates"] = adapted
    result["window_seconds"] = list(windows)
    result["diagnostic_window_seconds"] = list(windows)
    result["diagnostic_window_role"] = DIAGNOSTIC_WINDOW_ROLE
    result["global_window_is_production_temporal_contract"] = False
    result["construct_specific_temporal_contract_required"] = True
    result["construct_specific_temporal_contract_state"] = (
        CALIBRATION_REQUIRED if adapted else "NO_VISIBLE_CONSEQUENCE_CANDIDATES"
    )
    result["construct_temporal_contract_keys"] = sorted(contract_keys)
    result["construct_temporal_contract_key_count"] = len(contract_keys)
    result["construct_temporal_contract_calibration_required_candidate_count"] = len(adapted)
    result["construct_temporal_contract_unresolved_key_count"] = unresolved_key_count
    result["production_temporal_window_thresholds_admitted"] = False
    result["single_match_observed_latency_can_set_production_threshold"] = False
    result["diagnostic_window_can_authorize_claim"] = False
    result["diagnostic_window_can_authorize_professional_finding"] = False
    result["review_hits"] = sorted(review_hits)
    if adapted:
        result["status"] = "REVIEW_REQUIRED"
        result["module_status"] = "REVIEW_REQUIRED"
    result["canonical_event_count"] = "UNKNOWN"
    result["true_action_count"] = "UNKNOWN"
    result["production_release"] = False
    return result
