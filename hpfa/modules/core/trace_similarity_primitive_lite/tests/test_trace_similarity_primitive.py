from pathlib import Path

from hpfa.modules.core.trace_similarity_primitive_lite.src.trace_similarity_primitive import (
    METHOD_VERSION,
    build_trace_similarity_primitive,
)


def _variant(variant_id: str, *, action="PASS", outcome="CONTINUATION", relation="BEFORE_CONFIRMED", team="A", period="1"):
    return {
        "trace_variant_id": variant_id,
        "action_family_signature": [{"action_family_candidate": action, "count": 2}],
        "outcome_signature": [{"outcome_candidate": outcome, "count": 1}],
        "context_signature": {
            "team_identity_candidate_id": team,
            "period_candidate": period,
            "start_reason_candidate": "CONTINUATION",
            "end_reason_candidate": "PERIOD_END",
        },
        "edge_relations": [{"from_layer_ref": "l1", "to_layer_ref": "l2", "relation": relation}],
        "node_records": [],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
    }


def _payload(a=None, b=None, *, status="PASS"):
    variants = [a or _variant("a"), b or _variant("b")]
    return {
        "module_id": "partial_order_trace_variant_lite_v1",
        "status": status,
        "partial_order_trace_variants": variants,
        "partial_order_trace_variant_count": len(variants),
        "hard_block_hits": [],
        "review_hits": ["partial_order_preserved:a"] if status == "REVIEW_REQUIRED" else [],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _pair(result):
    assert result["trace_similarity_pair_count"] == 1
    return result["trace_similarity_pairs"][0]


def test_missing_spatial_does_not_fake_zero():
    pair = _pair(build_trace_similarity_primitive(_payload()))
    assert pair["spatial_similarity_if_eligible"] is None
    assert pair["component_states"]["spatial"].startswith("NOT_ELIGIBLE")
    assert pair["missing_component_policy"] == "MISSING_OR_INELIGIBLE_IS_NULL_NEVER_ZERO"


def test_unknown_order_penalized_or_marked_not_invented():
    pair = _pair(build_trace_similarity_primitive(_payload(b=_variant("b", relation="ORDER_INDETERMINATE"))))
    assert pair["order_similarity"] is None
    assert pair["component_states"]["order"] == "ORDER_COMPONENT_INDETERMINATE_NOT_INVENTED"
    assert pair["unknown_order_is_total_order"] is False


def test_similarity_symmetric_if_method_requires():
    a = _variant("a", action="PASS", outcome="CONTINUATION", team="A")
    b = _variant("b", action="CARRY", outcome="LOSS", team="B")
    first = _pair(build_trace_similarity_primitive(_payload(a, b)))
    second = _pair(build_trace_similarity_primitive(_payload(b, a)))
    assert first["similarity_vector"] == second["similarity_vector"]
    assert first["method_is_symmetric"] is True
    assert second["method_is_symmetric"] is True


def test_similarity_versioned():
    result = build_trace_similarity_primitive(_payload())
    pair = _pair(result)
    assert result["method_version"] == METHOD_VERSION == "TRACE_SIMILARITY_PRIMITIVE_V1.0.0"
    assert pair["method_version"] == METHOD_VERSION


def test_weight_sensitivity_available():
    unweighted = _pair(build_trace_similarity_primitive(_payload()))
    weighted = _pair(build_trace_similarity_primitive(_payload(), weights={"action": 2, "outcome": 1}))
    assert unweighted["composite_similarity"] is None
    assert unweighted["composite_state"] == "NOT_COMPUTED_EXPLICIT_WEIGHTS_REQUIRED"
    assert weighted["composite_similarity"] is not None
    assert weighted["weights"] == {"action": 0.666667, "outcome": 0.333333}
    assert weighted["weight_sensitivity_available"] is True
    assert weighted["weights_are_universal_football_truth"] is False


def test_no_tracking_feature_in_event_only_default():
    result = build_trace_similarity_primitive(_payload())
    pair = _pair(result)
    assert result["tracking_feature_used"] is False
    assert result["video_feature_used"] is False
    assert pair["tracking_feature_used"] is False
    assert pair["video_feature_used"] is False


def test_upstream_review_required_is_preserved():
    result = build_trace_similarity_primitive(_payload(status="REVIEW_REQUIRED"))
    assert result["status"] == "REVIEW_REQUIRED"
    assert "partial_order_variant_upstream_review_required" in result["review_hits"]


def test_same_time_policy_breach_fails_closed():
    payload = _payload()
    payload["same_timestamp_internal_ordering_allowed"] = True
    result = build_trace_similarity_primitive(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "same_timestamp_policy_breached" in result["hard_block_hits"]


def test_negative_weight_fails_closed():
    result = build_trace_similarity_primitive(_payload(), weights={"action": -1})
    assert result["status"] == "FAIL_CLOSED"
    assert "negative_similarity_weight:action" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/trace_similarity_primitive_lite/src/trace_similarity_primitive.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
