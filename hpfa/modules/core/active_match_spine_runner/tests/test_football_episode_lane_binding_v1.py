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


def _upstream_payload():
    return {
        "module_id": "analyst_episode_locator_lite_v1",
        "status": "PASS",
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "episode_candidates": [
            {
                "episode_candidate_id": "macro_1",
                "period_candidate": 1,
                "time_layer_refs": ["l1", "l2"],
            }
        ],
        "episode_time_layer_candidates": [
            {
                "episode_time_layer_candidate_id": "l1",
                "second_candidate": 10.0,
                "context_refs": ["ctx1"],
                "eligible_action_family_counts": {"PASS": 1},
                "team_candidates": ["TEAM_A"],
                "restart_visible": False,
                "terminal_action_visible": False,
                "ball_loss_visible": True,
                "recovery_visible": False,
                "same_time_unordered": False,
            },
            {
                "episode_time_layer_candidate_id": "l2",
                "second_candidate": 12.0,
                "context_refs": ["ctx2"],
                "eligible_action_family_counts": {"RECOVERY": 1},
                "team_candidates": ["TEAM_B"],
                "restart_visible": False,
                "terminal_action_visible": False,
                "ball_loss_visible": False,
                "recovery_visible": True,
                "same_time_unordered": False,
            },
        ],
    }


def test_episode_lane_writes_current_football_episode_artifacts(tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    (output / episode_lane_runner.ANALYST_EPISODE_OUTPUT).write_text(
        json.dumps(_upstream_payload()),
        encoding="utf-8",
    )

    report = episode_lane_runner._write_football_episode_boundary_outputs(output)

    assert report["status"] == "PASS"
    assert report["football_episode_candidate_count"] == 1
    candidate = report["football_episode_candidates"][0]
    assert candidate["visible_outcome_candidate"] == "BALL_LOSS_THEN_RECOVERY_VISIBLE"
    assert (output / episode_lane_runner.FOOTBALL_EPISODE_OUTPUT).is_file()
    assert (output / episode_lane_runner.FOOTBALL_EPISODE_TXT).is_file()
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_episode_lane_boundary_binding_fails_closed_on_invalid_upstream(tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    payload = _upstream_payload()
    payload["canonical_event_count"] = 2
    (output / episode_lane_runner.ANALYST_EPISODE_OUTPUT).write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    report = episode_lane_runner._write_football_episode_boundary_outputs(output)

    assert report["status"] == "FAIL_CLOSED"
    assert report["football_episode_candidate_count"] == 0
    assert "upstream_canonical_event_count_claimed" in report["hard_block_hits"]
    assert report["production_release"] is False


def test_football_episode_outputs_are_owned_and_stale_clearable(tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    for name in (episode_lane_runner.FOOTBALL_EPISODE_OUTPUT, episode_lane_runner.FOOTBALL_EPISODE_TXT):
        (output / name).write_text("stale", encoding="utf-8")

    cleared = episode_lane_runner._clear_episode_owned_outputs(output)

    assert episode_lane_runner.FOOTBALL_EPISODE_OUTPUT in cleared
    assert episode_lane_runner.FOOTBALL_EPISODE_TXT in cleared
    assert not (output / episode_lane_runner.FOOTBALL_EPISODE_OUTPUT).exists()
    assert not (output / episode_lane_runner.FOOTBALL_EPISODE_TXT).exists()


def test_no_sample_match_identity_leak():
    source = Path(episode_lane_runner.__file__).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "Turkey", "Australia", "15.08.2026"):
        assert token not in source
