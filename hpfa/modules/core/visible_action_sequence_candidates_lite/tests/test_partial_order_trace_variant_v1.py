from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.partial_order_trace_variant import (
    build_partial_order_trace_variants,
)

BINDING = "msb_" + "b" * 24


def _trace(trace_id: str, *, start: float, occurrence: str | None, family: str = "PASS") -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": f"actor_{trace_id}",
        "period_candidate": "1",
        "start_candidate": start,
        "pos_x_candidate": "10",
        "pos_y_candidate": "20",
        "action_family_candidates": [family],
        "supporting_action_occurrence_candidate_ids": [] if occurrence is None else [occurrence],
        "supporting_evidence_atom_ids": [f"atom_{occurrence}"] if occurrence else [],
        "supporting_relation_candidate_ids": [],
        "reflection_context_action_bundle_candidate_ids": [],
        "primary_source_lineage_records": [],
        "reflection_source_lineage_records": [],
    }


def _consequence(trace_id: str, outcome: str = "SAME_TEAM_CONTINUATION_CANDIDATE") -> dict:
    return {
        "trackable_action_consequence_candidate_id": f"c_{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "primary_consequence_candidate": outcome,
    }


def _payload(traces: list[dict]) -> tuple[dict, dict, dict]:
    ordered = sorted(traces, key=lambda row: (str(row["period_candidate"]), float(row["start_candidate"]), row["trackable_action_trace_candidate_id"]))
    buckets: list[dict] = []
    for trace in ordered:
        if buckets and buckets[-1]["start_candidate"] == float(trace["start_candidate"]):
            buckets[-1]["trackable_action_trace_candidate_ids"].append(trace["trackable_action_trace_candidate_id"])
        else:
            buckets.append({
                "visible_action_time_layer_candidate_id": f"layer_{len(buckets)+1}",
                "start_candidate": float(trace["start_candidate"]),
                "trackable_action_trace_candidate_ids": [trace["trackable_action_trace_candidate_id"]],
            })
    sequence = {
        "module_id": "visible_action_sequence_candidates_lite_v1",
        "status": "PASS",
        "visible_action_sequence_candidates": [{
            "visible_action_sequence_candidate_id": "seq_1",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_reason_candidate": "PERIOD_START",
            "end_reason_candidate": "PERIOD_END",
            "time_layer_candidate_ids": [row["visible_action_time_layer_candidate_id"] for row in buckets],
        }],
        "visible_action_time_layer_candidates": buckets,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    trace_payload = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "status": "PASS",
        "trackable_action_trace_candidates": traces,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    consequence = {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "status": "PASS",
        "trackable_action_consequence_candidates": [_consequence(row["trackable_action_trace_candidate_id"]) for row in traces],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return sequence, trace_payload, consequence


def test_same_timestamp_remains_unordered() -> None:
    result = build_partial_order_trace_variants(*_payload([
        _trace("a", start=10.0, occurrence="occ_a"),
        _trace("b", start=10.0, occurrence="occ_b", family="CARRY"),
    ]))
    variant = result["partial_order_trace_variants"][0]
    assert all(node["internal_same_time_order"] == "SAME_TIME_UNORDERED" for node in variant["node_records"])
    assert variant["ordering_completeness"] == "PARTIAL_ORDER_WITH_UNORDERED_SAME_TIME_NODES"
    assert variant["same_timestamp_internal_ordering_allowed"] is False


def test_row_order_not_promoted_to_chronology() -> None:
    traces = [_trace("b", start=14.0, occurrence="occ_b"), _trace("a", start=10.0, occurrence="occ_a")]
    result = build_partial_order_trace_variants(*_payload(traces))
    variant = result["partial_order_trace_variants"][0]
    assert variant["source_row_order_is_temporal_truth"] is False
    assert any(edge["relation"] == "BEFORE_CONFIRMED" for edge in variant["edge_relations"])


def test_reflection_duplicate_not_double_counted() -> None:
    trace = _trace("a", start=10.0, occurrence="occ_a")
    trace["supporting_evidence_atom_ids"] = ["atom_shared", "atom_shared"]
    result = build_partial_order_trace_variants(*_payload([trace]))
    variant = result["partial_order_trace_variants"][0]
    assert variant["dependency_group_refs"] == ["evidence_atom:atom_shared"]


def test_trace_variant_requires_admitted_occurrence() -> None:
    result = build_partial_order_trace_variants(*_payload([_trace("a", start=10.0, occurrence=None)]))
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("variant_trace_requires_admitted_occurrence") for hit in result["hard_block_hits"])


def test_partial_order_survives_serialization() -> None:
    result = build_partial_order_trace_variants(*_payload([
        _trace("a", start=10.0, occurrence="occ_a"),
        _trace("b", start=14.0, occurrence="occ_b"),
    ]))
    roundtrip = json.loads(json.dumps(result, sort_keys=True))
    assert roundtrip["partial_order_trace_variants"][0]["edge_relations"] == result["partial_order_trace_variants"][0]["edge_relations"]


def test_order_indeterminate_is_preserved_not_invented() -> None:
    sequence, trace_payload, consequence = _payload([
        _trace("a", start=10.0, occurrence="occ_a"),
        _trace("b", start=14.0, occurrence="occ_b"),
    ])
    sequence["visible_action_time_layer_candidates"][1]["start_candidate"] = 9.0
    result = build_partial_order_trace_variants(sequence, trace_payload, consequence)
    variant = result["partial_order_trace_variants"][0]
    assert variant["chronology_confidence"] == "PARTIAL_EXPLICIT_TIME_EVIDENCE"
    assert any(edge["relation"] == "ORDER_INDETERMINATE" for edge in variant["edge_relations"])


def test_no_sample_match_identity_leak() -> None:
    source = Path("hpfa/modules/core/visible_action_sequence_candidates_lite/src/partial_order_trace_variant.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
