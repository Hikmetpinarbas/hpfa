import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import episode_lane_runner


def test_stale_episode_outputs_are_cleared_before_snapshot_preflight_io(tmp_path, monkeypatch):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)
    output = tmp_path / "out"
    output.mkdir()
    stale = output / episode_lane_runner.TEMPORAL_OUTPUT
    stale.write_text("stale", encoding="utf-8")

    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "read_json",
        lambda _path: {"input_surface_snapshot_id": "snapshot-a"},
    )
    monkeypatch.setattr(
        episode_lane_runner,
        "_surface_snapshot",
        lambda _path: (_ for _ in ()).throw(OSError("synthetic preflight read failure")),
    )

    with pytest.raises(OSError):
        episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)

    assert not stale.exists()


def test_hard_block_dedup_preserves_observation_order():
    observed = [
        "temporal_specific_contract_failure",
        "active_match_surface_snapshot_mismatch_after_temporal",
        "temporal_specific_contract_failure",
    ]
    assert episode_lane_runner._dedupe_preserve_order(observed) == [
        "temporal_specific_contract_failure",
        "active_match_surface_snapshot_mismatch_after_temporal",
    ]
