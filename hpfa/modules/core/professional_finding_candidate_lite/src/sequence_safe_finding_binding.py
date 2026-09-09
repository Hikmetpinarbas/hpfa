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
SAFE_EMITTING_ADMISSION_STATES = {"DISCOVERY_ONLY", "PROXY_CANDIDATE", "RECURRENT_VISIBLE_TRACE", "ROBUST_RECURRENT_VISIBLE_TRACE"}
NON_EMITTING_ADMISSION_STATES = {"REJECTED_INSUFFICIENT_EVIDENCE", "REVIEW_REQUIRED"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _clean_ref_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fail(*blocks: str) -> dict[str, Any]:
    return {"module_id": MODULE_ID, "status": "FAIL_CLOSED", "decision": "SEQUENCE_SAFE_FINDING_BINDING_REJECTED", "analyst_report_blocks": [], "analyst_report_block_count": 0, "hard_block_hits": sorted(set(blocks)), "professional_finding_emitted_count": 0, "claim_output_allowed_count": 0, "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0}, "canonical_event_count": CANONICAL_EVENT_COUNT, "true_action_count": TRUE_ACTION_COUNT, "production_release": False, "claim_ceiling": CLAIM_CEILING}


def _index_null_contrast(null_payload: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    if null_payload is None:
        return {}, [], []
    blocks: list[str] = []
    reviews: list[str] = []
    if null_payload.get("contrast_id") != NULL_CONTRAST_ID: blocks.append("null_contrast_id_mismatch")
    if null_payload.get("claim_ceiling") != NULL_CLAIM_CEILING: blocks.append("null_contrast_claim_ceiling_mismatch")
    if null_payload.get("multiple_testing_corrected") is not False: blocks.append("null_contrast_multiple_testing_lock_breach")
    if null_payload.get("significance_claim_allowed") is not False: blocks.append("null_contrast_significance_lock_breach")
    if null_payload.get("tactical_pattern_truth_allowed") is not False: blocks.append("null_contrast_tactical_truth_lock_breach")
    if null_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT: blocks.append("null_contrast_canonical_event_count_claimed")
    if null_payload.get("true_action_count") != TRUE_ACTION_COUNT: blocks.append("null_contrast_true_action_count_claimed")
    if null_payload.get("production_release") is True: blocks.append("null_contrast_production_release_claimed")
    if null_payload.get("hard_block_hits"): blocks.append("null_contrast_hard_blocks_present")
    status = _clean(null_payload.get("status")).upper()
    if status == "FAIL_CLOSED": blocks.append("null_contrast_input_fail_closed")
    elif status == "REVIEW_REQUIRED": reviews.append("null_contrast_upstream_review_required")
    elif status != "PASS": reviews.append(f"null_contrast_status_review:{status or 'UNKNOWN'}")
    indexed: dict[str, dict[str, Any]] = {}
    for row in [r for r in (null_payload.get("rows") or []) if isinstance(r, dict)]:
        family_ref = _clean(row.get("trace_family_ref"))
        if not family_ref: blocks.append("null_contrast_family_ref_missing"); continue
        if family_ref in indexed: blocks.append(f"null_contrast_family_duplicate:{family_ref}"); continue
        indexed[family_ref] = row
    return indexed, blocks, reviews


def _safe_finding_occurrence_context(row: dict[str, Any], family_ref: str) -> tuple[dict[str, Any], str | None]:
    state = _clean(row.get("sequence_occurrence_object_context_state"))
    team_refs = _clean_ref_list(row.get("sequence_occurrence_team_context_refs")); goalkeeper_refs = _clean_ref_list(row.get("sequence_occurrence_goalkeeper_context_refs")); goalkeeper_bundle_refs = _clean_ref_list(row.get("sequence_occurrence_goalkeeper_context_bundle_refs")); reflection_refs = _clean_ref_list(row.get("sequence_occurrence_reflection_context_refs")); relation_types = _clean_ref_list(row.get("sequence_occurrence_relation_type_candidates"))
    has_refs = any((team_refs, goalkeeper_refs, goalkeeper_bundle_refs, reflection_refs, relation_types))
    if state == "REVIEW_REQUIRED": return {}, f"safe_finding_occurrence_context_upstream_review:{family_ref}"
    if state == "PATTERN_OCCURRENCE_CONTEXT_LINEAGE_ONLY":
        locks = (row.get("sequence_occurrence_context_is_pattern_support") is False, row.get("sequence_occurrence_context_is_independent_support") is False, row.get("goalkeeper_context_is_pattern_participant_truth") is False, row.get("reflection_context_is_pattern_equivalence_truth") is False, row.get("sequence_occurrence_context_ref_count_is_pattern_count") is False, row.get("sequence_occurrence_context_ref_count_is_recurrence_count") is False, row.get("sequence_occurrence_context_creates_event") is False)
        if not all(locks): return {}, f"safe_finding_occurrence_context_claim_boundary_mismatch:{family_ref}"
    elif has_refs: return {}, f"safe_finding_occurrence_context_state_missing_or_unexpected:{family_ref}"
    elif state not in {"", "NO_CONTEXT_VISIBLE"}: return {}, f"safe_finding_occurrence_context_state_unrecognized:{family_ref}"
    return {"sequence_occurrence_object_context_state": "SAFE_FINDING_OCCURRENCE_CONTEXT_LINEAGE_ONLY" if has_refs else "NO_CONTEXT_VISIBLE", "sequence_occurrence_team_context_refs": team_refs, "sequence_occurrence_goalkeeper_context_refs": goalkeeper_refs, "sequence_occurrence_goalkeeper_context_bundle_refs": goalkeeper_bundle_refs, "sequence_occurrence_reflection_context_refs": reflection_refs, "sequence_occurrence_relation_type_candidates": relation_types, "sequence_occurrence_context_is_finding_support": False, "sequence_occurrence_context_is_prose_support": False, "sequence_occurrence_context_is_independent_support": False, "goalkeeper_context_is_finding_participant_truth": False, "reflection_context_is_finding_equivalence_truth": False, "sequence_occurrence_context_ref_count_is_action_count": False, "sequence_occurrence_context_ref_count_is_event_count": False, "sequence_occurrence_context_ref_count_is_recurrence_strength": False, "sequence_occurrence_context_ref_count_is_robustness_score": False, "sequence_occurrence_context_creates_event": False, "sequence_occurrence_context_is_tactical_truth": False, "sequence_occurrence_context_is_causal_truth": False}, None


def _finding_status(*, admission_state: str, independent_support: Any, counter_refs: list[str], alternatives: list[dict[str, Any]], withdrawal_condition: str, uncertainty: dict[str, Any], dependency: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if admission_state in {"DISCOVERY_ONLY", "PROXY_CANDIDATE"}: reasons.append("admission_ceiling_below_recurrent_visible_trace")
    if not isinstance(independent_support, int) or independent_support < 1: reasons.append("independent_support_not_admitted")
    if not withdrawal_condition: reasons.append("withdrawal_condition_missing")
    if uncertainty.get("recurrence_is_tactical_intention_truth") is not False: reasons.append("uncertainty_truth_lock_missing")
    if dependency.get("independence_proven") is not True: reasons.append("dependency_independence_not_proven")
    if not counter_refs and not alternatives: reasons.append("challenge_surface_empty")
    if admission_state == "ROBUST_RECURRENT_VISIBLE_TRACE" and not reasons: return "EMIT", []
    return "DOWNGRADE", sorted(set(reasons))


def build_sequence_safe_finding_blocks(admission_payload: dict[str, Any], null_contrast_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    blocks: list[str] = []; reviews: list[str] = []; abstain_count = 0
    if admission_payload.get("module_id") != ADMISSION_MODULE_ID: blocks.append("admission_module_id_mismatch")
    if admission_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT: blocks.append("canonical_event_count_claimed")
    if admission_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}: blocks.append("true_action_count_claimed")
    if admission_payload.get("production_release") is True: blocks.append("production_release_claimed")
    if admission_payload.get("hard_block_hits"): blocks.append("admission_hard_blocks_present")
    if admission_payload.get("tactical_pattern_state_allowed") is not False: blocks.append("tactical_pattern_lock_missing")
    if admission_payload.get("coach_intention_state_allowed") is not False: blocks.append("coach_intention_lock_missing")
    if admission_payload.get("team_style_truth_state_allowed") is not False: blocks.append("team_style_truth_lock_missing")
    status = _clean(admission_payload.get("status")).upper()
    if status == "FAIL_CLOSED": blocks.append("admission_input_fail_closed")
    elif status == "REVIEW_REQUIRED": reviews.append("admission_upstream_review_required")
    elif status != "PASS": reviews.append(f"admission_status_review:{status or 'UNKNOWN'}")
    null_by_family, null_blocks, null_reviews = _index_null_contrast(null_contrast_payload); blocks.extend(null_blocks); reviews.extend(null_reviews)
    if blocks: return _fail(*blocks)
    admissions = [row for row in (admission_payload.get("sequence_pattern_admissions") or []) if isinstance(row, dict)]
    for row in admissions:
        state = _clean(row.get("admission_state"))
        if state not in SAFE_EMITTING_ADMISSION_STATES | NON_EMITTING_ADMISSION_STATES: return _fail(f"unsupported_admission_state:{state or 'UNKNOWN'}")
    if reviews:
        return {"module_id": MODULE_ID, "status": "REVIEW_REQUIRED", "decision": "SEQUENCE_SAFE_FINDING_BLOCKS_ABSTAINED_PENDING_UPSTREAM_REVIEW", "analyst_report_blocks": [], "analyst_report_block_count": 0, "hard_block_hits": [], "review_hits": sorted(set(reviews)), "complexity_inside_clarity_outside": True, "null_contrast_consumed": null_contrast_payload is not None, "professional_finding_emitted_count": 0, "claim_output_allowed_count": 0, "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": len(admissions)}, "canonical_event_count": CANONICAL_EVENT_COUNT, "true_action_count": TRUE_ACTION_COUNT, "production_release": False, "claim_ceiling": CLAIM_CEILING}
    report_blocks: list[dict[str, Any]] = []
    for row in admissions:
        state = _clean(row.get("admission_state")); family_ref = _clean(row.get("trace_family_ref"))
        if not family_ref: reviews.append("admission_missing_trace_family_ref"); abstain_count += 1; continue
        if state == "REVIEW_REQUIRED": reviews.append(f"admission_row_review_required:{family_ref}"); abstain_count += 1; continue
        if state == "REJECTED_INSUFFICIENT_EVIDENCE": abstain_count += 1; continue
        support = int(row.get("observed_support") or 0); eligible_refs = sorted({_clean(x) for x in (row.get("eligible_trace_refs") or []) if _clean(x)})
        if not eligible_refs: return _fail(f"admission_missing_eligible_trace_refs:{family_ref}")
        if len(eligible_refs) != support: return _fail(f"admission_trace_cohort_support_mismatch:{family_ref}")
        if family_ref not in eligible_refs: return _fail(f"admission_anchor_not_in_trace_cohort:{family_ref}")
        occurrence_context, occurrence_context_review = _safe_finding_occurrence_context(row, family_ref)
        if occurrence_context_review: reviews.append(occurrence_context_review); abstain_count += 1; continue
        independent = row.get("independent_support_count", "UNKNOWN"); failures = int(row.get("failure_variant_count") or 0); divergences = int(row.get("divergence_count") or 0); no_followup = int(row.get("no_visible_followup_count") or 0); robustness = _clean(row.get("robustness_state")) or "UNKNOWN"; counter_refs = sorted({_clean(x) for x in (row.get("counterevidence_refs") or []) if _clean(x)}); alternatives = [x for x in (row.get("alternative_explanations") or []) if isinstance(x, dict)]; uncertainty = dict(row.get("uncertainty") or {}); dependency = dict(row.get("dependency_summary") or {}); withdrawal = _clean(row.get("withdrawal_condition"))
        null_summary: dict[str, Any] = {"state": "NOT_EVALUATED", "claim_strengthened": False}
        null_row = null_by_family.get(family_ref)
        if null_row is not None:
            null_refs = sorted({_clean(x) for x in (null_row.get("eligible_trace_refs") or []) if _clean(x)})
            if null_refs != eligible_refs: return _fail(f"null_contrast_trace_cohort_mismatch:{family_ref}")
            observed_null = null_row.get("observed_independent_recurrence")
            if isinstance(independent, int):
                if observed_null != independent: return _fail(f"null_contrast_independent_support_mismatch:{family_ref}")
            elif observed_null != "UNKNOWN": return _fail(f"null_contrast_unknown_independence_escalated:{family_ref}")
            if null_row.get("claim_ceiling") != NULL_CLAIM_CEILING: return _fail(f"null_contrast_row_claim_ceiling_mismatch:{family_ref}")
            if null_row.get("multiple_testing_corrected") is not False: return _fail(f"null_contrast_multiple_testing_lock_breach:{family_ref}")
            if null_row.get("significance_claim_allowed") is not False: return _fail(f"null_contrast_significance_lock_breach:{family_ref}")
            if null_row.get("tactical_pattern_truth_allowed") is not False: return _fail(f"null_contrast_tactical_truth_lock_breach:{family_ref}")
            if null_row.get("causality_allowed") is not False: return _fail(f"null_contrast_causality_lock_breach:{family_ref}")
            simulation_count = null_row.get("simulation_count"); tail_resolution = null_row.get("empirical_upper_tail_resolution")
            if not isinstance(simulation_count, int) or simulation_count < 1: return _fail(f"null_contrast_simulation_count_invalid:{family_ref}")
            expected_resolution = 1 / (simulation_count + 1)
            if not isinstance(tail_resolution, (int, float)) or abs(float(tail_resolution) - expected_resolution) > 1e-12: return _fail(f"null_contrast_tail_resolution_mismatch:{family_ref}")
            if null_row.get("finite_simulation_resolution_only") is not True: return _fail(f"null_contrast_finite_resolution_lock_breach:{family_ref}")
            null_withdrawal = _clean(null_row.get("withdrawal_condition"))
            if not null_withdrawal: return _fail(f"null_contrast_withdrawal_condition_missing:{family_ref}")
            null_summary = {"state": _clean(null_row.get("state")) or "UNKNOWN", "observed_independent_recurrence": observed_null, "simulation_count": simulation_count, "null_mean": null_row.get("null_mean"), "null_median": null_row.get("null_median"), "null_q95": null_row.get("null_q95"), "empirical_upper_tail_probability_uncorrected": null_row.get("empirical_upper_tail_probability_uncorrected"), "empirical_upper_tail_resolution": float(tail_resolution), "finite_simulation_resolution_only": True, "observed_percentile_in_null_draws": null_row.get("observed_percentile_in_null_draws"), "null_model_id": null_row.get("null_model_id"), "null_model_version": null_row.get("null_model_version"), "null_mechanism": null_row.get("null_mechanism"), "preserved_constraints": list(null_row.get("preserved_constraints") or []), "exchangeability_assumption": null_row.get("exchangeability_assumption"), "multiple_testing_corrected": False, "significance_claim_allowed": False, "tactical_pattern_truth_allowed": False, "causality_allowed": False, "claim_strengthened": False, "withdrawal_condition": null_withdrawal, "claim_ceiling": NULL_CLAIM_CEILING}
        what_visible = f"A comparable admitted visible trace family was observed {support} times in the current evidence scope."; where_when = "The statement is restricted to the admitted match-local context and ordering evidence attached to the trace family."; support_text = f"Observed support={support}; independent support={independent}; admission={state}; robustness={robustness}."
        if null_row is not None and isinstance(independent, int): support_text += f" Defined-null contrast={null_summary['state']}; null median={null_summary['null_median']}; uncorrected upper-tail probability={null_summary['empirical_upper_tail_probability_uncorrected']}; finite-simulation tail resolution={null_summary['empirical_upper_tail_resolution']}."
        counter_text = f"Visible failure variants={failures}; divergence variants={divergences}; counterevidence refs={len(counter_refs)}. No-visible-followup={no_followup} is reported separately and is not failure."
        alt_types = sorted({_clean(x.get("type")) for x in alternatives if _clean(x.get("type"))}); alternative_text = "Visible alternatives/challenges: " + ", ".join(alt_types) if alt_types else "No explicit alternative signal is attached in the current evaluated scope; this does not prove the primary explanation."
        if state == "ROBUST_RECURRENT_VISIBLE_TRACE": safe_meaning = "A recurrent visible process candidate is supported across the tested robustness scope and explicitly admitted independent support; it remains descriptive evidence rather than tactical or causal truth."
        elif state == "RECURRENT_VISIBLE_TRACE": safe_meaning = "A recurrent visible process candidate exists in the observed scope, but independence is not sufficiently established for a stronger robustness claim."
        elif state == "PROXY_CANDIDATE": safe_meaning = "A visible process candidate exists, but sensitivity evidence makes the recurrence interpretation conditional and fragile."
        else: safe_meaning = "A discovery-level visible process candidate exists and requires stronger recurrence/robustness evidence before promotion."
        if null_row is not None and isinstance(independent, int): safe_meaning += " Its admitted independent recurrence can also be described relative to the supplied audited null distribution at the explicit finite-simulation tail resolution, without treating the uncorrected tail probability as significance, tactical truth or causality."
        forbidden = sorted(set(["coach intention", "tactical plan truth", "team style truth", "causality", "dominance", "team shape", "true pressure geometry", "no-visible-followup as failure", "statistical significance from uncorrected null tail"] + [_clean(x) for x in (row.get("forbidden_inference") or []) if _clean(x)])); analyst_action = "Review recurrent examples with failed/divergent twins, context-sensitive cases, dependency-linked views and any available defined-null contrast before using the finding in match analysis."
        finding_status, downgrade_reasons = _finding_status(admission_state=state, independent_support=independent, counter_refs=counter_refs, alternatives=alternatives, withdrawal_condition=withdrawal, uncertainty=uncertainty, dependency=dependency); professional_finding_emitted = finding_status == "EMIT"
        report_blocks.append({"analyst_report_block_id": "sfb_" + _digest(family_ref, eligible_refs, state, support, robustness)[:24], "proposition": safe_meaning, "entity_scope": (row.get("source_anchor_context") or {}).get("team_identity_candidate_id") or "MATCH_LOCAL_ENTITY_SCOPE_CANDIDATE", "context_scope": row.get("context_scope") or [], "trace_family_refs": [family_ref], "trace_variant_refs": eligible_refs, "success_support": max(0, support - failures - divergences - no_followup), "failure_support": failures, "divergence_support": divergences, "no_visible_followup_support": no_followup, "recurrence_summary": {"observed_support": support, "eligible_trace_count": len(eligible_refs), "independent_support_count": independent, "admission_state": state}, "robustness_summary": {"robustness_state": robustness}, "null_contrast_summary": null_summary, "context_deviation_summary": "BOUND_TO_ADMITTED_CONTEXT_SCOPE_ONLY", **occurrence_context, "counterevidence": {"refs": counter_refs, "summary": counter_text}, "alternative_explanations": alternatives, "dependency_summary": dependency, "uncertainty": uncertainty, "WHAT_VISIBLE": what_visible, "WHERE_WHEN": where_when, "SUPPORT": support_text, "COUNTEREVIDENCE": counter_text, "ALTERNATIVE_EXPLANATIONS": alternative_text, "SAFE_MEANING": safe_meaning, "FORBIDDEN_INFERENCE": forbidden, "ANALYST_ACTION": analyst_action, "withdrawal_condition": withdrawal or "Withdraw or downgrade if the admitted occurrence, ordering, dependency, contrast, robustness or context evidence changes materially.", "finding_status": finding_status, "downgrade_reasons": downgrade_reasons, "claim_ceiling": CLAIM_CEILING, "professional_finding_emitted": professional_finding_emitted, "claim_output_allowed": professional_finding_emitted, "canonical_event_count": CANONICAL_EVENT_COUNT, "true_action_count": TRUE_ACTION_COUNT, "production_release": False})
    emitted = sum(1 for row in report_blocks if row["finding_status"] == "EMIT"); downgraded = sum(1 for row in report_blocks if row["finding_status"] == "DOWNGRADE")
    return {"module_id": MODULE_ID, "status": "REVIEW_REQUIRED" if reviews else "PASS", "decision": "SEQUENCE_SAFE_FINDING_BLOCKS_BUILT", "analyst_report_blocks": report_blocks, "analyst_report_block_count": len(report_blocks), "hard_block_hits": [], "review_hits": sorted(set(reviews)), "complexity_inside_clarity_outside": True, "null_contrast_consumed": null_contrast_payload is not None, "professional_finding_emitted_count": emitted, "claim_output_allowed_count": emitted, "finding_status_counts": {"EMIT": emitted, "DOWNGRADE": downgraded, "ABSTAIN": abstain_count}, "canonical_event_count": CANONICAL_EVENT_COUNT, "true_action_count": TRUE_ACTION_COUNT, "production_release": False, "claim_ceiling": CLAIM_CEILING}
