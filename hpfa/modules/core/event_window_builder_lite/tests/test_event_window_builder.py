import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "event_window_builder_lite" / "src"
sys.path.insert(0, str(SRC))

from event_window_builder import build_report, build_windows_from_context, write_outputs


def write_context(path: Path, contexts):
    path.write_text(json.dumps({
        "module_id": "minimum_viable_context_lite_v1",
        "context_candidate_count": len(contexts),
        "context_candidates_sample": contexts,
    }, ensure_ascii=False), encoding="utf-8")


def test_builds_windows_from_minimum_context_json(tmp_path):
    contexts = [
        {"minute_bucket": "1", "action_family": "PASS", "team_label": "a", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
        {"minute_bucket": "4", "action_family": "SHOT", "team_label": "a", "zone_candidate": "FINAL_THIRD", "channel_candidate": "RIGHT_CHANNEL"},
        {"minute_bucket": "6", "action_family": "RECOVERY", "team_label": "b", "zone_candidate": "DEFENSIVE_THIRD", "channel_candidate": "LEFT_CHANNEL"},
    ]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT, window_size_mins=5, hop_mins=5)
    assert report["input_context_count"] == 3
    assert report["event_window_count"] == 2


def test_window_counts_action_families():
    contexts = [
        {"minute_bucket": "0", "action_family": "PASS", "team_label": "a", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
        {"minute_bucket": "1", "action_family": "PASS", "team_label": "a", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
        {"minute_bucket": "2", "action_family": "SHOT", "team_label": "a", "zone_candidate": "FINAL_THIRD", "channel_candidate": "RIGHT_CHANNEL"},
    ]
    windows = build_windows_from_context(contexts, window_size_mins=5, hop_mins=5)
    assert windows[0]["action_family_counts"] == {"PASS": 2, "SHOT": 1}
    assert windows[0]["surface_row_count"] == 3


def test_terminal_loss_restart_flags():
    contexts = [
        {"minute_bucket": "0", "action_family": "SHOT", "team_label": "a", "zone_candidate": "FINAL_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
        {"minute_bucket": "1", "action_family": "BALL_LOSS", "team_label": "a", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
        {"minute_bucket": "2", "action_family": "RESTART", "team_label": "b", "zone_candidate": "DEFENSIVE_THIRD", "channel_candidate": "LEFT_CHANNEL"},
    ]
    windows = build_windows_from_context(contexts, window_size_mins=5, hop_mins=5)
    assert windows[0]["terminal_action_surface_present"] is True
    assert windows[0]["loss_recovery_surface_present"] is True
    assert windows[0]["restart_surface_present"] is True


def test_claim_boundaries_remain_false(tmp_path):
    contexts = [{"minute_bucket": "0", "action_family": "PASS", "team_label": "a", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["phase_truth"] is False
    assert report["possession_truth"] is False
    assert report["sequence_truth"] is False
    assert report["rhythm_truth"] is False
    assert report["claim_allowed"] is False


def test_raw_input_dir_rebuilds_minute_windows(tmp_path):
    out_input = tmp_path / "HPFA"
    out_input.mkdir()
    raw_input = tmp_path / "raw"
    raw_input.mkdir()
    write_context(out_input / "minimum_viable_context_lite_v1.json", [
        {"minute_bucket": "unknown", "action_family": "UNKNOWN_OR_OTHER", "team_label": "unknown", "zone_candidate": "UNKNOWN_ZONE", "channel_candidate": "UNKNOWN_CHANNEL"}
    ])
    (raw_input / "surface.csv").write_text(
        "minute_raw;team;action;pos_x;pos_y\n5;A;Pass;50;34\n6;A;Shot;80;44\n",
        encoding="utf-8",
    )
    report = build_report(out_input, root=ROOT, raw_input_dir=raw_input, window_size_mins=5, hop_mins=5)
    assert report["minute_bearing_context_count"] == 2
    assert report["event_window_count"] == 1
    assert report["window_summary"]["window_axis_counts"] == {"minute": 1}


def test_flat_outputs(tmp_path):
    contexts = [{"minute_bucket": "0", "action_family": "PASS", "team_label": "a", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    out = tmp_path / "HPFA"
    out.mkdir()
    report = write_outputs(tmp_path, out, root=ROOT)
    assert (out / "event_window_builder_lite_v1.json").exists()
    assert (out / "event_window_builder_lite_v1.txt").exists()
    assert report["claim_safety"] == "EVENT_WINDOW_CANDIDATE_ONLY"


def test_no_sample_match_identity_leak():
    src = (SRC / "event_window_builder.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "event_window_builder_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
        assert token not in contract
