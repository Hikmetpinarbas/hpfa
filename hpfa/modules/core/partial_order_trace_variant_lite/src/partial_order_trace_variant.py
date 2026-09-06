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

ORDER_VOCABULARY = {
    "BEFORE_CONFIRMED",
    "AFTER_CONFIRMED",
    "SAME_TIME_UNORDERED",
    "ORDER_INDETERMINATE",
    "PROVENANCE_ORDER_ONLY",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


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


def build_partial_order_trace_variants(
    sequence_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks, reviews = _validate_inputs(sequence_payload, trace_payload, consequence_payload)
    if blocks:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "PARTIAL_ORDER_TRACE_VARIANT_INPUT_REJECTED",
            "partial_order_trace_variants": [],
            "partial_order_trace_variant_count": 0,
            "hard_block_hits": blocks,
            "review_hits": reviews,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "provenance_order_is_football_chronology": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    traces = [row for row in (trace_payload.get("trackable_action_trace_candidates") or []) if isinstance(row, dict)]
    consequences = [row for row in (consequence_payload.get("trackable_action_consequence_candidates") or []) if isinstance(row, dict)]
    sequences = [row for row in (sequence_payload.get("visible_action_sequence_candidates") or []) if isinstance(row, dict)]
    layers = [row for row in (sequence_payload.get("visible_action_time_layer_candidates") or []) if isinstance(row, dict)]

    trace_by_id = {_clean(row.get("trackable_action_trace_candidate_id")): row for row in traces}
    consequence_by_trace = {_clean(row.get("anchor_trackable_action_trace_candidate_id")): row for row in consequences}
    layer_by_id = {_clean(row.get("visible_action_time_layer_candidate_id")): row for row in layers}

    variants: list[dict[str, Any]] = []

    for sequence in sequences:
        sequence_id = _clean(sequence.get("visible_action_sequence_candidate_id"))
        layer_ids = [_clean(value) for value in (sequence.get("time_layer_candidate_ids") or []) if _clean(value)]
        if not sequence_id or not layer_ids:
            blocks.append(f"sequence_variant_input_incomplete:{sequence_id or 'UNKNOWN'}")
            continue

        node_refs: list[str] = []
        node_records: list[dict[str, Any]] = []
        edge_relations: list[dict[str, Any]] = []
        family_counter: Counter[str] = Counter()
        outcome_counter: Counter[str] = Counter()
        dependency_group_refs: set[str] = set()
        provenance_refs: set[str] = set()
        order_indeterminate = False

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
                occurrence_refs = [
                    _clean(value)
                    for value in (trace.get("supporting_action_occurrence_candidate_ids") or [])
                    if _clean(value)
                ]
                if not occurrence_refs:
                    blocks.append(f"variant_trace_requires_admitted_occurrence:{trace_id}")
                families = sorted({_clean(value) for value in (trace.get("action_family_candidates") or []) if _clean(value)})
                for family in families:
                    family_counter[family] += 1
                outcome = _clean(consequence.get("primary_consequence_candidate"))
                if not outcome:
                    blocks.append(f"variant_consequence_outcome_missing:{sequence_id}:{trace_id}")
                    continue
                outcome_counter[outcome] += 1

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
                    "time_layer_ref": layer_id,
                    "time_candidate": current_time,
                    "action_family_candidates": families,
                    "consequence_ref": consequence.get("trackable_action_consequence_candidate_id"),
                    "outcome_candidate": outcome,
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

        ordering_completeness = (
            "PARTIAL_ORDER_WITH_UNORDERED_SAME_TIME_NODES"
            if order_indeterminate
            else "LAYER_ORDER_CONFIRMED_INTERNAL_SINGLETONS"
        )
        chronology_confidence = (
            "PARTIAL_EXPLICIT_TIME_EVIDENCE"
            if order_indeterminate
            else "EXPLICIT_POSITIVE_TIME_LAYER_ORDER"
        )
        if order_indeterminate:
            reviews.append(f"partial_order_preserved:{sequence_id}")

        action_family_signature = [
            {"action_family_candidate": family, "count": count}
            for family, count in sorted(family_counter.items())
        ]
        outcome_signature = [
            {"outcome_candidate": outcome, "count": count}
            for outcome, count in sorted(outcome_counter.items())
        ]
        variant_id = "potv_" + _digest(
            sequence_id,
            layer_ids,
            action_family_signature,
            outcome_signature,
            ordering_completeness,
        )[:24]
        variants.append({
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
            "ordering_completeness": ordering_completeness,
            "chronology_confidence": chronology_confidence,
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
        })

    if blocks:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "PARTIAL_ORDER_TRACE_VARIANT_BUILD_REJECTED",
            "partial_order_trace_variants": [],
            "partial_order_trace_variant_count": 0,
            "hard_block_hits": sorted(set(blocks)),
            "review_hits": sorted(set(reviews)),
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "provenance_order_is_football_chronology": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "PARTIAL_ORDER_TRACE_VARIANTS_BUILT",
        "partial_order_trace_variants": variants,
        "partial_order_trace_variant_count": len(variants),
        "source_visible_action_sequence_candidate_count": len(sequences),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "provenance_order_is_football_chronology": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
