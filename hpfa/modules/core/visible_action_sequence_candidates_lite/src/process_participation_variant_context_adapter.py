from __future__ import annotations

import copy
import re
from typing import Any

CLAIM_CEILING = "MATCH_LOCAL_PROVIDER_PROCESS_CONTEXT_DIFFERENCE_CANDIDATE_ONLY"
_LAYER_TOKEN_RE = re.compile(r"^LAYER\[(\d+)\]::")
_PROCESS_ROLES = {"PARTICIPATION_INTERVAL", "CONTEXT_INTERVAL"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _index(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    return {
        _clean(row.get(key)): row
        for row in (rows or [])
        if isinstance(row, dict) and _clean(row.get(key))
    }


def _variant_occurrence_layers(variant: dict[str, Any]) -> dict[str, set[int]]:
    layer_positions: dict[str, int] = {}
    occurrence_layers: dict[str, set[int]] = {}
    for node in variant.get("node_records") or []:
        if not isinstance(node, dict):
            continue
        layer_ref = _clean(node.get("time_layer_ref"))
        if layer_ref and layer_ref not in layer_positions:
            layer_positions[layer_ref] = len(layer_positions)
        position = layer_positions.get(layer_ref)
        if position is None:
            continue
        for occurrence_ref in node.get("occurrence_refs") or []:
            occurrence_ref = _clean(occurrence_ref)
            if occurrence_ref:
                occurrence_layers.setdefault(occurrence_ref, set()).add(position)
    return occurrence_layers


def _ranges_overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> bool:
    return start_a <= end_b and start_b <= end_a


def _process_tokens_for_occurrence(
    occurrence: dict[str, Any],
    process_rows: list[dict[str, Any]],
) -> set[str]:
    periods = {_clean(value) for value in occurrence.get("period_candidates") or [] if _clean(value)}
    starts = [_number(value) for value in occurrence.get("start_candidates") or []]
    ends = [_number(value) for value in occurrence.get("end_candidates") or []]
    starts = [value for value in starts if value is not None]
    ends = [value for value in ends if value is not None]
    if not periods or not starts:
        return set()
    occurrence_start = min(starts)
    occurrence_end = max(ends) if ends else occurrence_start
    actors = {_clean(value) for value in occurrence.get("actor_identity_candidate_ids") or [] if _clean(value)}
    teams = {_clean(value) for value in occurrence.get("team_identity_candidate_ids") or [] if _clean(value)}

    tokens: set[str] = set()
    for process in process_rows:
        if not isinstance(process, dict):
            continue
        role = _clean(process.get("semantic_role"))
        if role not in _PROCESS_ROLES:
            continue
        process_period = _clean(process.get("period_candidate"))
        process_start = _number(process.get("start_candidate"))
        process_end = _number(process.get("end_candidate"))
        if process_period not in periods or process_start is None or process_end is None:
            continue
        if not _ranges_overlap(occurrence_start, occurrence_end, process_start, process_end):
            continue
        if role == "PARTICIPATION_INTERVAL":
            actor = _clean(process.get("actor_identity_candidate_id"))
            if not actor or actor not in actors:
                continue
        else:
            team = _clean(process.get("team_identity_candidate_id"))
            if not team or team not in teams:
                continue

        family = _clean(process.get("process_family_candidate"))
        if family:
            tokens.add(f"process_family_candidate:{family}")
        tokens.add(f"process_semantic_role:{role}")
        if process.get("shot_present_annotation_candidate") is True:
            tokens.add("process_shot_present_annotation_candidate:TRUE")
        if _clean(process.get("episode_candidate_id")):
            tokens.add("process_episode_navigation_binding_visible:TRUE")
    return tokens


def _feature_rows(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    success = [
        row for row in profiles
        if row.get("visible_outcome_state") == "SUCCESS_SEMANTIC_VISIBLE"
        and row.get("process_context_coverage_visible") is True
    ]
    failure = [
        row for row in profiles
        if row.get("visible_outcome_state") == "FAILURE_SEMANTIC_VISIBLE"
        and row.get("process_context_coverage_visible") is True
    ]
    if not success or not failure:
        return []
    features = {
        feature
        for row in success + failure
        for feature in (row.get("process_context_feature_tokens") or [])
        if _clean(feature)
    }
    rows: list[dict[str, Any]] = []
    for feature in sorted(features):
        success_numerator = sum(feature in (row.get("process_context_feature_tokens") or []) for row in success)
        failure_numerator = sum(feature in (row.get("process_context_feature_tokens") or []) for row in failure)
        success_denominator = len(success)
        failure_denominator = len(failure)
        success_rate = success_numerator / success_denominator
        failure_rate = failure_numerator / failure_denominator
        if success_rate == failure_rate:
            continue
        layer_match = _LAYER_TOKEN_RE.match(feature)
        rows.append({
            "feature_token": feature,
            "feature_surface_detail": "PROVIDER_REVIEWED_PROCESS_PARTICIPATION_CONTEXT",
            "feature_scope": "PARTIAL_ORDER_LAYER" if layer_match else "VARIANT_AGGREGATE",
            "partial_order_layer_index": int(layer_match.group(1)) if layer_match else None,
            "eligible_denominator_basis": "VARIANTS_WITH_MATCHED_PROVIDER_REVIEWED_PROCESS_ANNOTATION",
            "success_visible_numerator": success_numerator,
            "success_eligible_denominator": success_denominator,
            "failure_visible_numerator": failure_numerator,
            "failure_eligible_denominator": failure_denominator,
            "success_visible_rate": round(success_rate, 6),
            "failure_visible_rate": round(failure_rate, 6),
            "descriptive_rate_delta_success_minus_failure": round(success_rate - failure_rate, 6),
            "feature_absence_is_counterevidence": False,
            "difference_is_statistically_significant": False,
            "difference_is_failure_cause_truth": False,
            "difference_is_tactical_explanation": False,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "claim_ceiling": CLAIM_CEILING,
        })
    return rows


def _first_layer(rows: list[dict[str, Any]]) -> int | None:
    layers = [
        row.get("partial_order_layer_index")
        for row in rows
        if row.get("feature_scope") == "PARTIAL_ORDER_LAYER"
        and isinstance(row.get("partial_order_layer_index"), int)
    ]
    return min(layers) if layers else None


def apply_process_participation_context(
    sequence_payload: dict[str, Any],
    feature_delta_payload: dict[str, Any],
    process_participation_payload: dict[str, Any] | None,
    occurrence_consequence_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    result = copy.deepcopy(feature_delta_payload)
    result["process_participation_context_enrichment_consumed"] = False
    result["process_participation_context_binding_state"] = "NOT_AVAILABLE"
    result["process_context_rows_are_independent_evidence_votes"] = False
    result["process_annotation_is_tactical_plan_truth"] = False
    result["episode_navigation_binding_is_possession_truth"] = False
    result["temporal_overlap_is_causal_truth"] = False

    if not process_participation_payload or not occurrence_consequence_payload:
        return result
    for label, payload in (
        ("sequence", sequence_payload),
        ("feature_delta", feature_delta_payload),
        ("process_participation", process_participation_payload),
        ("occurrence_consequence", occurrence_consequence_payload),
    ):
        if payload.get("canonical_event_count") != "UNKNOWN":
            result.setdefault("review_hits", []).append(
                f"{label}_canonical_event_count_claimed_process_context_not_consumed"
            )
            result["process_participation_context_binding_state"] = "REVIEW_REQUIRED_NOT_CONSUMED"
            return result
        if payload.get("production_release") is True:
            result.setdefault("review_hits", []).append(
                f"{label}_production_release_claimed_process_context_not_consumed"
            )
            result["process_participation_context_binding_state"] = "REVIEW_REQUIRED_NOT_CONSUMED"
            return result
    if (
        process_participation_payload.get("status") == "FAIL_CLOSED"
        or occurrence_consequence_payload.get("status") == "FAIL_CLOSED"
    ):
        result.setdefault("review_hits", []).append("process_context_upstream_fail_closed_not_consumed")
        result["process_participation_context_binding_state"] = "REVIEW_REQUIRED_NOT_CONSUMED"
        return result

    process_rows = [
        row
        for row in (process_participation_payload.get("process_participation_candidates") or [])
        if isinstance(row, dict)
    ]
    occurrence_by_id = _index(
        occurrence_consequence_payload.get("occurrence_consequence_projections"),
        "action_occurrence_candidate_id",
    )
    variant_by_id = _index(
        sequence_payload.get("partial_order_occurrence_variants"),
        "partial_order_occurrence_variant_id",
    )

    enriched_family_count = 0
    appended_row_count = 0
    for family in result.get("grammar_stable_variant_feature_delta_records") or []:
        if not isinstance(family, dict):
            continue
        profiles = [row for row in (family.get("member_profiles") or []) if isinstance(row, dict)]
        for profile in profiles:
            variant_ref = _clean(profile.get("variant_ref"))
            occurrence_layers = _variant_occurrence_layers(variant_by_id.get(variant_ref) or {})
            tokens: set[str] = set()
            matched_occurrence_count = 0
            for occurrence_ref in profile.get("supporting_occurrence_refs") or []:
                occurrence_ref = _clean(occurrence_ref)
                occurrence = occurrence_by_id.get(occurrence_ref)
                if occurrence is None:
                    continue
                base_tokens = _process_tokens_for_occurrence(occurrence, process_rows)
                if not base_tokens:
                    continue
                matched_occurrence_count += 1
                tokens.update(base_tokens)
                for layer in sorted(occurrence_layers.get(occurrence_ref, set())):
                    tokens.update(f"LAYER[{layer}]::{token}" for token in base_tokens)
            profile["process_context_feature_tokens"] = sorted(tokens)
            profile["process_context_coverage_visible"] = bool(tokens)
            profile["process_context_matched_occurrence_count"] = matched_occurrence_count
            profile["process_context_absence_is_counterevidence"] = False

        process_rows_delta = _feature_rows(profiles)
        success_eligible = sum(
            row.get("visible_outcome_state") == "SUCCESS_SEMANTIC_VISIBLE"
            and row.get("process_context_coverage_visible") is True
            for row in profiles
        )
        failure_eligible = sum(
            row.get("visible_outcome_state") == "FAILURE_SEMANTIC_VISIBLE"
            and row.get("process_context_coverage_visible") is True
            for row in profiles
        )
        family["process_context_feature_difference_candidates"] = process_rows_delta
        family["process_context_feature_difference_candidate_count"] = len(process_rows_delta)
        family["process_context_success_eligible_variant_count"] = success_eligible
        family["process_context_failure_eligible_variant_count"] = failure_eligible
        family["process_context_coverage_incomplete_variant_count"] = sum(
            row.get("process_context_coverage_visible") is not True for row in profiles
        )
        family["first_supported_process_context_difference_layer_candidate"] = _first_layer(process_rows_delta)
        family["process_context_absence_is_counterevidence"] = False
        family["process_annotation_is_tactical_plan_truth"] = False
        family["episode_navigation_binding_is_possession_truth"] = False
        family["temporal_overlap_is_causal_truth"] = False

        if process_rows_delta:
            enriched_family_count += 1
            existing = [
                row
                for row in (family.get("context_feature_difference_candidates") or [])
                if isinstance(row, dict)
            ]
            existing_tokens = {_clean(row.get("feature_token")) for row in existing}
            additions = [
                row
                for row in process_rows_delta
                if _clean(row.get("feature_token")) not in existing_tokens
            ]
            existing.extend(additions)
            family["context_feature_difference_candidates"] = existing
            family["context_feature_difference_candidate_count"] = len(existing)
            appended_row_count += len(additions)
            process_first = _first_layer(process_rows_delta)
            existing_first = family.get("first_supported_context_difference_layer_candidate")
            candidates = [
                value for value in (existing_first, process_first) if isinstance(value, int)
            ]
            family["first_supported_context_difference_layer_candidate"] = (
                min(candidates) if candidates else None
            )

    result["process_participation_context_enrichment_consumed"] = True
    result["process_participation_context_binding_state"] = "MATCHED_PROVIDER_REVIEWED_PROCESS_CONTEXT"
    result["process_context_enriched_family_count"] = enriched_family_count
    result["process_context_feature_difference_appended_count"] = appended_row_count
    result["process_context_rows_are_independent_evidence_votes"] = False
    result["process_annotation_is_tactical_plan_truth"] = False
    result["episode_navigation_binding_is_possession_truth"] = False
    result["temporal_overlap_is_causal_truth"] = False
    result["review_hits"] = sorted(set(result.get("review_hits") or []))
    return result
