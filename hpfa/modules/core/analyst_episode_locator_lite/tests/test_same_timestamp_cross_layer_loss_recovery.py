from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from football_episode_boundary import build_football_episode_boundaries


def _layer(layer_id: str, *, loss: bool = False, recovery: bool = False) -> dict:
    return {
        "episode_time_layer_candidate_id": layer_id,
        "second_candidate": 10.0,
        "context_refs": [f"ctx_{layer_id}"],
        "eligible_action_family_counts": {"TURNOVER" if loss else "RECOVERY": 1},
        "team_candidates": ["TEAM_A"],
        "restart_visible": False,
        "terminal_action_visible": False,
        "ball_loss_visible": loss,
        "recovery_visible": recovery,
        "same_time_unordered": False,
    }


def test_same_timestamp_loss_and_recovery_across_distinct_layers_remain_unordered():
    layers = [_layer("loss_layer", loss=True), _layer("recovery_layer", recovery=True)]
    payload = {
        "module_id": "analyst_episode_locator_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "episode_time_layer_candidates": layers,
        "episode_candidates": [{
            "episode_candidate_id": "macro_1",
            "period_candidate": "1",
            "time_layer_refs": ["loss_layer", "recovery_layer"],
        }],
    }

    out = build_football_episode_boundaries(payload)
    episode = out["football_episode_candidates"][0]

    assert episode["visible_outcome_candidate"] == "LOSS_AND_RECOVERY_VISIBLE_ORDER_INDETERMINATE"
    assert episode["same_time_unordered_visible"] is True
    assert episode["same_timestamp_internal_ordering_allowed"] is False
    assert out["canonical_event_count"] == "UNKNOWN"
    assert out["true_action_count"] == "UNKNOWN"
    assert out["production_release"] is False
