from __future__ import annotations

import importlib.util
from pathlib import Path

import reconstruction_intelligence_packet_adapter_current_v1 as reconstruction
from hpfa.modules.core.active_match_spine_runner.src.shared_surface_snapshot_contract import surface_snapshot_id


def _load_entrypoint():
    root = Path(__file__).resolve().parents[5]
    path = root / "active_match_spine_runner.py"
    spec = importlib.util.spec_from_file_location("hpfa_active_match_entrypoint_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shared_snapshot_matches_reconstruction_contract(tmp_path: Path) -> None:
    match = tmp_path / "current"
    match.mkdir()
    (match / "a.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    nested = match / "nested"
    nested.mkdir()
    (nested / "b.xml").write_text("<r><x>1</x></r>\n", encoding="utf-8")

    assert surface_snapshot_id(match) == reconstruction._surface_snapshot(match)["snapshot_id"]


def test_entrypoint_normalizes_completed_feature_surface() -> None:
    entrypoint = _load_entrypoint()
    result = {
        "engineering_evidence": {
            "current_context_episode_feature_lane_reused": True,
        }
    }
    entrypoint._normalize_current_surface_evidence(result)
    assert result["engineering_evidence"]["current_context_episode_feature_lane_completed"] is True


def test_entrypoint_does_not_promote_failed_feature_surface() -> None:
    entrypoint = _load_entrypoint()
    result = {
        "engineering_evidence": {
            "current_context_episode_feature_lane_reused": False,
        }
    }
    entrypoint._normalize_current_surface_evidence(result)
    assert result["engineering_evidence"]["current_context_episode_feature_lane_completed"] is False
