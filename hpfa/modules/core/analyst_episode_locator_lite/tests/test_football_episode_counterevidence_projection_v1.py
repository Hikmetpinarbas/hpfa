from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from football_episode_boundary import build_football_episode_boundaries


def _layer(layer_id, second, *, shot=False, loss=False, families=None):
    return {
        "episode_time_layer_candidate_id": layer_id,
        "second_candidate": second,
        "context_refs": [f"ctx_{layer_id}"],
        "eligible_action_family_counts": families or {"PASS": 1},
        "team_candidates": ["TEAM_A"],
        "restart_visible": False,
        "terminal_action_visible": shot,
        "ball_loss_visible": loss,
        "recovery_visible": False,
        "same_time_unordered": False,
    }


def _payload():
    layers = [
        _layer("a", 10.0, families={"PASS": 1}),
        _layer("b", 12.0, shot=True, families={"SHOT": 1}),
        _layer("c", 20.0, families={"PASS": 1}),
        _layer("d", 22.0, loss=True, families={"SHOT": 1}),
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
            "time_layer_refs": [row["episode_time_layer_candidate_id"] for row in layers],
        }],
    }


def test_same_composition_different_outcome_exposes_provenance_counterevidence_pair():
    out = build_football_episode_boundaries(_payload())

    assert out["episode_recurrence_change_candidate_count"] == 1
    recurrence = out["episode_recurrence_change_candidates"][0]
    assert recurrence["different_visible_outcome_candidate"] is True
    assert recurrence["visible_outcome_contrast_pair_count"] == 1
    assert out["visible_outcome_counterevidence_pair_count"] == 1

    pair = recurrence["visible_outcome_contrast_pairs"][0]
    assert pair["counterevidence_candidate"] is True
    assert pair["counterevidence_scope"] == "SAME_MATCH_SAME_VISIBLE_COMPOSITION_DIFFERENT_VISIBLE_OUTCOME_ONLY"
    assert pair["football_episode_candidate_id_a"] in recurrence["football_episode_candidate_ids"]
    assert pair["football_episode_candidate_id_b"] in recurrence["football_episode_candidate_ids"]
    assert pair["visible_outcome_candidate_a"] != pair["visible_outcome_candidate_b"]
    assert pair["dependent_episode_projection_only"] is True
    assert pair["independent_evidence_vote_count"] == 0
    assert pair["causal_falsification_truth"] is False
    assert pair["tactical_change_truth"] is False
    assert pair["claim_output_allowed"] is False
    assert out["counterevidence_candidate_is_causal_falsification_truth"] is False
    assert out["canonical_event_count"] == "UNKNOWN"
    assert out["true_action_count"] == "UNKNOWN"
    assert out["production_release"] is False


def test_same_outcome_repeat_does_not_invent_counterevidence_pair():
    payload = _payload()
    payload["episode_time_layer_candidates"][3]["ball_loss_visible"] = False
    payload["episode_time_layer_candidates"][3]["terminal_action_visible"] = True

    out = build_football_episode_boundaries(payload)

    recurrence = out["episode_recurrence_change_candidates"][0]
    assert recurrence["different_visible_outcome_candidate"] is False
    assert recurrence["visible_outcome_contrast_pairs"] == []
    assert recurrence["visible_outcome_contrast_pair_count"] == 0
    assert out["visible_outcome_counterevidence_pair_count"] == 0


def test_no_sample_match_identity_leak():
    product = (SRC / "football_episode_boundary.py").read_text(encoding="utf-8").casefold()
    forbidden = ["genclerbirligi", "fenerbahce", "15.08.2026", "sturm graz", "heart of midlothian"]
    assert not any(token in product for token in forbidden)
