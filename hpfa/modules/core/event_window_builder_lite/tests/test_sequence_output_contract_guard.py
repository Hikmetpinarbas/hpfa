import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "event_window_builder_lite" / "src"
sys.path.insert(0, str(SRC))

from sequence_output_contract_guard import build_sequence_output_contract


def base_report():
    return {
        "claim_safety": "EVENT_WINDOW_CANDIDATE_ONLY",
        "time_axis_status": "AVAILABLE",
        "index_window_enabled": True,
        "event_window_count": 1,
        "canonical_action_id_present": True,
        "event_windows_sample": [
            {
                "window_id": "win_0001",
                "window_axis": "minute",
                "team_label_counts": {"a": 2},
                "action_family_counts": {"PASS": 1, "SHOT": 1},
                "claim_boundary": "event_window_candidate_only",
            }
        ],
    }


def test_sequence_contract_requires_timestamp_or_order():
    report = base_report()
    report["time_axis_status"] = "MISSING"
    report["index_window_enabled"] = False
    report["event_windows_sample"][0]["window_axis"] = "unknown"
    contract = build_sequence_output_contract(report)
    assert "timestamp_or_order_missing" in contract["hard_block_hits"]
    assert contract["sequence_decision"] == "BLOCK_SEQUENCE_LAYER"


def test_sequence_contract_requires_team_or_side():
    report = base_report()
    report["event_windows_sample"][0]["team_label_counts"] = {"unknown": 3}
    contract = build_sequence_output_contract(report)
    assert "team_or_side_missing" in contract["hard_block_hits"]


def test_sequence_contract_requires_canonical_family():
    report = base_report()
    report["event_windows_sample"][0]["action_family_counts"] = {"UNKNOWN_OR_OTHER": 3}
    contract = build_sequence_output_contract(report)
    assert "canonical_family_missing" in contract["hard_block_hits"]


def test_sequence_contract_blocks_if_claim_ceiling_missing():
    report = base_report()
    report.pop("claim_safety")
    report["event_windows_sample"][0].pop("claim_boundary")
    contract = build_sequence_output_contract(report)
    assert "claim_ceiling_missing" in contract["hard_block_hits"]


def test_sequence_contract_requires_sequence_window_defined():
    report = base_report()
    report["event_window_count"] = 0
    report["event_windows_sample"] = []
    contract = build_sequence_output_contract(report)
    assert "sequence_window_not_defined" in contract["hard_block_hits"]


def test_sequence_contract_requires_canonical_action_id():
    report = base_report()
    report["canonical_action_id_present"] = False
    contract = build_sequence_output_contract(report)
    assert "canonical_action_id_missing" in contract["hard_block_hits"]


def test_sequence_contract_ready_when_required_fields_present():
    contract = build_sequence_output_contract(base_report())
    assert contract["hard_block_hits"] == []
    assert contract["sequence_decision"] == "READY_FOR_SEQUENCE_CANDIDATE_CONSUMER"


def test_sequence_contract_does_not_create_sequence_truth():
    contract = build_sequence_output_contract(base_report())
    assert contract["sequence_truth"] is False
    assert contract["consequence_truth"] is False
    assert contract["tactical_truth"] is False
    assert contract["dominance_truth"] is False
    assert contract["canonical_event_count"] == "UNKNOWN"


def test_sequence_contract_required_outputs_supported():
    contract = build_sequence_output_contract(base_report())
    assert "sequence_windows.csv" in contract["required_outputs_supported"]
    assert "sequence_decision.md" in contract["required_outputs_supported"]


def test_no_sample_match_identity_leak():
    src = (SRC / "sequence_output_contract_guard.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
