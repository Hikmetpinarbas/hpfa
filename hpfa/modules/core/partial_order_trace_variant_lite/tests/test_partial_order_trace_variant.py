from hpfa.modules.core.partial_order_trace_variant_lite.src.partial_order_trace_variant import (
    build_partial_order_trace_variants,
)


def _trace(trace_id, start, occurrence_id, family="PASS"):
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": "b1",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": f"actor_{trace_id}",
        "start_candidate": start,
        "period_candidate": "1",
        "action_family_candidates": [family],
        "supporting_action_occurrence_candidate_ids": [occurrence_id],
        "dependency_group": f"dep:{occurrence_id}",
        "provenance_root": f"prov:{occurrence_id}",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence(trace_id, outcome="VISIBLE_CONTINUATION"):
    return {
        "trackable_action_consequence_candidate_id": f"c:{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "primary_consequence_candidate": outcome,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def _payloads(same_time=False, missing_occurrence=False):
    traces = [
        _trace("t1", 10.0, "o1", "PASS"),
        _trace("t2", 10.0 if same_time else 12.0, "o2", "CARRY"),
    ]
    if missing_occurrence:
        traces[1]["supporting_action_occurrence_candidate_ids"] = []
    layers = [
        {
            "visible_action_time_layer_candidate_id": "l1",
            "start_candidate": 10.0,
            "trackable_action_trace_candidate_ids": ["t1"] + (["t2"] if same_time else []),
        }
    ]
    layer_ids = ["l1"]
    if not same_time:
        layers.append({
            "visible_action_time_layer_candidate_id": "l2",
            "start_candidate": 12.0,
            "trackable_action_trace_candidate_ids": ["t2"],
        })
        layer_ids.append("l2")
    sequence = {
        "visible_action_sequence_candidate_id": "s1",
        "team_identity_candidate_id": "team_a",
        "period_candidate": "1",
        "start_reason_candidate": "PERIOD_START",
        "end_reason_candidate": "PERIOD_END",
        "time_layer_candidate_ids": layer_ids,
    }
    sequence_payload = {
        "module_id": "visible_action_sequence_candidates_lite_v1",
        "status": "PASS",
        "visible_action_sequence_candidates": [sequence],
        "visible_action_time_layer_candidates": layers,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    trace_payload = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "status": "PASS",
        "trackable_action_trace_candidates": traces,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    consequence_payload = {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "status": "PASS",
        "trackable_action_consequence_candidates": [_consequence("t1"), _consequence("t2")],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return sequence_payload, trace_payload, consequence_payload


def test_same_timestamp_remains_unordered():
    result = build_partial_order_trace_variants(*_payloads(same_time=True))
    row = result["partial_order_trace_variants"][0]
    assert row["ordering_completeness"] == "PARTIAL_ORDER_WITH_UNORDERED_SAME_TIME_NODES"
    assert all(node["internal_same_time_order"] == "SAME_TIME_UNORDERED" for node in row["node_records"])
    assert row["same_timestamp_internal_ordering_allowed"] is False


def test_row_order_not_promoted_to_chronology():
    result = build_partial_order_trace_variants(*_payloads())
    row = result["partial_order_trace_variants"][0]
    assert row["source_row_order_is_temporal_truth"] is False
    assert row["provenance_order_is_football_chronology"] is False


def test_trace_variant_requires_admitted_occurrence():
    result = build_partial_order_trace_variants(*_payloads(missing_occurrence=True))
    assert result["status"] == "FAIL_CLOSED"
    assert any("variant_trace_requires_admitted_occurrence:t2" == hit for hit in result["hard_block_hits"])


def test_partial_order_survives_serialization():
    result = build_partial_order_trace_variants(*_payloads(same_time=True))
    row = result["partial_order_trace_variants"][0]
    assert row["node_refs"] == ["t1", "t2"]
    assert row["chronology_confidence"] == "PARTIAL_EXPLICIT_TIME_EVIDENCE"
    assert row["trace_variant_is_tactical_pattern_truth"] is False


def test_reflection_duplicate_not_double_counted_by_dependency_identity():
    result = build_partial_order_trace_variants(*_payloads())
    row = result["partial_order_trace_variants"][0]
    assert sorted(row["dependency_group_refs"]) == ["dep:o1", "dep:o2"]
    assert len(row["dependency_group_refs"]) == len(set(row["dependency_group_refs"]))


def test_order_indeterminate_fail_closed_when_upstream_policy_is_breached():
    sequence, trace, consequence = _payloads()
    sequence["same_timestamp_internal_ordering_allowed"] = True
    result = build_partial_order_trace_variants(sequence, trace, consequence)
    assert result["status"] == "FAIL_CLOSED"
    assert "sequence_same_timestamp_policy_breached" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    result = build_partial_order_trace_variants(*_payloads())
    encoded = str(result)
    assert "Genclerbirligi" not in encoded
    assert "Fenerbahce" not in encoded
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
