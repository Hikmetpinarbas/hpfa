import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "multi_signal_evidence_fusion_lite" / "src"
sys.path.insert(0, str(SRC))

from multi_signal_evidence_fusion import build_fusion_report, fuse_packet, write_outputs


def base_packet():
    return {
        "packet_id": "cep_progression_001",
        "packet_family": "progression",
        "input_features": ["final_third_entry", "box_entry"],
        "input_windows": ["window_001"],
        "input_sequences": ["sequence_001"],
        "input_metrics": ["terminal_action_count"],
        "supporting_signals": ["right_channel_access"],
        "contradicting_signals": ["low_shot_volume"],
        "claim_ceiling": "composite_candidate_only",
        "claim_output_allowed": False,
        "report_language_allowed": False,
    }


def test_fusion_requires_composite_packet():
    record = fuse_packet({"packet_id": "broken"})
    assert record["decision"] == "BLOCK_FUSION"
    assert "composite_packet_required_fields_missing" in record["hard_block_hits"]


def test_fusion_records_signal_sources():
    record = fuse_packet(base_packet())
    signal_refs = {row["signal_ref"] for row in record["relation_records"]}
    assert "right_channel_access" in signal_refs
    assert "low_shot_volume" in signal_refs
    assert "final_third_entry" in signal_refs
    assert "window_001" in signal_refs


def test_fusion_detects_support_relation():
    record = fuse_packet(base_packet())
    assert record["support_signal_count"] == 1
    assert any(row["relation_type"] == "SUPPORTS" for row in record["relation_records"])


def test_fusion_detects_contradiction_relation():
    record = fuse_packet(base_packet())
    assert record["contradiction_signal_count"] == 1
    assert record["fusion_status"] == "MIXED_WITH_CONTRADICTION"
    assert any(row["relation_type"] == "CONTRADICTS" for row in record["relation_records"])


def test_fusion_preserves_contextualizes_relation():
    record = fuse_packet(base_packet())
    assert record["context_signal_count"] == 1
    assert any(row["relation_type"] == "CONTEXTUALIZES" for row in record["relation_records"])


def test_fusion_does_not_emit_claim_text():
    record = fuse_packet(base_packet())
    assert "claim_text" not in record
    assert "safe_sentence" not in record
    assert record["claim_output_allowed"] is False
    assert record["report_language_allowed"] is False


def test_fusion_preserves_candidate_only_claim_ceiling():
    record = fuse_packet(base_packet())
    assert record["upstream_claim_ceiling"] == "composite_candidate_only"
    assert record["claim_ceiling"] == "fusion_relation_candidate_only"


def test_non_candidate_upstream_claim_ceiling_blocks_fusion():
    packet = base_packet()
    packet["claim_ceiling"] = "claim_text_allowed"
    record = fuse_packet(packet)
    assert record["decision"] == "BLOCK_FUSION"
    assert "upstream_packet_claim_ceiling_not_candidate_only" in record["hard_block_hits"]


def test_forbidden_upstream_output_blocks_fusion():
    packet = base_packet()
    packet["claim_text"] = "unsafe text"
    record = fuse_packet(packet)
    assert record["decision"] == "BLOCK_FUSION"
    assert "upstream_packet_forbidden_output_attempted" in record["hard_block_hits"]
    assert "claim_text" in record["forbidden_output_hits"]


def test_no_tactical_truth():
    record = fuse_packet(base_packet())
    assert record["tactical_truth"] is False
    assert record["dominance_truth"] is False
    assert record["control_truth"] is False
    assert record["coach_intention_truth"] is False
    assert record["off_ball_truth"] is False
    assert record["pitch_control_truth"] is False
    assert record["causal_truth"] is False


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_packet()], "/sdcard/Download/HPFA/multi_signal_evidence_fusion_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_packet()], tmp_path)
    assert report["module_id"] == "multi_signal_evidence_fusion_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert (tmp_path / "multi_signal_evidence_fusion_lite_v1.json").exists()
    assert (tmp_path / "multi_signal_evidence_fusion_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "multi_signal_evidence_fusion_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["fusion_record_count"] == 1


def test_no_sample_match_identity_leak():
    src = (SRC / "multi_signal_evidence_fusion.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
