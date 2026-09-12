from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING_DOWNGRADE = "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _fail_closed(reason: str, admission_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "FAIL_CLOSED",
        "safe_finding_admission_decisions": [],
        "safe_finding_admission_decision_count": 0,
        "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
        "professional_finding_emitted_count": 0,
        "claim_output_allowed_count": 0,
        "variant_feature_challenge_consumed": True,
        "variant_feature_challenge_can_increase_support": False,
        "variant_feature_challenge_can_authorize_emit": False,
        "variant_feature_challenge_refs_are_independent_evidence_votes": False,
        "challenge_adapter_creates_new_evidence": False,
        "hard_block_hits": [reason],
        "review_hits": list(admission_payload.get("review_hits") or []),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _validate_payload(
    challenge_payload: dict[str, Any] | None,
    process_variant_payload: dict[str, Any] | None,
) -> str | None:
    if not challenge_payload or not process_variant_payload:
        return None
    for label, payload in (
        ("variant_feature_challenge", challenge_payload),
        ("process_variant", process_variant_payload),
    ):
        if payload.get("production_release") is True:
            return f"{label}_production_release_claimed"
        if payload.get("canonical_event_count") != "UNKNOWN":
            return f"{label}_canonical_event_count_claimed"
        if payload.get("true_action_count") != "UNKNOWN":
            return f"{label}_true_action_count_claimed"
        if payload.get("status") == "FAIL_CLOSED":
            return f"{label}_fail_closed"
    if challenge_payload.get("professional_finding_emit_allowed") is not False:
        return "variant_feature_challenge_emit_lock_not_false"
    if challenge_payload.get("feature_absence_is_counterevidence") is not False:
        return "variant_feature_challenge_absence_counterevidence_lock_breached"
    if challenge_payload.get("difference_rows_are_independent_evidence_votes") is not False:
        return "variant_feature_challenge_independent_vote_lock_breached"
    return None


def _family_lineage(process_variant_payload: dict[str, Any]) -> dict[str, tuple[set[str], set[str]]]:
    result: dict[str, tuple[set[str], set[str]]] = {}
    for family in process_variant_payload.get("observable_process_variant_families") or []:
        if not isinstance(family, dict):
            continue
        family_ref = _clean(family.get("observable_process_variant_family_id"))
        if not family_ref:
            continue
        success_refs: set[str] = set()
        failure_refs: set[str] = set()
        for member in family.get("member_records") or []:
            if not isinstance(member, dict):
                continue
            sequence_ref = _clean(member.get("sequence_ref"))
            outcome = _clean(member.get("visible_outcome_state"))
            if not sequence_ref:
                continue
            if outcome == "SUCCESS_SEMANTIC_VISIBLE":
                success_refs.add(sequence_ref)
            elif outcome == "FAILURE_SEMANTIC_VISIBLE":
                failure_refs.add(sequence_ref)
        result[family_ref] = (success_refs, failure_refs)
    return result


def _binding_for_handoff(
    handoff: dict[str, Any],
    challenge_payload: dict[str, Any] | None,
    process_variant_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    unavailable = {
        "state": "UNAVAILABLE_REVIEW_REQUIRED",
        "family_refs": [],
        "challenge_refs": [],
        "challenge_reason_codes": [],
        "counter_scenario_candidates": [],
        "withdrawal_condition_candidates": [],
        "coverage_partial": False,
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
    }
    if not challenge_payload or not process_variant_payload:
        return unavailable

    support = handoff.get("support") if isinstance(handoff.get("support"), dict) else {}
    counter = handoff.get("counterevidence") if isinstance(handoff.get("counterevidence"), dict) else {}
    handoff_success = set(_refs(support.get("visible_success_sequence_refs")))
    handoff_failure = set(_refs(counter.get("visible_failure_sequence_refs")))
    if not handoff_success or not handoff_failure:
        return {**unavailable, "state": "NOT_APPLICABLE_HANDOFF_LINEAGE_UNAVAILABLE"}

    family_lineage = _family_lineage(process_variant_payload)
    family_refs = sorted(
        family_ref
        for family_ref, (success_refs, failure_refs) in family_lineage.items()
        if handoff_success.intersection(success_refs)
        and handoff_failure.intersection(failure_refs)
    )
    if not family_refs:
        return {**unavailable, "state": "NOT_APPLICABLE_NO_GRAMMAR_STABLE_LINEAGE"}

    rows_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in challenge_payload.get("variant_feature_challenge_records") or []:
        if not isinstance(row, dict):
            continue
        family_ref = _clean(row.get("source_process_variant_family_ref"))
        if family_ref:
            rows_by_family[family_ref].append(row)

    rows = [row for family_ref in family_refs for row in rows_by_family.get(family_ref, [])]
    if not rows:
        return {
            **unavailable,
            "state": "MATCHED_LINEAGE_CHALLENGE_MISSING",
            "family_refs": family_refs,
        }

    challenge_refs = sorted(
        {
            _clean(row.get("variant_feature_challenge_id"))
            for row in rows
            if _clean(row.get("variant_feature_challenge_id"))
        }
    )
    reason_codes = sorted(
        {
            _clean(reason)
            for row in rows
            for reason in (row.get("challenge_reasons") or [])
            if _clean(reason)
        }
    )
    counter_scenarios = sorted(
        {
            _clean(value)
            for row in rows
            for value in (row.get("counter_scenario_candidates") or [])
            if _clean(value)
        }
    )
    withdrawals = sorted(
        {
            _clean(value)
            for row in rows
            for value in (row.get("withdrawal_conditions") or [])
            if _clean(value)
        }
    )
    return {
        "state": "MATCHED_CHALLENGE_VISIBLE",
        "family_refs": family_refs,
        "challenge_refs": challenge_refs,
        "challenge_reason_codes": reason_codes,
        "counter_scenario_candidates": counter_scenarios,
        "withdrawal_condition_candidates": withdrawals,
        "coverage_partial": any(
            int(row.get("relevant_coverage_incomplete_variant_count") or 0) > 0
            for row in rows
        ),
        "dependency_independence_proven": all(
            row.get("dependency_independence_proven") is True for row in rows
        ),
        "statistical_independence_proven": all(
            row.get("statistical_independence_proven") is True for row in rows
        ),
    }


def apply_variant_feature_challenge_to_admission(
    sequence_payload: dict[str, Any],
    admission_payload: dict[str, Any],
    challenge_payload: dict[str, Any] | None,
    process_variant_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Attach existing challenge lineage to Safe Finding decisions without claim inflation.

    The adapter may preserve a decision or lower EMIT to DOWNGRADE. It can never create
    evidence, increase admitted support, prove independence, or turn DOWNGRADE/ABSTAIN
    into EMIT.
    """
    if admission_payload.get("status") == "FAIL_CLOSED":
        return admission_payload

    block = _validate_payload(challenge_payload, process_variant_payload)
    if block:
        return _fail_closed(block, admission_payload)

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
            row["decision"] = "ABSTAIN"
            row["claim_output_allowed"] = False
            reasons = set(_refs(row.get("decision_reasons")))
            reasons.add("SAFE_FINDING_HANDOFF_LINEAGE_MISSING")
            row["decision_reasons"] = sorted(reasons)
            adapted.append(row)
            review_hits.append("safe_finding_handoff_lineage_missing")
            continue

        binding = _binding_for_handoff(
            handoff,
            challenge_payload,
            process_variant_payload,
        )
        row["variant_feature_challenge_binding_state"] = binding["state"]
        row["variant_feature_challenge_family_refs"] = list(binding["family_refs"])
        row["variant_feature_challenge_refs"] = list(binding["challenge_refs"])
        row["variant_feature_challenge_reason_codes"] = list(binding["challenge_reason_codes"])
        row["variant_feature_challenge_counter_scenario_candidates"] = list(
            binding["counter_scenario_candidates"]
        )
        row["variant_feature_challenge_withdrawal_condition_candidates"] = list(
            binding["withdrawal_condition_candidates"]
        )
        row["variant_feature_challenge_coverage_partial"] = bool(binding["coverage_partial"])
        row["variant_feature_challenge_dependency_independence_proven"] = bool(
            binding["dependency_independence_proven"]
        )
        row["variant_feature_challenge_statistical_independence_proven"] = bool(
            binding["statistical_independence_proven"]
        )

        reasons = set(_refs(row.get("decision_reasons")))
        state = binding["state"]
        challenge_downgrade_reasons: list[str] = []
        if state == "UNAVAILABLE_REVIEW_REQUIRED":
            challenge_downgrade_reasons.append("VARIANT_FEATURE_CHALLENGE_NOT_AVAILABLE")
        elif state == "MATCHED_LINEAGE_CHALLENGE_MISSING":
            challenge_downgrade_reasons.append("VARIANT_FEATURE_CHALLENGE_NOT_LINKED")
        elif state == "MATCHED_CHALLENGE_VISIBLE":
            if binding["coverage_partial"]:
                challenge_downgrade_reasons.append("VARIANT_FEATURE_CHALLENGE_COVERAGE_PARTIAL")
            if not binding["dependency_independence_proven"]:
                challenge_downgrade_reasons.append(
                    "VARIANT_FEATURE_CHALLENGE_DEPENDENCY_INDEPENDENCE_UNPROVEN"
                )
            if not binding["statistical_independence_proven"]:
                challenge_downgrade_reasons.append(
                    "VARIANT_FEATURE_CHALLENGE_STATISTICAL_INDEPENDENCE_UNPROVEN"
                )

        reasons.update(challenge_downgrade_reasons)
        if challenge_downgrade_reasons and _clean(row.get("decision")).upper() == "EMIT":
            row["decision"] = "DOWNGRADE"
            row["claim_output_allowed"] = False
            row["claim_ceiling"] = CLAIM_CEILING_DOWNGRADE
        row["decision_reasons"] = sorted(reasons)
        adapted.append(row)

        if challenge_downgrade_reasons:
            review_hits.append("variant_feature_challenge_lowered_or_preserved_claim_ceiling")

    counts = Counter(_clean(row.get("decision")).upper() for row in adapted)
    emitted = int(counts.get("EMIT", 0))
    abstained = int(counts.get("ABSTAIN", 0))
    if abstained:
        review_hits.append("one_or_more_handoffs_abstained")

    result = dict(admission_payload)
    result.update({
        "status": "REVIEW_REQUIRED" if review_hits else "PASS",
        "safe_finding_admission_decisions": adapted,
        "safe_finding_admission_decision_count": len(adapted),
        "finding_status_counts": {
            "EMIT": emitted,
            "DOWNGRADE": int(counts.get("DOWNGRADE", 0)),
            "ABSTAIN": abstained,
        },
        "professional_finding_emitted_count": emitted,
        "claim_output_allowed_count": emitted,
        "variant_feature_challenge_consumed": True,
        "variant_feature_challenge_can_increase_support": False,
        "variant_feature_challenge_can_authorize_emit": False,
        "variant_feature_challenge_refs_are_independent_evidence_votes": False,
        "challenge_adapter_creates_new_evidence": False,
        "review_hits": sorted(set(review_hits)),
        "hard_block_hits": list(admission_payload.get("hard_block_hits") or []),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    })
    return result
