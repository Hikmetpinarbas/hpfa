from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from football_episode_boundary import build_football_episode_boundaries


def _payload(action_family_counts):
    return {
        "module_id": "analyst_episode_locator_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "episode_time_layer_candidates": [{
            "episode_time_layer_candidate_id": "layer_1",
            "second_candidate": 10.0,
            "context_refs": ["ctx_1"],
            "eligible_action_family_counts": action_family_counts,
            "team_candidates": ["TEAM_A"],
            "restart_visible": False,
            "terminal_action_visible": False,
            "ball_loss_visible": False,
            "recovery_visible": False,
            "same_time_unordered": False,
        }],
        "episode_candidates": [{
            "episode_candidate_id": "macro_1",
            "period_candidate": "1",
            "time_layer_refs": ["layer_1"],
        }],
    }


def test_truthy_non_mapping_action_family_counts_fail_closed_without_exception():
    for invalid_value in (["PASS"], "PASS"):
        out = build_football_episode_boundaries(_payload(invalid_value))
        assert out["status"] == "FAIL_CLOSED"
        assert out["football_episode_candidate_count"] == 0
        assert out["hard_block_hits"] == ["time_layer_action_family_counts_invalid:layer_1"]
        assert out["canonical_event_count"] == "UNKNOWN"
        assert out["true_action_count"] == "UNKNOWN"
        assert out["production_release"] is False
