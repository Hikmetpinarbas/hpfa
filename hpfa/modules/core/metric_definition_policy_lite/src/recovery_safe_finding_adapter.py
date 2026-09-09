from __future__ import annotations

from copy import deepcopy
from typing import Any

from hpfa.modules.core.metric_definition_policy_lite.src.progression_safe_finding_projection import (
    build_progression_safe_finding_projection,
)

MODULE_ID = "recovery_safe_finding_projection_v1"
RECOVERY_MODULE_ID = "recovery_yield_construct_v1"
PROGRESSION_MODULE_ID = "progression_effectiveness_construct_v1"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_RECOVERY_YIELD_FINDING_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _fail(*blocks: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "finding_candidate": None,
        "finding_candidate_count": 0,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": [],
        "engineering_envelope_complete": False,
        "physical_active_match_evidence_present": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "event_only_is_product_ceiling": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _adapt_recovery_to_existing_safe_finding_schema(
    recovery_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    if recovery_payload.get("module_id") != RECOVERY_MODULE_ID:
        blocks.append("recovery_construct_module_id_mismatch")
    if recovery_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("recovery_construct_canonical_event_count_claimed")
    if recovery_payload.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append("recovery_construct_true_action_count_claimed")
    if recovery_payload.get("production_release") is True:
        blocks.append("recovery_construct_production_release_claimed")
    if recovery_payload.get("professional_finding_emitted") is True:
        blocks.append("upstream_professional_finding_claimed")
    if recovery_payload.get("claim_output_allowed") is True:
        blocks.append("upstream_claim_output_allowed")
    if recovery_payload.get("hard_block_hits"):
        blocks.append("recovery_construct_hard_blocks_present")
    if blocks:
        raise ValueError(";".join(sorted(set(blocks))))

    construct = recovery_payload.get("construct_candidate")
    if not isinstance(construct, dict):
        return {
            "module_id": PROGRESSION_MODULE_ID,
            "status": recovery_payload.get("status") or "REVIEW_REQUIRED",
            "construct_candidate": None,
            "hard_block_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
        }

    required_false_locks = {
        "recovery_yield_score_emitted": "recovery_yield_score_lock_missing",
        "same_provider_reflection_adds_independent_vote": "same_provider_independence_lock_missing",
        "missing_consequence_is_counterevidence": "missingness_counterevidence_lock_missing",
        "construct_validity_truth": "construct_validity_truth_claimed",
        "recovery_quality_truth": "recovery_quality_truth_claimed",
        "possession_gain_truth": "possession_gain_truth_claimed",
        "team_control_truth": "team_control_truth_claimed",
        "causal_truth": "causal_truth_claimed",
        "no_visible_progression_followup_is_failure": "no_visible_progression_followup_failure_lock_missing",
        "no_visible_progression_followup_is_counterevidence": "no_visible_progression_followup_counterevidence_lock_missing",
        "conversion_candidate_is_sequence_truth": "recovery_progression_sequence_truth_claimed",
        "conversion_candidate_is_possession_truth": "recovery_progression_possession_truth_claimed",
        "conversion_candidate_is_causal_truth": "recovery_progression_causal_truth_claimed",
        "source_row_order_is_temporal_truth": "source_row_order_temporal_truth_claimed",
        "same_time_is_ordered": "same_time_order_truth_claimed",
    }
    lock_blocks = [name for field, name in required_false_locks.items() if construct.get(field) is not False]
    if lock_blocks:
        raise ValueError(";".join(sorted(set(lock_blocks))))

    adapted = deepcopy(construct)
    adapted.update({
        "eligible_progression_trace_candidate_count": construct.get("eligible_recovery_trace_candidate_count"),
        "evaluable_progression_consequence_candidate_count": construct.get("evaluable_recovery_consequence_candidate_count"),
        "progression_consequence_coverage_rate_candidate": construct.get("recovery_consequence_coverage_rate_candidate"),
        "visible_positive_follow_up_candidate_count": construct.get("visible_same_team_yield_candidate_count"),
        "visible_adverse_handover_candidate_count": construct.get("visible_adverse_post_recovery_handover_candidate_count"),
        "team_progression_effectiveness_profile_candidates": list(construct.get("team_recovery_yield_profile_candidates") or []),
        "actor_progression_effectiveness_profile_candidates": list(construct.get("actor_recovery_yield_profile_candidates") or []),
        "effectiveness_score_emitted": False,
        "player_quality_truth": False,
    })
    return {
        "module_id": PROGRESSION_MODULE_ID,
        "status": recovery_payload.get("status") or "REVIEW_REQUIRED",
        "construct_candidate": adapted,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
    }


def build_recovery_safe_finding_projection(
    recovery_payload: dict[str, Any],
) -> dict[str, Any]:
    """Reuse the admitted Safe Finding envelope for Recovery Yield without a parallel engine."""
    try:
        adapted = _adapt_recovery_to_existing_safe_finding_schema(recovery_payload)
    except ValueError as exc:
        return _fail(*[item for item in str(exc).split(";") if item])

    projected = build_progression_safe_finding_projection(adapted)
    result = deepcopy(projected)
    result["module_id"] = MODULE_ID
    result["claim_ceiling"] = CLAIM_CEILING
    result["event_only_is_product_ceiling"] = False

    finding = result.get("finding_candidate")
    construct = recovery_payload.get("construct_candidate")
    if not isinstance(finding, dict) or not isinstance(construct, dict):
        return result

    conversions = [
        row for row in (construct.get("visible_recovery_to_progression_candidates") or [])
        if isinstance(row, dict)
    ]
    conversion_refs = sorted({
        _clean(row.get("recovery_trace_candidate_id"))
        for row in conversions
        if _clean(row.get("recovery_trace_candidate_id"))
    })
    progression_refs = sorted({
        _clean(row.get("progression_trace_candidate_id"))
        for row in conversions
        if _clean(row.get("progression_trace_candidate_id"))
    })

    what_visible = {
        "eligible_recovery_trace_candidate_count": construct.get("eligible_recovery_trace_candidate_count"),
        "evaluable_recovery_consequence_candidate_count": construct.get("evaluable_recovery_consequence_candidate_count"),
        "recovery_consequence_coverage_rate_candidate": construct.get("recovery_consequence_coverage_rate_candidate"),
        "visible_same_team_yield_candidate_count": construct.get("visible_same_team_yield_candidate_count"),
        "visible_adverse_post_recovery_handover_candidate_count": construct.get("visible_adverse_post_recovery_handover_candidate_count"),
        "unresolved_or_missing_consequence_candidate_count": construct.get("unresolved_or_missing_consequence_candidate_count"),
        "recovery_progression_conversion_eligible_recovery_trace_candidate_count": construct.get("recovery_progression_conversion_eligible_recovery_trace_candidate_count"),
        "visible_recovery_to_progression_candidate_count": construct.get("visible_recovery_to_progression_candidate_count"),
        "visible_recovery_to_progression_rate_candidate": construct.get("visible_recovery_to_progression_rate_candidate"),
        "no_visible_progression_followup_candidate_count": construct.get("no_visible_progression_followup_candidate_count"),
    }
    support = {
        "support_refs": list(finding.get("support_refs") or []),
        "team_recovery_yield_profile_candidates": list(construct.get("team_recovery_yield_profile_candidates") or []),
        "actor_recovery_yield_profile_candidates": list(construct.get("actor_recovery_yield_profile_candidates") or []),
        "visible_recovery_to_progression_recovery_trace_candidate_refs": conversion_refs,
        "visible_recovery_to_progression_progression_trace_candidate_refs": progression_refs,
        "recovery_progression_conversion_is_independent_support": False,
    }
    counterevidence = {
        "refs": list(finding.get("counterevidence_refs") or []),
        "unresolved_refs": list(finding.get("unresolved_refs") or []),
        "absence_is_confirmation": False,
        "missing_follow_up_is_failure": False,
        "no_visible_progression_followup_is_failure": False,
        "no_visible_progression_followup_is_counterevidence": False,
    }
    safe_meaning = (
        "Describe the match-local visible recovery/interception opportunity set, its positive/adverse/unresolved consequence distribution, "
        "and separately the admitted positive-time same-team same-episode recovery-to-progression bindings; none is recovery quality, possession, sequence, tactical or causal truth."
    )
    forbidden = [
        "recovery quality truth",
        "possession gain truth",
        "team control truth",
        "individual causal value",
        "tactical plan truth",
        "sequence truth from recovery-to-progression binding",
        "missing consequence as counterevidence",
        "no visible progression follow-up as failure",
        "conversion-rate complement as failure rate",
    ]

    finding.update({
        "finding_candidate_id": "rsf_" + _clean(construct.get("construct_candidate_id") or "recovery")[-24:],
        "construct_candidate_id": construct.get("construct_candidate_id"),
        "construct_target": "RECOVERY_YIELD",
        "what_visible": what_visible,
        "support": support,
        "counterevidence": counterevidence,
        "safe_meaning": safe_meaning,
        "forbidden_inference": forbidden,
        "WHAT_VISIBLE": what_visible,
        "SUPPORT": support,
        "COUNTEREVIDENCE": counterevidence,
        "SAFE_MEANING": safe_meaning,
        "FORBIDDEN_INFERENCE": forbidden,
        "same_provider_support_is_independent_vote": False,
        "independent_support_vote_count": 0,
        "physical_active_match_evidence_required": True,
        "physical_active_match_evidence_present": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "claim_ceiling": CLAIM_CEILING,
    })
    result["finding_candidate"] = finding
    result["physical_active_match_evidence_present"] = False
    result["professional_finding_emitted"] = False
    result["claim_output_allowed"] = False
    result["canonical_event_count"] = "UNKNOWN"
    result["true_action_count"] = "UNKNOWN"
    result["production_release"] = False
    return result
