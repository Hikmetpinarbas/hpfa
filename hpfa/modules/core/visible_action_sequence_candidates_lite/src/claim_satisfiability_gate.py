from __future__ import annotations

from typing import Any, Iterable

MODULE_ID = "claim_satisfiability_gate_v1"
GATE_CEILING = "MATCH_LOCAL_CLAIM_SATISFIABILITY_ASSESSMENT_ONLY"

SATISFIED = "SATISFIED_WITH_CEILING"
UNSATISFIED = "UNSATISFIED_MISSING_REQUIRED_CAPABILITY"
UNSATISFIABLE = "UNSATISFIABLE_CURRENT_PRODUCT_CEILING"
REVIEW = "REVIEW_REQUIRED_UNKNOWN_CLAIM_FAMILY"

CLAIM_FAMILY_SPECS: dict[str, dict[str, Any]] = {
    "MATCH_LOCAL_VISIBLE_VARIATION": {
        "required_capabilities": {"ACTION", "TEMPORAL", "OUTCOME", "PROVENANCE"},
        "claim_ceiling": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
    },
    "PROGRESSION_ACCESS_DESCRIPTION": {
        "required_capabilities": {"ACTION", "TEMPORAL", "PROVIDER_DERIVED", "PROVENANCE"},
        "claim_ceiling": "MATCH_LOCAL_PROVIDER_SEMANTIC_PROGRESSION_ACCESS_ONLY",
    },
    "RETENTION_LOSS_DESCRIPTION": {
        "required_capabilities": {"ACTION", "TEMPORAL", "PROVENANCE"},
        "claim_ceiling": "MATCH_LOCAL_VISIBLE_RETENTION_LOSS_ONLY",
    },
    "PROCESS_PARTICIPATION_DESCRIPTION": {
        "required_capabilities": {"PROCESS", "ACTOR", "PROVENANCE"},
        "claim_ceiling": "MATCH_LOCAL_VISIBLE_PROCESS_PARTICIPATION_ONLY",
    },
    "SPATIAL_ZONE_DESCRIPTION": {
        "required_capabilities": {"ACTION", "SPATIAL", "PROVENANCE"},
        "claim_ceiling": "MATCH_LOCAL_ADMITTED_SPATIAL_DESCRIPTION_ONLY",
    },
    "TRACKING_GEOMETRY_DESCRIPTION": {
        "required_capabilities": {"TRACKING_VIDEO_PHYSICAL", "PROVENANCE"},
        "claim_ceiling": "TRACKING_VIDEO_BOUND_PHYSICAL_OBSERVATION_ONLY",
    },
    "MATCH_LOCAL_RECURRENCE_CANDIDATE": {
        "required_capabilities": {"ACTION", "TEMPORAL", "PROVENANCE"},
        "claim_ceiling": "MATCH_LOCAL_RECURRENCE_CANDIDATE_ONLY",
        "requires_independent_support": True,
        "requires_episode_spread": True,
    },
    "CAUSALITY": {
        "required_capabilities": set(),
        "claim_ceiling": "NO_CAUSAL_CLAIM_OUTPUT",
        "current_product_unsatisfiable": True,
    },
    "TACTICAL_PATTERN_TRUTH": {
        "required_capabilities": set(),
        "claim_ceiling": "NO_TACTICAL_PATTERN_TRUTH",
        "current_product_unsatisfiable": True,
    },
    "COACH_INTENTION": {
        "required_capabilities": set(),
        "claim_ceiling": "NO_COACH_INTENTION_CLAIM",
        "current_product_unsatisfiable": True,
    },
    "CROSS_MATCH_GENERALIZATION": {
        "required_capabilities": set(),
        "claim_ceiling": "NO_CROSS_MATCH_GENERALIZATION",
        "current_product_unsatisfiable": True,
    },
}


def _normalized(values: Iterable[Any] | None) -> set[str]:
    return {
        str(value or "").strip().upper()
        for value in (values or [])
        if str(value or "").strip()
    }


def assess_claim_satisfiability(
    claim_family: str,
    *,
    admitted_capabilities: Iterable[Any] | None,
    admitted_independent_support_count: int = 0,
    dependency_independence_proven: bool = False,
    statistical_independence_proven: bool = False,
    episode_spread_observed: bool = False,
) -> dict[str, Any]:
    """Assess whether current admitted evidence can support a bounded claim family.

    This is a one-way safety gate. It may preserve a bounded claim family or lower it,
    with authority limited to claim-scope validation; professional EMIT and claim strength follow admitted evidence
    ceiling, convert provider semantics into tactical truth, or infer causality.
    """
    family = str(claim_family or "").strip().upper()
    admitted = _normalized(admitted_capabilities)
    spec = CLAIM_FAMILY_SPECS.get(family)

    base = {
        "module_id": MODULE_ID,
        "claim_family": family or "UNKNOWN",
        "admitted_capabilities": sorted(admitted),
        "creates_new_evidence": False,
        "gate_can_authorize_emit": False,
        "gate_can_strengthen_claim_ceiling": False,
        "absence_is_counterevidence": False,
        "provider_label_is_tactical_truth": False,
        "same_timestamp_is_total_order": False,
        "recurrence_is_causality": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "gate_claim_ceiling": GATE_CEILING,
    }

    if spec is None:
        return {
            **base,
            "state": REVIEW,
            "required_capabilities": [],
            "missing_required_capabilities": [],
            "claim_ceiling": "NO_CLAIM_OUTPUT_PENDING_REVIEW",
            "noncompensating_requirement_failures": ["UNKNOWN_CLAIM_FAMILY"],
        }

    required = set(spec.get("required_capabilities") or set())
    missing = sorted(required - admitted)
    failures: list[str] = []

    if spec.get("current_product_unsatisfiable") is True:
        state = UNSATISFIABLE
        failures.append("CURRENT_PRODUCT_CLAIM_CEILING_FORBIDS_FAMILY")
    else:
        if missing:
            failures.append("REQUIRED_OBSERVATION_CAPABILITY_MISSING")

        if spec.get("requires_independent_support") is True:
            if int(admitted_independent_support_count or 0) < 2:
                failures.append("INDEPENDENT_SUPPORT_COUNT_LT_2")
            if dependency_independence_proven is not True:
                failures.append("DEPENDENCY_INDEPENDENCE_NOT_PROVEN")
            if statistical_independence_proven is not True:
                failures.append("STATISTICAL_INDEPENDENCE_NOT_PROVEN")

        if spec.get("requires_episode_spread") is True and episode_spread_observed is not True:
            failures.append("EPISODE_SPREAD_NOT_OBSERVED")

        state = SATISFIED if not failures else UNSATISFIED

    return {
        **base,
        "state": state,
        "required_capabilities": sorted(required),
        "missing_required_capabilities": missing,
        "claim_ceiling": str(spec.get("claim_ceiling") or "NO_CLAIM_OUTPUT"),
        "noncompensating_requirement_failures": sorted(set(failures)),
        "admitted_independent_support_count": int(admitted_independent_support_count or 0),
        "dependency_independence_proven": dependency_independence_proven is True,
        "statistical_independence_proven": statistical_independence_proven is True,
        "episode_spread_observed": episode_spread_observed is True,
    }
