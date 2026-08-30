import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import episode_lane_runner


def _base_fixture(tmp_path: Path):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)
    surface = active_match / "surface.csv"
    surface.write_text("id,start\n1,0\n", encoding="utf-8")
    output = tmp_path / "out"
    output.mkdir()
    (output / episode_lane_runner.ROW_NUCLEUS_OUTPUT).write_text("{}", encoding="utf-8")
    snapshot = episode_lane_runner._surface_snapshot(active_match)
    (output / episode_lane_runner.BRIDGE_OUTPUT).write_text(
        json.dumps({"input_surface_snapshot_id": snapshot["snapshot_id"]}),
        encoding="utf-8",
    )
    return active_match, output, surface


def _passing_step(command):
    return {"command": command, "returncode": 0, "stdout": "", "stderr": "", "passed": True}


def test_final_snapshot_drift_after_temporal_fails_closed(tmp_path, monkeypatch):
    active_match, output, surface = _base_fixture(tmp_path)
    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "run_provider_time_context_step",
        lambda *_a, **_k: _passing_step(["internal:provider_time_semantic_admission_lite_v1"]),
    )
    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "run_step",
        lambda _root, command: _passing_step(command),
    )
    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "write_summary",
        lambda *_a, **_k: {"status": "SMOKE_PASS", "analyst_evidence": {}},
    )

    def mutating_temporal(*_args, **_kwargs):
        surface.write_text("id,start\n1,999\n", encoding="utf-8")
        return {
            "status": "SMOKE_PASS",
            "temporal_episode_signature_count": 1,
            "hard_block_hits": [],
            "review_hits": [],
        }

    monkeypatch.setattr(episode_lane_runner, "write_temporal_episode_signature", mutating_temporal)
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)

    assert report["status"] == "FAIL_CLOSED"
    assert "active_match_surface_snapshot_mismatch_after_temporal" in report["hard_block_hits"]
    assert report["surface_snapshot_bound"] is False
    assert report["temporal_episode_signature_executed"] is True
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_preflight_failure_still_clears_episode_owned_outputs(tmp_path):
    active_match, output, _surface = _base_fixture(tmp_path)
    stale = output / episode_lane_runner.CURRENT_EPISODE_RUNNER_OUTPUT
    stale.write_text(json.dumps({"episode_candidate_count": 999}), encoding="utf-8")
    stale_temporal = output / episode_lane_runner.TEMPORAL_OUTPUT
    stale_temporal.write_text(json.dumps({"temporal_episode_signature_count": 999}), encoding="utf-8")

    (output / episode_lane_runner.BRIDGE_OUTPUT).write_text(
        json.dumps({"input_surface_snapshot_id": "stale-snapshot-id"}),
        encoding="utf-8",
    )

    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)

    assert report["status"] == "FAIL_CLOSED"
    assert "active_match_surface_snapshot_mismatch_before_episode" in report["hard_block_hits"]
    assert not stale.exists()
    assert not stale_temporal.exists()
    assert episode_lane_runner.CURRENT_EPISODE_RUNNER_OUTPUT in report["cleared_stale_episode_outputs"]
    assert episode_lane_runner.TEMPORAL_OUTPUT in report["cleared_stale_episode_outputs"]
    assert report["context_episode_feature_lane_executed"] is False
    assert report["temporal_episode_signature_executed"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path(episode_lane_runner.__file__).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "Turkey", "Australia", "15.08.2026"):
        assert token not in source
