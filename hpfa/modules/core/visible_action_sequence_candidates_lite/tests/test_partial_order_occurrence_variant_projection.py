from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.partial_order_occurrence_variant_projection import (
    build_partial_order_occurrence_variants,
)


def _trace(trace_id: str, occ_id: str, actor: str) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "occurrence_backed_trace_candidate": True,
        "supporting_action_occurrence_candidate_ids": [occ_id],
        "actor_identity_candidate_id": actor,
        "action_family_candidates": ["PASS"],
        "supporting_evidence_atom_ids": [f"atom_{trace_id}"],
        "supporting_relation_candidate_ids": [],
        "reflection_context_action_bundle_candidate_ids": [f"bundle_{trace_id}"],
        "primary_source_lineage_records": [{"source_sha256": f"sha_{trace_id}"}],
        "reflection_source_lineage_records": [],
    }


def _consequence(trace_id: str) -> dict:
    return {
        "trackable_action_consequence_candidate_id": f"cons_{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
    }


def _payloads(status: str = "PASS"):
    sequence = {
        "status": status,
        "primary_sequence_projection_mode": "OCCURRENCE_TEMPORAL_PRIMARY",
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "visible_action_time_layer_candidates": [
            {
                "visible_action_time_layer_candidate_id": "layer_a",
                "start_candidate": 10.0,
                "trackable_action_trace_candidate_ids": ["trace_a", "trace_b"],
            },
            {
                "visible_action_time_layer_candidate_id": "layer_b",
                "start_candidate": 16.0,
                "trackable_action_trace_candidate_ids": ["trace_c"],
            },
        ],
        "visible_action_sequence_candidates": [
            {
                "visible_action_sequence_candidate_id": "seq_alpha",
                "team_identity_candidate_id": "team_candidate",
                "period_candidate": "1",
                "time_layer_candidate_ids": ["layer_a", "layer_b"],
            }
        ],
    }
    trace = {
        "trackable_action_trace_candidates": [
            _trace("trace_a", "occ_a", "actor_a"),
            _trace("trace_b", "occ_b", "actor_b"),
            _trace("trace_c", "occ_c", "actor_c"),
        ]
    }
    consequence = {
        "trackable_action_consequence_candidates": [
            _consequence("trace_a"),
            _consequence("trace_b"),
            _consequence("trace_c"),
        ]
    }
    return sequence, trace, consequence


def test_preserves_same_time_unordered_and_positive_layer_order() -> None:
    sequence, trace, consequence = _payloads()
    report = build_partial_order_occurrence_variants(sequence, trace, consequence)
    assert report["status"] == "PASS"
    assert report["partial_order_occurrence_variant_count"] == 1
    variant = report["partial_order_occurrence_variants"][0]
    assert variant["edge_relations"] == [{
        "from_layer_ref": "layer_a",
        "to_layer_ref": "layer_b",
        "relation": "BEFORE_CONFIRMED",
        "relation_is_football_chronology": True,
    }]
    first_layer_nodes = [row for row in variant["node_records"] if row["time_layer_ref"] == "layer_a"]
    assert len(first_layer_nodes) == 2
    assert all(row["internal_same_time_order"] == "SAME_TIME_UNORDERED" for row in first_layer_nodes)
    assert variant["same_timestamp_internal_ordering_allowed"] is False
    assert variant["partial_order_variant_is_tactical_pattern_truth"] is False
    assert variant["canonical_event_count"] == "UNKNOWN"
    assert variant["true_action_count"] == "UNKNOWN"


def test_missing_occurrence_binding_fails_closed() -> None:
    sequence, trace, consequence = _payloads()
    trace["trackable_action_trace_candidates"][0]["supporting_action_occurrence_candidate_ids"] = []
    trace["trackable_action_trace_candidates"][0]["occurrence_backed_trace_candidate"] = False
    report = build_partial_order_occurrence_variants(sequence, trace, consequence)
    assert report["status"] == "FAIL_CLOSED"
    assert report["partial_order_occurrence_variant_count"] == 0
    assert any("variant_requires_occurrence_backed_trace" in item for item in report["hard_block_hits"])


def test_upstream_review_required_is_not_laundered_to_pass() -> None:
    sequence, trace, consequence = _payloads(status="REVIEW_REQUIRED")
    report = build_partial_order_occurrence_variants(sequence, trace, consequence)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["partial_order_occurrence_variant_count"] == 1


def test_missing_consequence_anchor_fails_closed() -> None:
    sequence, trace, consequence = _payloads()
    consequence["trackable_action_consequence_candidates"] = consequence["trackable_action_consequence_candidates"][:-1]
    report = build_partial_order_occurrence_variants(sequence, trace, consequence)
    assert report["status"] == "FAIL_CLOSED"
    assert any("variant_consequence_missing" in item for item in report["hard_block_hits"])


def test_no_sample_match_identity_leak() -> None:
    root = Path(__file__).resolve().parents[5]
    text = (root / "hpfa/modules/core/visible_action_sequence_candidates_lite/src/partial_order_occurrence_variant_projection.py").read_text(encoding="utf-8")
    forbidden = ("Galatasaray", "Sporting", "Fenerbahce", "Roma", "09.09.2026", "10.09.2026")
    assert not any(token in text for token in forbidden)
