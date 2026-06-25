import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "axis_integrity_tagger_lite" / "src"
sys.path.insert(0, str(SRC))

from axis_integrity_tagger import AVAILABLE, MISSING, build_axis_report, write_outputs


def dump(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def seed(path: Path):
    dump(path / "time_scale_router_lite_v1.json", {"routed_window_count": 2, "minute_axis_window_count": 2, "event_index_window_count": 0})
    dump(path / "event_window_builder_lite_v1.json", {"event_window_count": 2, "event_windows_sample": [{"window_id": "w1", "window_axis": "minute", "start_minute": 0, "end_minute": 5}]})
    dump(path / "minimum_viable_context_lite_v1.json", {"context_candidates_sample": [{"second_raw": "20", "zone_candidate": "MIDDLE_THIRD", "team_label": "A", "action_family": "PASS"}]})


def test_detects_available_minute_axis(tmp_path):
    seed(tmp_path)
    report = build_axis_report(tmp_path)
    assert report["axis_status"]["minute_axis_status"] == AVAILABLE
    assert report["downstream_permissions"]["downstream_time_allowed"] is True


def test_marks_missing_time_axis_as_not_allowed(tmp_path):
    dump(tmp_path / "time_scale_router_lite_v1.json", {"routed_window_count": 0, "minute_axis_window_count": 0, "event_index_window_count": 0})
    dump(tmp_path / "event_window_builder_lite_v1.json", {"event_window_count": 1, "event_windows_sample": [{"window_id": "w1", "window_axis": "event_index", "start_index": 0, "end_index": 100}]})
    dump(tmp_path / "minimum_viable_context_lite_v1.json", {"context_candidates_sample": [{"zone_candidate": "MIDDLE_THIRD", "team_label": "A", "action_family": "PASS"}]})
    report = build_axis_report(tmp_path)
    assert report["axis_status"]["minute_axis_status"] == MISSING
    assert report["downstream_permissions"]["downstream_time_allowed"] is False


def test_detects_space_team_action_axes(tmp_path):
    seed(tmp_path)
    report = build_axis_report(tmp_path)
    assert report["axis_status"]["space_axis_status"] == AVAILABLE
    assert report["axis_status"]["team_axis_status"] == AVAILABLE
    assert report["axis_status"]["action_family_axis_status"] == AVAILABLE


def test_claim_boundaries_remain_false(tmp_path):
    seed(tmp_path)
    report = build_axis_report(tmp_path)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["phase_truth"] is False
    assert report["possession_truth"] is False
    assert report["sequence_truth"] is False
    assert report["rhythm_truth"] is False
    assert report["claim_allowed"] is False


def test_flat_phone_outputs(tmp_path):
    seed(tmp_path)
    out = tmp_path / "HPFA"
    out.mkdir()
    report = write_outputs(tmp_path, out, root=ROOT)
    assert (out / "axis_integrity_tagger_lite_v1.json").exists()
    assert (out / "axis_integrity_tagger_lite_v1.txt").exists()
    assert report["claim_safety"] == "AXIS_INTEGRITY_CANDIDATE_ONLY"


def test_no_sample_match_identity_leak():
    src = (SRC / "axis_integrity_tagger.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "axis_integrity_tagger_lite_v1.md").read_text(encoding="utf-8")
    root_cli = (ROOT / "axis_integrity_tagger.py").read_text(encoding="utf-8")
    for token in ["sample_match_identity_token"]:
        assert token not in src
        assert token not in contract
        assert token not in root_cli
