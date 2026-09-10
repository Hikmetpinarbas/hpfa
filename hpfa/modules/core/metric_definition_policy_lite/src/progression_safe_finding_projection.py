from __future__ import annotations

from typing import Any

MODULE_ID = "progression_safe_finding_projection_v1"
CONSTRUCT_MODULE_ID = "progression_effectiveness_construct_v1"
OBSERVATION_MODEL = "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_PROGRESSION_FINDING_CANDIDATE_ONLY"


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
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_progression_safe_finding_projection(
    progression_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if progression_payload.get("module_id") != CONSTRUCT_MODULE_ID:
        blocks.append("progression_construct_module_id_mismatch")
    if progression_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("progression_construct_canonical_event_count_claimed")
    if progression_payload.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append("progression_construct_true_action_count_claimed")
    if progression_payload.get("production_release") is True:
        blocks.append("progression_construct_production_release_claimed")
    if progression_payload.get("professional_finding_emitted") is True:
        blocks.append("upstream_professional_finding_claimed")
    if progression_payload.get("claim_output_allowed") is True:
        blocks.append("upstream_claim_output_allowed")
    if progression_payload.get("hard_block_hits"):
        blocks.append("progression_construct_hard_blocks_present")

    upstream_status = _clean(progression_payload.get("status")).upper()
    if upstream_status == "FAIL_CLOSED":
        blocks.append("progression_construct_fail_closed")
    elif upstream_status in {"REVIEW_REQUIRED", "PASS_CANDIDATE"}:
        if upstream_status == "REVIEW_REQUIRED":
            reviews.append("progression_construct_upstream_review_required")
    else:
        reviews.append(f"progression_construct_status_review:{upstream_status or 'UNKNOWN'}")

    if blocks:
        return _fail(*blocks)

    construct = progression_payload.get("construct_candidate")
    if not isinstance(construct, dict):
        reviews.append("progression_construct_candidate_missing")
        return {
            "module_id": MODULE_ID,
            "status": "REVIEW_REQUIRED",
            "finding_candidate": None,
            "finding_candidate_count": 0,
            "hard_block_hits": [],
            "review_hits": sorted(set(reviews)),
            "engineering_envelope_complete": False,
            "physical_active_match_evidence_present": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    required_list_fields = (
        "support_consequence_candidate_refs",
        "counterevidence_consequence_candidate_refs",
        "unresolved_consequence_candidate_refs",
        "alternative_explanations",
    )
    for field in required_list_fields:
        if field not in construct or not isinstance(construct.get(field), list):
            blocks.append(f"finding_envelope_field_invalid:{field}")

    required_text_fields = ("uncertainty", "withdrawal_condition", "analyst_action")
    for field in required_text_fields:
        if not _clean(construct.get(field)):
            blocks.append(f"finding_envelope_field_missing:{field}")

    alternatives = [
        _clean(item) for item in (construct.get("alternative_explanations") or []) if _clean(item)
    ]
    if not alternatives:
        blocks.append("finding_envelope_alternative_explanation_missing")

    denominator = construct.get("eligible_progression_trace_candidate_count")
    evaluable = construct.get("evaluable_progression_consequence_candidate_count")
    if not isinstance(denominator, int) or denominator < 0:
        blocks.append("progression_denominator_invalid")
    if not isinstance(evaluable, int) or evaluable < 0:
        blocks.append("progression_evaluable_count_invalid")
    if isinstance(denominator, int) and isinstance(evaluable, int) and evaluable > denominator:
        blocks.append("progression_evaluable_exceeds_denominator")

    if construct.get("effectiveness_score_emitted") is not False:
        blocks.append("effectiveness_score_lock_missing")
    if construct.get("same_provider_reflection_adds_independent_vote") is not False:
        blocks.append("same_provider_independence_lock_missing")
    if construct.get("missing_consequence_is_counterevidence") is not False:
        blocks.append("missingness_counterevidence_lock_missing")
    if construct.get("construct_validity_truth") is True:
        blocks.append("construct_validity_truth_claimed")
    if construct.get("player_quality_truth") is True:
        blocks.append("player_quality_truth_claimed")
    if construct.get("team_control_truth") is True:
        blocks.append("team_control_truth_claimed")

    if blocks:
        return _fail(*blocks)

    support_refs = sorted({_clean(x) for x in construct["support_consequence_candidate_refs"] if _clean(x)})
    counter_refs = sorted({_clean(x) for x in construct["counterevidence_consequence_candidate_refs"] if _clean(x)})
    unresolved_refs = sorted({_clean(x) for x in construct["unresolved_consequence_candidate_refs"] if _clean(x)})

    if denominator == 0:
        reviews.append("finding_population_empty")
    if evaluable == 0 and denominator:
        reviews.append("finding_consequence_population_not_evaluable")
    if unresolved_refs:
        reviews.append("finding_contains_unresolved_consequence_context")

    envelope_complete = denominator > 0 and evaluable > 0
    finding_state = (
        "ENGINEERING_ENVELOPE_READY_PHYSICAL_ACTIVE_MATCH_REQUIRED"
        if envelope_complete
        else "REVIEW_REQUIRED_INSUFFICIENT_EVALUABLE_POPULATION"
    )

    what_visible = {
        "eligible_progression_trace_candidate_count": denominator,
        "evaluable_progression_consequence_candidate_count": evaluable,
        "progression_consequence_coverage_rate_candidate": construct.get("progression_consequence_coverage_rate_candidate"),
        "visible_positive_follow_up_candidate_count": construct.get("visible_positive_follow_up_candidate_count"),
        "visible_adverse_handover_candidate_count": construct.get("visible_adverse_handover_candidate_count"),
        "unresolved_or_missing_consequence_candidate_count": construct.get("unresolved_or_missing_consequence_candidate_count"),
    }
    where_when = {
        "observation_window": construct.get("observation_window"),
        "period_scope": construct.get("period_scope"),
        "entity_scope": construct.get("entity_scope"),
        "team_scope": construct.get("team_scope"),
        "denominator_set_id": construct.get("denominator_set_id"),
        "context_policy_id": construct.get("context_policy_id"),
    }
    support = {
        "support_refs": support_refs,
        "team_progression_effectiveness_profile_candidates": list(
            construct.get("team_progression_effectiveness_profile_candidates") or []
        ),
        "actor_progression_effectiveness_profile_candidates": list(
            construct.get("actor_progression_effectiveness_profile_candidates") or []
        ),
    }
    counterevidence = {
        "refs": counter_refs,
        "unresolved_refs": unresolved_refs,
        "absence_is_confirmation": False,
        "missing_follow_up_is_failure": False,
    }
    safe_meaning = (
        "Describe the match-local visible progression opportunity set and its observed positive, adverse, and unresolved follow-up distribution; "
        "entity decomposition is contribution-surface evidence only."
    )
    forbidden_inference = [
        "individual causal value",
        "player quality truth",
        "team control truth",
        "tactical plan truth",
        "defensive line bypass truth",
        "dominance",
        "missing follow-up as failure",
    ]
    dependency_summary = {
        "dependency_group": construct.get("dependency_group"),
        "provenance_root": construct.get("provenance_root"),
        "same_provider_support_is_independent_vote": False,
        "independent_support_vote_count": 0,
    }

    finding = {
        "finding_candidate_id": "psf_" + _clean(construct.get("construct_candidate_id") or "progression")[-24:],
        "observation_model": OBSERVATION_MODEL,
        "construct_candidate_id": construct.get("construct_candidate_id"),
        "construct_target": construct.get("construct_target"),
        "finding_state": finding_state,
        "what_visible": what_visible,
        "where_when": where_when,
        "support": support,
        "counterevidence": counterevidence,
        "alternative_explanations": alternatives,
        "safe_meaning": safe_meaning,
        "forbidden_inference": forbidden_inference,
        "analyst_action": construct.get("analyst_action"),
        "uncertainty": construct.get("uncertainty"),
        "withdrawal_condition": construct.get("withdrawal_condition"),
        "dependency_summary": dependency_summary,
        "WHAT_VISIBLE": what_visible,
        "WHERE_WHEN": where_when,
        "SUPPORT": support,
        "COUNTEREVIDENCE": counterevidence,
        "ALTERNATIVE_EXPLANATION": alternatives,
        "SAFE_MEANING": safe_meaning,
        "FORBIDDEN_INFERENCE": forbidden_inference,
        "ANALYST_ACTION": construct.get("analyst_action"),
        "UNCERTAINTY": construct.get("uncertainty"),
        "WITHDRAWAL_CONDITION": construct.get("withdrawal_condition"),
        "support_refs": support_refs,
        "counterevidence_refs": counter_refs,
        "unresolved_refs": unresolved_refs,
        "counterevidence_absence_is_confirmation": False,
        "team_progression_effectiveness_profile_candidates": support[
            "team_progression_effectiveness_profile_candidates"
        ],
        "actor_progression_effectiveness_profile_candidates": support[
            "actor_progression_effectiveness_profile_candidates"
        ],
        "same_provider_support_is_independent_vote": False,
        "independent_support_vote_count": 0,
        "physical_active_match_evidence_required": True,
        "physical_active_match_evidence_present": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "claim_ceiling": CLAIM_CEILING,
    }

    status = "REVIEW_REQUIRED" if reviews or not envelope_complete else "PASS_CANDIDATE"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "finding_candidate": finding,
        "finding_candidate_count": 1,
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "engineering_envelope_complete": envelope_complete,
        "physical_active_match_evidence_present": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "event_only_is_product_ceiling": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
