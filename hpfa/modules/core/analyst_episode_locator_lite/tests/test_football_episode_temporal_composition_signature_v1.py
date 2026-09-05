from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from football_episode_boundary import build_football_episode_boundaries


def _layer(layer_id, second, family, *, loss=False):
    return {
        "episode_time_layer_candidate_id": layer_id,
        "second_candidate": second,
        "context_refs": [f"ctx_{layer_id}"],
        "eligible_action_family_counts": {family: 1},
        "team_candidates": ["TEAM_A"],
        "restart_visible": False,
        "terminal_action_visible": False,
        "ball_loss_visible": loss,
        "recovery_visible": False,
        "same_time_unordered": False,
    }


def _payload(layers):
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
            "time_layer_refs": [row["episode_time_layer_candidate_id"] for row in layers],
        }],
    }


def test_equal_family_totals_with_reversed_positive_time_order_are_not_recurrence():
    layers = [
        _layer("a", 10.0, "PASS", loss=True),
        _layer("b", 11.0, "SHOT"),
        _layer("c", 20.0, "SHOT", loss=True),
        _layer("d", 21.0, "PASS"),
    ]

    out = build_football_episode_boundaries(_payload(layers))

    assert out["football_episode_candidate_count"] == 2
    first, second = out["football_episode_candidates"]
    assert first["action_family_distribution"] == second["action_family_distribution"] == {"PASS": 1, "SHOT": 1}
    assert first["visible_action_family_time_layer_sequence_candidate"] == [{"PASS": 1}, {"SHOT": 1}]
    assert second["visible_action_family_time_layer_sequence_candidate"] == [{"SHOT": 1}, {"PASS": 1}]
    assert first["visible_process_composition_signature_candidate"] != second["visible_process_composition_signature_candidate"]
    assert out["episode_recurrence_change_candidate_count"] == 0
    assert out["visible_outcome_counterevidence_pair_count"] == 0
    assert out["claim_output_allowed"] is False
    assert out["canonical_event_count"] == "UNKNOWN"
    assert out["true_action_count"] == "UNKNOWN"
    assert out["production_release"] is False


def test_same_timestamp_family_rows_fold_without_creating_internal_order():
    layers = [
        _layer("a", 10.0, "PASS"),
        _layer("b", 10.0, "SHOT", loss=True),
    ]

    out = build_football_episode_boundaries(_payload(layers))

    assert out["football_episode_candidate_count"] == 1
    episode = out["football_episode_candidates"][0]
    assert episode["visible_action_family_time_layer_sequence_candidate"] == [{"PASS": 1, "SHOT": 1}]
    assert episode["same_timestamp_internal_ordering_allowed"] is False
    assert out["source_row_order_is_temporal_truth"] is False
