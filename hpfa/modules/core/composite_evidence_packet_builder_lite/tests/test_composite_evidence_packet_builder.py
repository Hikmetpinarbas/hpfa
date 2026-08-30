import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "composite_evidence_packet_builder_lite" / "src"
sys.path.insert(0, str(SRC))

from composite_evidence_packet_builder import build_composite_packet, build_report, write_outputs


def base_candidate():
    return {
        "packet_family": "progression",
        "input_features": [
            {"feature_id": "final_third_entry", "source_surface": "feature_primitive_registry_lite_v1"},
            {"feature_id": "box_entry", "source_surface": "feature_primitive_registry_lite_v1"},
        ],
        "input_windows": [{"window_id": "window_001", "source_surface": "event_window_builder_lite_v1"}],
        "input_metrics": [{"metric_id": "terminal_action_count", "source_surface": "metric_candidate_governance_lite_v1"}],
        "supporting_signals": [{"signal_id": "right_channel_access", "source_surface": "minimum_viable_context_lite_v1"}],
        "contradicting_signals": [{"signal_id": "low_shot_volume", "source_surface": "active_match_analyst_report_lite_v1"}],
        "claim_ceiling": "composite_candidate_only",
    }


def test_composite_packet_requires_minimum_two_sources():
    packet = build_composite_packet({
        "packet_family": "progression",
        "input_features": [{"feature_id": "final_third_entry"}],
        "claim_ceiling": "composite_candidate_only",
    })
    assert packet["status"] == "FAIL_CLOSED"
    assert "minimum_two_sources_required" in packet["hard_block_hits"]


def test_packet_preserves_all_evidence_refs():
    packet = build_composite_packet(base_candidate())
    assert "final_third_entry" in packet["input_features"]
    assert "box_entry" in packet["input_features"]
    assert "window_001" in packet["input_windows"]
    assert "terminal_action_count" in packet["input_metrics"]
    assert "right_channel_access" in packet["supporting_signals"]
    assert "low_shot_volume" in packet["contradicting_signals"]


def test_packet_has_support_and_contradiction_slots():
    packet = build_composite_packet(base_candidate())
    assert "supporting_signals" in packet
    assert "contradicting_signals" in packet
    assert packet["supporting_signal_count"] == 1
    assert packet["contradicting_signal_count"] == 1


def test_single_signal_cannot_create_composite_argument():
    packet = build_composite_packet({
        "packet_family": "risk",
        "supporting_signals": [{"signal_id": "loss_cluster"}],
        "claim_ceiling": "composite_candidate_only",
    })
    assert packet["decision"] == "BLOCK_PACKET"
    assert "single_signal_cannot_create_composite_argument" in packet["hard_block_hits"]


def test_packet_claim_ceiling_candidate_only():
    packet = build_composite_packet(base_candidate())
    assert packet["claim_ceiling"] == "composite_candidate_only"
    assert packet["claim_output_allowed"] is False
    assert packet["report_language_allowed"] is False
    assert packet["canonical_event_count"] == "UNKNOWN"


def test_non_candidate_claim_ceiling_fails_closed():
    candidate = base_candidate()
    candidate["claim_ceiling"] = "claim_text_allowed"
    packet = build_composite_packet(candidate)
    assert packet["status"] == "FAIL_CLOSED"
    assert "non_candidate_claim_ceiling_rejected" in packet["hard_block_hits"]


def test_blocked_language_families_cannot_be_shortened():
    candidate = base_candidate()
    candidate["blocked_language_families"] = ["tactical_truth"]
    packet = build_composite_packet(candidate)
    for required in ["tactical_truth", "dominance_truth", "control_truth", "coach_intention", "off_ball_truth", "pitch_control_truth"]:
        assert required in packet["blocked_language_families"]


def test_no_tactical_truth():
    packet = build_composite_packet(base_candidate())
    assert packet["tactical_truth"] is False
    assert packet["dominance_truth"] is False
    assert packet["control_truth"] is False
    assert packet["coach_intention_truth"] is False
    assert packet["off_ball_truth"] is False
    assert packet["pitch_control_truth"] is False
    assert "tactical_truth" in packet["blocked_language_families"]
    assert "dominance_truth" in packet["blocked_language_families"]
    assert "control_truth" in packet["blocked_language_families"]


def test_no_dominance_control_language():
    packet = build_composite_packet(base_candidate())
    assert packet["dominance_truth"] is False
    assert packet["control_truth"] is False
    assert "dominance_truth" in packet["blocked_language_families"]
    assert "control_truth" in packet["blocked_language_families"]


def test_forbidden_output_attempt_blocks_packet():
    candidate = base_candidate()
    candidate["claim_text"] = "unsafe claim attempt"
    packet = build_composite_packet(candidate)
    assert packet["status"] == "FAIL_CLOSED"
    assert "forbidden_output_attempted" in packet["hard_block_hits"]
    assert "claim_text" in packet["forbidden_output_hits"]


def test_nested_feature_claim_text_blocks_packet_with_path():
    candidate = base_candidate()
    candidate["input_features"][0]["claim_text"] = "unsafe nested claim"
    packet = build_composite_packet(candidate)
    assert packet["status"] == "FAIL_CLOSED"
    assert "forbidden_output_attempted" in packet["hard_block_hits"]
    assert "input_features[0].claim_text" in packet["forbidden_output_hits"]


def test_nested_signal_truth_blocks_packet_with_path():
    candidate = base_candidate()
    candidate["supporting_signals"][0]["payload"] = {"tactical_truth": True}
    packet = build_composite_packet(candidate)
    assert packet["status"] == "FAIL_CLOSED"
    assert "supporting_signals[0].payload.tactical_truth" in packet["forbidden_output_hits"]


def test_nominal_refs_do_not_become_independent_support_by_default():
    packet = build_composite_packet(base_candidate())
    assert packet["status"] == "SMOKE_PASS"
    assert packet["nominal_ref_count"] >= 2
    assert packet["independent_support_count"] == 0
    assert packet["independence_state"] == "INDEPENDENCE_NOT_ADMITTED"
    assert packet["nominal_ref_count_is_independent_support_count"] is False
    assert packet["evidence_strength"] == "weak"


def test_same_provenance_root_does_not_multiply_independent_support():
    candidate = base_candidate()
    candidate["supporting_signals"] = [
        {
            "signal_id": "support_a",
            "source_surface": "surface_a",
            "provenance_root": "root_same_fact",
            "dependency_group": "dep_same_fact",
            "independence_group": "ind_a",
            "independent_support_vote": True,
        },
        {
            "signal_id": "support_b",
            "source_surface": "surface_b",
            "provenance_root": "root_same_fact",
            "dependency_group": "dep_same_fact",
            "independence_group": "ind_b",
            "independent_support_vote": True,
        },
    ]
    packet = build_composite_packet(candidate)
    assert packet["status"] == "SMOKE_PASS"
    assert packet["independent_support_count"] == 1
    assert packet["independent_support_provenance_roots"] == ["root_same_fact"]


def test_independent_support_claim_requires_complete_lineage_metadata():
    candidate = base_candidate()
    candidate["supporting_signals"] = [
        {
            "signal_id": "unsupported_independence_claim",
            "source_surface": "surface_a",
            "independent_support_vote": True,
            "provenance_root": "root_a",
        }
    ]
    packet = build_composite_packet(candidate)
    assert packet["status"] == "FAIL_CLOSED"
    assert "independent_support_claim_not_proven" in packet["hard_block_hits"]
    assert packet["invalid_independence_claims"] == [
        "independent_support_metadata_incomplete:supporting_signals:unsupported_independence_claim"
    ]


def test_distinct_provenance_roots_can_be_counted_without_becoming_truth_probability():
    candidate = base_candidate()
    candidate["supporting_signals"] = [
        {
            "signal_id": "support_a",
            "source_surface": "surface_a",
            "provenance_root": "root_a",
            "dependency_group": "dep_a",
            "independence_group": "ind_a",
            "independent_support_vote": True,
        },
        {
            "signal_id": "support_b",
            "source_surface": "surface_b",
            "provenance_root": "root_b",
            "dependency_group": "dep_b",
            "independence_group": "ind_b",
            "independent_support_vote": True,
        },
    ]
    packet = build_composite_packet(candidate)
    assert packet["status"] == "SMOKE_PASS"
    assert packet["independent_support_count"] == 2
    assert packet["evidence_strength"] in {"medium", "strong"}
    assert packet["evidence_strength_is_probability"] is False
    assert packet["claim_output_allowed"] is False


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_candidate()], "/sdcard/Download/HPFA/composite_evidence_packet_builder_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_candidate()], tmp_path)
    assert report["module_id"] == "composite_evidence_packet_builder_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert report["independent_support_count_total"] == 0
    assert (tmp_path / "composite_evidence_packet_builder_lite_v1.json").exists()
    assert (tmp_path / "composite_evidence_packet_builder_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "composite_evidence_packet_builder_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["packet_count"] == 1


def test_no_sample_match_identity_leak():
    src = (SRC / "composite_evidence_packet_builder.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
