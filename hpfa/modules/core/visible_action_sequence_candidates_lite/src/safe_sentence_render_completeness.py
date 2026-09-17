from __future__ import annotations

from typing import Any

COMPLETE_BOUNDED_RENDER = "COMPLETE_BOUNDED_RENDER"
FACT_ONLY_RENDER = "FACT_ONLY_RENDER"
INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED = "INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED"
REVIEW_REQUIRED_SOURCE_CONTRACT_UNRESOLVED = "REVIEW_REQUIRED_SOURCE_CONTRACT_UNRESOLVED"

FACT_ONLY = "FACT_ONLY"
INTERPRETIVE = "INTERPRETIVE"

CLAIM_SCOPE_STRENGTH = {
    "NO_CLAIM_OUTPUT": 0,
    "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY": 1,
    "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY": 2,
}

TRUTH_LOCKS = {
    "render_creates_new_evidence": False,
    "render_can_authorize_emit": False,
    "render_can_strengthen_claim_ceiling": False,
    "analyst_or_llm_text_is_evidence": False,
    "absence_is_counterevidence": False,
    "provider_label_is_tactical_truth": False,
    "recurrence_is_causality": False,
    "coordinate_is_tracking_truth": False,
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
}


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return value not in (None, False, {}, [])


def _source_counter_scenarios(source_contract: dict[str, Any]) -> list[str]:
    return _strings(
        source_contract.get("variant_feature_challenge_counter_scenario_candidates")
        or source_contract.get("counter_scenario_candidates")
    )


def _source_withdrawal_conditions(source_contract: dict[str, Any]) -> list[str]:
    return _strings(
        source_contract.get("variant_feature_challenge_withdrawal_condition_candidates")
        or source_contract.get("withdrawal_condition_candidates")
    )


def _subset_or_reason(
    rendered: list[str],
    source: list[str],
    *,
    invented_reason: str,
) -> list[str]:
    return [invented_reason] if set(rendered) - set(source) else []


def validate_safe_sentence_render(
    source_contract: dict[str, Any] | None,
    rendered_sentence_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate one human-readable sentence contract against its source claim contract.

    This is a render-completeness guard only. It creates no evidence, cannot authorize
    EMIT, and cannot strengthen a source claim ceiling. Missing source qualifications are
    never invented; an interpretive sentence is blocked and may fall back to a visible
    fact only when WHAT_VISIBLE is already supplied by an admitted upstream surface.
    """
    source = source_contract if isinstance(source_contract, dict) else {}
    rendered = rendered_sentence_contract if isinstance(rendered_sentence_contract, dict) else {}

    source_ref = str(source.get("analyst_output_contract_id") or "").strip()
    rendered_source_ref = str(rendered.get("source_analyst_output_contract_ref") or "").strip()
    sentence_type = str(rendered.get("sentence_type") or "").strip().upper()
    source_scope = str(source.get("claim_scope") or "").strip()
    rendered_scope = str(rendered.get("claim_scope") or source_scope).strip()
    source_decision = str(source.get("safe_finding_admission_decision") or "NOT_EVALUATED").strip().upper()

    source_qualifiers = _strings(source.get("required_qualifiers"))
    rendered_qualifiers = _strings(rendered.get("required_qualifiers"))
    source_forbidden = _strings(source.get("forbidden_claim_families"))
    rendered_forbidden = _strings(rendered.get("forbidden_claim_families"))
    source_counter_scenarios = _source_counter_scenarios(source)
    rendered_counter_scenarios = _strings(rendered.get("counter_scenarios"))
    source_withdrawal = _source_withdrawal_conditions(source)
    rendered_withdrawal = _strings(rendered.get("withdrawal_conditions"))

    blocking: list[str] = []
    review: list[str] = []

    if not source_ref:
        review.append("source_analyst_output_contract_ref_missing")
    if not rendered_source_ref:
        review.append("render_source_contract_ref_missing")
    elif source_ref and rendered_source_ref != source_ref:
        review.append("render_source_contract_ref_mismatch")
    if source.get("canonical_event_count") != "UNKNOWN":
        blocking.append("source_canonical_event_count_claimed")
    if source.get("true_action_count") != "UNKNOWN":
        blocking.append("source_true_action_count_claimed")
    if source.get("production_release") is True:
        blocking.append("source_production_release_claimed")
    if source.get("analyst_or_llm_text_is_evidence") is not False:
        blocking.append("source_text_evidence_lock_missing")
    if sentence_type not in {FACT_ONLY, INTERPRETIVE}:
        review.append("sentence_type_unresolved")

    what_visible = str(rendered.get("what_visible") or "").strip()
    safe_meaning = str(rendered.get("safe_meaning") or "").strip()
    claim_limiter = str(rendered.get("claim_limiter") or "").strip()

    fallback_allowed = bool(what_visible)
    fallback_mode = FACT_ONLY_RENDER if fallback_allowed else None

    if rendered.get("render_authorizes_emit") is True or rendered.get("professional_emit_allowed") is True:
        blocking.append("render_attempted_to_authorize_emit")
    if rendered.get("render_creates_new_evidence") is True:
        blocking.append("render_attempted_to_create_evidence")
    if rendered.get("analyst_or_llm_text_is_evidence") is True:
        blocking.append("render_attempted_to_promote_text_to_evidence")
    if rendered.get("absence_is_counterevidence") is True:
        blocking.append("render_attempted_to_promote_absence_to_counterevidence")

    source_evidence_refs = _strings(source.get("render_evidence_refs") or source.get("evidence_refs"))
    rendered_evidence_refs = _strings(rendered.get("evidence_refs"))
    source_counterevidence_refs = _strings(source.get("render_counterevidence_refs") or source.get("counterevidence_refs"))
    rendered_counterevidence_refs = _strings(rendered.get("counterevidence_refs"))
    blocking.extend(
        _subset_or_reason(
            rendered_evidence_refs,
            source_evidence_refs,
            invented_reason="render_invented_evidence_ref",
        )
    )
    blocking.extend(
        _subset_or_reason(
            rendered_counterevidence_refs,
            source_counterevidence_refs,
            invented_reason="render_invented_counterevidence_ref",
        )
    )
    blocking.extend(
        _subset_or_reason(
            rendered_counter_scenarios,
            source_counter_scenarios,
            invented_reason="render_invented_counter_scenario",
        )
    )
    blocking.extend(
        _subset_or_reason(
            rendered_withdrawal,
            source_withdrawal,
            invented_reason="render_invented_withdrawal_condition",
        )
    )

    source_strength = CLAIM_SCOPE_STRENGTH.get(source_scope)
    rendered_strength = CLAIM_SCOPE_STRENGTH.get(rendered_scope)
    if source_strength is None or rendered_strength is None:
        review.append("claim_scope_strength_unresolved")
    elif rendered_strength > source_strength:
        blocking.append("render_claim_scope_stronger_than_source")

    if sentence_type == FACT_ONLY:
        if not what_visible:
            blocking.append("fact_only_what_visible_missing")
        if _nonempty(rendered.get("safe_meaning")):
            blocking.append("fact_only_render_contains_interpretation")
        state = FACT_ONLY_RENDER if not blocking and not review else (
            REVIEW_REQUIRED_SOURCE_CONTRACT_UNRESOLVED if review and not blocking else INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED
        )
        render_allowed = state == FACT_ONLY_RENDER
    elif sentence_type == INTERPRETIVE:
        if source_decision == "ABSTAIN":
            blocking.append("source_abstain_blocks_interpretive_render")
        if not what_visible:
            blocking.append("interpretive_what_visible_missing")
        if not safe_meaning:
            blocking.append("interpretive_safe_meaning_missing")
        if not claim_limiter:
            blocking.append("interpretive_claim_limiter_missing")
        if source_qualifiers and not set(source_qualifiers).issubset(rendered_qualifiers):
            blocking.append("required_qualifiers_not_preserved")
        if source_forbidden and not set(source_forbidden).issubset(rendered_forbidden):
            blocking.append("forbidden_claim_families_not_preserved")
        if source_counter_scenarios and not rendered_counter_scenarios:
            blocking.append("required_counter_scenario_missing")
        if source_withdrawal and not rendered_withdrawal:
            blocking.append("required_withdrawal_condition_missing")
        if blocking:
            state = INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED
        elif review:
            state = REVIEW_REQUIRED_SOURCE_CONTRACT_UNRESOLVED
        else:
            state = COMPLETE_BOUNDED_RENDER
        render_allowed = state == COMPLETE_BOUNDED_RENDER
    else:
        state = REVIEW_REQUIRED_SOURCE_CONTRACT_UNRESOLVED
        render_allowed = False

    return {
        "source_analyst_output_contract_ref": source_ref or None,
        "source_safe_finding_handoff_ref": source.get("source_safe_finding_handoff_ref"),
        "source_safe_finding_admission_decision": source_decision,
        "source_claim_scope": source_scope or None,
        "rendered_claim_scope": rendered_scope or None,
        "sentence_type": sentence_type or None,
        "what_visible": what_visible or None,
        "safe_meaning": safe_meaning or None,
        "claim_limiter": claim_limiter or None,
        "counter_scenarios": rendered_counter_scenarios,
        "withdrawal_conditions": rendered_withdrawal,
        "analyst_action": rendered.get("analyst_action"),
        "render_completeness_state": state,
        "blocking_reasons": sorted(set(blocking)),
        "review_reasons": sorted(set(review)),
        "render_allowed": render_allowed,
        "fallback_allowed": fallback_allowed and not render_allowed,
        "fallback_mode": fallback_mode if fallback_allowed and not render_allowed else None,
        "source_required_qualifiers": source_qualifiers,
        "source_forbidden_claim_families": source_forbidden,
        "source_counter_scenario_candidates": source_counter_scenarios,
        "source_withdrawal_condition_candidates": source_withdrawal,
        "rendered_required_qualifiers": rendered_qualifiers,
        "rendered_forbidden_claim_families": rendered_forbidden,
        "rendered_evidence_refs": rendered_evidence_refs,
        "rendered_counterevidence_refs": rendered_counterevidence_refs,
        "render_pass_increases_independent_support": False,
        "render_pass_authorizes_emit": False,
        **TRUTH_LOCKS,
    }
