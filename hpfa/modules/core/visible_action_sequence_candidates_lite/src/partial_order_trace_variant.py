from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "PARTIAL_ORDER_TRACE_VARIANT_CANDIDATE_ONLY"
ORDER_STATES = {
    "BEFORE_CONFIRMED",
    "AFTER_CONFIRMED",
    "SAME_TIME_UNORDERED",
    "ORDER_INDETERMINATE",
    "PROVENANCE_ORDER_ONLY",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_partial_order_trace_variants(
    sequence_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("module_id") != "visible_action_sequence_candidates_lite_v1":
        blocks.append("sequence_module_id_mismatch")
    if trace_payload.get("module_id") != "trackable_action_trace_candidates_lite_v1":
        blocks.append("trace_module_id_mismatch")
    if consequence_payload.get("module_id") != "trackable_action_consequence_candidates_lite_v1":
        blocks.append("consequence_module_id_mismatch")
    for prefix, payload in (("sequence", sequence_payload), ("trace", trace_payload), ("consequence", consequence_payload)):
        if payload.get("status") == "FAIL_CLOSED" or payload.get("hard_block_hits"):
            blocks.append(f"{prefix}_input_fail_closed")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{prefix}_production_release_claimed")

    traces = [row for row in (trace_payload.get("trackable_action_trace_candidates") or []) if isinstance(row, dict)]
    consequences = [row for row in (consequence_payload.get("trackable_action_consequence_candidates") or []) if isinstance(row, dict)]
    trace_by_id = {_clean(row.get("trackable_action_trace_candidate_id")): row for row in traces}
    consequence_by_trace = {_clean(row.get("anchor_trackable_action_trace_candidate_id")): row for row in consequences}

    variants: list[dict[str, Any]] = []
    for sequence in sequence_payload.get("visible_action_sequence_candidates") or []:
        if not isinstance(sequence, dict):
            continue
        sequence_id = _clean(sequence.get("visible_action_sequence_candidate_id"))
        trace_ids = [_clean(value) for value in (sequence.get("trackable_action_trace_candidate_ids") or []) if _clean(value)]
        if not trace_ids:
            reviews.append(f"sequence_without_trace_members:{sequence_id}")
            continue

        nodes: list[dict[str, Any]] = []
        time_buckets: dict[tuple[str, float], list[str]] = defaultdict(list)
        dependency_groups: set[str] = set()
        provenance_refs: set[str] = set()
        outcome_signature: list[str] = []
        action_family_signature: list[str] = []

        for trace_id in trace_ids:
            trace = trace_by_id.get(trace_id)
            if not trace:
                blocks.append(f"sequence_trace_missing:{sequence_id}:{trace_id}")
                continue
            occurrence_ids = sorted({_clean(value) for value in (trace.get("supporting_action_occurrence_candidate_ids") or []) if _clean(value)})
            if not occurrence_ids:
                blocks.append(f"trace_variant_requires_admitted_occurrence:{trace_id}")
            start = _number(trace.get("start_candidate"))
            period = _clean(trace.get("period_candidate"))
            if start is None:
                blocks.append(f"trace_start_missing_for_variant:{trace_id}")
                continue
            families = sorted({_clean(value) for value in (trace.get("action_family_candidates") or []) if _clean(value)})
            consequence = consequence_by_trace.get(trace_id) or {}
            primary_outcome = _clean(consequence.get("primary_consequence_candidate")) or "UNKNOWN_VISIBLE_OUTCOME"
            node_id = "potn_" + _digest(sequence_id, trace_id, occurrence_ids)[:24]
            nodes.append({
                "node_ref": node_id,
                "trackable_action_trace_candidate_id": trace_id,
                "supporting_action_occurrence_candidate_ids": occurrence_ids,
                "action_family_candidates": families,
                "team_identity_candidate_id": trace.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": trace.get("actor_identity_candidate_id"),
                "period_candidate": period,
                "start_candidate": start,
                "pos_x_candidate": trace.get("pos_x_candidate"),
                "pos_y_candidate": trace.get("pos_y_candidate"),
                "primary_consequence_candidate": primary_outcome,
                "source_row_order_is_temporal_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            })
            time_buckets[(period, start)].append(node_id)
            action_family_signature.extend(families)
            outcome_signature.append(primary_outcome)
            for value in trace.get("supporting_evidence_atom_ids") or []:
                cleaned = _clean(value)
                if cleaned:
                    dependency_groups.add(cleaned)
            for field in ("primary_source_lineage_records", "reflection_source_lineage_records"):
                for value in trace.get(field) or []:
                    if isinstance(value, dict):
                        cleaned = _clean(value.get("source_sha256") or value.get("path") or value.get("source_path"))
                    else:
                        cleaned = _clean(value)
                    if cleaned:
                        provenance_refs.add(cleaned)

        if blocks:
            continue

        ordered_buckets = sorted(time_buckets.items(), key=lambda item: (item[0][0], item[0][1]))
        edges: list[dict[str, Any]] = []
        unordered_node_count = 0
        for _, members in ordered_buckets:
            if len(members) > 1:
                unordered_node_count += len(members)
                for index, left in enumerate(sorted(members)):
                    for right in sorted(members)[index + 1:]:
                        edges.append({
                            "from_node_ref": left,
                            "to_node_ref": right,
                            "relation": "SAME_TIME_UNORDERED",
                            "football_chronology_admitted": False,
                        })
        for index in range(len(ordered_buckets) - 1):
            (period_a, time_a), members_a = ordered_buckets[index]
            (period_b, time_b), members_b = ordered_buckets[index + 1]
            if period_a != period_b:
                relation = "ORDER_INDETERMINATE"
                admitted = False
            elif time_b > time_a:
                relation = "BEFORE_CONFIRMED"
                admitted = True
            else:
                relation = "ORDER_INDETERMINATE"
                admitted = False
            for left in sorted(members_a):
                for right in sorted(members_b):
                    edges.append({
                        "from_node_ref": left,
                        "to_node_ref": right,
                        "relation": relation,
                        "football_chronology_admitted": admitted,
                    })

        indeterminate_edges = sum(edge["relation"] == "ORDER_INDETERMINATE" for edge in edges)
        ordering_completeness = (
            "PARTIAL_ORDER_WITH_UNORDERED_TIES"
            if unordered_node_count and not indeterminate_edges
            else "ORDER_INDETERMINATE_PRESENT"
            if indeterminate_edges
            else "STRICT_BETWEEN_LAYER_ORDER_ONLY"
        )
        chronology_confidence = (
            "FAIL_CLOSED_FOR_TOTAL_ORDER"
            if indeterminate_edges
            else "ADMITTED_BETWEEN_VISIBLE_TIME_LAYERS_ONLY"
        )

        variant_id = "potv_" + _digest(
            sequence.get("team_identity_candidate_id"),
            sorted(set(action_family_signature)),
            sorted(outcome_signature),
            [(edge["from_node_ref"], edge["to_node_ref"], edge["relation"]) for edge in edges],
        )[:24]
        variants.append({
            "trace_variant_id": variant_id,
            "sequence_ref": sequence_id,
            "episode_ref": None,
            "node_refs": [node["node_ref"] for node in nodes],
            "nodes": nodes,
            "edge_relations": edges,
            "action_family_signature": sorted(set(action_family_signature)),
            "context_signature": {
                "team_identity_candidate_id": sequence.get("team_identity_candidate_id"),
                "period_candidate": sequence.get("period_candidate"),
                "start_reason_candidate": sequence.get("start_reason_candidate"),
                "end_reason_candidate": sequence.get("end_reason_candidate"),
            },
            "outcome_signature": sorted(outcome_signature),
            "ordering_completeness": ordering_completeness,
            "chronology_confidence": chronology_confidence,
            "dependency_group_refs": sorted(dependency_groups),
            "provenance_refs": sorted(provenance_refs),
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "provenance_order_only_is_football_chronology": False,
            "partial_order_variant_is_tactical_pattern_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if any(
        edge.get("relation") not in ORDER_STATES
        for variant in variants
        for edge in variant.get("edge_relations") or []
    ):
        blocks.append("unknown_partial_order_relation_state")

    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": "partial_order_trace_variant_v1",
        "status": status,
        "trace_variants": variants if not blocks else [],
        "trace_variant_count": 0 if blocks else len(variants),
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "provenance_order_only_is_football_chronology": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
