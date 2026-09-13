from __future__ import annotations

import hashlib
import json
from typing import Any

CLAIM_CEILING = "MATCH_LOCAL_DESCRIPTIVE_VARIANT_FEATURE_CHALLENGE_PACKET_ONLY"

_COUNTER_SCENARIOS = [
    "OPPONENT_BEHAVIOUR_OR_SCORE_STATE_MAY_EXPLAIN_DIFFERENCE",
    "SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE",
    "UNRESOLVED_DEPENDENCY_MAY_INFLATE_APPARENT_SUPPORT",
    "OBSERVATION_COVERAGE_OR_PROVIDER_SEMANTICS_MAY_EXPLAIN_DIFFERENCE",
]

_WITHDRAWAL_CONDITIONS = [
    "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_DISAPPEARS_IN_ADMITTED_COMPARABLE_CONTEXT",
    "WITHDRAW_OR_QUALIFY_IF_DEPENDENCY_RESOLUTION_REMOVES_APPARENT_SUPPORT",
    "WITHDRAW_OR_QUALIFY_IF_SOURCE_EVIDENCE_REFS_CANNOT_BE_RESOLVED",
]

_CONSEQUENCE_COUNTER_SCENARIOS = [
    "CONSEQUENCE_HORIZON_DEFINITION_MAY_CHANGE_APPARENT_DIFFERENCE",
    "UNASSESSED_CENSORING_MAY_CHANGE_APPARENT_DIFFERENCE",
]

_CONSEQUENCE_WITHDRAWAL_CONDITIONS = [
    "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_IS_NOT_STABLE_ACROSS_ADMITTED_CONSEQUENCE_HORIZONS",
    "WITHDRAW_OR_QUALIFY_IF_CENSORING_RESOLUTION_CHANGES_THE_APPARENT_DIFFERENCE",
]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _index(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    return {
        _clean(row.get(key)): row
        for row in (rows or [])
        if isinstance(row, dict) and _clean(row.get(key))
    }


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _challenge_row(
    *,
    delta_record: dict[str, Any],
    family: dict[str, Any],
    feature: dict[str, Any],
    feature_surface: str,
) -> dict[str, Any] | None:
    source_delta_ref = _clean(delta_record.get("grammar_stable_variant_feature_delta_id"))
    family_ref = _clean(delta_record.get("source_process_variant_family_ref"))
    feature_token = _clean(feature.get("feature_token"))
    if not source_delta_ref or not family_ref or not feature_token:
        return None

    success_numerator = _int(feature.get("success_visible_numerator"))
    success_denominator = _int(feature.get("success_eligible_denominator"))
    failure_numerator = _int(feature.get("failure_visible_numerator"))
    failure_denominator = _int(feature.get("failure_eligible_denominator"))
    if None in (success_numerator, success_denominator, failure_numerator, failure_denominator):
        return None
    if success_denominator <= 0 or failure_denominator <= 0:
        return None
    if success_numerator < 0 or failure_numerator < 0:
        return None
    if success_numerator > success_denominator or failure_numerator > failure_denominator:
        return None

    periods = sorted({_clean(v) for v in (family.get("period_candidates") or []) if _clean(v)})
    teams = sorted({_clean(v) for v in (family.get("team_identity_candidate_ids") or []) if _clean(v)})
    dependency_refs = sorted({_clean(v) for v in (family.get("dependency_group_refs") or []) if _clean(v)})
    dependency_count_raw = _int(family.get("dependency_group_ref_count"))
    dependency_count = dependency_count_raw if dependency_count_raw is not None else len(dependency_refs)

    visible_in_success = success_numerator > 0
    visible_in_failure = failure_numerator > 0
    if visible_in_success and visible_in_failure:
        partition_visibility_state = "VISIBLE_IN_BOTH_OUTCOME_PARTITIONS"
        failed_trace_falsifier_state = "NON_DISCRIMINATIVE_PRESENCE_VISIBLE"
    else:
        partition_visibility_state = "VISIBLE_IN_ONE_OUTCOME_PARTITION_ONLY"
        failed_trace_falsifier_state = "ONE_PARTITION_ONLY_VISIBLE_ABSENCE_NOT_COUNTEREVIDENCE"

    context_scope_state = (
        "SINGLE_TEAM_SINGLE_PERIOD_SCOPE"
        if len(teams) <= 1 and len(periods) <= 1
        else "MULTI_SCOPE_PRESENT_CONTEXT_ROBUSTNESS_NOT_ESTABLISHED"
    )
    segment_falsifier_state = (
        "PENDING_SINGLE_PERIOD_SCOPE"
        if len(periods) <= 1
        else "MULTI_PERIOD_SCOPE_PRESENT_PERIOD_ALONE_NOT_CONTEXT_ROBUSTNESS"
    )

    context_incomplete = int(delta_record.get("context_coverage_incomplete_variant_count") or 0)
    consequence_incomplete = int(delta_record.get("consequence_coverage_incomplete_variant_count") or 0)
    relevant_incomplete = context_incomplete if feature_surface == "CONTEXT" else consequence_incomplete

    dependency_independence_proven = (
        feature.get("dependency_independence_proven") is True
        and family.get("family_is_independent_recurrence_truth") is True
    )
    statistical_independence_proven = feature.get("statistical_independence_proven") is True

    consequence_contract_present = (
        feature_surface == "CONSEQUENCE"
        and delta_record.get("consequence_observation_state_features_consumed") is True
    )
    consequence_horizon_state = (
        _clean(delta_record.get("consequence_horizon_definition_state"))
        if consequence_contract_present
        else "LEGACY_OR_NOT_APPLICABLE"
    )
    consequence_horizon_sensitivity_tested = (
        delta_record.get("consequence_horizon_sensitivity_tested") is True
        if consequence_contract_present
        else False
    )
    admitted_followup_horizon_sensitivity_tested = (
        delta_record.get("admitted_followup_horizon_sensitivity_tested") is True
        if consequence_contract_present
        else False
    )
    admitted_followup_horizon_sensitive_variant_count = (
        int(delta_record.get("admitted_followup_horizon_sensitive_variant_count") or 0)
        if consequence_contract_present
        else 0
    )
    admitted_followup_horizon_sensitivity_incomplete_variant_count = (
        int(delta_record.get("admitted_followup_horizon_sensitivity_incomplete_variant_count") or 0)
        if consequence_contract_present
        else 0
    )
    right_censoring_assessed = (
        delta_record.get("right_censoring_assessed") is True
        if consequence_contract_present
        else False
    )
    right_censored_variant_count = (
        int(delta_record.get("right_censored_variant_count") or 0)
        if consequence_contract_present
        else 0
    )
    right_censoring_incomplete_variant_count = (
        int(delta_record.get("right_censoring_incomplete_variant_count") or 0)
        if consequence_contract_present
        else 0
    )
    fully_observed_no_followup_variant_count = (
        int(delta_record.get("fully_observed_no_followup_variant_count") or 0)
        if consequence_contract_present
        else 0
    )

    challenge_reasons = [
        "SAMPLE_STRENGTH_UNCALIBRATED",
        "CONTEXT_ROBUSTNESS_NOT_TESTED",
    ]
    if not dependency_independence_proven:
        challenge_reasons.append("DEPENDENCY_INDEPENDENCE_UNPROVEN")
    if not statistical_independence_proven:
        challenge_reasons.append("STATISTICAL_INDEPENDENCE_UNPROVEN")
    if relevant_incomplete:
        challenge_reasons.append("OBSERVATION_COVERAGE_PARTIAL")
    if len(periods) <= 1:
        challenge_reasons.append("SINGLE_PERIOD_SCOPE")
    if visible_in_success and visible_in_failure:
        challenge_reasons.append("FEATURE_VISIBLE_IN_BOTH_OUTCOME_PARTITIONS")

    counter_scenarios = list(_COUNTER_SCENARIOS)
    withdrawal_conditions = list(_WITHDRAWAL_CONDITIONS)
    if consequence_contract_present:
        counter_scenarios.extend(_CONSEQUENCE_COUNTER_SCENARIOS)
        withdrawal_conditions.extend(_CONSEQUENCE_WITHDRAWAL_CONDITIONS)
        if consequence_horizon_state == "HORIZON_UNSPECIFIED":
            challenge_reasons.append("CONSEQUENCE_HORIZON_UNSPECIFIED")
        elif not consequence_horizon_sensitivity_tested:
            challenge_reasons.append("CONSEQUENCE_HORIZON_SENSITIVITY_NOT_TESTED")
        if admitted_followup_horizon_sensitive_variant_count:
            challenge_reasons.append("ADMITTED_FOLLOWUP_HORIZON_SENSITIVE")
        if admitted_followup_horizon_sensitivity_incomplete_variant_count:
            challenge_reasons.append("ADMITTED_FOLLOWUP_HORIZON_SENSITIVITY_PARTIAL")
        elif not admitted_followup_horizon_sensitivity_tested:
            challenge_reasons.append("ADMITTED_FOLLOWUP_HORIZON_SENSITIVITY_NOT_TESTED")
        if not right_censoring_assessed:
            challenge_reasons.append("RIGHT_CENSORING_NOT_ASSESSED")
        if right_censoring_incomplete_variant_count:
            challenge_reasons.append("RIGHT_CENSORING_PARTIAL")
        if right_censored_variant_count:
            challenge_reasons.append("RIGHT_CENSORED_VARIANT_PRESENT")
            challenge_reasons.append("NO_VISIBLE_FOLLOWUP_CENSORING_UNRESOLVED")
        if "right_censoring_status:RIGHT_CENSORED_BY_ADMIN_BOUNDARY" in feature_token:
            challenge_reasons.append("RIGHT_CENSORED_VARIANT_PRESENT")
            challenge_reasons.append("NO_VISIBLE_FOLLOWUP_CENSORING_UNRESOLVED")
        if "right_censoring_status:CENSORING_UNRESOLVED_" in feature_token:
            challenge_reasons.append("RIGHT_CENSORING_PARTIAL")
        if "NO_VISIBLE_FOLLOWUP" in feature_token or "CENSORING_NOT_ASSESSED" in feature_token:
            challenge_reasons.append("NO_VISIBLE_FOLLOWUP_CENSORING_UNRESOLVED")

    return {
        "variant_feature_challenge_id": "vfc_" + _digest(
            source_delta_ref, family_ref, feature_surface, feature_token
        )[:24],
        "source_feature_delta_record_ref": source_delta_ref,
        "source_process_variant_family_ref": family_ref,
        "feature_surface": feature_surface,
        "feature_token": feature_token,
        "success_visible_numerator": success_numerator,
        "success_eligible_denominator": success_denominator,
        "failure_visible_numerator": failure_numerator,
        "failure_eligible_denominator": failure_denominator,
        "descriptive_rate_delta_success_minus_failure": feature.get(
            "descriptive_rate_delta_success_minus_failure"
        ),
        "partition_visibility_state": partition_visibility_state,
        "team_identity_candidate_ids": teams,
        "period_candidates": periods,
        "context_scope_state": context_scope_state,
        "segment_falsifier_state": segment_falsifier_state,
        "failed_trace_falsifier_state": failed_trace_falsifier_state,
        "dependency_group_ref_count": dependency_count,
        "dependency_independence_proven": dependency_independence_proven,
        "statistical_independence_proven": statistical_independence_proven,
        "sample_strength_state": "UNCALIBRATED_NO_ARBITRARY_THRESHOLD_APPLIED",
        "relevant_coverage_incomplete_variant_count": relevant_incomplete,
        "context_robustness_proven": False,
        "consequence_observation_contract_present": consequence_contract_present,
        "consequence_horizon_definition_state": consequence_horizon_state,
        "consequence_horizon_sensitivity_tested": consequence_horizon_sensitivity_tested,
        "admitted_followup_horizon_sensitivity_tested": admitted_followup_horizon_sensitivity_tested,
        "admitted_followup_horizon_sensitive_variant_count": admitted_followup_horizon_sensitive_variant_count,
        "admitted_followup_horizon_sensitivity_incomplete_variant_count": admitted_followup_horizon_sensitivity_incomplete_variant_count,
        "right_censoring_assessed": right_censoring_assessed,
        "right_censored_variant_count": right_censored_variant_count,
        "right_censoring_incomplete_variant_count": right_censoring_incomplete_variant_count,
        "fully_observed_no_followup_variant_count": fully_observed_no_followup_variant_count,
        "period_spread_is_context_robustness_truth": False,
        "feature_absence_is_counterevidence": False,
        "no_visible_followup_is_failure": False,
        "right_censoring_is_failure": False,
        "difference_is_statistically_significant": False,
        "difference_is_failure_cause_truth": False,
        "difference_is_tactical_explanation": False,
        "difference_is_coach_intention_truth": False,
        "counter_scenario_candidates": sorted(set(counter_scenarios)),
        "alternative_explanations_present": True,
        "withdrawal_conditions": sorted(set(withdrawal_conditions)),
        "challenge_reasons": sorted(set(challenge_reasons)),
        "qualification_state": "DESCRIPTIVE_DIFFERENCE_REQUIRES_CHALLENGE",
        "analyst_hypothesis_review_candidate": True,
        "hypothesis_candidate_is_truth": False,
        "professional_finding_emit_allowed": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_variant_feature_challenge_projection(
    feature_delta_payload: dict[str, Any],
    process_variant_payload: dict[str, Any],
) -> dict[str, Any]:
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    for label, payload in (
        ("feature_delta", feature_delta_payload),
        ("process_variant", process_variant_payload),
    ):
        if payload.get("canonical_event_count") != "UNKNOWN":
            hard_blocks.append(f"{label}_canonical_event_count_claimed")
        if payload.get("true_action_count") != "UNKNOWN":
            hard_blocks.append(f"{label}_true_action_count_claimed")
        if payload.get("production_release") is True:
            hard_blocks.append(f"{label}_production_release_claimed")
        if payload.get("status") == "FAIL_CLOSED":
            hard_blocks.append(f"{label}_fail_closed")

    if feature_delta_payload.get("outcome_used_only_as_partition_label") is not True:
        hard_blocks.append("outcome_partition_only_lock_missing")
    if feature_delta_payload.get("outcome_used_to_define_features") is not False:
        hard_blocks.append("outcome_feature_leakage_lock_missing")
    if feature_delta_payload.get("feature_absence_is_counterevidence") is not False:
        hard_blocks.append("absence_counterevidence_lock_breached")
    if feature_delta_payload.get("no_visible_followup_is_failure") is True:
        hard_blocks.append("no_visible_followup_failure_lock_breached")
    if feature_delta_payload.get("right_censoring_is_failure") is True:
        hard_blocks.append("right_censoring_failure_lock_breached")

    families = _index(
        process_variant_payload.get("observable_process_variant_families"),
        "observable_process_variant_family_id",
    )

    rows: list[dict[str, Any]] = []
    source_record_count = 0
    for delta_record in feature_delta_payload.get("grammar_stable_variant_feature_delta_records") or []:
        if not isinstance(delta_record, dict):
            hard_blocks.append("feature_delta_record_not_object")
            continue
        source_record_count += 1
        source_delta_ref = _clean(delta_record.get("grammar_stable_variant_feature_delta_id"))
        family_ref = _clean(delta_record.get("source_process_variant_family_ref"))
        if not source_delta_ref or not family_ref:
            hard_blocks.append("feature_delta_source_ref_missing")
            continue
        family = families.get(family_ref)
        if family is None:
            hard_blocks.append(f"source_process_variant_family_unresolved:{family_ref}")
            continue
        if family.get("same_grammar_visible_outcome_variation_observed") is not True:
            hard_blocks.append(f"source_family_not_grammar_stable_outcome_variant:{family_ref}")
            continue

        for surface, field in (
            ("CONTEXT", "context_feature_difference_candidates"),
            ("CONSEQUENCE", "consequence_feature_difference_candidates"),
        ):
            for feature in delta_record.get(field) or []:
                if not isinstance(feature, dict):
                    hard_blocks.append(f"feature_difference_row_not_object:{source_delta_ref}")
                    continue
                row = _challenge_row(
                    delta_record=delta_record,
                    family=family,
                    feature=feature,
                    feature_surface=surface,
                )
                if row is None:
                    hard_blocks.append(f"feature_difference_contract_invalid:{source_delta_ref}")
                    continue
                rows.append(row)

    if feature_delta_payload.get("status") == "REVIEW_REQUIRED":
        review_hits.append("feature_delta_upstream_review_required")
    if any(row.get("dependency_independence_proven") is not True for row in rows):
        review_hits.append("dependency_independence_unproven")
    if any(row.get("statistical_independence_proven") is not True for row in rows):
        review_hits.append("statistical_independence_unproven")
    if any(row.get("relevant_coverage_incomplete_variant_count", 0) > 0 for row in rows):
        review_hits.append("one_or_more_feature_surfaces_have_partial_coverage")
    if any(
        row.get("consequence_observation_contract_present") is True
        and row.get("consequence_horizon_sensitivity_tested") is not True
        for row in rows
    ):
        review_hits.append("consequence_horizon_sensitivity_not_tested")
    if any(row.get("admitted_followup_horizon_sensitive_variant_count", 0) > 0 for row in rows):
        review_hits.append("admitted_followup_horizon_sensitive_variant_present")
    if any(
        row.get("consequence_observation_contract_present") is True
        and row.get("admitted_followup_horizon_sensitivity_tested") is not True
        for row in rows
    ):
        review_hits.append("admitted_followup_horizon_sensitivity_not_fully_tested")
    if any(
        row.get("consequence_observation_contract_present") is True
        and row.get("right_censoring_assessed") is not True
        for row in rows
    ):
        review_hits.append("right_censoring_not_assessed")
    if any(row.get("right_censoring_incomplete_variant_count", 0) > 0 for row in rows):
        review_hits.append("right_censoring_partial_variant_present")
    if any(row.get("right_censored_variant_count", 0) > 0 for row in rows):
        review_hits.append("right_censored_variant_present")
    if rows:
        review_hits.append("sample_strength_uncalibrated")
        review_hits.append("context_robustness_not_tested")

    if hard_blocks:
        status = "FAIL_CLOSED"
        rows = []
    elif review_hits:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "status": status,
        "variant_feature_challenge_records": rows,
        "variant_feature_challenge_record_count": len(rows),
        "source_feature_delta_record_count": source_record_count,
        "projection_creates_new_evidence": False,
        "projection_reconstructs_sequences": False,
        "projection_recomputes_feature_differences": False,
        "difference_rows_are_independent_evidence_votes": False,
        "period_spread_is_context_robustness_truth": False,
        "feature_absence_is_counterevidence": False,
        "no_visible_followup_is_failure": False,
        "right_censoring_is_failure": False,
        "consequence_horizon_sensitivity_can_be_ignored": False,
        "unassessed_censoring_can_be_treated_as_failure": False,
        "hypothesis_candidate_is_truth": False,
        "professional_finding_emit_allowed": False,
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
