from __future__ import annotations

import hashlib
import json
from typing import Any

MODULE_ID = "sequence_safe_finding_binding_lite_v1"
ADMISSION_MODULE_ID = "sequence_pattern_admission_lite_v1"
NULL_CONTRAST_ID = "recurrence_null_contrast_v1"
NULL_CLAIM_CEILING = "UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"
SAFE_EMITTING_ADMISSION_STATES = {
    "DISCOVERY_ONLY",
    "PROXY_CANDIDATE",
    "RECURRENT_VISIBLE_TRACE",
    "ROBUST_RECURRENT_VISIBLE_TRACE",
}
NON_EMITTING_ADMISSION_STATES = {
    "REJECTED_INSUFFICIENT_EVIDENCE",
    "REVIEW_REQUIRED",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fail(*blocks: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "SEQUENCE_SAFE_FINDING_BINDING_REJECTED",
        "analyst_report_blocks": [],
        "analyst_report_block_count": 0,
        "hard_block_hits": sorted(set(blocks)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _index_null_contrast(null_payload: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    if null_payload is None:
        return {}, [], []
    blocks: list[str] = []
    reviews: list[str] = []
    if null_payload.get("contrast_id") != NULL_CONTRAST_ID:
        blocks.append("null_contrast_id_mismatch")
    if null_payload.get("claim_ceiling") != NULL_CLAIM_CEILING:
        blocks.append("null_contrast_claim_ceiling_mismatch")
    if null_payload.get("multiple_testing_corrected") is not False:
        blocks.append("null_contrast_multiple_testing_lock_breach")
    if null_payload.get("significance_claim_allowed") is not False:
        blocks.append("null_contrast_significance_lock_breach")
    if null_payload.get("tactical_pattern_truth_allowed") is not False:
        blocks.append("null_contrast_tactical_truth_lock_breach")
    if null_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("null_contrast_canonical_event_count_claimed")
    if null_payload.get("true_action_count") != TRUE_ACTION_COUNT:
        blocks.append("null_contrast_true_action_count_claimed")
    if null_payload.get("production_release") is True:
        blocks.append("null_contrast_production_release_claimed")
    if null_payload.get("hard_block_hits"):
        blocks.append("null_contrast_hard_blocks_present")
    status = _clean(null_payload.get("status")).upper()
    if status == "FAIL_CLOSED":
        blocks.append("null_contrast_input_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("null_contrast_upstream_review_required")
    elif status != "PASS":
        reviews.append(f"null_contrast_status_review:{status or 'UNKNOWN'}")
    rows = [row for row in (null_payload.get("rows") or []) if isinstance(row, dict)]
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        family_ref = _clean(row.get("trace_family_ref"))
        if not family_ref:
            blocks.append("null_contrast_family_ref_missing")
            continue
        if family_ref in indexed:
            blocks.append(f"null_contrast_family_duplicate:{family_ref}")
            continue
        indexed[family_ref] = row
    return indexed, blocks, reviews


def build_sequence_safe_finding_blocks(
    admission_payload: dict[str, Any],
    null_contrast_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project admitted sequence evidence into readable, defeasible analyst blocks.

    Optional audited recurrence-null contrast may strengthen *context* for a finding but
    never upgrades its admission state, independence state, tactical meaning or release.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    if admission_payload.get("module_id") != ADMISSION_MODULE_ID:
        blocks.append("admission_module_id_mismatch")
    if admission_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed")
    if admission_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("true_action_count_claimed")
    if admission_payload.get("production_release") is True:
        blocks.append("production_release_claimed")
    if admission_payload.get("hard_block_hits"):
        blocks.append("admission_hard_blocks_present")
    if admission_payload.get("tactical_pattern_state_allowed") is not False:
        blocks.append("tactical_pattern_lock_missing")
    if admission_payload.get("coach_intention_state_allowed") is not False:
        blocks.append("coach_intention_lock_missing")
    if admission_payload.get("team_style_truth_state_allowed") is not False:
        blocks.append("team_style_truth_lock_missing")
    status = _clean(admission_payload.get("status")).upper()
    if status == "FAIL_CLOSED":
        blocks.append("admission_input_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("admission_upstream_review_required")
    elif status != "PASS":
        reviews.append(f"admission_status_review:{status or 'UNKNOWN'}")

    null_by_family, null_blocks, null_reviews = _index_null_contrast(null_contrast_payload)
    blocks.extend(null_blocks)
    reviews.extend(null_reviews)
    if blocks:
        return _fail(*blocks)

    admissions = [row for row in (admission_payload.get("sequence_pattern_admissions") or []) if isinstance(row, dict)]
    for row in admissions:
        state = _clean(row.get("admission_state"))
        if state not in SAFE_EMITTING_ADMISSION_STATES | NON_EMITTING_ADMISSION_STATES:
            return _fail(f"unsupported_admission_state:{state or 'UNKNOWN'}")

    report_blocks: list[dict[str, Any]] = []
    for row in admissions:
        state = _clean(row.get("admission_state"))
        family_ref = _clean(row.get("trace_family_ref"))
        if not family_ref:
            reviews.append("admission_missing_trace_family_ref")
            continue
        if state == "REVIEW_REQUIRED":
            reviews.append(f"admission_row_review_required:{family_ref}")
            continue
        if state == "REJECTED_INSUFFICIENT_EVIDENCE":
            continue

        support = int(row.get("observed_support") or 0)
        eligible_refs = sorted({_clean(x) for x in (row.get("eligible_trace_refs") or []) if _clean(x)})
        if not eligible_refs:
            return _fail(f"admission_missing_eligible_trace_refs:{family_ref}")
        if len(eligible_refs) != support:
            return _fail(f"admission_trace_cohort_support_mismatch:{family_ref}")
        if family_ref not in eligible_refs:
            return _fail(f"admission_anchor_not_in_trace_cohort:{family_ref}")

        independent = row.get("independent_support_count", "UNKNOWN")
        failures = int(row.get("failure_variant_count") or 0)
        divergences = int(row.get("divergence_count") or 0)
        no_followup = int(row.get("no_visible_followup_count") or 0)
        robustness = _clean(row.get("robustness_state")) or "UNKNOWN"
        counter_refs = sorted({_clean(x) for x in (row.get("counterevidence_refs") or []) if _clean(x)})
        alternatives = [x for x in (row.get("alternative_explanations") or []) if isinstance(x, dict)]
        uncertainty = dict(row.get("uncertainty") or {})
        dependency = dict(row.get("dependency_summary") or {})
        withdrawal = _clean(row.get("withdrawal_condition"))

        null_summary: dict[str, Any] = {"state": "NOT_EVALUATED", "claim_strengthened": False}
        null_row = null_by_family.get(family_ref)
        if null_row is not None:
            null_refs = sorted({_clean(x) for x in (null_row.get("eligible_trace_refs") or []) if _clean(x)})
            if null_refs != eligible_refs:
                return _fail(f"null_contrast_trace_cohort_mismatch:{family_ref}")
            observed_null = null_row.get("observed_independent_recurrence")
            if isinstance(independent, int):
                if observed_null != independent:
                    return _fail(f"null_contrast_independent_support_mismatch:{family_ref}")
            elif observed_null != "UNKNOWN":
                return _fail(f"null_contrast_unknown_independence_escalated:{family_ref}")
            if null_row.get("claim_ceiling") != NULL_CLAIM_CEILING:
                return _fail(f"null_contrast_row_claim_ceiling_mismatch:{family_ref}")
            if null_row.get("multiple_testing_corrected") is not False:
                return _fail(f"null_contrast_multiple_testing_lock_breach:{family_ref}")
            if null_row.get("significance_claim_allowed") is not False:
                return _fail(f"null_contrast_significance_lock_breach:{family_ref}")
            if null_row.get("tactical_pattern_truth_allowed") is not False:
                return _fail(f"null_contrast_tactical_truth_lock_breach:{family_ref}")
            if null_row.get("causality_allowed") is not False:
                return _fail(f"null_contrast_causality_lock_breach:{family_ref}")
            null_withdrawal = _clean(null_row.get("withdrawal_condition"))
            if not null_withdrawal:
                return _fail(f"null_contrast_withdrawal_condition_missing:{family_ref}")
            null_summary = {
                "state": _clean(null_row.get("state")) or "UNKNOWN",
                "observed_independent_recurrence": observed_null,
                "simulation_count": null_row.get("simulation_count"),
                "null_mean": null_row.get("null_mean"),
                "null_median": null_row.get("null_median"),
                "null_q95": null_row.get("null_q95"),
                "empirical_upper_tail_probability_uncorrected": null_row.get("empirical_upper_tail_probability_uncorrected"),
                "observed_percentile_in_null_draws": null_row.get("observed_percentile_in_null_draws"),
                "null_model_id": null_row.get("null_model_id"),
                "null_model_version": null_row.get("null_model_version"),
                "null_mechanism": null_row.get("null_mechanism"),
                "preserved_constraints": list(null_row.get("preserved_constraints") or []),
                "exchangeability_assumption": null_row.get("exchangeability_assumption"),
                "multiple_testing_corrected": False,
                "significance_claim_allowed": False,
                "tactical_pattern_truth_allowed": False,
                "causality_allowed": False,
                "claim_strengthened": False,
                "withdrawal_condition": null_withdrawal,
                "claim_ceiling": NULL_CLAIM_CEILING,
            }

        what_visible = f"A comparable admitted visible trace family was observed {support} times in the current evidence scope."
        where_when = "The statement is restricted to the admitted match-local context and ordering evidence attached to the trace family."
        support_text = f"Observed support={support}; independent support={independent}; admission={state}; robustness={robustness}."
        if null_row is not None and isinstance(independent, int):
            support_text += (
                f" Defined-null contrast={null_summary['state']}; null median={null_summary['null_median']}; "
                f"uncorrected upper-tail probability={null_summary['empirical_upper_tail_probability_uncorrected']}."
            )
        counter_text = (
            f"Visible failure variants={failures}; divergence variants={divergences}; counterevidence refs={len(counter_refs)}. "
            f"No-visible-followup={no_followup} is reported separately and is not failure."
        )
        alt_types = sorted({_clean(x.get("type")) for x in alternatives if _clean(x.get("type"))})
        alternative_text = (
            "Visible alternatives/challenges: " + ", ".join(alt_types)
            if alt_types else
            "No explicit alternative signal is attached in the current evaluated scope; this does not prove the primary explanation."
        )
        if state == "ROBUST_RECURRENT_VISIBLE_TRACE":
            safe_meaning = (
                "A recurrent visible process candidate is supported across the tested robustness scope and explicitly admitted independent support; "
                "it remains descriptive evidence rather than tactical or causal truth."
            )
        elif state == "RECURRENT_VISIBLE_TRACE":
            safe_meaning = "A recurrent visible process candidate exists in the observed scope, but independence is not sufficiently established for a stronger robustness claim."
        elif state == "PROXY_CANDIDATE":
            safe_meaning = "A visible process candidate exists, but sensitivity evidence makes the recurrence interpretation conditional and fragile."
        else:
            safe_meaning = "A discovery-level visible process candidate exists and requires stronger recurrence/robustness evidence before promotion."
        if null_row is not None and isinstance(independent, int):
            safe_meaning += (
                " Its admitted independent recurrence can also be described relative to the supplied audited null distribution, "
                "without treating the uncorrected tail probability as significance, tactical truth or causality."
            )

        forbidden = sorted(set([
            "coach intention",
            "tactical plan truth",
            "team style truth",
            "causality",
            "dominance",
            "team shape",
            "true pressure geometry",
            "no-visible-followup as failure",
            "statistical significance from uncorrected null tail",
        ] + [_clean(x) for x in (row.get("forbidden_inference") or []) if _clean(x)]))
        analyst_action = "Review recurrent examples with failed/divergent twins, context-sensitive cases, dependency-linked views and any available defined-null contrast before using the finding in match analysis."
        report_blocks.append({
            "analyst_report_block_id": "sfb_" + _digest(family_ref, eligible_refs, state, support, robustness)[:24],
            "proposition": safe_meaning,
            "entity_scope": (row.get("source_anchor_context") or {}).get("team_identity_candidate_id") or "MATCH_LOCAL_ENTITY_SCOPE_CANDIDATE",
            "context_scope": row.get("context_scope") or [],
            "trace_family_refs": [family_ref],
            "trace_variant_refs": eligible_refs,
            "success_support": max(0, support - failures - divergences - no_followup),
            "failure_support": failures,
            "divergence_support": divergences,
            "no_visible_followup_support": no_followup,
            "recurrence_summary": {"observed_support": support, "eligible_trace_count": len(eligible_refs), "independent_support_count": independent, "admission_state": state},
            "robustness_summary": {"robustness_state": robustness},
            "null_contrast_summary": null_summary,
            "context_deviation_summary": "BOUND_TO_ADMITTED_CONTEXT_SCOPE_ONLY",
            "counterevidence": {"refs": counter_refs, "summary": counter_text},
            "alternative_explanations": alternatives,
            "dependency_summary": dependency,
            "uncertainty": uncertainty,
            "WHAT_VISIBLE": what_visible,
            "WHERE_WHEN": where_when,
            "SUPPORT": support_text,
            "COUNTEREVIDENCE": counter_text,
            "ALTERNATIVE_EXPLANATIONS": alternative_text,
            "SAFE_MEANING": safe_meaning,
            "FORBIDDEN_INFERENCE": forbidden,
            "ANALYST_ACTION": analyst_action,
            "withdrawal_condition": withdrawal or "Withdraw or downgrade if the admitted occurrence, ordering, dependency, contrast, robustness or context evidence changes materially.",
            "claim_ceiling": CLAIM_CEILING,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        })

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "SEQUENCE_SAFE_FINDING_BLOCKS_BUILT",
        "analyst_report_blocks": report_blocks,
        "analyst_report_block_count": len(report_blocks),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "complexity_inside_clarity_outside": True,
        "null_contrast_consumed": null_contrast_payload is not None,
        "professional_finding_emitted_count": 0,
        "claim_output_allowed_count": 0,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
