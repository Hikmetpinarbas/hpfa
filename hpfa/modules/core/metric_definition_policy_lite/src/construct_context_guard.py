from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODULE_ID = "construct_context_guard_v1"
OBSERVATION_MODEL = "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
CLAIM_CEILING = "CONSTRUCT_CONTEXT_COMPARABILITY_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalized(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(sorted({_clean(item) for item in value if _clean(item)}))
    if isinstance(value, dict):
        return tuple(sorted((str(key), _normalized(val)) for key, val in value.items()))
    return _clean(value)


def load_guard(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("construct_context_guard_unreadable") from exc
    if not isinstance(payload, dict) or payload.get("module_id") != MODULE_ID:
        raise ValueError("construct_context_guard_invalid")
    if payload.get("observation_model") != OBSERVATION_MODEL:
        raise ValueError("construct_context_guard_observation_model_mismatch")
    return payload


def _dimension_state(dimension: str, left: dict[str, Any], right: dict[str, Any]) -> str:
    left_value = _normalized(left.get(dimension))
    right_value = _normalized(right.get(dimension))
    if left_value in {"", (), None} or right_value in {"", (), None}:
        return "MISSING"
    if left_value == right_value:
        return "ALIGNED"
    if dimension in {"denominator_set_id", "context_policy_id", "required_event_families", "construct_target"}:
        return "BLOCKING_MISMATCH"
    if dimension in {"observation_window", "entity_scope", "team_scope"}:
        return "CONTEXT_MISMATCH"
    if dimension in {"period_scope", "source_surface_roles"}:
        return "WARNING_MISMATCH"
    if dimension == "dependency_group":
        return "DEPENDENCY_DIFFERENT"
    return "CONTEXT_MISMATCH"


def assess_construct_comparison(
    left: dict[str, Any],
    right: dict[str, Any],
    guard: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    dimensions = guard.get("required_comparability_dimensions") or []
    if not isinstance(dimensions, list) or not dimensions:
        blocks.append("required_comparability_dimensions_missing")
        dimensions = []

    target_families = {_clean(item) for item in (guard.get("target_construct_families") or []) if _clean(item)}
    left_target = _clean(left.get("construct_target"))
    right_target = _clean(right.get("construct_target"))
    if target_families and (left_target not in target_families or right_target not in target_families):
        reviews.append("construct_target_outside_guard_registry")

    dimension_states: dict[str, str] = {}
    for dimension in dimensions:
        name = _clean(dimension)
        if not name:
            blocks.append("blank_comparability_dimension")
            continue
        state = _dimension_state(name, left, right)
        dimension_states[name] = state
        if state == "MISSING":
            blocks.append(f"missing_required_dimension:{name}")
        elif state == "BLOCKING_MISMATCH":
            blocks.append(f"comparison_blocked:{name}")
        elif state in {"CONTEXT_MISMATCH", "WARNING_MISMATCH"}:
            reviews.append(f"construct_context_warning:{name}")

    left_dependency = _clean(left.get("dependency_group"))
    right_dependency = _clean(right.get("dependency_group"))
    shared_dependency = bool(left_dependency and left_dependency == right_dependency)
    same_provider_reflection = shared_dependency or (
        _clean(left.get("provenance_root"))
        and _clean(left.get("provenance_root")) == _clean(right.get("provenance_root"))
    )

    if blocks:
        status = "COMPARISON_BLOCKED"
        comparison_admitted = False
    elif reviews:
        status = "CONSTRUCT_CONTEXT_WARNING"
        comparison_admitted = False
    else:
        status = "CONSTRUCT_COMPARABLE_CANDIDATE"
        comparison_admitted = True

    return {
        "module_id": MODULE_ID,
        "status": status,
        "comparison_admitted": comparison_admitted,
        "construct_target": left_target if left_target == right_target else None,
        "dimension_states": dimension_states,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "shared_dependency_group": shared_dependency,
        "dependent_support_only": same_provider_reflection,
        "same_provider_reflection_adds_independent_vote": False,
        "independent_support_vote_count": 0 if same_provider_reflection else None,
        "missing_context_is_counterevidence": False,
        "construct_validity_truth": False,
        "metric_validity_truth": False,
        "causal_truth": False,
        "tactical_truth": False,
        "event_only_is_product_ceiling": False,
        "observation_model": OBSERVATION_MODEL,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
