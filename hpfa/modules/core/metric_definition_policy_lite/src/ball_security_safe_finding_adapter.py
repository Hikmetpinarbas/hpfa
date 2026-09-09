from __future__ import annotations

from copy import deepcopy
from typing import Any

from hpfa.modules.core.metric_definition_policy_lite.src.progression_safe_finding_projection import (
    build_progression_safe_finding_projection,
)

MODULE_ID = "ball_security_safe_finding_projection_v1"
BALL_SECURITY_MODULE_ID = "ball_security_construct_v1"
PROGRESSION_MODULE_ID = "progression_effectiveness_construct_v1"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_BALL_SECURITY_FINDING_CANDIDATE_ONLY"


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


def _adapt_ball_security_to_existing_safe_finding_schema(
    ball_security_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    if ball_security_payload.get("module_id") != BALL_SECURITY_MODULE_ID:
        blocks.append("ball_security_construct_module_id_mismatch")
    if ball_security_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("ball_security_construct_canonical_event_count_claimed")
    if ball_security_payload.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append("ball_security_construct_true_action_count_claimed")
    if ball_security_payload.get("production_release") is True:
        blocks.append("ball_security_construct_production_release_claimed")
    if ball_security_payload.get("professional_finding_emitted") is True:
        blocks.append("upstream_professional_finding_claimed")
    if ball_security_payload.get("claim_output_allowed") is True:
        blocks.append("upstream_claim_output_allowed")
    if ball_security_payload.get("hard_block_hits"):
        blocks.append("ball_security_construct_hard_blocks_present")
    if blocks:
        raise ValueError(";".join(sorted(set(blocks))))

    construct = ball_security_payload.get("construct_candidate")
    if not isinstance(construct, dict):
        return {
            "module_id": PROGRESSION_MODULE_ID,
            "status": ball_security_payload.get("status") or "REVIEW_REQUIRED",
            "construct_candidate": None,
            "hard_block_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
        }

    required_false_locks = {
        "ball_security_score_emitted": "ball_security_score_lock_missing",
        "same_provider_reflection_adds_independent_vote": "same_provider_independence_lock_missing",
        "missing_consequence_is_counterevidence": "missingness_counterevidence_lock_missing",
        "construct_validity_truth": "construct_validity_truth_claimed",
        "player_quality_truth": "player_quality_truth_claimed",
        "team_control_truth": "team_control_truth_claimed",
        "causal_truth": "causal_truth_claimed",
        "explicit_turnover_is_denominator_member": "explicit_turnover_denominator_inflation_claimed",
    }
    lock_blocks = [name for field, name in required_false_locks.items() if construct.get(field) is not False]
    if lock_blocks:
        raise ValueError(";".join(sorted(set(lock_blocks))))

    adapted = deepcopy(construct)
    adapted.update({
        "eligible_progression_trace_candidate_count": construct.get("eligible_ball_use_trace_candidate_count"),
        "evaluable_progression_consequence_candidate_count": construct.get("evaluable_ball_security_consequence_candidate_count"),
        "progression_consequence_coverage_rate_candidate": construct.get("ball_security_consequence_coverage_rate_candidate"),
        "visible_positive_follow_up_candidate_count": construct.get("visible_retained_follow_up_candidate_count"),
        "visible_adverse_handover_candidate_count": construct.get("visible_adverse_handover_candidate_count"),
        "team_progression_effectiveness_profile_candidates": list(construct.get("team_ball_security_profile_candidates") or []),
        "actor_progression_effectiveness_profile_candidates": list(construct.get("actor_ball_security_profile_candidates") or []),
        "effectiveness_score_emitted": False,
    })
    return {
        "module_id": PROGRESSION_MODULE_ID,
        "status": ball_security_payload.get("status") or "REVIEW_REQUIRED",
        "construct_candidate": adapted,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
    }


def build_ball_security_safe_finding_projection(
    ball_security_payload: dict[str, Any],
) -> dict[str, Any]:
    """Reuse the admitted Safe Finding envelope for Ball Security without a parallel engine."""
    try:
        adapted = _adapt_ball_security_to_existing_safe_finding_schema(ball_security_payload)
    except ValueError as exc:
        return _fail(*[item for item in str(exc).split(";") if item])

    projected = build_progression_safe_finding_projection(adapted)
    result = deepcopy(projected)
    result["module_id"] = MODULE_ID
    result["claim_ceiling"] = CLAIM_CEILING
    result["event_only_is_product_ceiling"] = False

    finding = result.get("finding_candidate")
    construct = ball_security_payload.get("construct_candidate")
    if not isinstance(finding, dict) or not isinstance(construct, dict):
        return result

    explicit_turnover_refs = sorted({
        _clean(ref)
        for ref in (construct.get("explicit_turnover_trace_candidate_refs_outside_denominator") or [])
        if _clean(ref)
    })
    what_visible = {
        "eligible_ball_use_trace_candidate_count": construct.get("eligible_ball_use_trace_candidate_count"),
        "evaluable_ball_security_consequence_candidate_count": construct.get("evaluable_ball_security_consequence_candidate_count"),
        "ball_security_consequence_coverage_rate_candidate": construct.get("ball_security_consequence_coverage_rate_candidate"),
        "visible_retained_follow_up_candidate_count": construct.get("visible_retained_follow_up_candidate_count"),
        "visible_adverse_handover_candidate_count": construct.get("visible_adverse_handover_candidate_count"),
        "unresolved_or_missing_consequence_candidate_count": construct.get("unresolved_or_missing_consequence_candidate_count"),
        "explicit_turnover_trace_candidate_count_outside_denominator": construct.get("explicit_turnover_trace_candidate_count_outside_denominator"),
    }
    support = {
        "support_refs": list(finding.get("support_refs") or []),
        "team_ball_security_profile_candidates": list(construct.get("team_ball_security_profile_candidates") or []),
        "actor_ball_security_profile_candidates": list(construct.get("actor_ball_security_profile_candidates") or []),
        "explicit_turnover_trace_candidate_refs_outside_denominator": explicit_turnover_refs,
        "explicit_turnover_context_is_independent_support": False,
    }
    counterevidence = {
        "refs": list(finding.get("counterevidence_refs") or []),
        "unresolved_refs": list(finding.get("unresolved_refs") or []),
        "absence_is_confirmation": False,
        "missing_follow_up_is_failure": False,
        "explicit_turnover_context_is_denominator_member": False,
        "explicit_turnover_context_is_independent_counterevidence_vote": False,
    }
    safe_meaning = (
        "Describe the match-local visible PASS/CARRY/DRIBBLE opportunity set and its retained, adverse-handover, and unresolved follow-up distribution; "
        "explicit turnover traces remain outside the denominator as same-provider context and none of these surfaces is player quality, control, fault or causal truth."
    )
    forbidden = [
        "player ball-security quality truth",
        "team control truth",
        "individual fault for adverse handover",
        "causal value",
        "possession truth",
        "missing consequence as failure",
        "loss-exposure rate complement as total failure rate",
        "explicit turnover reflection as an additional denominator action",
        "explicit turnover reflection as an independent evidence vote",
    ]

    finding.update({
        "finding_candidate_id": "bsf_" + _clean(construct.get("construct_candidate_id") or "ball_security")[-24:],
        "construct_candidate_id": construct.get("construct_candidate_id"),
        "construct_target": "BALL_SECURITY",
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
