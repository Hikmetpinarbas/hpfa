import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "event_window_builder_lite" / "src"
sys.path.insert(0, str(SRC))

from event_window_builder import build_report, build_windows_from_context


def write_context(path: Path, contexts, reported_count=None):
    path.write_text(json.dumps({
        "module_id": "minimum_viable_context_lite_v1",
        "context_candidate_count": reported_count if reported_count is not None else len(contexts),
        "context_candidates_sample": contexts,
    }, ensure_ascii=False), encoding="utf-8")


def test_event_index_window_uses_context_ordinal_position():
    contexts = [{"action_family": "PASS", "team_label": "a"} for _ in range(105)]
    windows = build_windows_from_context(contexts)
    assert windows[0]["window_axis"] == "context_ordinal"
    assert windows[0]["window_assignment_basis"] == "context_ordinal"
    assert windows[0]["start_context_ordinal"] == 0
    assert windows[0]["end_context_ordinal"] == 100


def test_context_sample_truncation_blocks_complete_summary(tmp_path):
    contexts = [{"minute_bucket": "1", "action_family": "PASS", "team_label": "a"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts, reported_count=10)
    report = build_report(tmp_path, root=ROOT)
    assert report["context_input_scope"] == "sample_only"
    assert report["is_truncated_sample"] is True
    assert report["complete_context_available"] is False
    assert report["event_window_count"] == 0


def test_context_input_scope_reported(tmp_path):
    contexts = [{"minute_bucket": "1", "action_family": "PASS", "team_label": "a"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT)
    assert report["context_input_scope"] == "sample_only"
    assert "window_integrity_summary" in report


def test_time_axis_missing_disables_minute_windows(tmp_path):
    contexts = [{"action_family": "PASS", "team_label": "a"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT)
    assert report["time_axis_status"] == "MISSING"
    assert report["minute_window_enabled"] is False
    assert report["event_windows_sample"][0]["window_axis"] == "context_ordinal"


def test_time_axis_available_enables_minute_windows(tmp_path):
    contexts = [{"minute_bucket": "1", "action_family": "PASS", "team_label": "a"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT)
    assert report["time_axis_status"] == "AVAILABLE"
    assert report["minute_window_enabled"] is True
    assert report["event_windows_sample"][0]["window_axis"] == "minute"


def test_window_density_candidate_computed():
    contexts = [
        {"minute_bucket": "0", "action_family": "PASS", "team_label": "a"},
        {"minute_bucket": "1", "action_family": "SHOT", "team_label": "a"},
    ]
    windows = build_windows_from_context(contexts, window_size_mins=5, hop_mins=5)
    assert windows[0]["context_density"] == 0.4
    assert windows[0]["tempo_regime_candidate"] == "LOW"


def test_density_delta_candidate_uses_previous_window():
    contexts = []
    contexts.extend({"minute_bucket": str(i), "action_family": "PASS", "team_label": "a"} for i in range(5))
    contexts.extend({"minute_bucket": "6", "action_family": "SHOT", "team_label": "a"} for _ in range(6))
    windows = build_windows_from_context(contexts, window_size_mins=5, hop_mins=5)
    assert windows[1]["density_delta_candidate"] is not None
    assert windows[1]["volatility_candidate"] == abs(windows[1]["density_delta_candidate"])


def test_sequence_readiness_false_without_ordered_context():
    contexts = [{"action_family": "PASS", "team_label": "a"}]
    windows = build_windows_from_context(contexts)
    assert windows[0]["sequence_readiness"]["ready_for_sequence_candidate"] is False
    assert windows[0]["sequence_readiness"]["sequence_truth"] is False


def test_sequence_readiness_true_with_team_restart_terminal_signals():
    contexts = [
        {"minute_bucket": "1", "action_family": "RESTART", "team_label": "a"},
        {"minute_bucket": "2", "action_family": "SHOT", "team_label": "a"},
    ]
    windows = build_windows_from_context(contexts)
    assert windows[0]["sequence_readiness"]["has_team_labels"] is True
    assert windows[0]["sequence_readiness"]["has_restart_signal"] is True
    assert windows[0]["sequence_readiness"]["has_terminal_signal"] is True
    assert windows[0]["sequence_readiness"]["ready_for_sequence_candidate"] is True


def test_pattern_support_surface_contains_counts_only():
    contexts = [{"minute_bucket": "1", "action_family": "SHOT", "team_label": "a", "zone_candidate": "FINAL_THIRD", "channel_candidate": "RIGHT_CHANNEL"}]
    windows = build_windows_from_context(contexts)
    support = windows[0]["pattern_support_surface"]
    assert support["action_family_counts"] == {"SHOT": 1}
    assert support["pattern_truth"] is False


def test_no_sequence_truth_claim(tmp_path):
    contexts = [{"minute_bucket": "1", "action_family": "SHOT", "team_label": "a"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT)
    assert report["sequence_truth"] is False


def test_no_rhythm_state_assignment(tmp_path):
    contexts = [{"minute_bucket": "1", "action_family": "SHOT", "team_label": "a"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT)
    assert report["rhythm_truth"] is False
    assert "rhythm_state" not in report


def test_no_momentum_truth_claim(tmp_path):
    contexts = [{"minute_bucket": "1", "action_family": "SHOT", "team_label": "a"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT)
    assert report["momentum_truth"] is False


def test_no_canonical_event_count_claim(tmp_path):
    contexts = [{"minute_bucket": "1", "action_family": "SHOT", "team_label": "a"}]
    write_context(tmp_path / "minimum_viable_context_lite_v1.json", contexts)
    report = build_report(tmp_path, root=ROOT)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["event_windows_sample"][0]["canonical_event_count"] == "UNKNOWN"


def test_no_sample_match_identity_leak():
    src = (SRC / "event_window_builder.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
