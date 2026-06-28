from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "match_context_slicer_lite" / "src"
sys.path.insert(0, str(SRC))

import match_context_slicer  # type: ignore


def write_inputs(root: Path) -> None:
    (root / "minimum_viable_context_lite_v1.json").write_text(json.dumps({
        "module_id": "minimum_viable_context_lite_v1",
        "status": "REVIEW_REQUIRED",
        "context_candidate_count": 3,
        "context_candidates_sample": [
            {
                "context_id": "ctx_000000",
                "source_file": "canonical_event_lite_v1.tsv",
                "source_format": "tsv",
                "source_row_index": 0,
                "team_label": "turkey",
                "action_family": "PASS",
                "minute_bucket": "unknown",
                "period": "unknown",
                "zone_candidate": "MIDDLE_THIRD",
                "channel_candidate": "CENTRAL_CHANNEL",
                "previous_action_family": "UNKNOWN_PREVIOUS_ACTION",
                "next_action_family": "RESTART",
            },
            {
                "context_id": "ctx_000001",
                "source_file": "canonical_event_lite_v1.tsv",
                "source_format": "tsv",
                "source_row_index": 1,
                "team_label": "united states",
                "action_family": "RESTART",
                "minute_bucket": "unknown",
                "period": "unknown",
                "zone_candidate": "DEFENSIVE_THIRD",
                "channel_candidate": "LEFT_CHANNEL",
                "previous_action_family": "PASS",
                "next_action_family": "SHOT",
            },
            {
                "context_id": "ctx_000002",
                "source_file": "canonical_event_lite_v1.tsv",
                "source_format": "tsv",
                "source_row_index": 2,
                "team_label": "turkey",
                "action_family": "SHOT",
                "minute_bucket": "unknown",
                "period": "unknown",
                "zone_candidate": "FINAL_THIRD",
                "channel_candidate": "RIGHT_CHANNEL",
                "previous_action_family": "RESTART",
                "next_action_family": "UNKNOWN_NEXT_ACTION",
            },
        ],
    }), encoding="utf-8")
    (root / "event_window_builder_lite_v1.json").write_text(json.dumps({
        "module_id": "event_window_builder_lite_v1",
        "status": "REVIEW_REQUIRED",
        "event_window_count": 1,
        "event_windows_sample": [
            {"window_id": "idxwin_0000", "window_axis": "event_index", "start_index": 0, "end_index": 100}
        ],
    }), encoding="utf-8")


def test_context_slicer_reads_minimum_context(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "CONTEXT_SLICES_CANDIDATE_ONLY"
    assert report["context_slice_count"] == 3


def test_context_slicer_reads_event_windows(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["context_slices_sample"][0]["window_id"] == "idxwin_0000"
    assert report["context_slices_sample"][0]["window_axis"] == "event_index"


def test_team_slice_candidates(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["slice_summary"]["team_label_counts"] == {"turkey": 2, "united states": 1}


def test_half_candidate_unknown_when_time_missing(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["slice_summary"]["half_candidate_counts"] == {"UNKNOWN_HALF": 3}


def test_score_state_candidate_unknown_without_goal_timeline(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["slice_summary"]["score_state_candidate_counts"] == {"UNKNOWN_SCORE_STATE": 3}


def test_card_state_candidate_unknown_without_card_timeline(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["slice_summary"]["card_state_candidate_counts"] == {"UNKNOWN_CARD_STATE": 3}


def test_restart_open_play_candidate_from_action_family(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    counts = report["slice_summary"]["restart_open_play_candidate_counts"]
    assert counts["OPEN_PLAY_CANDIDATE"] == 2
    assert counts["RESTART_OR_DEAD_BALL_CANDIDATE"] == 1


def test_no_phase_possession_sequence_truth(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["phase_truth"] is False
    assert report["possession_truth"] is False
    assert report["sequence_truth"] is False


def test_no_tactical_or_dominance_claims(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["tactical_truth"] is False
    assert report["dominance_truth"] is False
    assert all(row["claim_allowed"] is False for row in report["context_slices_sample"])


def test_missing_required_inputs_fail_closed(tmp_path: Path) -> None:
    report = match_context_slicer.build_report(tmp_path, root=ROOT)
    assert report["status"] == "FAIL_CLOSED"
    assert report["decision"] == "FAIL_CLOSED_MISSING_REQUIRED_INPUTS"
    assert "minimum_viable_context_lite_v1.json" in report["missing_required_inputs"]


def test_flat_phone_outputs(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    out_dir = tmp_path / "out"
    report = match_context_slicer.write_outputs(tmp_path, out_dir, root=ROOT)
    assert Path(report["outputs"]["json"]).exists()
    assert Path(report["outputs"]["txt"]).exists()


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        match_context_slicer.write_outputs(tmp_path, "/sdcard/Download/HPFA/nested", root=ROOT)
