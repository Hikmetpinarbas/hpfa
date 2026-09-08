from __future__ import annotations

from copy import deepcopy
from typing import Any

OBSERVATION_MODEL = "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"

L0 = "L0_AGGREGATE_SURFACE"
L1 = "L1_ACTION_OBSERVATION"
L2 = "L2_TEMPORAL_OBSERVATION"
L3 = "L3_SPATIAL_OBSERVATION"
L4 = "L4_RELATIONAL_COOCCURRENCE_OBSERVATION"
L5 = "L5_PROCESS_CONTEXT_OBSERVATION"
L6 = "L6_CONSEQUENCE_OPPONENT_RESPONSE_OBSERVATION"
L7 = "L7_RECONSTRUCTED_STATE_TRANSITION_CANDIDATE"
L8 = "L8_TRACKING_VIDEO_PHYSICAL_OFF_BALL_STATE"

ALLOWED_OBSERVATION_LAYERS = {L0, L1, L2, L3, L4, L5, L6, L7, L8}
PHYSICAL_TRUTH_LAYER = L8


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def assess_observation_contract(row: dict[str, Any]) -> dict[str, Any]:
    """Assess construct-specific observation requirements without promoting truth.

    Legacy `event_only_compatible` is accepted only as a migration signal. It is
    never used as the product-wide capability ceiling.
    """
    metric_id = str(row.get("metric_id") or "UNKNOWN").strip() or "UNKNOWN"
    explicit_layers = _clean_list(row.get("required_observation_layers"))
    surface_semantics = _clean_list(row.get("required_surface_semantics"))
    tracking_video_required = row.get("tracking_video_required") is True
    legacy_flag = row.get("event_only_compatible")

    hard: list[str] = []
    review: list[str] = []
    migration_state = "EXPLICIT_OBSERVATION_CONTRACT"

    if explicit_layers:
        unknown = sorted(set(explicit_layers) - ALLOWED_OBSERVATION_LAYERS)
        if unknown:
            hard.append(f"unknown_observation_layer:{metric_id}:{','.join(unknown)}")
    else:
        # Backward-compatible read of existing contracts. `True` means only that
        # the legacy record did not request tracking/video truth; it does not mean
        # the construct is limited to action rows.
        if legacy_flag is True:
            explicit_layers = [L1]
            migration_state = "LEGACY_EVENT_ONLY_SHADOW"
            review.append(f"legacy_event_only_contract_requires_migration:{metric_id}")
        else:
            hard.append(f"required_observation_layers_missing:{metric_id}")

    if PHYSICAL_TRUTH_LAYER in explicit_layers and not tracking_video_required:
        hard.append(f"tracking_video_requirement_missing_for_l8:{metric_id}")
    if tracking_video_required and PHYSICAL_TRUTH_LAYER not in explicit_layers:
        hard.append(f"tracking_video_required_without_l8:{metric_id}")

    # Rich L2-L7 constructs must state which surface semantics are required.
    rich_nonphysical = any(layer in explicit_layers for layer in {L2, L3, L4, L5, L6, L7})
    if rich_nonphysical and not surface_semantics:
        hard.append(f"required_surface_semantics_missing:{metric_id}")

    legacy_shadow = PHYSICAL_TRUTH_LAYER not in explicit_layers
    return {
        "metric_id": metric_id,
        "observation_model": OBSERVATION_MODEL,
        "required_observation_layers": explicit_layers,
        "required_surface_semantics": surface_semantics,
        "tracking_video_required": tracking_video_required,
        "legacy_event_only_shadow_compatible": legacy_shadow,
        "event_only_is_product_ceiling": False,
        "migration_state": migration_state,
        "hard_block_hits": hard,
        "review_hits": review,
        "status": "FAIL_CLOSED" if hard else ("REVIEW_REQUIRED" if review else "PASS"),
    }


def normalize_dictionary_for_legacy_impl(
    dictionary: dict[str, Any],
    metric_policy: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    """Create a compatibility shadow for the v7 provider dictionary implementation.

    Only explicit enriched-observation contracts are translated. Pure legacy rows
    are left unchanged so old fail-closed tests and old semantics remain intact.
    """
    normalized_dictionary = deepcopy(dictionary)
    normalized_policy = deepcopy(metric_policy) if metric_policy is not None else None
    assessments: list[dict[str, Any]] = []

    policy_index: dict[str, dict[str, Any]] = {}
    if normalized_policy is not None:
        for policy_row in normalized_policy.get("metrics", []):
            metric_id = str(policy_row.get("metric_id") or "").strip()
            if metric_id:
                policy_index[metric_id] = policy_row

    for row in normalized_dictionary.get("metrics", []):
        assessment = assess_observation_contract(row)
        assessments.append(assessment)

        # Never make a hard-blocked enriched contract look legacy-compatible.
        if assessment["hard_block_hits"]:
            continue

        # Legacy rows remain untouched. Explicit enriched rows receive only a
        # compatibility shadow for the old implementation; the original semantic
        # model is preserved in the assessment returned to the caller.
        if assessment["migration_state"] != "EXPLICIT_OBSERVATION_CONTRACT":
            continue

        row["event_only_compatible"] = assessment["legacy_event_only_shadow_compatible"]
        upstream = row.get("upstream_bindings") or {}
        if isinstance(upstream, dict):
            policy_id = str(upstream.get("metric_policy_id") or "").strip()
            policy_row = policy_index.get(policy_id)
            if policy_row is not None:
                policy_assessment = assess_observation_contract(policy_row)
                if not policy_assessment["hard_block_hits"]:
                    policy_row["event_only_compatible"] = policy_assessment[
                        "legacy_event_only_shadow_compatible"
                    ]

    return normalized_dictionary, normalized_policy, assessments
