from pathlib import Path

from hpfa.modules.core.trace_contrast_packet_lite.src.trace_contrast_packet import (
    build_trace_contrast_packets,
)


def _variant(variant_id: str, outcome: str, *, dependency="dep:a"):
    return {
        "trace_variant_id": variant_id,
        "context_signature": {"team_identity_candidate_id": "A", "period_candidate": "1"},
        "outcome_signature": [{"outcome_candidate": outcome, "count": 1}],
        "dependency_group_refs": [dependency],
        "provenance_refs": [f"prov:{variant_id}"],
    }


def _variant_payload(rows, *, status="PASS"):
    return {
        "module_id": "partial_order_trace_variant_lite_v1",
        "status": status,
        "partial_order_trace_variants": rows,
        "partial_order_trace_variant_count": len(rows),
        "hard_block_hits": [],
        "review_hits": ["upstream"] if status == "REVIEW_REQUIRED" else [],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _pair(a, b, *, action=1.0, order=1.0, context=1.0, outcome=1.0):
    return {
        "trace_a_ref": a,
        "trace_b_ref": b,
        "action_similarity": action,
        "order_similarity": order,
        "context_similarity": context,
        "outcome_similarity": outcome,
    }


def _similarity_payload(pairs, *, status="PASS"):
    return {
        "module_id": "trace_similarity_primitive_lite_v1",
        "status": status,
        "trace_similarity_pairs": pairs,
        "trace_similarity_pair_count": len(pairs),
        "hard_block_hits": [],
        "review_hits": [],
        "method_version": "TRACE_SIMILARITY_PRIMITIVE_V1.0.0",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _build(rows, pairs, **kwargs):
    return build_trace_contrast_packets(
        _variant_payload(rows),
        _similarity_payload(pairs),
        minimum_similarity=kwargs.get("minimum_similarity", 0.8),
        eligibility_weights=kwargs.get("eligibility_weights", {"action": 1, "order": 1, "context": 1}),
    )


def test_no_visible_followup_not_failure():
    rows = [
        _variant("a", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
        _variant("b", "NO_VISIBLE_FOLLOW_UP_CANDIDATE"),
    ]
    result = _build(rows, [_pair("a", "b")])
    packet = result["trace_contrast_packets"][0]
    assert packet["failure_count"] == 0
    assert packet["no_visible_followup_count"] == 1
    assert packet["no_visible_followup_refs"] == ["b"]
    assert result["no_visible_followup_is_failure"] is False


def test_failure_requires_explicit_visible_outcome():
    rows = [
        _variant("a", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
        _variant("b", "OPPONENT_HANDOVER_CANDIDATE"),
    ]
    packet = _build(rows, [_pair("a", "b")])["trace_contrast_packets"][0]
    assert packet["failure_count"] == 1
    assert packet["failed_trace_refs"] == ["b"]
    assert packet["variant_distribution"]["LOSS_TERMINATION"] == 1


def test_success_failure_share_eligibility_contract():
    rows = [
        _variant("a", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
        _variant("b", "OPPONENT_HANDOVER_CANDIDATE"),
        _variant("c", "SAME_TEAM_CONTINUATION_CANDIDATE"),
    ]
    pairs = [
        _pair("a", "b", action=0.9, order=0.9, context=0.9, outcome=0.0),
        _pair("a", "c", action=0.7, order=0.7, context=0.7, outcome=1.0),
        _pair("b", "c", action=0.7, order=0.7, context=0.7, outcome=0.0),
    ]
    result = _build(rows, pairs, minimum_similarity=0.8)
    packet = next(row for row in result["trace_contrast_packets"] if row["anchor_trace_family"] == "a")
    assert packet["eligible_trace_refs"] == ["a", "b"]
    assert packet["similarity_parameters"]["outcome_similarity_used_for_eligibility"] is False
    assert result["success_failure_share_eligibility_contract"] is True


def test_dependent_reflections_not_independent_support():
    rows = [
        _variant("a", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE", dependency="reflection:same"),
        _variant("b", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE", dependency="reflection:same"),
    ]
    packet = _build(rows, [_pair("a", "b")])["trace_contrast_packets"][0]
    assert packet["dependency_groups"] == ["reflection:same"]
    assert packet["independence_groups"] == []
    assert packet["independent_support_count"] == "UNKNOWN"


def test_counterevidence_preserved_in_packet():
    rows = [
        _variant("a", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
        _variant("b", "OPPONENT_HANDOVER_CANDIDATE"),
        _variant("c", "SAME_TEAM_CONTINUATION_CANDIDATE"),
    ]
    pairs = [_pair("a", "b"), _pair("a", "c"), _pair("b", "c")]
    packet = _build(rows, pairs)["trace_contrast_packets"][0]
    assert set(packet["counterevidence_refs"]) == {"b", "c"}


def test_trace_contrast_does_not_claim_causality():
    rows = [_variant("a", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"), _variant("b", "OPPONENT_HANDOVER_CANDIDATE")]
    result = _build(rows, [_pair("a", "b")])
    assert result["trace_contrast_does_not_claim_causality"] is True
    assert result["production_release"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"


def test_missing_comparator_fails_closed():
    rows = [
        _variant("a", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
        _variant("b", "OPPONENT_HANDOVER_CANDIDATE"),
        _variant("c", "SAME_TEAM_CONTINUATION_CANDIDATE"),
    ]
    result = _build(rows, [_pair("a", "b"), _pair("a", "c")])
    assert result["status"] == "FAIL_CLOSED"
    assert "missing_similarity_comparator_pairs" in result["hard_block_hits"]


def test_outcome_weight_for_eligibility_fails_closed():
    rows = [_variant("a", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"), _variant("b", "OPPONENT_HANDOVER_CANDIDATE")]
    result = _build(rows, [_pair("a", "b")], eligibility_weights={"action": 1, "outcome": 1})
    assert result["status"] == "FAIL_CLOSED"
    assert "eligibility_component_forbidden:outcome" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/trace_contrast_packet_lite/src/trace_contrast_packet.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
