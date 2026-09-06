from hpfa.modules.core.trace_contrast_packet_lite.src.trace_contrast_packet import build_trace_contrast_packets


def test_missing_outcome_evidence_is_not_visible_divergence_or_counterevidence():
    variants = {
        "module_id": "partial_order_trace_variant_lite_v1",
        "status": "PASS",
        "partial_order_trace_variants": [
            {"trace_variant_id": "a", "outcome_signature": [{"outcome_candidate": "TERMINAL_OUTCOME_SUPPORT_CANDIDATE", "count": 1}]},
            {"trace_variant_id": "b", "outcome_signature": []},
        ],
        "partial_order_trace_variant_count": 2,
        "hard_block_hits": [],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    similarity = {
        "module_id": "trace_similarity_primitive_lite_v1",
        "status": "PASS",
        "trace_similarity_pairs": [{
            "trace_a_ref": "a", "trace_b_ref": "b",
            "action_similarity": 1.0, "order_similarity": 1.0,
            "context_similarity": 1.0, "outcome_similarity": None,
        }],
        "hard_block_hits": [],
        "method_version": "TRACE_SIMILARITY_PRIMITIVE_V1.0.0",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    result = build_trace_contrast_packets(
        variants, similarity, minimum_similarity=0.8,
        eligibility_weights={"action": 1, "order": 1, "context": 1},
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "missing_visible_outcome_evidence:b" in result["hard_block_hits"]
    assert result["trace_contrast_packets"] == []
