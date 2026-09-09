from hpfa.modules.core.trace_contrast_packet_lite.src.trace_contrast_packet import (
    build_trace_contrast_packets,
)


def _variant(ref: str, occurrence: str, dependency: str):
    return {
        "trace_variant_id": ref,
        "node_records": [{"occurrence_refs": [occurrence]}],
        "dependency_group_refs": [dependency],
        "provenance_refs": ["surface-a"],
        "outcome_signature": [{"outcome_candidate": "TERMINAL_OUTCOME_SUPPORT_CANDIDATE", "count": 1}],
        "context_signature": {"period_candidate": "P1"},
    }


def _payload(variants):
    return {
        "module_id": "partial_order_trace_variant_lite_v1",
        "status": "PASS",
        "partial_order_trace_variants": variants,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _similarity(refs):
    pairs = []
    for i, a in enumerate(refs):
        for b in refs[i + 1 :]:
            pairs.append({
                "trace_a_ref": a,
                "trace_b_ref": b,
                "action_similarity": 1.0,
                "order_similarity": 1.0,
                "context_similarity": 1.0,
            })
    return {
        "module_id": "trace_similarity_primitive_lite_v1",
        "status": "PASS",
        "trace_similarity_pairs": pairs,
        "method_version": "TEST",
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_disjoint_occurrence_and_dependency_components_create_distinct_independence_groups():
    variants = [_variant("v1", "occ1", "dep1"), _variant("v2", "occ2", "dep2"), _variant("v3", "occ3", "dep3")]
    result = build_trace_contrast_packets(
        _payload(variants),
        _similarity(["v1", "v2", "v3"]),
        minimum_similarity=0.8,
        eligibility_weights={"action": 1.0, "order": 1.0, "context": 1.0},
    )
    packet = next(row for row in result["trace_contrast_packets"] if row["anchor_trace_family"] == "v1")
    assert packet["independent_support_count"] == 3
    assert len(packet["independence_groups"]) == 3
    assert set(packet["independence_group_by_trace_ref"]) == {"v1", "v2", "v3"}
    assert packet["independence_state"] == "PROVEN_WITHIN_OCCURRENCE_DEPENDENCY_SCOPE"
    assert packet["independence_is_statistical_independence"] is False


def test_shared_occurrence_collapses_variants_into_same_independence_group():
    variants = [_variant("v1", "occ1", "dep1"), _variant("v2", "occ1", "dep2"), _variant("v3", "occ3", "dep3")]
    result = build_trace_contrast_packets(
        _payload(variants),
        _similarity(["v1", "v2", "v3"]),
        minimum_similarity=0.8,
        eligibility_weights={"action": 1.0, "order": 1.0, "context": 1.0},
    )
    packet = next(row for row in result["trace_contrast_packets"] if row["anchor_trace_family"] == "v1")
    assert packet["independent_support_count"] == 2
    assert packet["independence_group_by_trace_ref"]["v1"] == packet["independence_group_by_trace_ref"]["v2"]
    assert packet["independence_group_by_trace_ref"]["v1"] != packet["independence_group_by_trace_ref"]["v3"]


def test_shared_dependency_collapses_variants_even_when_occurrences_differ():
    variants = [_variant("v1", "occ1", "dep-shared"), _variant("v2", "occ2", "dep-shared")]
    result = build_trace_contrast_packets(
        _payload(variants),
        _similarity(["v1", "v2"]),
        minimum_similarity=0.8,
        eligibility_weights={"action": 1.0, "order": 1.0, "context": 1.0},
    )
    packet = result["trace_contrast_packets"][0]
    assert packet["independent_support_count"] == 1
    assert len(packet["independence_groups"]) == 1


def test_missing_occurrence_binding_keeps_independent_support_unknown():
    first = _variant("v1", "occ1", "dep1")
    second = _variant("v2", "occ2", "dep2")
    second["node_records"] = []
    result = build_trace_contrast_packets(
        _payload([first, second]),
        _similarity(["v1", "v2"]),
        minimum_similarity=0.8,
        eligibility_weights={"action": 1.0, "order": 1.0, "context": 1.0},
    )
    packet = result["trace_contrast_packets"][0]
    assert packet["independent_support_count"] == "UNKNOWN"
    assert packet["independence_groups"] == []
    assert packet["independence_state"] == "NOT_PROVEN_MISSING_OCCURRENCE_BINDING"
    assert any(hit.startswith("independence_missing_occurrence_binding:") for hit in result["review_hits"])


def test_claim_locks_and_sample_identity_lock():
    import pathlib

    source = pathlib.Path("hpfa/modules/core/trace_contrast_packet_lite/src/trace_contrast_packet.py").read_text(encoding="utf-8")
    assert "independence_is_statistical_independence" in source
    assert "canonical_event_count" in source
    assert "production_release" in source
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
