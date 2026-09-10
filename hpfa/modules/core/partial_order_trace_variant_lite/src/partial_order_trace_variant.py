from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

MODULE_ID = "partial_order_trace_variant_lite_v1"
SEQUENCE_MODULE_ID = "visible_action_sequence_candidates_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "PARTIAL_ORDER_VISIBLE_TRACE_VARIANT_CANDIDATE_ONLY"
RIGHT_CENSORED_CLASS = "RIGHT_CENSORED_NO_VISIBLE_FOLLOW_UP_CANDIDATE"

ORDER_VOCABULARY = {
    "BEFORE_CONFIRMED",
    "AFTER_CONFIRMED",
    "SAME_TIME_UNORDERED",
    "ORDER_INDETERMINATE",
    "PROVENANCE_ORDER_ONLY",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _clean_ref_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {_clean(item) for item in value if _clean(item)}


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _lineage_ref(value: Any) -> str:
    if isinstance(value, dict):
        for field in ("source_sha256", "path", "source_path", "source_file", "source_ref"):
            cleaned = _clean(value.get(field))
            if cleaned:
                return cleaned
        return _clean(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return _clean(value)


def _validate_inputs(
    sequence_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if sequence_payload.get("module_id") != SEQUENCE_MODULE_ID:
        blocks.append("sequence_module_id_mismatch")
    if trace_payload.get("module_id") != TRACE_MODULE_ID:
        blocks.append("trace_module_id_mismatch")
    if consequence_payload.get("module_id") != CONSEQUENCE_MODULE_ID:
        blocks.append("consequence_module_id_mismatch")
    for name, payload in (("sequence", sequence_payload), ("trace", trace_payload), ("consequence", consequence_payload)):
        status = _clean(payload.get("status") or payload.get("module_status")).upper()
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
            blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if status == "FAIL_CLOSED":
            blocks.append(f"{name}_input_fail_closed")
        elif status == "REVIEW_REQUIRED":
            reviews.append(f"{name}_upstream_review_required")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")
    if sequence_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("sequence_same_timestamp_policy_breached")
    if sequence_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("sequence_source_row_order_policy_breached")
    return sorted(set(blocks)), sorted(set(reviews))


def _sequence_occurrence_context(sequence: dict[str, Any], sequence_id: str) -> tuple[dict[str, Any], list[str]]:
    reviews: list[str] = []
    state = _clean(sequence.get("sequence_occurrence_object_context_state"))
    team_refs = _clean_ref_set(sequence.get("sequence_occurrence_team_context_refs"))
    goalkeeper_refs = _clean_ref_set(sequence.get("sequence_occurrence_goalkeeper_context_refs"))
    goalkeeper_bundle_refs = _clean_ref_set(sequence.get("sequence_occurrence_goalkeeper_context_bundle_refs"))
    reflection_refs = _clean_ref_set(sequence.get("sequence_occurrence_reflection_context_refs"))
    relation_types = _clean_ref_set(sequence.get("sequence_occurrence_relation_type_candidates"))
    has_refs = any((team_refs, goalkeeper_refs, goalkeeper_bundle_refs, reflection_refs, relation_types))

    if state == "REVIEW_REQUIRED":
        reviews.append(f"variant_sequence_occurrence_context_upstream_review:{sequence_id}")
    elif state == "SEQUENCE_OCCURRENCE_OBJECT_CONTEXT_ONLY":
        if (
            sequence.get("sequence_occurrence_context_is_independent_support") is not False
            or sequence.get("goalkeeper_context_is_sequence_participant_truth") is not False
            or sequence.get("reflection_context_is_sequence_equivalence_truth") is not False
            or sequence.get("sequence_occurrence_context_creates_event") is not False
            or sequence.get("sequence_occurrence_context_ref_count_is_action_count") is not False
            or sequence.get("canonical_event_count") != CANONICAL_EVENT_COUNT
        ):
            reviews.append(f"variant_sequence_occurrence_context_claim_boundary_mismatch:{sequence_id}")
    elif has_refs:
        reviews.append(f"variant_sequence_occurrence_context_state_missing_or_unexpected:{sequence_id}")

    if reviews:
        team_refs = set()
        goalkeeper_refs = set()
        goalkeeper_bundle_refs = set()
        reflection_refs = set()
        relation_types = set()
        variant_state = "REVIEW_REQUIRED"
    elif has_refs and state == "SEQUENCE_OCCURRENCE_OBJECT_CONTEXT_ONLY":
        variant_state = "VARIANT_SEQUENCE_OCCURRENCE_CONTEXT_LINEAGE_ONLY"
    else:
        variant_state = "NO_CONTEXT_VISIBLE"

    return {
        "sequence_occurrence_object_context_state": variant_state,
        "sequence_occurrence_team_context_refs": sorted(team_refs),
        "sequence_occurrence_goalkeeper_context_refs": sorted(goalkeeper_refs),
        "sequence_occurrence_goalkeeper_context_bundle_refs": sorted(goalkeeper_bundle_refs),
        "sequence_occurrence_reflection_context_refs": sorted(reflection_refs),
        "sequence_occurrence_relation_type_candidates": sorted(relation_types),
        "sequence_occurrence_context_is_variant_support": False,
        "sequence_occurrence_context_is_independent_support": False,
        "goalkeeper_context_is_variant_participant_truth": False,
        "reflection_context_is_variant_equivalence_truth": False,
        "sequence_occurrence_context_ref_count_is_variant_count": False,
        "sequence_occurrence_context_ref_count_is_recurrence_count": False,
        "sequence_occurrence_context_creates_event": False,
    }, reviews


def _rejected(blocks: list[str], reviews: list[str], decision: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": decision,
        "partial_order_trace_variants": [],
        "partial_order_trace_variant_count": 0,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "provenance_order_is_football_chronology": False,
        "sequence_occurrence_context_is_variant_support": False,
        "sequence_occurrence_context_is_independent_support": False,
        "sequence_occurrence_context_ref_count_is_recurrence_count": False,
        "trace_only_node_is_event_truth": False,
        "trace_only_node_is_independent_support": False,
        "trace_only_node_count_is_recurrence_count": False,
        "right_censored_nodes_are_terminal_outcomes": False,
        "right_censored_nodes_are_failures": False,
        "right_censored_nodes_are_neutral_outcomes": False,
        "right_censored_node_count_is_recurrence_count": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_partial_order_trace_variants(
    sequence_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks, reviews = _validate_inputs(sequence_payload, trace_payload, consequence_payload)
    if blocks:
        return _rejected(blocks, reviews, "PARTIAL_ORDER_TRACE_VARIANT_INPUT_REJECTED")

    traces = [row for row in (trace_payload.get("trackable_action_trace_candidates") or []) if isinstance(row, dict)]
    consequences = [row for row in (consequence_payload.get("trackable_action_consequence_candidates") or []) if isinstance(row, dict)]
    sequences = [row for row in (sequence_payload.get("visible_action_sequence_candidates") or []) if isinstance(row, dict)]
    layers = [row for row in (sequence_payload.get("visible_action_time_layer_candidates") or []) if isinstance(row, dict)]

    trace_by_id = {_clean(row.get("trackable_action_trace_candidate_id")): row for row in traces}
    consequence_by_trace = {_clean(row.get("anchor_trackable_action_trace_candidate_id")): row for row in consequences}
    layer_by_id = {_clean(row.get("visible_action_time_layer_candidate_id")): row for row in layers}

    variants: list[dict[str, Any]] = []
    total_occurrence_backed_nodes = 0
    total_trace_only_nodes = 0
    total_right_censored_nodes = 0
    total_non_censored_consequence_nodes = 0

    for sequence in sequences:
        sequence_id = _clean(sequence.get("visible_action_sequence_candidate_id"))
        layer_ids = [_clean(value) for value in (sequence.get("time_layer_candidate_ids") or []) if _clean(value)]
        if not sequence_id or not layer_ids:
            blocks.append(f"sequence_variant_input_incomplete:{sequence_id or 'UNKNOWN'}")
            continue

        sequence_context, sequence_context_reviews = _sequence_occurrence_context(sequence, sequence_id)
        reviews.extend(sequence_context_reviews)

        node_refs: list[str] = []
        node_records: list[dict[str, Any]] = []
        edge_relations: list[dict[str, Any]] = []
        family_counter: Counter[str] = Counter()
        legacy_outcome_counter: Counter[str] = Counter()
        non_censored_outcome_counter: Counter[str] = Counter()
        censoring_counter: Counter[str] = Counter()
        dependency_group_refs: set[str] = set()
        provenance_refs: set[str] = set()
        order_indeterminate = False
        occurrence_backed_node_count = 0
        trace_only_node_count = 0
        right_censored_node_count = 0
        non_censored_consequence_node_count = 0

        previous_layer_id: str | None = None
        previous_time: float | None = None
        for layer_id in layer_ids:
            layer = layer_by_id.get(layer_id)
            if not layer:
                blocks.append(f"variant_layer_missing:{sequence_id}:{layer_id}")
                continue
            current_time = _number(layer.get("start_candidate"))
            trace_ids = [_clean(value) for value in (layer.get("trackable_action_trace_candidate_ids") or []) if _clean(value)]
            if len(trace_ids) > 1:
                order_indeterminate = True

            for trace_id in trace_ids:
                trace = trace_by_id.get(trace_id)
                consequence = consequence_by_trace.get(trace_id)
                if not trace:
                    blocks.append(f"variant_trace_missing:{sequence_id}:{trace_id}")
                    continue
                if not consequence:
                    blocks.append(f"variant_consequence_missing:{sequence_id}:{trace_id}")
                    continue

                occurrence_refs = [_clean(value) for value in (trace.get("supporting_action_occurrence_candidate_ids") or []) if _clean(value)]
                if occurrence_refs:
                    occurrence_binding_state = "OCCURRENCE_BACKED_VARIANT_NODE"
                    occurrence_backed_node_count += 1
                    total_occurrence_backed_nodes += 1
                else:
                    occurrence_binding_state = "TRACE_ONLY_VARIANT_NODE_REVIEW_BOUND"
                    trace_only_node_count += 1
                    total_trace_only_nodes += 1
                    reviews.append(f"variant_trace_without_admitted_occurrence:{trace_id}")

                families = sorted({_clean(value) for value in (trace.get("action_family_candidates") or []) if _clean(value)})
                for family in families:
                    family_counter[family] += 1

                outcome = _clean(consequence.get("primary_consequence_candidate"))
                if not outcome:
                    blocks.append(f"variant_consequence_outcome_missing:{sequence_id}:{trace_id}")
                    continue
                legacy_outcome_counter[outcome] += 1

                right_censored = consequence.get("right_censored_no_visible_follow_up") is True or outcome == RIGHT_CENSORED_CLASS
                if right_censored:
                    right_censored_node_count += 1
                    total_right_censored_nodes += 1
                    censoring_counter["RIGHT_CENSORED_OBSERVATION"] += 1
                    consequence_observation_state = "RIGHT_CENSORED_OBSERVATION"
                else:
                    non_censored_consequence_node_count += 1
                    total_non_censored_consequence_nodes += 1
                    non_censored_outcome_counter[outcome] += 1
                    consequence_observation_state = "VISIBLE_CONSEQUENCE_OBSERVED"

                for value in trace.get("supporting_evidence_atom_ids") or []:
                    cleaned = _clean(value)
                    if cleaned:
                        dependency_group_refs.add(f"evidence_atom:{cleaned}")
                for value in trace.get("supporting_relation_candidate_ids") or []:
                    cleaned = _clean(value)
                    if cleaned:
                        dependency_group_refs.add(f"relation:{cleaned}")
                for value in trace.get("reflection_context_action_bundle_candidate_ids") or []:
                    cleaned = _clean(value)
                    if cleaned:
                        dependency_group_refs.add(f"reflection_bundle:{cleaned}")
                for field in ("primary_source_lineage_records", "reflection_source_lineage_records"):
                    for value in trace.get(field) or []:
                        cleaned = _lineage_ref(value)
                        if cleaned:
                            provenance_refs.add(cleaned)

                node_refs.append(trace_id)
                node_records.append({
                    "trace_ref": trace_id,
                    "occurrence_refs": occurrence_refs,
                    "occurrence_binding_state": occurrence_binding_state,
                    "trace_only_is_event_truth": False,
                    "trace_only_is_independent_support": False,
                    "trace_only_counts_as_recurrence_support": False,
                    "time_layer_ref": layer_id,
                    "time_candidate": current_time,
                    "action_family_candidates": families,
                    "consequence_ref": consequence.get("trackable_action_consequence_candidate_id"),
                    "outcome_candidate": outcome,
                    "consequence_observation_state": consequence_observation_state,
                    "right_censored_observation": right_censored,
                    "right_censoring_is_terminal_outcome": False,
                    "right_censoring_is_failure": False,
                    "right_censoring_is_neutral_outcome": False,
                    "right_censoring_is_counterevidence": False,
                    "right_censoring_counts_as_recurrence_support": False,
                    "same_time_peer_count": max(0, len(trace_ids) - 1),
                    "internal_same_time_order": "SAME_TIME_UNORDERED" if len(trace_ids) > 1 else "NOT_APPLICABLE",
                })

            if previous_layer_id is not None:
                if current_time is None or previous_time is None:
                    relation = "ORDER_INDETERMINATE"
                    order_indeterminate = True
                elif current_time > previous_time:
                    relation = "BEFORE_CONFIRMED"
                elif current_time == previous_time:
                    relation = "SAME_TIME_UNORDERED"
                    order_indeterminate = True
                else:
                    relation = "ORDER_INDETERMINATE"
                    order_indeterminate = True
                edge_relations.append({
                    "from_layer_ref": previous_layer_id,
                    "to_layer_ref": layer_id,
                    "relation": relation,
                    "relation_is_football_chronology": relation == "BEFORE_CONFIRMED",
                })
            previous_layer_id = layer_id
            previous_time = current_time

        ordering_completeness = "PARTIAL_ORDER_WITH_UNORDERED_SAME_TIME_NODES" if order_indeterminate else "LAYER_ORDER_CONFIRMED_INTERNAL_SINGLETONS"
        chronology_confidence = "PARTIAL_EXPLICIT_TIME_EVIDENCE" if order_indeterminate else "EXPLICIT_POSITIVE_TIME_LAYER_ORDER"
        if order_indeterminate:
            reviews.append(f"partial_order_preserved:{sequence_id}")

        action_family_signature = [
            {"action_family_candidate": family, "count": count}
            for family, count in sorted(family_counter.items())
        ]
        outcome_signature = [
            {"outcome_candidate": outcome, "count": count}
            for outcome, count in sorted(legacy_outcome_counter.items())
        ]
        non_censored_outcome_signature = [
            {"outcome_candidate": outcome, "count": count}
            for outcome, count in sorted(non_censored_outcome_counter.items())
        ]
        censoring_signature = [
            {"censoring_state": state, "count": count}
            for state, count in sorted(censoring_counter.items())
        ]

        variant_id = "potv_" + _digest(
            sequence_id,
            layer_ids,
            action_family_signature,
            outcome_signature,
            ordering_completeness,
        )[:24]
        variant_row = {
            "trace_variant_id": variant_id,
            "sequence_ref": sequence_id,
            "episode_ref": None,
            "node_refs": node_refs,
            "node_records": node_records,
            "edge_relations": edge_relations,
            "action_family_signature": action_family_signature,
            "context_signature": {
                "team_identity_candidate_id": sequence.get("team_identity_candidate_id"),
                "period_candidate": sequence.get("period_candidate"),
                "start_reason_candidate": sequence.get("start_reason_candidate"),
                "end_reason_candidate": sequence.get("end_reason_candidate"),
            },
            "outcome_signature": outcome_signature,
            "outcome_signature_role": "LEGACY_CONSEQUENCE_LINEAGE_ONLY_NOT_DENOMINATOR_AUTHORITY",
            "non_censored_outcome_signature": non_censored_outcome_signature,
            "censoring_signature": censoring_signature,
            "non_censored_consequence_node_count": non_censored_consequence_node_count,
            "right_censored_node_count": right_censored_node_count,
            "outcome_denominator_authority": "NON_CENSORED_VISIBLE_CONSEQUENCE_NODES_ONLY",
            "right_censored_nodes_are_terminal_outcomes": False,
            "right_censored_nodes_are_failures": False,
            "right_censored_nodes_are_neutral_outcomes": False,
            "right_censored_nodes_are_counterevidence": False,
            "right_censored_node_count_is_recurrence_count": False,
            "ordering_completeness": ordering_completeness,
            "chronology_confidence": chronology_confidence,
            "occurrence_backed_node_count": occurrence_backed_node_count,
            "trace_only_node_count": trace_only_node_count,
            "contains_trace_only_nodes": trace_only_node_count > 0,
            "trace_only_nodes_are_event_truth": False,
            "trace_only_nodes_are_independent_support": False,
            "trace_only_node_count_is_recurrence_count": False,
            "dependency_group_refs": sorted(dependency_group_refs),
            "provenance_refs": sorted(provenance_refs),
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "provenance_order_is_football_chronology": False,
            "trace_variant_is_tactical_pattern_truth": False,
            "trace_variant_is_coach_intention_truth": False,
            "trace_variant_is_sequence_truth": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "claim_ceiling": CLAIM_CEILING,
        }
        variant_row.update(sequence_context)
        variants.append(variant_row)

    if blocks:
        return _rejected(blocks, reviews, "PARTIAL_ORDER_TRACE_VARIANT_BUILD_REJECTED")

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "PARTIAL_ORDER_TRACE_VARIANTS_BUILT",
        "partial_order_trace_variants": variants,
        "partial_order_trace_variant_count": len(variants),
        "source_visible_action_sequence_candidate_count": len(sequences),
        "occurrence_backed_variant_node_count": total_occurrence_backed_nodes,
        "trace_only_variant_node_count": total_trace_only_nodes,
        "right_censored_variant_node_count": total_right_censored_nodes,
        "non_censored_consequence_variant_node_count": total_non_censored_consequence_nodes,
        "trace_only_nodes_present": total_trace_only_nodes > 0,
        "trace_only_node_is_event_truth": False,
        "trace_only_node_is_independent_support": False,
        "trace_only_node_count_is_recurrence_count": False,
        "right_censored_nodes_are_terminal_outcomes": False,
        "right_censored_nodes_are_failures": False,
        "right_censored_nodes_are_neutral_outcomes": False,
        "right_censored_nodes_are_counterevidence": False,
        "right_censored_node_count_is_recurrence_count": False,
        "outcome_signature_may_be_used_as_denominator_authority": False,
        "non_censored_outcome_signature_is_denominator_candidate_only": True,
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "provenance_order_is_football_chronology": False,
        "sequence_occurrence_context_is_variant_support": False,
        "sequence_occurrence_context_is_independent_support": False,
        "sequence_occurrence_context_ref_count_is_recurrence_count": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
