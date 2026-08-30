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
import reconstruction_intelligence_packet_adapter_current_v1 as current_bridge


def _write_bridge_snapshot(active_match: Path, output: Path) -> dict:
    snapshot = episode_lane_runner._surface_snapshot(active_match)
    (output / episode_lane_runner.BRIDGE_OUTPUT).write_text(
        json.dumps({"input_surface_snapshot_id": snapshot["snapshot_id"]}),
        encoding="utf-8",
    )
    return snapshot


def test_reconstruction_snapshot_covers_nested_tsv_mutation(tmp_path, monkeypatch):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"
    nested = active_match / "nested"
    nested.mkdir(parents=True)
    surface = nested / "surface.tsv"
    surface.write_text("id\tstart\n1\t0\n", encoding="utf-8")
    output = tmp_path / "out"

    monkeypatch.setattr(current_bridge.adapter, "validate_out", lambda value: Path(value))

    def mutating_sequence(_input_dir, out_dir):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        surface.write_text("id\tstart\n1\t42\n", encoding="utf-8")
        return {"status": "SMOKE_PASS"}

    monkeypatch.setattr(current_bridge.current_sequence, "runtime_write_outputs", mutating_sequence)
    monkeypatch.setattr(
        current_bridge.adapter,
        "write_outputs",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("adapter must not run on unstable nested TSV snapshot")
        ),
    )

    report = current_bridge.runtime_write_outputs(active_match, output)
    assert report["status"] == "FAIL_CLOSED"
    assert report["input_surface_snapshot_stable"] is False
    assert report["adapter_status"] == "NOT_EVALUATED"
    assert report["hard_block_hits"] == [
        "active_match_surface_snapshot_changed_during_reconstruction"
    ]


def test_episode_lane_clears_stale_owned_outputs_before_early_stop(tmp_path, monkeypatch):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)
    (active_match / "surface.csv").write_text("id,start\n1,0\n", encoding="utf-8")

    output = tmp_path / "out"
    output.mkdir()
    (output / episode_lane_runner.ROW_NUCLEUS_OUTPUT).write_text("{}", encoding="utf-8")
    _write_bridge_snapshot(active_match, output)

    stale_episode = output / "analyst_episode_locator_lite_v1.json"
    stale_feature = output / "episode_feature_vector_lite_v1.json"
    stale_temporal = output / "temporal_episode_signature_lite_v1.json"
    stale_episode.write_text('{"episode_candidate_count":999}', encoding="utf-8")
    stale_feature.write_text('{"episode_feature_vector_count":999}', encoding="utf-8")
    stale_temporal.write_text('{"temporal_episode_signature_count":999}', encoding="utf-8")

    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "run_provider_time_context_step",
        lambda *_a, **_k: {
            "command": ["internal:provider_time_semantic_admission_lite_v1"],
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        },
    )

    def fail_first_dependent(_root, command):
        return {
            "command": command,
            "returncode": 17,
            "stdout": "",
            "stderr": "synthetic failure",
            "passed": False,
        }

    monkeypatch.setattr(episode_lane_runner.current_episode, "run_step", fail_first_dependent)

    def summary_must_not_see_stale(out_dir, _steps, _input_status):
        out = Path(out_dir)
        assert not (out / stale_episode.name).exists()
        assert not (out / stale_feature.name).exists()
        assert not (out / stale_temporal.name).exists()
        return {"status": "FAIL_CLOSED", "analyst_evidence": {}}

    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "write_summary",
        summary_must_not_see_stale,
    )

    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["first_failed_episode_step"]["stage"] == "context_action_semantics_rebind.py"
    assert report["context_episode_feature_lane_executed"] is False
    assert report["temporal_episode_signature_executed"] is False
    assert stale_episode.name in report["cleared_stale_episode_outputs"]
    assert stale_feature.name in report["cleared_stale_episode_outputs"]
    assert stale_temporal.name in report["cleared_stale_episode_outputs"]


def test_no_sample_match_identity_leak_review_fix_v2():
    for source_path in [
        ROOT / "reconstruction_intelligence_packet_adapter_current_v1.py",
        SRC / "episode_lane_runner.py",
    ]:
        source = source_path.read_text(encoding="utf-8")
        for token in [
            "Genclerbirligi",
            "Fenerbahce",
            "Sturm Graz",
            "Heart of Midlothian",
            "Turkey",
            "Australia",
            "15.08.2026",
            "22.08.2026",
        ]:
            assert token not in source
