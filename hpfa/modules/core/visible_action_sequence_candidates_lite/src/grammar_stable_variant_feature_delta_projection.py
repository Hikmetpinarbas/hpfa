from __future__ import annotations

import hashlib
import json
import re
from typing import Any

CLAIM_CEILING = "MATCH_LOCAL_DEPENDENCY_QUALIFIED_VARIANT_FEATURE_DIFFERENCE_CANDIDATE_ONLY"

_CONTEXT_KEYS = (
    "provider_context_candidates",
    "provider_direction_candidates",
    "provider_progression_candidates",
    "provider_zone_candidates",
    "coordinate_derived_zone_candidates",
)
_CONTEXT_LIST_KEYS = (
    "actor_identity_candidate_ids",
    "action_family_candidates",
)
_CONTEXT_SCALAR_KEYS = (
    "occurrence_topology",
    "required_participant_scope",
    "binding_state",
)
_STATE_CONSEQUENCE_KEYS = (
    "primary_consequence_candidates",
    "adverse_consequence_candidates",
    "transition_class_candidates",
    "support_candidates",
)
_CONSEQUENCE_KEYS = (
    "consequence_signal_candidates",
    "primary_consequence_candidates",
    "followup_observation_status",
    "process_continuation_status",
    "terminal_status",
    "observation_status",
    "admitted_followup_horizon_sensitivity_state",
    "right_censoring_status",
)
_RESOLVED_OUTCOMES = {"SUCCESS_SEMANTIC_VISIBLE", "FAILURE_SEMANTIC_VISIBLE"}
_LAYER_TOKEN_RE = re.compile(r"^LAYER\[(\d+)\]::")


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


def _tokens(row: dict[str, Any], keys: tuple[str, ...]) -> set[str]:
    result: set[str] = set()
    for key in keys:
        values = row.get(key) or []
        if not isinstance(values, list):
            values = [values]
        for value in values:
            text = _clean(value)
            if text:
                result.add(f"{key}:{text}")
    return result


def _scalar_tokens(row: dict[str, Any], keys: tuple[str, ...]) -> set[str]:
    result: set[str] = set()
    for key in keys:
        text = _clean(row.get(key))
        if text:
            result.add(f"{key}:{text}")
    return result


def _layer_occurrence_index(variant: dict[str, Any]) -> tuple[list[str], dict[str, set[int]]]:
    layer_refs: list[str] = []
    layer_position_by_ref: dict[str, int] = {}
    occurrence_layers: dict[str, set[int]] = {}
    occurrence_order: list[str] = []
    seen_occurrences: set[str] = set()

    for node in variant.get("node_records") or []:
        if not isinstance(node, dict):
            continue
        layer_ref = _clean(node.get("time_layer_ref"))
        if layer_ref and layer_ref not in layer_position_by_ref:
            layer_position_by_ref[layer_ref] = len(layer_refs)
            layer_refs.append(layer_ref)
        position = layer_position_by_ref.get(layer_ref)
        for occurrence_ref in node.get("occurrence_refs") or []:
            occurrence_ref = _clean(occurrence_ref)
            if not occurrence_ref:
                continue
            if occurrence_ref not in seen_occurrences:
                seen_occurrences.add(occurrence_ref)
                occurrence_order.append(occurrence_ref)
            if position is not None:
                occurrence_layers.setdefault(occurrence_ref, set()).add(position)

    if not occurrence_order:
        occurrence_order = [
            _clean(value)
            for value in (variant.get("supporting_action_occurrence_candidate_ids") or [])
            if _clean(value)
        ]
    return occurrence_order, occurrence_layers


def _with_layer_tokens(base_tokens: set[str], layer_positions: set[int]) -> set[str]:
    result = set(base_tokens)
    for position in sorted(layer_positions):
        result.update(f"LAYER[{position}]::{token}" for token in base_tokens)
    return result


def _ensuing_visible_chain_tokens(consequence_row: dict[str, Any]) -> set[str]:
    signals = {
        _clean(value)
        for value in (consequence_row.get("consequence_signal_candidates") or [])
        if _clean(value)
    }
    primary = {
        _clean(value)
        for value in (consequence_row.get("primary_consequence_candidates") or [])
        if _clean(value)
    }
    tokens: set[str] = set()
    if "OPPONENT_SHOT_FOLLOW_UP_VISIBLE" in signals:
        tokens.add("ensuing_visible_chain:OPPONENT_SHOT_FOLLOW_UP_VISIBLE")
    if "SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE" in signals:
        tokens.add("ensuing_visible_chain:SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE")
    if "OPPONENT_HANDOVER_CANDIDATE" in primary and "OPPONENT_SHOT_FOLLOW_UP_VISIBLE" in signals:
        tokens.add("ensuing_visible_chain:OPPONENT_HANDOVER_PLUS_OPPONENT_SHOT_VISIBLE")
    if "SAME_TEAM_CONTINUATION_CANDIDATE" in primary and "SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE" in signals:
        tokens.add("ensuing_visible_chain:SAME_TEAM_CONTINUATION_PLUS_SHOT_VISIBLE")
    if "NO_VISIBLE_FOLLOW_UP_CANDIDATE" in primary or consequence_row.get("visible_consequence_support") is False:
        tokens.add("ensuing_visible_chain:NO_VISIBLE_FOLLOW_UP")
    return tokens


def _member_profile(
    member: dict[str, Any],
    variant_by_id: dict[str, dict[str, Any]],
    state_by_occurrence: dict[str, dict[str, Any]],
    consequence_by_occurrence: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    variant_ref = _clean(member.get("variant_ref"))
    outcome = _clean(member.get("visible_outcome_state"))
    if not variant_ref or outcome not in _RESOLVED_OUTCOMES:
        return None
    variant = variant_by_id.get(variant_ref)
    if variant is None:
        return None

    occurrence_refs, occurrence_layers = _layer_occurrence_index(variant)
    context_features: set[str] = set()
    consequence_features: set[str] = set()
    missing_state: list[str] = []
    missing_consequence: list[str] = []
    horizon_sensitive_occurrence_refs: list[str] = []
    horizon_tested_occurrence_refs: list[str] = []
    horizon_unresolved_occurrence_refs: list[str] = []
    censoring_assessed_occurrence_refs: list[str] = []
    right_censored_occurrence_refs: list[str] = []
    fully_observed_no_followup_occurrence_refs: list[str] = []
    censoring_unresolved_occurrence_refs: list[str] = []

    for occurrence_ref in occurrence_refs:
        layer_positions = occurrence_layers.get(occurrence_ref, set())
        state_row = state_by_occurrence.get(occurrence_ref)
        if state_row is None:
            missing_state.append(occurrence_ref)
        else:
            base_context = _tokens(state_row, _CONTEXT_KEYS)
            base_context |= _tokens(state_row, _CONTEXT_LIST_KEYS)
            base_context |= _scalar_tokens(state_row, _CONTEXT_SCALAR_KEYS)
            context_features |= _with_layer_tokens(base_context, layer_positions)

            base_state_consequence = _tokens(state_row, _STATE_CONSEQUENCE_KEYS)
            consequence_features |= _with_layer_tokens(base_state_consequence, layer_positions)

        consequence_row = consequence_by_occurrence.get(occurrence_ref)
        if consequence_row is None:
            missing_consequence.append(occurrence_ref)
            horizon_unresolved_occurrence_refs.append(occurrence_ref)
            censoring_unresolved_occurrence_refs.append(occurrence_ref)
        else:
            base_consequence = _tokens(consequence_row, _CONSEQUENCE_KEYS)
            if consequence_row.get("visible_consequence_support") is True:
                base_consequence.add("visible_consequence_support:TRUE")
            elif consequence_row.get("visible_consequence_support") is False:
                base_consequence.add("visible_consequence_support:FALSE")
            if consequence_row.get("terminal_outcome_support_visible") is True:
                base_consequence.add("terminal_outcome_support_visible:TRUE")
            elif consequence_row.get("terminal_outcome_support_visible") is False:
                base_consequence.add("terminal_outcome_support_visible:FALSE")
            if consequence_row.get("ensuing_terminal_support_visible") is True:
                base_consequence.add("ensuing_terminal_support_visible:TRUE")
            elif consequence_row.get("ensuing_terminal_support_visible") is False:
                base_consequence.add("ensuing_terminal_support_visible:FALSE")
            if consequence_row.get("ensuing_derived_consequence_support_visible") is True:
                base_consequence.add("ensuing_derived_consequence_support_visible:TRUE")
            elif consequence_row.get("ensuing_derived_consequence_support_visible") is False:
                base_consequence.add("ensuing_derived_consequence_support_visible:FALSE")
            if consequence_row.get("admitted_followup_horizon_sensitivity_tested") is True:
                horizon_tested_occurrence_refs.append(occurrence_ref)
            else:
                horizon_unresolved_occurrence_refs.append(occurrence_ref)
            if consequence_row.get("admitted_followup_horizon_sensitive") is True:
                horizon_sensitive_occurrence_refs.append(occurrence_ref)

            censoring_status = _clean(consequence_row.get("right_censoring_status"))
            if consequence_row.get("right_censoring_assessed") is True:
                censoring_assessed_occurrence_refs.append(occurrence_ref)
            else:
                censoring_unresolved_occurrence_refs.append(occurrence_ref)
            if (
                consequence_row.get("right_censored") is True
                or censoring_status == "RIGHT_CENSORED_BY_ADMIN_BOUNDARY"
            ):
                right_censored_occurrence_refs.append(occurrence_ref)
            if censoring_status == "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP":
                fully_observed_no_followup_occurrence_refs.append(occurrence_ref)
            if (
                censoring_status == "CENSORING_NOT_ASSESSED"
                or censoring_status.startswith("CENSORING_UNRESOLVED_")
            ):
                censoring_unresolved_occurrence_refs.append(occurrence_ref)

            base_consequence |= _ensuing_visible_chain_tokens(consequence_row)
            consequence_features |= _with_layer_tokens(base_consequence, layer_positions)

    horizon_complete = bool(occurrence_refs) and (
        len(set(horizon_tested_occurrence_refs)) == len(set(occurrence_refs))
    )
    censoring_complete = bool(occurrence_refs) and (
        len(set(censoring_assessed_occurrence_refs)) == len(set(occurrence_refs))
        and not censoring_unresolved_occurrence_refs
    )
    return {
        "variant_ref": variant_ref,
        "sequence_ref": member.get("sequence_ref"),
        "visible_outcome_state": outcome,
        "supporting_occurrence_refs": occurrence_refs,
        "partial_order_layer_count": len(variant.get("time_layer_refs") or []),
        "context_feature_tokens": sorted(context_features),
        "consequence_feature_tokens": sorted(consequence_features),
        "context_coverage_complete": bool(occurrence_refs) and not missing_state,
        "consequence_coverage_complete": bool(occurrence_refs) and not missing_consequence,
        "missing_context_occurrence_refs": sorted(missing_state),
        "missing_consequence_occurrence_refs": sorted(missing_consequence),
        "admitted_followup_horizon_sensitivity_complete": horizon_complete,
        "admitted_followup_horizon_sensitive": bool(horizon_sensitive_occurrence_refs),
        "admitted_followup_horizon_sensitive_occurrence_refs": sorted(set(horizon_sensitive_occurrence_refs)),
        "admitted_followup_horizon_tested_occurrence_refs": sorted(set(horizon_tested_occurrence_refs)),
        "admitted_followup_horizon_unresolved_occurrence_refs": sorted(set(horizon_unresolved_occurrence_refs)),
        "right_censoring_complete": censoring_complete,
        "right_censored": bool(right_censored_occurrence_refs),
        "right_censored_occurrence_refs": sorted(set(right_censored_occurrence_refs)),
        "fully_observed_no_followup_occurrence_refs": sorted(set(fully_observed_no_followup_occurrence_refs)),
        "right_censoring_assessed_occurrence_refs": sorted(set(censoring_assessed_occurrence_refs)),
        "right_censoring_unresolved_occurrence_refs": sorted(set(censoring_unresolved_occurrence_refs)),
    }


def _feature_rows(
    profiles: list[dict[str, Any]],
    *,
    feature_field: str,
    coverage_field: str,
) -> list[dict[str, Any]]:
    success = [
        row for row in profiles
        if row.get("visible_outcome_state") == "SUCCESS_SEMANTIC_VISIBLE" and row.get(coverage_field) is True
    ]
    failure = [
        row for row in profiles
        if row.get("visible_outcome_state") == "FAILURE_SEMANTIC_VISIBLE" and row.get(coverage_field) is True
    ]
    features = {
        feature
        for row in success + failure
        for feature in (row.get(feature_field) or [])
        if _clean(feature)
    }
    rows: list[dict[str, Any]] = []
    for feature in sorted(features):
        success_numerator = sum(feature in (row.get(feature_field) or []) for row in success)
        failure_numerator = sum(feature in (row.get(feature_field) or []) for row in failure)
        success_denominator = len(success)
        failure_denominator = len(failure)
        success_rate = success_numerator / success_denominator if success_denominator else None
        failure_rate = failure_numerator / failure_denominator if failure_denominator else None
        if success_rate == failure_rate:
            continue
        layer_match = _LAYER_TOKEN_RE.match(feature)
        rows.append({
            "feature_token": feature,
            "feature_scope": "PARTIAL_ORDER_LAYER" if layer_match else "VARIANT_AGGREGATE",
            "partial_order_layer_index": int(layer_match.group(1)) if layer_match else None,
            "success_visible_numerator": success_numerator,
            "success_eligible_denominator": success_denominator,
            "failure_visible_numerator": failure_numerator,
            "failure_eligible_denominator": failure_denominator,
            "success_visible_rate": round(success_rate, 6) if success_rate is not None else None,
            "failure_visible_rate": round(failure_rate, 6) if failure_rate is not None else None,
            "descriptive_rate_delta_success_minus_failure": (
                round(success_rate - failure_rate, 6)
                if success_rate is not None and failure_rate is not None
                else None
            ),
            "feature_absence_is_counterevidence": False,
            "difference_is_statistically_significant": False,
            "difference_is_failure_cause_truth": False,
            "difference_is_tactical_explanation": False,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "claim_ceiling": CLAIM_CEILING,
        })
    return rows


def _first_supported_layer_candidate(rows: list[dict[str, Any]]) -> int | None:
    layers = [
        row.get("partial_order_layer_index")
        for row in rows
        if row.get("feature_scope") == "PARTIAL_ORDER_LAYER"
        and isinstance(row.get("partial_order_layer_index"), int)
    ]
    return min(layers) if layers else None


def build_grammar_stable_variant_feature_delta(
    sequence_payload: dict[str, Any],
    process_variant_payload: dict[str, Any],
    occurrence_state_transition_payload: dict[str, Any],
    occurrence_consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    for label, payload in (
        ("sequence", sequence_payload),
        ("process_variant", process_variant_payload),
        ("occurrence_state_transition", occurrence_state_transition_payload),
        ("occurrence_consequence", occurrence_consequence_payload),
    ):
        if payload.get("canonical_event_count") != "UNKNOWN":
            blocks.append(f"{label}_canonical_event_count_claimed")
        if payload.get("true_action_count") != "UNKNOWN":
            blocks.append(f"{label}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{label}_production_release_claimed")

    if process_variant_payload.get("status") == "FAIL_CLOSED":
        blocks.append("process_variant_binding_fail_closed")
    if occurrence_state_transition_payload.get("status") == "FAIL_CLOSED":
        blocks.append("occurrence_state_transition_fail_closed")
    if occurrence_consequence_payload.get("status") == "FAIL_CLOSED":
        blocks.append("occurrence_consequence_fail_closed")
    if occurrence_consequence_payload.get("no_visible_followup_is_failure") is True:
        blocks.append("no_visible_followup_failure_lock_breached")
    if occurrence_consequence_payload.get("followup_is_terminal_outcome_truth") is True:
        blocks.append("followup_terminal_truth_lock_breached")
    if occurrence_consequence_payload.get("projection_is_causal_truth") is True:
        blocks.append("consequence_causal_truth_lock_breached")
    if occurrence_consequence_payload.get("ensuing_terminal_support_is_causal_truth") is True:
        blocks.append("ensuing_terminal_support_causal_truth_lock_breached")
    if occurrence_consequence_payload.get("admitted_followup_horizon_sensitivity_is_terminal_outcome_truth") is True:
        blocks.append("horizon_sensitivity_terminal_truth_lock_breached")

    horizon = occurrence_consequence_payload.get("source_consequence_horizon")
    horizon = horizon if isinstance(horizon, dict) else {}
    horizon_state = _clean(horizon.get("horizon_definition_state")) or "HORIZON_UNSPECIFIED"
    source_right_censoring_assessed = occurrence_consequence_payload.get("right_censoring_assessed") is True
    observation_state_surface_present = any(
        any(
            key in row
            for key in (
                "followup_observation_status",
                "process_continuation_status",
                "terminal_status",
                "observation_status",
                "right_censoring_status",
            )
        )
        for row in (occurrence_consequence_payload.get("occurrence_consequence_projections") or [])
        if isinstance(row, dict)
    )
    horizon_sensitivity_surface_present = any(
        "admitted_followup_horizon_sensitivity_state" in row
        for row in (occurrence_consequence_payload.get("occurrence_consequence_projections") or [])
        if isinstance(row, dict)
    )
    if observation_state_surface_present and horizon_state == "HORIZON_UNSPECIFIED":
        reviews.append("consequence_horizon_unspecified")

    variant_by_id = _index(sequence_payload.get("partial_order_occurrence_variants"), "partial_order_occurrence_variant_id")
    state_by_occurrence = _index(
        occurrence_state_transition_payload.get("occurrence_state_transition_projections"),
        "action_occurrence_candidate_id",
    )
    consequence_by_occurrence = _index(
        occurrence_consequence_payload.get("occurrence_consequence_projections"),
        "action_occurrence_candidate_id",
    )

    family_records: list[dict[str, Any]] = []
    for family in process_variant_payload.get("observable_process_variant_families") or []:
        if not isinstance(family, dict) or family.get("same_grammar_visible_outcome_variation_observed") is not True:
            continue
        family_ref = _clean(family.get("observable_process_variant_family_id"))
        profiles: list[dict[str, Any]] = []
        for member in family.get("member_records") or []:
            if not isinstance(member, dict):
                continue
            profile = _member_profile(member, variant_by_id, state_by_occurrence, consequence_by_occurrence)
            if profile is None:
                continue
            profiles.append(profile)

        success_count = sum(row.get("visible_outcome_state") == "SUCCESS_SEMANTIC_VISIBLE" for row in profiles)
        failure_count = sum(row.get("visible_outcome_state") == "FAILURE_SEMANTIC_VISIBLE" for row in profiles)
        if not success_count or not failure_count:
            reviews.append(f"resolved_outcome_partition_incomplete:{family_ref or 'UNKNOWN'}")
            continue

        context_rows = _feature_rows(
            profiles,
            feature_field="context_feature_tokens",
            coverage_field="context_coverage_complete",
        )
        consequence_rows = _feature_rows(
            profiles,
            feature_field="consequence_feature_tokens",
            coverage_field="consequence_coverage_complete",
        )
        missing_context_count = sum(row.get("context_coverage_complete") is not True for row in profiles)
        missing_consequence_count = sum(row.get("consequence_coverage_complete") is not True for row in profiles)
        if horizon_sensitivity_surface_present:
            horizon_sensitive_variant_count = sum(
                row.get("admitted_followup_horizon_sensitive") is True for row in profiles
            )
            horizon_incomplete_variant_count = sum(
                row.get("admitted_followup_horizon_sensitivity_complete") is not True
                for row in profiles
            )
            horizon_tested = bool(profiles) and horizon_incomplete_variant_count == 0
        else:
            horizon_sensitive_variant_count = 0
            horizon_incomplete_variant_count = 0
            horizon_tested = False

        right_censored_variant_count = sum(row.get("right_censored") is True for row in profiles)
        right_censoring_incomplete_variant_count = sum(
            row.get("right_censoring_complete") is not True for row in profiles
        )
        fully_observed_no_followup_variant_count = sum(
            bool(row.get("fully_observed_no_followup_occurrence_refs")) for row in profiles
        )
        family_right_censoring_assessed = bool(profiles) and right_censoring_incomplete_variant_count == 0

        if missing_context_count:
            reviews.append(f"variant_context_coverage_partial:{family_ref or 'UNKNOWN'}")
        if missing_consequence_count:
            reviews.append(f"variant_consequence_coverage_partial:{family_ref or 'UNKNOWN'}")
        if horizon_sensitivity_surface_present and horizon_sensitive_variant_count:
            reviews.append(f"variant_admitted_followup_horizon_sensitive:{family_ref or 'UNKNOWN'}")
        if horizon_sensitivity_surface_present and horizon_incomplete_variant_count:
            reviews.append(f"variant_admitted_followup_horizon_sensitivity_partial:{family_ref or 'UNKNOWN'}")
        if right_censored_variant_count:
            reviews.append(f"variant_right_censored_occurrence_present:{family_ref or 'UNKNOWN'}")
        if right_censoring_incomplete_variant_count:
            reviews.append(f"variant_right_censoring_partial:{family_ref or 'UNKNOWN'}")

        first_context_layer = _first_supported_layer_candidate(context_rows)
        first_consequence_layer = _first_supported_layer_candidate(consequence_rows)

        family_records.append({
            "grammar_stable_variant_feature_delta_id": "gsvfd_" + _digest(family_ref, context_rows, consequence_rows)[:24],
            "source_process_variant_family_ref": family_ref or None,
            "grammar_signature_tokens": list(family.get("grammar_signature_tokens") or []),
            "team_identity_candidate_ids": list(family.get("team_identity_candidate_ids") or []),
            "period_candidates": list(family.get("period_candidates") or []),
            "success_resolved_variant_count": success_count,
            "failure_resolved_variant_count": failure_count,
            "resolved_variant_count": len(profiles),
            "context_coverage_incomplete_variant_count": missing_context_count,
            "consequence_coverage_incomplete_variant_count": missing_consequence_count,
            "context_feature_difference_candidates": context_rows,
            "context_feature_difference_candidate_count": len(context_rows),
            "consequence_feature_difference_candidates": consequence_rows,
            "consequence_feature_difference_candidate_count": len(consequence_rows),
            "first_supported_context_difference_layer_candidate": first_context_layer,
            "first_supported_consequence_difference_layer_candidate": first_consequence_layer,
            "consequence_observation_state_features_consumed": observation_state_surface_present,
            "consequence_horizon_definition_state": horizon_state,
            "consequence_horizon_sensitivity_tested": False,
            "admitted_followup_horizon_sensitivity_surface_consumed": horizon_sensitivity_surface_present,
            "admitted_followup_horizon_sensitivity_tested": horizon_tested,
            "admitted_followup_horizon_sensitive_variant_count": horizon_sensitive_variant_count,
            "admitted_followup_horizon_sensitivity_incomplete_variant_count": horizon_incomplete_variant_count,
            "right_censoring_assessed": family_right_censoring_assessed,
            "right_censored_variant_count": right_censored_variant_count,
            "right_censoring_incomplete_variant_count": right_censoring_incomplete_variant_count,
            "fully_observed_no_followup_variant_count": fully_observed_no_followup_variant_count,
            "member_profiles": profiles,
            "outcome_used_only_as_partition_label": True,
            "outcome_used_to_define_features": False,
            "same_timestamp_internal_ordering_used_for_first_difference": False,
            "partial_order_layer_position_is_total_order_truth": False,
            "layer_position_does_not_order_same_time_peers": True,
            "feature_absence_is_counterevidence": False,
            "no_visible_followup_is_failure": False,
            "right_censoring_is_failure": False,
            "followup_is_terminal_outcome_truth": False,
            "difference_is_failure_cause_truth": False,
            "difference_is_tactical_explanation": False,
            "difference_is_coach_intention_truth": False,
            "ensuing_visible_chain_is_causal_truth": False,
            "ensuing_terminal_support_is_causal_truth": False,
            "admitted_followup_horizon_sensitivity_is_terminal_outcome_truth": False,
            "actor_identity_difference_is_player_quality_truth": False,
            "independent_recurrence_support_count": 0,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
        family_records = []
    elif reviews or process_variant_payload.get("status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    all_family_horizon_tested = bool(family_records) and all(
        row.get("admitted_followup_horizon_sensitivity_tested") is True
        for row in family_records
    )
    horizon_sensitive_family_count = sum(
        int(row.get("admitted_followup_horizon_sensitive_variant_count") or 0) > 0
        for row in family_records
    )
    all_family_censoring_assessed = bool(family_records) and all(
        row.get("right_censoring_assessed") is True for row in family_records
    )
    right_censored_family_count = sum(
        int(row.get("right_censored_variant_count") or 0) > 0 for row in family_records
    )

    return {
        "status": status,
        "grammar_stable_variant_feature_delta_records": family_records,
        "grammar_stable_variant_feature_delta_record_count": len(family_records),
        "source_grammar_stable_visible_outcome_variation_family_count": int(
            process_variant_payload.get("grammar_stable_visible_outcome_variation_family_count") or 0
        ),
        "consequence_observation_state_features_consumed": observation_state_surface_present,
        "consequence_horizon_definition_state": horizon_state,
        "consequence_horizon_sensitivity_tested": False,
        "admitted_followup_horizon_sensitivity_surface_consumed": horizon_sensitivity_surface_present,
        "admitted_followup_horizon_sensitivity_tested": all_family_horizon_tested,
        "admitted_followup_horizon_sensitive_family_count": horizon_sensitive_family_count,
        "right_censoring_source_assessed": source_right_censoring_assessed,
        "right_censoring_assessed": all_family_censoring_assessed,
        "right_censored_family_count": right_censored_family_count,
        "outcome_used_only_as_partition_label": True,
        "outcome_used_to_define_features": False,
        "same_timestamp_internal_ordering_used_for_first_difference": False,
        "partial_order_layer_position_is_total_order_truth": False,
        "layer_position_does_not_order_same_time_peers": True,
        "feature_absence_is_counterevidence": False,
        "no_visible_followup_is_failure": False,
        "right_censoring_is_failure": False,
        "followup_is_terminal_outcome_truth": False,
        "difference_is_failure_cause_truth": False,
        "difference_is_tactical_explanation": False,
        "difference_is_coach_intention_truth": False,
        "ensuing_visible_chain_is_causal_truth": False,
        "ensuing_terminal_support_is_causal_truth": False,
        "admitted_followup_horizon_sensitivity_is_terminal_outcome_truth": False,
        "actor_identity_difference_is_player_quality_truth": False,
        "difference_rows_are_independent_evidence_votes": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


_BASE_BUILD_GRAMMAR_STABLE_VARIANT_FEATURE_DELTA = build_grammar_stable_variant_feature_delta
_PROVIDER_SEMANTIC_CONTEXT_FIELDS = {
    "provider_context_candidates",
    "provider_direction_candidates",
    "provider_progression_candidates",
    "provider_zone_candidates",
}
_COORDINATE_DERIVED_CONTEXT_FIELDS = {"coordinate_derived_zone_candidates"}
_OCCURRENCE_STRUCTURE_CONTEXT_FIELDS = {
    "occurrence_topology",
    "required_participant_scope",
    "binding_state",
}


def _base_context_feature_field(feature_token: Any) -> str:
    token = _clean(feature_token)
    if _LAYER_TOKEN_RE.match(token) and "::" in token:
        token = token.split("::", 1)[1]
    return token.split(":", 1)[0] if ":" in token else token


def _base_context_feature_provenance_record(feature: dict[str, Any]) -> dict[str, Any] | None:
    feature_token = _clean(feature.get("feature_token"))
    if not feature_token:
        return None
    source_field = _base_context_feature_field(feature_token)

    if source_field in _PROVIDER_SEMANTIC_CONTEXT_FIELDS:
        information_role = "PROVIDER_SEMANTIC_CONTEXT_CANDIDATE_ONLY"
        dependency_surface = "spatial_transition_candidate_lite_v1"
    elif source_field in _COORDINATE_DERIVED_CONTEXT_FIELDS:
        information_role = "COORDINATE_DERIVED_ZONE_CONTEXT_CANDIDATE_ONLY"
        dependency_surface = "spatial_transition_candidate_lite_v1"
    elif source_field == "actor_identity_candidate_ids":
        information_role = "ACTOR_IDENTITY_CONTEXT_CANDIDATE_ONLY"
        dependency_surface = "occurrence_consequence_projection_v1"
    elif source_field == "action_family_candidates":
        information_role = "ACTION_FAMILY_CONTEXT_CANDIDATE_ONLY"
        dependency_surface = "occurrence_consequence_projection_v1"
    elif source_field in _OCCURRENCE_STRUCTURE_CONTEXT_FIELDS:
        information_role = "OCCURRENCE_STRUCTURE_CONTEXT_CANDIDATE_ONLY"
        dependency_surface = "occurrence_consequence_projection_v1"
    else:
        information_role = "SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED"
        dependency_surface = "UNRESOLVED_DEPENDENCY_SURFACE"

    return {
        "feature_token": feature_token,
        "feature_source_surface": "occurrence_state_transition_projection_v1",
        "feature_dependency_surface": dependency_surface,
        "feature_source_field": source_field or None,
        "feature_information_role": information_role,
        "eligible_denominator_basis": "VARIANTS_WITH_COMPLETE_OCCURRENCE_STATE_CONTEXT_COVERAGE",
        "feature_is_physical_geometry_truth": False,
        "feature_is_tracking_truth": False,
        "feature_is_tactical_truth": False,
        "feature_is_causal_truth": False,
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _bind_base_context_feature_provenance(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("status") == "FAIL_CLOSED":
        payload["base_context_feature_provenance_contract_applied"] = False
        payload["base_context_feature_provenance_record_count"] = 0
        payload["base_context_feature_provenance_unresolved_count"] = 0
        payload["base_context_feature_provenance_is_independent_evidence_vote"] = False
        payload["base_context_feature_provenance_changes_feature_difference"] = False
        return payload

    total = 0
    unresolved = 0
    provenance_review_hits: list[str] = []
    for family in payload.get("grammar_stable_variant_feature_delta_records") or []:
        if not isinstance(family, dict):
            continue
        rows: list[dict[str, Any]] = []
        for feature in family.get("context_feature_difference_candidates") or []:
            if not isinstance(feature, dict):
                continue
            if _clean(feature.get("feature_surface_detail")):
                continue
            record = _base_context_feature_provenance_record(feature)
            if record is None:
                continue
            rows.append(record)
            if record.get("feature_information_role") == "SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED":
                unresolved += 1
        family["base_context_feature_provenance_records"] = rows
        family["base_context_feature_provenance_record_count"] = len(rows)
        family["base_context_feature_provenance_complete"] = not any(
            row.get("feature_information_role") == "SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED"
            for row in rows
        )
        family["base_context_feature_provenance_is_independent_evidence_vote"] = False
        family["base_context_feature_provenance_changes_feature_difference"] = False
        total += len(rows)
        if family["base_context_feature_provenance_complete"] is not True:
            family_ref = _clean(family.get("source_process_variant_family_ref")) or "UNKNOWN"
            provenance_review_hits.append(f"base_context_feature_provenance_unresolved:{family_ref}")

    payload["base_context_feature_provenance_contract_applied"] = True
    payload["base_context_feature_provenance_record_count"] = total
    payload["base_context_feature_provenance_unresolved_count"] = unresolved
    payload["base_context_feature_provenance_is_independent_evidence_vote"] = False
    payload["base_context_feature_provenance_changes_feature_difference"] = False
    if provenance_review_hits:
        payload["review_hits"] = sorted(
            set(payload.get("review_hits") or []) | set(provenance_review_hits)
        )
        if payload.get("status") == "PASS":
            payload["status"] = "REVIEW_REQUIRED"
    return payload


def build_grammar_stable_variant_feature_delta(
    sequence_payload: dict[str, Any],
    process_variant_payload: dict[str, Any],
    occurrence_state_transition_payload: dict[str, Any],
    occurrence_consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    payload = _BASE_BUILD_GRAMMAR_STABLE_VARIANT_FEATURE_DELTA(
        sequence_payload,
        process_variant_payload,
        occurrence_state_transition_payload,
        occurrence_consequence_payload,
    )
    return _bind_base_context_feature_provenance(payload)


_BASE_BUILD_GRAMMAR_STABLE_VARIANT_FEATURE_DELTA_WITH_PROVENANCE = build_grammar_stable_variant_feature_delta


def _visible_consequence_class_signature(
    variant: dict[str, Any],
    consequence_by_occurrence: dict[str, dict[str, Any]],
) -> tuple[list[str], bool]:
    occurrence_refs, _ = _layer_occurrence_index(variant)
    if not occurrence_refs:
        return [], False
    classes: set[str] = set()
    for occurrence_ref in occurrence_refs:
        consequence = consequence_by_occurrence.get(occurrence_ref)
        if consequence is None:
            return [], False
        primary = [
            _clean(value)
            for value in (consequence.get("primary_consequence_candidates") or [])
            if _clean(value)
        ]
        if primary:
            classes.update(primary)
            continue
        followup_state = _clean(consequence.get("followup_observation_status"))
        if followup_state == "NO_VISIBLE_FOLLOWUP":
            classes.add("NO_VISIBLE_FOLLOW_UP_CANDIDATE")
        elif consequence.get("visible_consequence_support") is not True:
            return [], False
    return sorted(classes), True


def _bind_grammar_stable_consequence_contrast(
    payload: dict[str, Any],
    sequence_payload: dict[str, Any],
    process_variant_payload: dict[str, Any],
    occurrence_consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    if payload.get("status") == "FAIL_CLOSED":
        payload["grammar_stable_consequence_contrast_records"] = []
        payload["grammar_stable_consequence_contrast_record_count"] = 0
        payload["provider_outcome_partition_required_for_consequence_contrast"] = False
        return payload

    variant_by_id = _index(
        sequence_payload.get("partial_order_occurrence_variants"),
        "partial_order_occurrence_variant_id",
    )
    consequence_by_occurrence = _index(
        occurrence_consequence_payload.get("occurrence_consequence_projections"),
        "action_occurrence_candidate_id",
    )
    records: list[dict[str, Any]] = []

    for family in process_variant_payload.get("observable_process_variant_families") or []:
        if not isinstance(family, dict):
            continue
        family_ref = _clean(family.get("observable_process_variant_family_id"))
        member_signatures: list[dict[str, Any]] = []
        for member in family.get("member_records") or []:
            if not isinstance(member, dict):
                continue
            variant_ref = _clean(member.get("variant_ref"))
            variant = variant_by_id.get(variant_ref)
            if not variant:
                continue
            classes, complete = _visible_consequence_class_signature(
                variant,
                consequence_by_occurrence,
            )
            if not complete or not classes:
                continue
            member_signatures.append({
                "variant_ref": variant_ref,
                "sequence_ref": member.get("sequence_ref"),
                "provider_visible_outcome_state": _clean(member.get("visible_outcome_state")) or None,
                "visible_consequence_classes": classes,
            })

        if len(member_signatures) < 2:
            continue
        signatures = {
            tuple(row.get("visible_consequence_classes") or [])
            for row in member_signatures
        }
        if len(signatures) < 2:
            continue
        visible_classes = sorted({
            value
            for row in member_signatures
            for value in (row.get("visible_consequence_classes") or [])
            if _clean(value)
        })
        records.append({
            "grammar_stable_consequence_contrast_id": "gscc_" + _digest(
                family_ref,
                sorted(signatures),
            )[:24],
            "source_process_variant_family_ref": family_ref or None,
            "grammar_signature_tokens": list(family.get("grammar_signature_tokens") or []),
            "team_identity_candidate_ids": list(family.get("team_identity_candidate_ids") or []),
            "period_candidates": list(family.get("period_candidates") or []),
            "member_consequence_profiles": member_signatures,
            "member_count": len(member_signatures),
            "visible_consequence_classes": visible_classes,
            "consequence_variant_state": "GRAMMAR_STABLE_VISIBLE_CONSEQUENCE_VARIATION",
            "provider_outcome_partition_required": False,
            "provider_outcome_used_to_define_consequence_variation": False,
            "no_visible_followup_is_failure": False,
            "consequence_variation_is_success_failure_truth": False,
            "consequence_variation_is_counterevidence_truth": False,
            "consequence_variation_is_causal_truth": False,
            "consequence_variation_is_tactical_truth": False,
            "consequence_variation_is_coach_intention_truth": False,
            "independent_recurrence_support_count": 0,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": "MATCH_LOCAL_GRAMMAR_STABLE_VISIBLE_CONSEQUENCE_VARIATION_CANDIDATE_ONLY",
        })

    payload["grammar_stable_consequence_contrast_records"] = records
    payload["grammar_stable_consequence_contrast_record_count"] = len(records)
    payload["provider_outcome_partition_required_for_consequence_contrast"] = False
    payload["consequence_contrast_is_independent_evidence_vote"] = False
    payload["consequence_contrast_is_causal_truth"] = False
    payload["consequence_contrast_is_tactical_truth"] = False
    return payload


def build_grammar_stable_variant_feature_delta(
    sequence_payload: dict[str, Any],
    process_variant_payload: dict[str, Any],
    occurrence_state_transition_payload: dict[str, Any],
    occurrence_consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    payload = _BASE_BUILD_GRAMMAR_STABLE_VARIANT_FEATURE_DELTA_WITH_PROVENANCE(
        sequence_payload,
        process_variant_payload,
        occurrence_state_transition_payload,
        occurrence_consequence_payload,
    )
    return _bind_grammar_stable_consequence_contrast(
        payload,
        sequence_payload,
        process_variant_payload,
        occurrence_consequence_payload,
    )
