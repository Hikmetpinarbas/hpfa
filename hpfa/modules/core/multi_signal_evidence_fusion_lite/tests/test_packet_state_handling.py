import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "multi_signal_evidence_fusion_lite" / "src"
sys.path.insert(0, str(SRC))

from multi_signal_evidence_fusion import fuse_packet


def packet_fixture():
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


def test_fail_closed_status_stops_relation_creation():
    packet = packet_fixture()
    packet["status"] = "FAIL_CLOSED"
    record = fuse_packet(packet)
    assert record["decision"] == "BLOCK_FUSION"
    assert record["fusion_status"] == "BLOCKED"
    assert "upstream_composite_packet_failed_closed" in record["hard_block_hits"]
    assert record["relation_records"] == []


def test_block_decision_stops_relation_creation():
    packet = packet_fixture()
    packet["decision"] = "BLOCK_PACKET"
    record = fuse_packet(packet)
    assert record["decision"] == "BLOCK_FUSION"
    assert "upstream_composite_packet_failed_closed" in record["hard_block_hits"]
    assert record["relation_records"] == []


def test_upstream_hard_blocks_stop_signal_counts():
    packet = packet_fixture()
    packet["hard_block_hits"] = ["minimum_two_sources_required"]
    record = fuse_packet(packet)
    assert record["decision"] == "BLOCK_FUSION"
    assert record["support_signal_count"] == 0
    assert record["qualifier_signal_count"] == 0


def test_nested_forbidden_output_stops_fusion():
    packet = packet_fixture()
    packet["supporting_signals"] = [
        {"signal_id": "unsafe_signal", "payload": {"tactical_truth": True}}
    ]
    record = fuse_packet(packet)
    assert record["decision"] == "BLOCK_FUSION"
    assert record["relation_records"] == []
    assert record["forbidden_output_hits"] == [
        "supporting_signals[0].payload.tactical_truth"
    ]


def test_error_status_stops_relation_creation():
    packet = packet_fixture()
    packet["status"] = "ERROR"
    record = fuse_packet(packet)
    assert record["decision"] == "BLOCK_FUSION"
    assert "upstream_composite_packet_failed_closed" in record["hard_block_hits"]


def test_empty_hard_block_container_does_not_block_valid_packet():
    packet = packet_fixture()
    packet["hard_block_hits"] = []
    record = fuse_packet(packet)
    assert record["decision"] == "READY_FOR_ARGUMENT_WITH_QUALIFIER"
    packet["hard_block_hits"] = False
    record = fuse_packet(packet)
    assert record["decision"] == "READY_FOR_ARGUMENT_WITH_QUALIFIER"

