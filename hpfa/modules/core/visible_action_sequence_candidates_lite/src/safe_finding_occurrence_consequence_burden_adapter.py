from __future__ import annotations

from collections import Counter
from typing import Any

CLAIM_CEILING_DOWNGRADE = "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"
CLAIM_CEILING_RATE_BOUND = "MATCH_LOCAL_VISIBLE_OUTCOME_RATE_BOUND_ONLY"
IDENTIFICATION_ASSUMPTION_SET_ID = "BINARY_VISIBLE_OUTCOME_KNOWN_ELIGIBLE_DENOMINATOR_WORST_CASE_UNRESOLVED_V1"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def build_binary_visible_outcome_identification_bound(
    *,
    resolved_success_n: int,
    resolved_failure_n: int,
    unresolved_eligible_n: int,
    denominator_membership_admitted: bool,
    target_outcome_semantics_fixed: bool,
    eligible_denominator_basis: str,
    estimand_id: str = "MATCH_LOCAL_VISIBLE_PROCESS_OUTCOME_RATE",
) -> dict[str, Any]:
    """Return worst-case identification bounds for an admitted binary visible outcome.

    This is a deterministic partial-identification interval, not a sampling/confidence
    interval. Unknown eligible units are assigned failure in the lower bound and success
    in the upper bound. Denominator membership and target semantics must already be
    admitted; this helper never invents eligibility from absence or off-ball availability.
    """
    counts = (resolved_success_n, resolved_failure_n, unresolved_eligible_n)
    counts_valid = all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in counts)
    base = {
        "estimand_id": estimand_id,
        "eligible_denominator_basis": eligible_denominator_basis,
        "resolved_success_n": resolved_success_n if counts_valid else None,
        "resolved_failure_n": resolved_failure_n if counts_valid else None,
        "unresolved_eligible_n": unresolved_eligible_n if counts_valid else None,
        "eligible_total_n": None,
        "lower_bound": None,
        "upper_bound": None,
        "bound_width": None,
        "assumption_set_id": IDENTIFICATION_ASSUMPTION_SET_ID,
        "denominator_membership_admitted": bool(denominator_membership_admitted),
        "target_outcome_semantics_fixed": bool(target_outcome_semantics_fixed),
        "identification_interval_is_confidence_interval": False,
        "unknown_eligible_is_failure": False,
        "unknown_eligible_is_success": False,
        "rate_bound_is_true_probability": False,
        "rate_bound_is_population_rate": False,
        "rate_bound_is_causal_effect": False,
        "rate_bound_can_authorize_emit": False,
        "rate_bound_can_strengthen_claim_ceiling": False,
        "rate_bound_creates_new_evidence": False,
        "claim_ceiling": CLAIM_CEILING_RATE_BOUND,
    }
    if not counts_valid:
        return {**base, "bound_state": "BOUND_UNRESOLVED", "bound_review_reasons": ["BOUND_COUNT_CONTRACT_INVALID"]}
    if not denominator_membership_admitted:
        return {**base, "bound_state": "BOUND_UNRESOLVED", "bound_review_reasons": ["ELIGIBLE_DENOMINATOR_MEMBERSHIP_UNRESOLVED"]}
    if not target_outcome_semantics_fixed:
        return {**base, "bound_state": "BOUND_UNRESOLVED", "bound_review_reasons": ["TARGET_OUTCOME_SEMANTICS_UNRESOLVED"]}

    total = resolved_success_n + resolved_failure_n + unresolved_eligible_n
    if total == 0:
        return {
            **base,
            "bound_state": "NO_OPPORTUNITY",
            "eligible_total_n": 0,
            "bound_review_reasons": [],
        }

    lower = resolved_success_n / total
    upper = (resolved_success_n + unresolved_eligible_n) / total
    state = "POINT_IDENTIFIED_OBSERVED_RATE" if unresolved_eligible_n == 0 else "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE"
    return {
        **base,
        "bound_state": state,
        "eligible_total_n": total,
        "lower_bound": lower,
        "upper_bound": upper,
        "bound_width": upper - lower,
        "bound_review_reasons": [],
    }


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



def _handoff_visible_outcome_identification_bound(
    handoff: dict[str, Any],
    process_variant_payload: dict[str, Any],
) -> dict[str, Any]:
    family_refs, _ = _handoff_family_occurrences(handoff, process_variant_payload)
    if not family_refs:
        result = build_binary_visible_outcome_identification_bound(
            resolved_success_n=0,
            resolved_failure_n=0,
            unresolved_eligible_n=0,
            denominator_membership_admitted=False,
            target_outcome_semantics_fixed=False,
            eligible_denominator_basis="NO_MATCHED_PROCESS_VARIANT_LINEAGE",
        )
        result["bound_state"] = "NOT_APPLICABLE_NO_MATCHED_PROCESS_VARIANT_LINEAGE"
        result["bound_review_reasons"] = []
        return result

    selected = set(family_refs)
    outcome_by_sequence: dict[str, str | None] = {}
    denominator_membership_admitted = True
    target_outcome_semantics_fixed = True
    for family in process_variant_payload.get("observable_process_variant_families") or []:
        if not isinstance(family, dict):
            continue
        if _clean(family.get("observable_process_variant_family_id")) not in selected:
            continue
        for member in family.get("member_records") or []:
            if not isinstance(member, dict):
                continue
            sequence_ref = _clean(member.get("sequence_ref"))
            if not sequence_ref:
                denominator_membership_admitted = False
                continue
            raw_outcome = _clean(member.get("visible_outcome_state"))
            if raw_outcome == "SUCCESS_SEMANTIC_VISIBLE":
                outcome: str | None = "SUCCESS"
            elif raw_outcome == "FAILURE_SEMANTIC_VISIBLE":
                outcome = "FAILURE"
            elif not raw_outcome:
                outcome = None
            else:
                outcome = None
                target_outcome_semantics_fixed = False
            if sequence_ref in outcome_by_sequence and outcome_by_sequence[sequence_ref] != outcome:
                target_outcome_semantics_fixed = False
            else:
                outcome_by_sequence.setdefault(sequence_ref, outcome)

    success_n = sum(value == "SUCCESS" for value in outcome_by_sequence.values())
    failure_n = sum(value == "FAILURE" for value in outcome_by_sequence.values())
    unresolved_n = sum(value is None for value in outcome_by_sequence.values())
    return build_binary_visible_outcome_identification_bound(
        resolved_success_n=success_n,
        resolved_failure_n=failure_n,
        unresolved_eligible_n=unresolved_n,
        denominator_membership_admitted=denominator_membership_admitted,
        target_outcome_semantics_fixed=target_outcome_semantics_fixed,
        eligible_denominator_basis="UNIQUE_OBSERVABLE_PROCESS_VARIANT_FAMILY_MEMBER_SEQUENCE_REFS",
    )


def _profile(
    handoff: dict[str, Any],
    process_variant_payload: dict[str, Any] | None,
    occurrence_consequence_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    unavailable_bound = build_binary_visible_outcome_identification_bound(
        resolved_success_n=0,
        resolved_failure_n=0,
        unresolved_eligible_n=0,
        denominator_membership_admitted=False,
        target_outcome_semantics_fixed=False,
        eligible_denominator_basis="CONSEQUENCE_OBSERVATION_BURDEN_NOT_AVAILABLE",
    )
    unavailable = {
        "profile_state": "UNAVAILABLE_REVIEW_REQUIRED",
        **unavailable_bound,
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
    identification_bound = _handoff_visible_outcome_identification_bound(handoff, process_variant_payload)
    if not family_refs:
        return {
            **unavailable,
            **identification_bound,
            "profile_state": "NOT_APPLICABLE_NO_MATCHED_PROCESS_VARIANT_LINEAGE",
        }, []
    if not occurrence_refs:
        return {
            **unavailable,
            **identification_bound,
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
        **identification_bound,
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
        "partial_identification_rate_bound_consumed": True,
        "partial_identification_rate_bound_can_authorize_emit": False,
        "partial_identification_rate_bound_can_strengthen_claim_ceiling": False,
        "partial_identification_rate_bound_is_confidence_interval": False,
        "partial_identification_rate_bound_claim_ceiling": CLAIM_CEILING_RATE_BOUND,
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
