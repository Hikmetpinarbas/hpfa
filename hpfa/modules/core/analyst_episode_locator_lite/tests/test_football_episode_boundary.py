from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from football_episode_boundary import build_football_episode_boundaries


def _layer(layer_id, second, *, restart=False, shot=False, loss=False, recovery=False, families=None):
    return {
        "episode_time_layer_candidate_id": layer_id,
        "second_candidate": second,
        "context_refs": [f"ctx_{layer_id}"],
        "eligible_action_family_counts": families or {"PASS": 1},
        "team_candidates": ["TEAM_A"],
        "restart_visible": restart,
        "terminal_action_visible": shot,
        "ball_loss_visible": loss,
        "recovery_visible": recovery,
        "same_time_unordered": False,
    }


def _payload(layers):
    refs = [row["episode_time_layer_candidate_id"] for row in layers]
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
            "time_layer_refs": refs,
        }],
    }


def test_terminal_shot_closes_visible_process_candidate():
    payload = _payload([
        _layer("a", 10.0),
        _layer("b", 14.0, shot=True, families={"SHOT": 1}),
        _layer("c", 16.0),
    ])
    out = build_football_episode_boundaries(payload)
    assert out["football_episode_candidate_count"] == 2
    first = out["football_episode_candidates"][0]
    assert first["visible_outcome_candidate"] == "TERMINAL_SHOT_VISIBLE"
    assert first["break_or_end_evidence_candidate"] == "TERMINAL_SHOT_VISIBLE"
    assert out["all_macro_time_layers_assigned_once"] is True


def test_visible_restart_starts_new_process_candidate():
    payload = _payload([
        _layer("a", 10.0),
        _layer("b", 12.0, restart=True, families={"RESTART": 1}),
    ])
    out = build_football_episode_boundaries(payload)
    assert out["football_episode_candidate_count"] == 2
    assert out["football_episode_candidates"][1]["start_evidence_candidate"] == "VISIBLE_RESTART"


def test_admitted_gap_can_split_without_calling_it_possession_truth():
    payload = _payload([_layer("a", 10.0), _layer("b", 30.0)])
    out = build_football_episode_boundaries(payload, gap_seconds=8.0)
    assert out["football_episode_candidate_count"] == 2
    assert out["football_episode_candidates"][0]["break_or_end_evidence_candidate"] == "ADMITTED_VISIBLE_TIME_GAP"
    assert out["episode_is_possession_truth"] is False
    assert out["episode_is_tactical_truth"] is False


def test_same_layer_loss_recovery_does_not_create_internal_order():
    payload = _payload([_layer("a", 10.0, loss=True, recovery=True, families={"TURNOVER": 1, "RECOVERY": 1})])
    out = build_football_episode_boundaries(payload)
    ep = out["football_episode_candidates"][0]
    assert ep["visible_outcome_candidate"] == "LOSS_AND_RECOVERY_VISIBLE_ORDER_INDETERMINATE"
    assert ep["same_timestamp_internal_ordering_allowed"] is False
    assert out["status"] == "REVIEW_REQUIRED"


def test_boundary_requires_visible_evidence_no_arbitrary_split():
    payload = _payload([_layer("a", 10.0), _layer("b", 12.0), _layer("c", 14.0)])
    out = build_football_episode_boundaries(payload)
    assert out["football_episode_candidate_count"] == 1
    assert out["football_episode_candidates"][0]["boundary_requires_visible_evidence"] is True


def test_duplicate_macro_layer_reference_fails_closed():
    payload = _payload([_layer("a", 10.0)])
    payload["episode_candidates"][0]["time_layer_refs"] = ["a", "a"]
    out = build_football_episode_boundaries(payload)
    assert out["status"] == "FAIL_CLOSED"
    assert out["football_episode_candidate_count"] == 0


def test_upstream_fail_closed_contracts_downstream_permission():
    payload = _payload([_layer("a", 10.0)])
    payload["status"] = "FAIL_CLOSED"
    out = build_football_episode_boundaries(payload)
    assert out["status"] == "FAIL_CLOSED"


def test_no_sample_match_identity_leak():
    product = (SRC / "football_episode_boundary.py").read_text(encoding="utf-8").casefold()
    forbidden = ["genclerbirligi", "fenerbahce", "15.08.2026", "sturm graz", "heart of midlothian"]
    assert not any(token in product for token in forbidden)
