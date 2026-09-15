from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

CLAIM_CEILING = "PARTIAL_ORDER_VISIBLE_SEQUENCE_VARIANT_CANDIDATE_ONLY"


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


def build_partial_order_occurrence_variants(
    sequence_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("primary_sequence_projection_mode") != "OCCURRENCE_TEMPORAL_PRIMARY":
        blocks.append("occurrence_temporal_primary_inventory_not_admitted")
    if sequence_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_internal_ordering_policy_breached")
    if sequence_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_temporal_policy_breached")
    if sequence_payload.get("sequence_truth") is True or sequence_payload.get("possession_truth") is True:
        blocks.append("upstream_truth_promotion_breached")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if sequence_payload.get("production_release") is True:
        blocks.append("production_release_claimed")

    sequences = [row for row in (sequence_payload.get("visible_action_sequence_candidates") or []) if isinstance(row, dict)]
    layers = [row for row in (sequence_payload.get("visible_action_time_layer_candidates") or []) if isinstance(row, dict)]
    traces = [row for row in (trace_payload.get("trackable_action_trace_candidates") or []) if isinstance(row, dict)]
    consequences = [row for row in (consequence_payload.get("trackable_action_consequence_candidates") or []) if isinstance(row, dict)]

    layer_by_id = {_clean(row.get("visible_action_time_layer_candidate_id")): row for row in layers}
    trace_by_id = {_clean(row.get("trackable_action_trace_candidate_id")): row for row in traces}
    consequence_by_trace = {
        _clean(row.get("anchor_trackable_action_trace_candidate_id")): row for row in consequences
    }

    variants: list[dict[str, Any]] = []
    for sequence in sequences:
        sequence_id = _clean(sequence.get("visible_action_sequence_candidate_id"))
        layer_ids = [_clean(value) for value in (sequence.get("time_layer_candidate_ids") or []) if _clean(value)]
        if not sequence_id or len(layer_ids) < 2:
            reviews.append(f"variant_requires_multi_layer_sequence:{sequence_id or 'UNKNOWN'}")
            continue

        node_records: list[dict[str, Any]] = []
        edge_relations: list[dict[str, Any]] = []
        family_counts: Counter[str] = Counter()
        outcome_counts: Counter[str] = Counter()
        occurrence_refs: set[str] = set()
        dependency_refs: set[str] = set()
        provenance_refs: set[str] = set()
        variant_blocked = False

        previous_layer_id: str | None = None
        previous_time: float | None = None
        for layer_id in layer_ids:
            layer = layer_by_id.get(layer_id)
            if not layer:
                blocks.append(f"variant_layer_missing:{sequence_id}:{layer_id}")
                variant_blocked = True
                continue
            current_time = _number(layer.get("start_candidate"))
            trace_ids = [_clean(value) for value in (layer.get("trackable_action_trace_candidate_ids") or []) if _clean(value)]
            if not trace_ids:
                blocks.append(f"variant_layer_trace_refs_missing:{sequence_id}:{layer_id}")
                variant_blocked = True
                continue

            layer_occurrence_refs: list[str] = []
            for trace_id in trace_ids:
                trace = trace_by_id.get(trace_id)
                consequence = consequence_by_trace.get(trace_id)
                if not trace:
                    blocks.append(f"variant_trace_missing:{sequence_id}:{trace_id}")
                    variant_blocked = True
                    continue
                if not consequence:
                    blocks.append(f"variant_consequence_missing:{sequence_id}:{trace_id}")
                    variant_blocked = True
                    continue
                occs = [_clean(value) for value in (trace.get("supporting_action_occurrence_candidate_ids") or []) if _clean(value)]
                if not trace.get("occurrence_backed_trace_candidate") or not occs:
                    blocks.append(f"variant_requires_occurrence_backed_trace:{sequence_id}:{trace_id}")
                    variant_blocked = True
                    continue
                layer_occurrence_refs.extend(occs)
                occurrence_refs.update(occs)
                families = sorted({_clean(value) for value in (trace.get("action_family_candidates") or []) if _clean(value)})
                for family in families:
                    family_counts[family] += 1
                outcome = _clean(consequence.get("primary_consequence_candidate"))
                if outcome:
                    outcome_counts[outcome] += 1
                else:
                    reviews.append(f"variant_outcome_missing:{sequence_id}:{trace_id}")

                for field, prefix in (
                    ("supporting_evidence_atom_ids", "atom"),
                    ("supporting_relation_candidate_ids", "relation"),
                    ("reflection_context_action_bundle_candidate_ids", "reflection_bundle"),
                ):
                    for value in trace.get(field) or []:
                        cleaned = _clean(value)
                        if cleaned:
                            dependency_refs.add(f"{prefix}:{cleaned}")
                for field in ("primary_source_lineage_records", "reflection_source_lineage_records"):
                    for value in trace.get(field) or []:
                        if isinstance(value, dict):
                            cleaned = _clean(value.get("source_sha256") or value.get("source_file"))
                        else:
                            cleaned = _clean(value)
                        if cleaned:
                            provenance_refs.add(cleaned)

                node_records.append({
                    "trace_ref": trace_id,
                    "occurrence_refs": occs,
                    "time_layer_ref": layer_id,
                    "time_candidate": current_time,
                    "action_family_candidates": families,
                    "outcome_candidate": outcome or None,
                    "same_time_peer_count": max(0, len(trace_ids) - 1),
                    "internal_same_time_order": "SAME_TIME_UNORDERED" if len(trace_ids) > 1 else "NOT_APPLICABLE",
                })

            if previous_layer_id is not None:
                if current_time is None or previous_time is None or current_time <= previous_time:
                    relation = "ORDER_INDETERMINATE"
                    reviews.append(f"variant_inter_layer_order_not_confirmed:{sequence_id}")
                else:
                    relation = "BEFORE_CONFIRMED"
                edge_relations.append({
                    "from_layer_ref": previous_layer_id,
                    "to_layer_ref": layer_id,
                    "relation": relation,
                    "relation_is_football_chronology": relation == "BEFORE_CONFIRMED",
                })
            previous_layer_id = layer_id
            previous_time = current_time

        if variant_blocked:
            continue

        action_signature = [
            {"action_family_candidate": key, "count": value}
            for key, value in sorted(family_counts.items())
        ]
        outcome_signature = [
            {"outcome_candidate": key, "count": value}
            for key, value in sorted(outcome_counts.items())
        ]
        variant_id = "pov_" + _digest(
            sequence_id,
            layer_ids,
            action_signature,
            outcome_signature,
            edge_relations,
        )[:24]
        variants.append({
            "partial_order_occurrence_variant_id": variant_id,
            "sequence_ref": sequence_id,
            "team_identity_candidate_id": sequence.get("team_identity_candidate_id"),
            "period_candidate": sequence.get("period_candidate"),
            "time_layer_refs": layer_ids,
            "node_records": node_records,
            "edge_relations": edge_relations,
            "action_family_signature": action_signature,
            "outcome_signature": outcome_signature,
            "supporting_action_occurrence_candidate_ids": sorted(occurrence_refs),
            "dependency_group_refs": sorted(dependency_refs),
            "provenance_refs": sorted(provenance_refs),
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "partial_order_variant_is_sequence_truth": False,
            "partial_order_variant_is_possession_truth": False,
            "partial_order_variant_is_tactical_pattern_truth": False,
            "partial_order_variant_is_coach_intention_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or str(sequence_payload.get("status") or "").upper() == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "status": status,
        "partial_order_occurrence_variants": variants if not blocks else [],
        "partial_order_occurrence_variant_count": len(variants) if not blocks else 0,
        "source_visible_action_sequence_candidate_count": len(sequences),
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "partial_order_variant_is_sequence_truth": False,
        "partial_order_variant_is_possession_truth": False,
        "partial_order_variant_is_tactical_pattern_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
