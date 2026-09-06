from __future__ import annotations

import hashlib
import json
from typing import Any

MODULE_ID = "sequence_safe_finding_binding_lite_v1"
ADMISSION_MODULE_ID = "sequence_pattern_admission_lite_v1"
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


def build_sequence_safe_finding_blocks(admission_payload: dict[str, Any]) -> dict[str, Any]:
    """Project admitted sequence evidence into readable, defeasible analyst blocks.

    This is a presentation/binding layer over admitted evidence. It does not discover
    patterns, infer causality, manufacture independence, or release production truth.
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

        what_visible = f"A comparable admitted visible trace family was observed {support} times in the current evidence scope."
        where_when = "The statement is restricted to the admitted match-local context and ordering evidence attached to the trace family."
        support_text = f"Observed support={support}; independent support={independent}; admission={state}; robustness={robustness}."
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

        forbidden = sorted(set([
            "coach intention",
            "tactical plan truth",
            "team style truth",
            "causality",
            "dominance",
            "team shape",
            "true pressure geometry",
            "no-visible-followup as failure",
        ] + [_clean(x) for x in (row.get("forbidden_inference") or []) if _clean(x)]))
        analyst_action = "Review the recurrent trace examples together with failed/divergent twins, context-sensitive cases and dependency-linked views before using the finding in match analysis."
        proposition = safe_meaning
        report_blocks.append({
            "analyst_report_block_id": "sfb_" + _digest(family_ref, eligible_refs, state, support, robustness)[:24],
            "proposition": proposition,
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
        "professional_finding_emitted_count": 0,
        "claim_output_allowed_count": 0,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
