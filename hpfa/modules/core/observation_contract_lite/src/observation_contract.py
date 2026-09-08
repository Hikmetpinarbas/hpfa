from __future__ import annotations

import hashlib
import json
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

# Capability vocabulary is construct-facing and deliberately more expressive than
# the coarse observation-layer ladder. Layers remain the backward-compatible
# structural gate; capabilities state what the construct actually needs.
CAP_AGGREGATE = "AGGREGATE"
CAP_ACTION = "ACTION"
CAP_ACTOR = "ACTOR"
CAP_TEMPORAL = "TEMPORAL"
CAP_SPATIAL = "SPATIAL"
CAP_OUTCOME = "OUTCOME"
CAP_CONTEXT = "CONTEXT"
CAP_RELATIONAL = "RELATIONAL"
CAP_PROVIDER_DERIVED = "PROVIDER_DERIVED"
CAP_PROVENANCE = "PROVENANCE"
CAP_PROCESS = "PROCESS"
CAP_STATE_TRANSITION = "STATE_TRANSITION"
CAP_TRACKING_VIDEO_PHYSICAL = "TRACKING_VIDEO_PHYSICAL"

ALLOWED_OBSERVATION_CAPABILITIES = {
    CAP_AGGREGATE,
    CAP_ACTION,
    CAP_ACTOR,
    CAP_TEMPORAL,
    CAP_SPATIAL,
    CAP_OUTCOME,
    CAP_CONTEXT,
    CAP_RELATIONAL,
    CAP_PROVIDER_DERIVED,
    CAP_PROVENANCE,
    CAP_PROCESS,
    CAP_STATE_TRANSITION,
    CAP_TRACKING_VIDEO_PHYSICAL,
}

LAYER_DEFAULT_CAPABILITIES = {
    L0: {CAP_AGGREGATE},
    L1: {CAP_ACTION},
    L2: {CAP_TEMPORAL},
    L3: {CAP_SPATIAL},
    L4: {CAP_RELATIONAL},
    L5: {CAP_CONTEXT, CAP_PROCESS},
    L6: {CAP_OUTCOME},
    L7: {CAP_STATE_TRANSITION},
    L8: {CAP_TRACKING_VIDEO_PHYSICAL},
}

# These tokens are evidence prerequisites, not claims. Unknown values fail closed
# so a typo cannot silently widen the claim ceiling.
ALLOWED_FORBIDDEN_WITHOUT = {
    "TRACKING",
    "VIDEO",
    "TEMPORAL_SEMANTICS",
    "COORDINATE_FRAME",
    "ATTACKING_DIRECTION",
    "IDENTITY_ADMISSION",
    "REFLECTION_CONTROL",
    "PROVIDER_SEMANTICS",
    "POSSESSION_PROCESS_ADMISSION",
    "DEPENDENCY_CONTROL",
    "INDEPENDENCE_ADMISSION",
}

OBSERVATION_FINGERPRINT_FIELDS = (
    "required_observation_layers",
    "required_surface_semantics",
    "required_observation_capabilities",
    "optional_observation_capabilities",
    "forbidden_without",
    "tracking_video_required",
    "claim_ceiling",
    "does_not_measure",
    "forbidden_claims",
)


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _derived_capabilities(layers: list[str]) -> list[str]:
    capabilities = {CAP_PROVENANCE}
    for layer in layers:
        capabilities.update(LAYER_DEFAULT_CAPABILITIES.get(layer, set()))
    return sorted(capabilities)


def observation_semantic_fingerprint(row: dict[str, Any]) -> str:
    payload = {field: row.get(field) for field in OBSERVATION_FINGERPRINT_FIELDS}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assess_observation_contract(row: dict[str, Any]) -> dict[str, Any]:
    """Assess construct-specific observation requirements without promoting truth.

    Legacy `event_only_compatible` is accepted only as a migration signal. It is
    never used as the product-wide capability ceiling.
    """
    metric_id = str(row.get("metric_id") or "UNKNOWN").strip() or "UNKNOWN"
    explicit_layers = _clean_list(row.get("required_observation_layers"))
    surface_semantics = _clean_list(row.get("required_surface_semantics"))
    explicit_required_capabilities = _clean_list(row.get("required_observation_capabilities"))
    optional_capabilities = _clean_list(row.get("optional_observation_capabilities"))
    forbidden_without = _clean_list(row.get("forbidden_without"))
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
        if legacy_flag is True:
            explicit_layers = [L1]
            migration_state = "LEGACY_EVENT_ONLY_SHADOW"
        else:
            hard.append(f"required_observation_layers_missing:{metric_id}")

    if explicit_required_capabilities:
        required_capabilities = sorted(set(explicit_required_capabilities) | {CAP_PROVENANCE})
        unknown_required = sorted(set(required_capabilities) - ALLOWED_OBSERVATION_CAPABILITIES)
        if unknown_required:
            hard.append(
                f"unknown_required_observation_capability:{metric_id}:{','.join(unknown_required)}"
            )
        capability_state = "EXPLICIT_CAPABILITY_MANIFEST"
    else:
        required_capabilities = _derived_capabilities(explicit_layers)
        capability_state = "DERIVED_FROM_OBSERVATION_LAYERS"

    unknown_optional = sorted(set(optional_capabilities) - ALLOWED_OBSERVATION_CAPABILITIES)
    if unknown_optional:
        hard.append(
            f"unknown_optional_observation_capability:{metric_id}:{','.join(unknown_optional)}"
        )

    overlap = sorted(set(required_capabilities) & set(optional_capabilities))
    if overlap:
        hard.append(f"required_optional_capability_overlap:{metric_id}:{','.join(overlap)}")

    unknown_forbidden_without = sorted(set(forbidden_without) - ALLOWED_FORBIDDEN_WITHOUT)
    if unknown_forbidden_without:
        hard.append(
            f"unknown_forbidden_without_requirement:{metric_id}:{','.join(unknown_forbidden_without)}"
        )

    if PHYSICAL_TRUTH_LAYER in explicit_layers and not tracking_video_required:
        hard.append(f"tracking_video_requirement_missing_for_l8:{metric_id}")
    if tracking_video_required and PHYSICAL_TRUTH_LAYER not in explicit_layers:
        hard.append(f"tracking_video_required_without_l8:{metric_id}")
    if CAP_TRACKING_VIDEO_PHYSICAL in required_capabilities and PHYSICAL_TRUTH_LAYER not in explicit_layers:
        hard.append(f"physical_capability_requires_l8:{metric_id}")
    if PHYSICAL_TRUTH_LAYER in explicit_layers and CAP_TRACKING_VIDEO_PHYSICAL not in required_capabilities:
        hard.append(f"l8_requires_physical_capability_manifest:{metric_id}")

    if tracking_video_required and not ({"TRACKING", "VIDEO"} & set(forbidden_without)):
        # Backward-compatible rows can still pass while being explicitly flagged for
        # migration; an explicit capability manifest must state the physical evidence gate.
        if capability_state == "EXPLICIT_CAPABILITY_MANIFEST":
            hard.append(f"tracking_video_forbidden_without_gate_missing:{metric_id}")
        else:
            review.append(f"tracking_video_forbidden_without_gate_not_declared:{metric_id}")

    rich_nonphysical = any(layer in explicit_layers for layer in {L2, L3, L4, L5, L6, L7})
    if rich_nonphysical and not surface_semantics:
        hard.append(f"required_surface_semantics_missing:{metric_id}")

    # Capability-specific evidence prerequisites. These checks do not prove the
    # prerequisites are satisfied at runtime; they ensure the construct declares them.
    declared_prerequisites = set(forbidden_without)
    if capability_state == "EXPLICIT_CAPABILITY_MANIFEST":
        if CAP_TEMPORAL in required_capabilities and "TEMPORAL_SEMANTICS" not in declared_prerequisites:
            hard.append(f"temporal_capability_prerequisite_missing:{metric_id}")
        if CAP_SPATIAL in required_capabilities and "COORDINATE_FRAME" not in declared_prerequisites:
            hard.append(f"spatial_capability_coordinate_frame_missing:{metric_id}")
        if CAP_RELATIONAL in required_capabilities and "IDENTITY_ADMISSION" not in declared_prerequisites:
            hard.append(f"relational_capability_identity_admission_missing:{metric_id}")
        if CAP_RELATIONAL in required_capabilities and "REFLECTION_CONTROL" not in declared_prerequisites:
            hard.append(f"relational_capability_reflection_control_missing:{metric_id}")
        if CAP_PROVIDER_DERIVED in required_capabilities and "PROVIDER_SEMANTICS" not in declared_prerequisites:
            hard.append(f"provider_derived_capability_semantics_missing:{metric_id}")
        if CAP_STATE_TRANSITION in required_capabilities and "DEPENDENCY_CONTROL" not in declared_prerequisites:
            hard.append(f"state_transition_dependency_control_missing:{metric_id}")

    legacy_shadow = PHYSICAL_TRUTH_LAYER not in explicit_layers
    return {
        "metric_id": metric_id,
        "observation_model": OBSERVATION_MODEL,
        "required_observation_layers": explicit_layers,
        "required_surface_semantics": surface_semantics,
        "required_observation_capabilities": required_capabilities,
        "optional_observation_capabilities": sorted(set(optional_capabilities)),
        "forbidden_without": sorted(set(forbidden_without)),
        "tracking_video_required": tracking_video_required,
        "legacy_event_only_shadow_compatible": legacy_shadow,
        "event_only_is_product_ceiling": False,
        "migration_state": migration_state,
        "capability_manifest_state": capability_state,
        "observation_semantic_fingerprint_sha256": observation_semantic_fingerprint(row),
        "hard_block_hits": hard,
        "review_hits": review,
        "status": "FAIL_CLOSED" if hard else ("REVIEW_REQUIRED" if review else "PASS"),
    }


def normalize_dictionary_for_legacy_impl(
    dictionary: dict[str, Any],
    metric_policy: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    """Translate explicit enriched contracts into a compatibility shadow for v7.

    The old implementation can continue running while enriched observation layers
    and capability manifests become authoritative. Pure legacy rows remain unchanged.
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
        if assessment["hard_block_hits"]:
            continue
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
