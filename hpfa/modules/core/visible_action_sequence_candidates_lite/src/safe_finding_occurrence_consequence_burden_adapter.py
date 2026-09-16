from __future__ import annotations

from collections import Counter
from typing import Any

CLAIM_CEILING_DOWNGRADE = "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _index_occurrence_consequence(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _clean(row.get("action_occurrence_candidate_id")): row
        for row in (payload.get("occurrence_consequence_projections") or [])
        if isinstance(row, dict) and _clean(row.get("action_occurrence_candidate_id"))
    }


def _handoff_family_occurrences(
    handoff: dict[str, Any],
    process_variant_payload: dict[str, Any],
) -> tuple[list[str], list[str]]:
    support = handoff.get("support") if isinstance(handoff.get("support"), dict) else {}
    counter = handoff.get("counterevidence") if isinstance(handoff.get("counterevidence"), dict) else {}
    success_refs = set(_refs(support.get("visible_success_sequence_refs")))
    failure_refs = set(_refs(counter.get("visible_failure_sequence_refs")))
    if not success_refs or not failure_refs:
        return [], []

    family_refs: list[str] = []
    occurrence_refs: set[str] = set()
    eligible_sequences = success_refs | failure_refs
    for family in process_variant_payload.get("observable_process_variant_families") or []:
        if not isinstance(family, dict):
            continue
        family_ref = _clean(family.get("observable_process_variant_family_id"))
        if not family_ref:
            continue
        family_success: set[str] = set()
        family_failure: set[str] = set()
        family_members: list[dict[str, Any]] = []
        for member in family.get("member_records") or []:
            if not isinstance(member, dict):
                continue
            sequence_ref = _clean(member.get("sequence_ref"))
            if not sequence_ref:
                continue
            family_members.append(member)
            outcome = _clean(member.get("visible_outcome_state"))
            if outcome == "SUCCESS_SEMANTIC_VISIBLE":
                family_success.add(sequence_ref)
            elif outcome == "FAILURE_SEMANTIC_VISIBLE":
                family_failure.add(sequence_ref)
        if not success_refs.intersection(family_success) or not failure_refs.intersection(family_failure):
            continue
        family_refs.append(family_ref)
        for member in family_members:
            if _clean(member.get("sequence_ref")) not in eligible_sequences:
                continue
            occurrence_refs.update(_refs(member.get("supporting_action_occurrence_candidate_ids")))
    return sorted(set(family_refs)), sorted(occurrence_refs)


def _profile(
    handoff: dict[str, Any],
    process_variant_payload: dict[str, Any] | None,
    occurrence_consequence_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    unavailable = {
        "profile_state": "UNAVAILABLE_REVIEW_REQUIRED",
        "matched_process_variant_family_refs": [],
        "supporting_occurrence_candidate_count": 0,
        "resolved_occurrence_consequence_count": 0,
        "missing_occurrence_consequence_count": 0,
        "visible_followup_occurrence_count": 0,
        "fully_observed_no_visible_followup_occurrence_count": 0,
        "followup_unresolved_occurrence_count": 0,
        "right_censored_occurrence_count": 0,
        "right_censoring_unresolved_occurrence_count": 0,
        "no_visible_followup_is_failure": False,
        "right_censoring_is_failure": False,
        "observation_burden_is_confidence_score": False,
        "observation_burden_can_authorize_emit": False,
        "burden_counts_are_independent_support_counts": False,
    }
    if not process_variant_payload or not occurrence_consequence_payload:
        return unavailable, ["CONSEQUENCE_OBSERVATION_BURDEN_NOT_AVAILABLE"]

    if occurrence_consequence_payload.get("production_release") is True:
        return unavailable, ["CONSEQUENCE_OBSERVATION_TRUTH_LOCK_BREACHED"]
    if occurrence_consequence_payload.get("canonical_event_count") != "UNKNOWN":
        return unavailable, ["CONSEQUENCE_OBSERVATION_TRUTH_LOCK_BREACHED"]
    if occurrence_consequence_payload.get("true_action_count") != "UNKNOWN":
        return unavailable, ["CONSEQUENCE_OBSERVATION_TRUTH_LOCK_BREACHED"]
    if occurrence_consequence_payload.get("no_visible_followup_is_failure") is True:
        return unavailable, ["NO_VISIBLE_FOLLOWUP_FAILURE_LOCK_BREACHED"]

    family_refs, occurrence_refs = _handoff_family_occurrences(handoff, process_variant_payload)
    if not family_refs:
        return {
            **unavailable,
            "profile_state": "NOT_APPLICABLE_NO_MATCHED_PROCESS_VARIANT_LINEAGE",
        }, []
    if not occurrence_refs:
        return {
            **unavailable,
            "profile_state": "MATCHED_PROCESS_LINEAGE_OCCURRENCE_SUPPORT_UNRESOLVED",
            "matched_process_variant_family_refs": family_refs,
        }, ["CONSEQUENCE_OCCURRENCE_LINEAGE_UNRESOLVED"]

    by_occurrence = _index_occurrence_consequence(occurrence_consequence_payload)
    missing: list[str] = []
    rows: list[dict[str, Any]] = []
    for occurrence_ref in occurrence_refs:
        row = by_occurrence.get(occurrence_ref)
        if row is None:
            missing.append(occurrence_ref)
        else:
            rows.append(row)

    visible_followup = sum(
        _clean(row.get("followup_observation_status")) == "VISIBLE_FOLLOWUP" for row in rows
    )
    no_visible_followup = sum(
        _clean(row.get("followup_observation_status")) == "NO_VISIBLE_FOLLOWUP" for row in rows
    )
    followup_unresolved = sum(
        _clean(row.get("followup_observation_status")) == "FOLLOWUP_UNRESOLVED" for row in rows
    )
    right_censored = sum(
        row.get("right_censored") is True
        or _clean(row.get("right_censoring_status")) == "RIGHT_CENSORED_BY_ADMIN_BOUNDARY"
        for row in rows
    )
    censoring_unresolved = sum(
        row.get("right_censoring_assessed") is not True
        or _clean(row.get("right_censoring_status")) == "CENSORING_NOT_ASSESSED"
        or _clean(row.get("right_censoring_status")).startswith("CENSORING_UNRESOLVED_")
        for row in rows
    )
    fully_observed_no_followup = sum(
        _clean(row.get("right_censoring_status"))
        == "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP"
        for row in rows
    )

    reasons: list[str] = []
    if missing:
        reasons.append("CONSEQUENCE_OBSERVATION_COVERAGE_UNRESOLVED")
    if followup_unresolved:
        reasons.append("FOLLOWUP_OBSERVATION_UNRESOLVED_BURDEN")
    if right_censored:
        reasons.append("RIGHT_CENSORED_OBSERVATION_BURDEN")
    if censoring_unresolved:
        reasons.append("RIGHT_CENSORING_UNRESOLVED_BURDEN")

    if reasons:
        state = "CONSEQUENCE_OBSERVATION_BURDEN_PRESENT"
    else:
        state = "CONSEQUENCE_OBSERVATION_BURDEN_ASSESSED_NO_BLOCK_VISIBLE"

    return {
        "profile_state": state,
        "matched_process_variant_family_refs": family_refs,
        "supporting_occurrence_candidate_count": len(occurrence_refs),
        "resolved_occurrence_consequence_count": len(rows),
        "missing_occurrence_consequence_count": len(missing),
        "visible_followup_occurrence_count": visible_followup,
        "fully_observed_no_visible_followup_occurrence_count": fully_observed_no_followup,
        "followup_unresolved_occurrence_count": followup_unresolved,
        "right_censored_occurrence_count": right_censored,
        "right_censoring_unresolved_occurrence_count": censoring_unresolved,
        "no_visible_followup_is_failure": False,
        "right_censoring_is_failure": False,
        "observation_burden_is_confidence_score": False,
        "observation_burden_can_authorize_emit": False,
        "burden_counts_are_independent_support_counts": False,
    }, sorted(set(reasons))


def apply_occurrence_consequence_burden_to_admission(
    sequence_payload: dict[str, Any],
    admission_payload: dict[str, Any],
    process_variant_payload: dict[str, Any] | None,
    occurrence_consequence_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Bind observed follow-up/censoring debt to final Safe Finding decisions.

    This adapter cannot create evidence or upgrade a decision. It distinguishes a fully
    observed no-follow-up from unresolved or right-censored observation and preserves
    NO_VISIBLE_FOLLOWUP != FAILURE.
    """
    if admission_payload.get("status") == "FAIL_CLOSED":
        return admission_payload

    handoffs = {
        _clean(row.get("safe_finding_handoff_candidate_id")): row
        for row in (sequence_payload.get("safe_finding_handoff_candidates") or [])
        if isinstance(row, dict) and _clean(row.get("safe_finding_handoff_candidate_id"))
    }

    review_hits = list(admission_payload.get("review_hits") or [])
    adapted: list[dict[str, Any]] = []
    for decision in admission_payload.get("safe_finding_admission_decisions") or []:
        if not isinstance(decision, dict):
            continue
        row = dict(decision)
        source_ref = _clean(row.get("source_safe_finding_handoff_ref"))
        handoff = handoffs.get(source_ref)
        if handoff is None:
            reasons = set(_refs(row.get("decision_reasons")))
            reasons.add("SAFE_FINDING_HANDOFF_LINEAGE_MISSING_FOR_CONSEQUENCE_BURDEN")
            row["decision"] = "ABSTAIN"
            row["claim_output_allowed"] = False
            row["decision_reasons"] = sorted(reasons)
            adapted.append(row)
            review_hits.append("safe_finding_handoff_lineage_missing_for_consequence_burden")
            continue

        burden_profile, burden_reasons = _profile(
            handoff,
            process_variant_payload,
            occurrence_consequence_payload,
        )
        row["consequence_observation_burden_profile"] = burden_profile
        reasons = set(_refs(row.get("decision_reasons")))
        reasons.update(burden_reasons)
        if burden_reasons and _clean(row.get("decision")).upper() == "EMIT":
            row["decision"] = "DOWNGRADE"
            row["claim_output_allowed"] = False
            row["claim_ceiling"] = CLAIM_CEILING_DOWNGRADE
        row["decision_reasons"] = sorted(reasons)
        adapted.append(row)
        if burden_reasons:
            review_hits.append("occurrence_consequence_observation_burden_preserved_claim_ceiling")

    counts = Counter(_clean(row.get("decision")).upper() for row in adapted)
    result = dict(admission_payload)
    result.update({
        "status": "REVIEW_REQUIRED" if review_hits else "PASS",
        "safe_finding_admission_decisions": adapted,
        "safe_finding_admission_decision_count": len(adapted),
        "finding_status_counts": {
            "EMIT": int(counts.get("EMIT", 0)),
            "DOWNGRADE": int(counts.get("DOWNGRADE", 0)),
            "ABSTAIN": int(counts.get("ABSTAIN", 0)),
        },
        "professional_finding_emitted_count": int(counts.get("EMIT", 0)),
        "claim_output_allowed_count": int(counts.get("EMIT", 0)),
        "occurrence_consequence_observation_burden_consumed": True,
        "occurrence_consequence_observation_burden_can_increase_support": False,
        "occurrence_consequence_observation_burden_can_authorize_emit": False,
        "fully_observed_no_visible_followup_is_failure": False,
        "right_censoring_is_failure": False,
        "observation_burden_counts_are_independent_support_counts": False,
        "review_hits": sorted(set(review_hits)),
        "hard_block_hits": list(admission_payload.get("hard_block_hits") or []),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    })
    return result
