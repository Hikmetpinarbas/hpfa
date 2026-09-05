from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from football_episode_boundary import build_football_episode_boundaries


def _layer(layer_id: str, second: float, *, loss: bool = False, recovery: bool = False, families=None) -> dict:
    return {
        "episode_time_layer_candidate_id": layer_id,
        "second_candidate": second,
        "context_refs": [f"ctx_{layer_id}"],
        "eligible_action_family_counts": families or ({"TURNOVER": 1, "RECOVERY": 1} if loss and recovery else {"PASS": 1}),
        "team_candidates": ["TEAM_A"],
        "restart_visible": False,
        "terminal_action_visible": False,
        "ball_loss_visible": loss,
        "recovery_visible": recovery,
        "same_time_unordered": False,
    }


def _payload(combined_id: str, sibling_id: str) -> dict:
    layers = [
        _layer(combined_id, 10.0, loss=True, recovery=True),
        _layer(sibling_id, 10.0, families={"PASS": 1}),
        _layer("later", 12.0, families={"PASS": 1}),
    ]
    return {
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
            "time_layer_refs": [combined_id, sibling_id, "later"],
        }],
    }


def test_same_timestamp_bucket_boundary_is_invariant_to_layer_id_sort_order():
    combined_first = build_football_episode_boundaries(_payload("a_combined", "z_sibling"))
    sibling_first = build_football_episode_boundaries(_payload("z_combined", "a_sibling"))

    assert combined_first["football_episode_candidate_count"] == 2
    assert sibling_first["football_episode_candidate_count"] == 2

    first_a = combined_first["football_episode_candidates"][0]
    first_b = sibling_first["football_episode_candidates"][0]

    assert set(first_a["time_layer_refs"]) == {"a_combined", "z_sibling"}
    assert set(first_b["time_layer_refs"]) == {"z_combined", "a_sibling"}
    assert first_a["visible_outcome_candidate"] == "LOSS_AND_RECOVERY_VISIBLE_ORDER_INDETERMINATE"
    assert first_b["visible_outcome_candidate"] == "LOSS_AND_RECOVERY_VISIBLE_ORDER_INDETERMINATE"
    assert first_a["same_timestamp_internal_ordering_allowed"] is False
    assert first_b["same_timestamp_internal_ordering_allowed"] is False
    assert combined_first["canonical_event_count"] == "UNKNOWN"
    assert sibling_first["true_action_count"] == "UNKNOWN"
    assert combined_first["production_release"] is False
