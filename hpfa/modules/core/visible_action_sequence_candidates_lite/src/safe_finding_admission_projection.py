from __future__ import annotations

from collections import Counter
from typing import Any

CLAIM_CEILING_EMIT = "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY"
CLAIM_CEILING_DOWNGRADE = "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"
CLAIM_CEILING_ABSTAIN = "NO_CLAIM_OUTPUT"
_ALLOWED_ALTERNATIVE_KEYS = {"code", "meaning"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _validated_alternatives(value: Any) -> tuple[list[dict[str, str]], str | None]:
    """Accept only the compact non-truth-bearing alternative schema.

    Alternative explanations can satisfy the challenge-surface requirement only when each
    row is an explicit ``code`` + ``meaning`` observation-level explanation. Arbitrary or
    truth-bearing fields must not be laundered into a claim-enabled finding.
    """
    if value is None:
        return [], None
    if not isinstance(value, list):
        return [], "alternative_explanations_invalid"

    validated: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict):
            return [], "alternative_explanation_not_object"
        if set(row) - _ALLOWED_ALTERNATIVE_KEYS:
            return [], "alternative_explanation_schema_not_allowlisted"
        code = _clean(row.get("code"))
        meaning = _clean(row.get("meaning"))
        if not code or not meaning:
            return [], "alternative_explanation_incomplete"
        validated.append({"code": code, "meaning": meaning})
    return validated, None


def _abstain(source_ref: str | None, *reasons: str) -> dict[str, Any]:
    return {
        "source_safe_finding_handoff_ref": source_ref,
        "decision": "ABSTAIN",
        "decision_reasons": sorted({_clean(reason) for reason in reasons if _clean(reason)}),
        "claim_output_allowed": False,
        "claim_ceiling": CLAIM_CEILING_ABSTAIN,
    }


def build_safe_finding_admission(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    """Decide EMIT / DOWNGRADE / ABSTAIN over already-built Safe Finding handoffs.

    This projection is intentionally tiny: it creates no evidence, copies no sequence or
    counterevidence inventory, and never re-runs discovery. It only references the source
    handoff and returns a decision plus compact reasons.

    An upstream REVIEW_REQUIRED envelope is not assumed to be row-scoped. Until the
    upstream producer carries machine-readable review-to-handoff lineage, that review debt
    can preserve a match-local cue but cannot authorize a professional EMIT.
    """
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    if sequence_payload.get("production_release") is True:
        hard_blocks.append("production_release_claimed")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        hard_blocks.append("canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        hard_blocks.append("true_action_count_claimed")
    if sequence_payload.get("comparable_outcome_counterevidence_status") == "FAIL_CLOSED":
        hard_blocks.append("counterevidence_upstream_fail_closed")

    if hard_blocks:
        return {
            "status": "FAIL_CLOSED",
            "safe_finding_admission_decisions": [],
            "safe_finding_admission_decision_count": 0,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
            "hard_block_hits": sorted(set(hard_blocks)),
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    source_status = _clean(sequence_payload.get("comparable_outcome_counterevidence_status")).upper()
    source_review_unscoped = source_status == "REVIEW_REQUIRED"
    if source_review_unscoped:
        review_hits.append("counterevidence_upstream_review_unscoped")
    elif source_status != "PASS":
        review_hits.append(f"counterevidence_status_unrecognized:{source_status or 'UNKNOWN'}")

    decisions: list[dict[str, Any]] = []
    for handoff in sequence_payload.get("safe_finding_handoff_candidates") or []:
        if not isinstance(handoff, dict):
            decisions.append(_abstain(None, "handoff_not_object"))
            continue

        source_ref = _clean(handoff.get("safe_finding_handoff_candidate_id")) or None
        if source_ref is None:
            decisions.append(_abstain(None, "handoff_id_missing"))
            continue

        # Upstream must never pre-authorize a professional finding. This gate owns that decision.
        if handoff.get("professional_finding_emit_allowed") is not False:
            decisions.append(_abstain(source_ref, "upstream_emit_lock_not_false"))
            continue
        truth_locks = (
            handoff.get("safe_finding_handoff_is_professional_finding_truth") is False,
            handoff.get("safe_finding_handoff_is_tactical_truth") is False,
            handoff.get("safe_finding_handoff_is_causal_truth") is False,
            handoff.get("safe_finding_handoff_is_coach_intention_truth") is False,
            handoff.get("same_timestamp_internal_ordering_allowed") is False,
            handoff.get("source_row_order_is_temporal_truth") is False,
        )
        if not all(truth_locks):
            decisions.append(_abstain(source_ref, "truth_lock_missing"))
            continue

        sufficiency = handoff.get("evidence_sufficiency")
        support = handoff.get("support")
        counterevidence = handoff.get("counterevidence")
        if not isinstance(sufficiency, dict) or not isinstance(support, dict) or not isinstance(counterevidence, dict):
            decisions.append(_abstain(source_ref, "required_decision_input_missing"))
            continue

        blocking = _refs(sufficiency.get("blocking_dimensions"))
        sufficiency_state = _clean(sufficiency.get("state"))
        independent_support = support.get("admitted_independent_support_count")
        independence_proven = support.get("dependency_independence_proven") is True
        statistical_independence_proven = support.get("statistical_independence_proven") is True
        counter_refs = _refs(counterevidence.get("comparable_counterexample_refs"))
        alternatives, alternatives_error = _validated_alternatives(handoff.get("alternative_explanations"))
        withdrawals = _refs(handoff.get("withdrawal_conditions"))
        forbidden = _refs(handoff.get("forbidden_inference"))
        safe_meaning = _clean(handoff.get("safe_meaning"))

        if isinstance(independent_support, bool) or not isinstance(independent_support, int) or independent_support < 0:
            decisions.append(_abstain(source_ref, "independent_support_count_invalid"))
            continue
        if not sufficiency_state:
            decisions.append(_abstain(source_ref, "evidence_sufficiency_state_missing"))
            continue
        if not safe_meaning or not forbidden or not withdrawals:
            decisions.append(_abstain(source_ref, "safe_finding_contract_incomplete"))
            continue
        if alternatives_error:
            decisions.append(_abstain(source_ref, alternatives_error))
            continue

        uncertainty = handoff.get("uncertainty")
        if isinstance(uncertainty, dict) and any(
            uncertainty.get(key) is True
            for key in (
                "no_visible_followup_is_failure",
                "absence_of_evidence_is_counterevidence",
                "robustness_is_tactical_pattern_truth",
                "recurrence_is_tactical_intention_truth",
                "censoring_is_failure",
            )
        ):
            decisions.append(_abstain(source_ref, "uncertainty_truth_lock_breached"))
            continue

        challenge_visible = bool(counter_refs) or bool(alternatives)
        emit_reasons: list[str] = []
        if blocking:
            emit_reasons.extend(blocking)
        if independent_support < 1:
            emit_reasons.append("INDEPENDENT_SUPPORT_NOT_ADMITTED")
        if not independence_proven:
            emit_reasons.append("DEPENDENCY_INDEPENDENCE_NOT_PROVEN")
        if not statistical_independence_proven:
            emit_reasons.append("STATISTICAL_INDEPENDENCE_NOT_PROVEN")
        if not challenge_visible:
            emit_reasons.append("CHALLENGE_SURFACE_EMPTY")
        if source_review_unscoped:
            emit_reasons.append("UPSTREAM_COUNTEREVIDENCE_REVIEW_UNSCOPED")

        if not emit_reasons:
            decision = "EMIT"
            claim_output_allowed = True
            claim_ceiling = CLAIM_CEILING_EMIT
        else:
            decision = "DOWNGRADE"
            claim_output_allowed = False
            claim_ceiling = CLAIM_CEILING_DOWNGRADE

        decisions.append({
            "source_safe_finding_handoff_ref": source_ref,
            "decision": decision,
            "decision_reasons": sorted(set(emit_reasons)),
            "claim_output_allowed": claim_output_allowed,
            "claim_ceiling": claim_ceiling,
            "admitted_independent_support_count": independent_support,
            "dependency_independence_proven": independence_proven,
            "statistical_independence_proven": statistical_independence_proven,
            "comparable_counterexample_visible": bool(counter_refs),
            "withdrawal_condition_present": bool(withdrawals),
        })

    counts = Counter(row.get("decision") for row in decisions)
    emitted = int(counts.get("EMIT", 0))
    abstained = int(counts.get("ABSTAIN", 0))
    if abstained:
        review_hits.append("one_or_more_handoffs_abstained")

    return {
        "status": "REVIEW_REQUIRED" if review_hits else "PASS",
        "safe_finding_admission_decisions": decisions,
        "safe_finding_admission_decision_count": len(decisions),
        "finding_status_counts": {
            "EMIT": emitted,
            "DOWNGRADE": int(counts.get("DOWNGRADE", 0)),
            "ABSTAIN": abstained,
        },
        "professional_finding_emitted_count": emitted,
        "claim_output_allowed_count": emitted,
        "decision_rows_copy_evidence_payloads": False,
        "decision_projection_creates_new_evidence": False,
        "decision_projection_reconstructs_sequences": False,
        "review_required_is_not_fail": True,
        "unscoped_upstream_review_can_authorize_emit": False,
        "malformed_alternative_can_satisfy_challenge": False,
        "hard_block_hits": [],
        "review_hits": sorted(set(review_hits)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
