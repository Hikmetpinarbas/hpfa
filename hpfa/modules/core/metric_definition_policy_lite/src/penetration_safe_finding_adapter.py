from __future__ import annotations

from copy import deepcopy
from typing import Any

from hpfa.modules.core.metric_definition_policy_lite.src.progression_safe_finding_projection import (
    build_progression_safe_finding_projection,
)

MODULE_ID = "penetration_safe_finding_projection_v1"
PENETRATION_MODULE_ID = "penetration_construct_v1"
PROGRESSION_MODULE_ID = "progression_effectiveness_construct_v1"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_TERMINAL_PENETRATION_AND_EPISODE_RECURRENCE_FINDING_CANDIDATE_ONLY"


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


def _adapt_penetration_to_existing_safe_finding_schema(
    penetration_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    if penetration_payload.get("module_id") != PENETRATION_MODULE_ID:
        blocks.append("penetration_construct_module_id_mismatch")
    if penetration_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("penetration_construct_canonical_event_count_claimed")
    if penetration_payload.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append("penetration_construct_true_action_count_claimed")
    if penetration_payload.get("production_release") is True:
        blocks.append("penetration_construct_production_release_claimed")
    if penetration_payload.get("professional_finding_emitted") is True:
        blocks.append("upstream_professional_finding_claimed")
    if penetration_payload.get("claim_output_allowed") is True:
        blocks.append("upstream_claim_output_allowed")
    if penetration_payload.get("hard_block_hits"):
        blocks.append("penetration_construct_hard_blocks_present")
    if blocks:
        raise ValueError(";".join(sorted(set(blocks))))

    construct = penetration_payload.get("construct_candidate")
    if not isinstance(construct, dict):
        return {
            "module_id": PROGRESSION_MODULE_ID,
            "status": penetration_payload.get("status") or "REVIEW_REQUIRED",
            "construct_candidate": None,
            "hard_block_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
        }

    required_false_locks = {
        "penetration_score_emitted": "penetration_score_lock_missing",
        "same_provider_reflection_adds_independent_vote": "same_provider_independence_lock_missing",
        "missing_followup_is_counterevidence": "missingness_counterevidence_lock_missing",
        "penetration_truth": "penetration_truth_claimed",
        "territorial_control_truth": "territorial_control_truth_claimed",
        "causal_creation_truth": "causal_creation_truth_claimed",
        "professional_finding_emitted": "professional_finding_claimed",
        "claim_output_allowed": "claim_output_allowed_claimed",
    }
    lock_blocks = [name for field, name in required_false_locks.items() if construct.get(field) is not False]
    if construct.get("recurrence_truth") not in {None, False}:
        lock_blocks.append("recurrence_truth_claimed")
    if construct.get("tactical_pattern_truth") not in {None, False}:
        lock_blocks.append("tactical_pattern_truth_claimed")
    if construct.get("box_access_surface_available") is not False:
        lock_blocks.append("box_access_surface_unreviewed_or_claimed")
    if construct.get("box_access_rate_candidate") is not None:
        lock_blocks.append("box_access_rate_fabricated")
    if construct.get("box_access_not_inferred_from_shot") is not True:
        lock_blocks.append("shot_to_box_access_inference_guard_missing")
    if lock_blocks:
        raise ValueError(";".join(sorted(set(lock_blocks))))

    adapted = deepcopy(construct)
    adapted.update({
        "eligible_progression_trace_candidate_count": construct.get("eligible_progression_trace_candidate_count"),
        "evaluable_progression_consequence_candidate_count": construct.get("penetration_evaluable_progression_candidate_count"),
        "progression_consequence_coverage_rate_candidate": construct.get("penetration_followup_coverage_rate_candidate"),
        "visible_positive_follow_up_candidate_count": construct.get("visible_terminal_penetration_support_candidate_count"),
        "visible_adverse_handover_candidate_count": construct.get("visible_adverse_handover_candidate_count"),
        "team_progression_effectiveness_profile_candidates": [],
        "actor_progression_effectiveness_profile_candidates": [],
        "effectiveness_score_emitted": False,
        "construct_validity_truth": False,
        "player_quality_truth": False,
        "team_control_truth": False,
        "missing_consequence_is_counterevidence": False,
    })
    return {
        "module_id": PROGRESSION_MODULE_ID,
        "status": penetration_payload.get("status") or "REVIEW_REQUIRED",
        "construct_candidate": adapted,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
    }


def build_penetration_safe_finding_projection(
    penetration_payload: dict[str, Any],
) -> dict[str, Any]:
    """Reuse the admitted Safe Finding envelope for terminal penetration without inventing box access."""
    try:
        adapted = _adapt_penetration_to_existing_safe_finding_schema(penetration_payload)
    except ValueError as exc:
        return _fail(*[item for item in str(exc).split(";") if item])

    projected = build_progression_safe_finding_projection(adapted)
    result = deepcopy(projected)
    result["module_id"] = MODULE_ID
    result["claim_ceiling"] = CLAIM_CEILING
    result["event_only_is_product_ceiling"] = False

    finding = result.get("finding_candidate")
    construct = penetration_payload.get("construct_candidate")
    if not isinstance(finding, dict) or not isinstance(construct, dict):
        return result

    what_visible = {
        "eligible_progression_trace_candidate_count": construct.get("eligible_progression_trace_candidate_count"),
        "penetration_evaluable_progression_candidate_count": construct.get("penetration_evaluable_progression_candidate_count"),
        "penetration_followup_coverage_rate_candidate": construct.get("penetration_followup_coverage_rate_candidate"),
        "visible_terminal_penetration_support_candidate_count": construct.get("visible_terminal_penetration_support_candidate_count"),
        "visible_shot_followup_candidate_count": construct.get("visible_shot_followup_candidate_count"),
        "visible_terminal_outcome_support_candidate_count": construct.get("visible_terminal_outcome_support_candidate_count"),
        "visible_adverse_handover_candidate_count": construct.get("visible_adverse_handover_candidate_count"),
        "unresolved_or_missing_followup_candidate_count": construct.get("unresolved_or_missing_followup_candidate_count"),
        "terminal_support_episode_candidate_count": construct.get("terminal_support_episode_candidate_count"),
        "visible_terminal_penetration_recurrence_candidate": construct.get("visible_terminal_penetration_recurrence_candidate"),
        "box_access_surface_available": False,
        "box_access_rate_candidate": None,
    }
    where_when = {
        "episode_context_surface_available": construct.get("episode_context_surface_available") is True,
        "terminal_support_episode_binding_coverage_rate_candidate": construct.get("terminal_support_episode_binding_coverage_rate_candidate"),
        "terminal_support_episode_candidate_refs": list(construct.get("terminal_support_episode_candidate_refs") or []),
        "phase_activity_terminal_support_counts": dict(construct.get("phase_activity_terminal_support_counts") or {}),
        "process_family_terminal_support_counts": dict(construct.get("process_family_terminal_support_counts") or {}),
        "same_timestamp_total_order_inferred": False,
    }
    support = {
        "support_refs": list(finding.get("support_refs") or []),
        "shot_followup_is_terminal_access_support_only": True,
        "box_access_support_refs": [],
    }
    counterevidence = {
        "refs": list(finding.get("counterevidence_refs") or []),
        "unresolved_refs": list(finding.get("unresolved_refs") or []),
        "absence_is_confirmation": False,
        "missing_follow_up_is_failure": False,
        "no_box_access_surface_is_counterevidence": False,
        "incomplete_episode_binding_is_counterevidence": False,
    }
    safe_meaning = (
        "Describe the match-local admitted progression opportunity set, visible terminal/adverse/unresolved follow-up distribution, and—when episode binding coverage is complete—whether terminal support recurred across distinct navigation episodes. "
        "Episode recurrence is observed repetition only; it is not tactical intention, causal quality, complete box access or territorial control."
    )
    forbidden = [
        "complete box-access rate",
        "shot follow-up as box-entry truth",
        "territorial dominance",
        "individual causal creation value",
        "player penetration quality truth",
        "team tactical plan truth",
        "recurrence as tactical intention",
        "recurrence as causality",
        "missing follow-up as failure",
        "incomplete episode binding as counterevidence",
        "same-provider reflection as an independent evidence vote",
    ]

    finding.update({
        "finding_candidate_id": "pnf_" + _clean(construct.get("construct_candidate_id") or "penetration")[-24:],
        "construct_candidate_id": construct.get("construct_candidate_id"),
        "construct_target": "PENETRATION",
        "what_visible": what_visible,
        "where_when": where_when,
        "support": support,
        "counterevidence": counterevidence,
        "safe_meaning": safe_meaning,
        "forbidden_inference": forbidden,
        "WHAT_VISIBLE": what_visible,
        "WHERE_WHEN": where_when,
        "SUPPORT": support,
        "COUNTEREVIDENCE": counterevidence,
        "SAFE_MEANING": safe_meaning,
        "FORBIDDEN_INFERENCE": forbidden,
        "box_access_surface_available": False,
        "box_access_rate_candidate": None,
        "box_access_not_inferred_from_shot": True,
        "recurrence_truth": False,
        "tactical_pattern_truth": False,
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
