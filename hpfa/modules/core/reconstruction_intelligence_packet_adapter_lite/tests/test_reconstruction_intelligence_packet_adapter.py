from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.composite_evidence_packet_builder_lite.src import composite_evidence_packet_builder as packet_builder
from hpfa.modules.core.multi_signal_evidence_fusion_lite.src import multi_signal_evidence_fusion as fusion
from hpfa.modules.core.reconstruction_intelligence_packet_adapter_lite.src import reconstruction_intelligence_packet_adapter as adapter


def _layer(layer_id: str, start: float = 10.0) -> dict:
    return {
        "visible_action_time_layer_candidate_id": layer_id,
        "match_surface_binding_id": "binding_generic",
        "period_candidate": "1",
        "start_candidate": start,
        "layer_state": "SINGLE_TEAM_PRIMARY_LAYER",
        "same_timestamp_internal_ordering_allowed": False,
        "time_layer_is_event_group_truth": False,
        "time_layer_is_sequence_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def _sequence(status: str = "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE", review_count: int = 0) -> dict:
    return {
        "visible_action_sequence_candidate_id": "sequence_candidate_alpha",
        "match_surface_binding_id": "binding_generic",
        "team_identity_candidate_id": "team_candidate_alpha",
        "period_candidate": "1",
        "start_time_candidate": 10.0,
        "end_time_candidate": 15.0,
        "duration_candidate_seconds": 5.0,
        "time_layer_candidate_ids": ["layer_alpha", "layer_beta"],
        "time_layer_count": 2,
        "trackable_action_trace_candidate_ids": ["trace_alpha", "trace_beta"],
        "trace_candidate_count": 2,
        "action_family_counts": {"PASS": 2},
        "consequence_candidate_counts": {"SAME_TEAM_CONTINUATION_CANDIDATE": 1},
        "consequence_review_trace_count": review_count,
        "reflection_context_trace_count": 1,
        "sequence_record_status": status,
        "start_reason_candidate": "PERIOD_START",
        "end_reason_candidate": "TIME_GAP_BOUNDARY",
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "single_team_continuity_is_control_truth": False,
        "sequence_duration_is_physical_action_duration": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "VISIBLE_SEQUENCE_CANDIDATE_ONLY",
    }


def _payload(status: str = "PASS", sequence_status: str = "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE", review_count: int = 0) -> dict:
    return {
        "module_id": "visible_action_sequence_candidates_lite_v1",
        "status": status,
        "module_status": status,
        "match_surface_binding_id": "binding_generic",
        "visible_action_time_layer_candidates": [_layer("layer_alpha", 10.0), _layer("layer_beta", 15.0)],
        "visible_action_time_layer_candidate_count": 2,
        "visible_action_sequence_candidates": [_sequence(sequence_status, review_count)],
        "visible_action_sequence_candidate_count": 1,
        "hard_block_hits": [],
        "review_hits": [],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "single_team_continuity_is_control_truth": False,
        "sequence_duration_is_physical_action_duration": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_clean_reconstruction_maps_to_packet_builder_and_fusion() -> None:
    adapted = adapter.build_packet_input_candidates(_payload())
    assert adapted["status"] == "SMOKE_PASS"
    assert adapted["packet_input_assignment_complete"] is True
    assert adapted["packet_input_candidate_count"] == 1
    assert adapted["independent_support_vote_allowed"] is False

    packet_report = packet_builder.build_report(adapted["composite_packet_input_candidates"])
    assert packet_report["status"] == "SMOKE_PASS"
    packet = packet_report["packets"][0]
    assert packet["packet_family"] == "sequence"
    assert packet["claim_ceiling"] == "composite_candidate_only"
    assert packet["canonical_event_count"] == "UNKNOWN"
    assert packet["source_surface_count"] == 1

    fused = fusion.fuse_packet(packet)
    assert fused["hard_block_hits"] == []
    assert fused["support_signal_count"] == 1
    assert fused["context_signal_count"] == 2
    assert fused["contradiction_signal_count"] == 0
    assert fused["canonical_event_count"] == "UNKNOWN"


def test_review_required_sequence_becomes_qualifier_not_contradiction() -> None:
    adapted = adapter.build_packet_input_candidates(
        _payload(status="REVIEW_REQUIRED", sequence_status="REVIEW_REQUIRED_CONTEXT", review_count=1)
    )
    assert adapted["status"] == "REVIEW_REQUIRED"
    assert adapted["review_required_packet_input_candidate_count"] == 1

    packet = packet_builder.build_report(adapted["composite_packet_input_candidates"])["packets"][0]
    fused = fusion.fuse_packet(packet)
    assert fused["qualifier_signal_count"] == 1
    assert fused["contradiction_signal_count"] == 0
    assert fused["fusion_status"] == "SUPPORTED_WITH_QUALIFIER"


def test_upstream_hard_block_fails_closed_without_partial_packet_output() -> None:
    payload = _payload()
    payload["hard_block_hits"] = ["upstream_contract_failure"]
    adapted = adapter.build_packet_input_candidates(payload)
    assert adapted["status"] == "FAIL_CLOSED"
    assert adapted["packet_input_candidate_count"] == 0
    assert adapted["packet_input_assignment_complete"] is False
    assert "upstream_hard_blocks_present" in adapted["hard_block_hits"]


def test_truth_promotion_attempt_fails_closed() -> None:
    payload = _payload()
    payload["visible_action_sequence_candidates"][0]["visible_sequence_candidate_is_sequence_truth"] = True
    adapted = adapter.build_packet_input_candidates(payload)
    assert adapted["status"] == "FAIL_CLOSED"
    assert any("visible_sequence_candidate_is_sequence_truth" in hit for hit in adapted["hard_block_hits"])


def test_same_timestamp_internal_ordering_attempt_fails_closed() -> None:
    payload = _payload()
    payload["visible_action_time_layer_candidates"][0]["same_timestamp_internal_ordering_allowed"] = True
    adapted = adapter.build_packet_input_candidates(payload)
    assert adapted["status"] == "FAIL_CLOSED"
    assert any("same_timestamp_internal_ordering_allowed" in hit for hit in adapted["hard_block_hits"])


def test_sequence_count_mismatch_fails_closed() -> None:
    payload = _payload()
    payload["visible_action_sequence_candidate_count"] = 2
    adapted = adapter.build_packet_input_candidates(payload)
    assert adapted["status"] == "FAIL_CLOSED"
    assert "visible_action_sequence_candidate_count_mismatch" in adapted["hard_block_hits"]


def test_dependent_reconstruction_refs_are_never_independent_votes() -> None:
    adapted = adapter.build_packet_input_candidates(_payload())
    candidate = adapted["composite_packet_input_candidates"][0]
    assert candidate["derived_reconstruction_refs_are_independent_sources"] is False
    assert candidate["independent_support_vote_allowed"] is False
    assert candidate["supporting_signals"][0]["independent_support_vote"] is False
    assert all(window["independent_support_vote"] is False for window in candidate["input_windows"])
    assert candidate["input_sequences"][0]["independent_support_vote"] is False


def test_no_sample_match_identity_leak() -> None:
    root = Path(__file__).resolve().parents[5]
    production_files = [
        root / "hpfa/modules/core/reconstruction_intelligence_packet_adapter_lite/src/reconstruction_intelligence_packet_adapter.py",
        root / "reconstruction_intelligence_packet_adapter_current_v1.py",
        root / "tools/bootstrap_termux_reconstruction_intelligence_packet_adapter_current_v1.sh",
    ]
    forbidden_tokens = (
        "Fenerbahce",
        "Genclerbirligi",
        "Galatasaray",
        "Besiktas",
        "15.08.2026",
        "18.08.2026",
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in production_files)
    assert not any(token in text for token in forbidden_tokens)
