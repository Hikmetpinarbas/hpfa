from pathlib import Path

from hpfa.modules.core.visible_geometry_lens_lite.src.visible_geometry_lens import (
    build_visible_geometry_lens,
    write_outputs,
)


def _inputs():
    trace = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "status": "PASS",
        "trackable_action_trace_candidates": [
            {"trackable_action_trace_candidate_id": "t1", "team_identity_candidate_id": "ta", "actor_identity_candidate_id": "pa", "period_candidate": "1", "pos_x_candidate": "10", "pos_y_candidate": "10", "coordinate_evidence_status": "COORDINATE_PRESENT"},
            {"trackable_action_trace_candidate_id": "t2", "team_identity_candidate_id": "ta", "actor_identity_candidate_id": "pa", "period_candidate": "1", "pos_x_candidate": "20", "pos_y_candidate": "20", "coordinate_evidence_status": "COORDINATE_PRESENT"},
            {"trackable_action_trace_candidate_id": "t3", "team_identity_candidate_id": "tb", "actor_identity_candidate_id": "pb", "period_candidate": "1", "pos_x_candidate": "80", "pos_y_candidate": "40", "coordinate_evidence_status": "COORDINATE_PRESENT"},
            {"trackable_action_trace_candidate_id": "t4", "team_identity_candidate_id": "ta", "actor_identity_candidate_id": "pa", "period_candidate": "2", "pos_x_candidate": None, "pos_y_candidate": "30", "coordinate_evidence_status": "COORDINATE_MISSING"},
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    identity = {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": "PASS",
        "actor_identity_candidates": [
            {"actor_identity_candidate_id": "pa", "actor_normalized_key": "alpha_player", "team_identity_candidate_id": "ta"},
            {"actor_identity_candidate_id": "pb", "actor_normalized_key": "beta_player", "team_identity_candidate_id": "tb"},
        ],
        "team_identity_candidates": [
            {"team_identity_candidate_id": "ta", "team_normalized_key": "alpha"},
            {"team_identity_candidate_id": "tb", "team_normalized_key": "beta"},
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    return trace, identity


def test_period_conditioned_team_and_player_point_geometry():
    result = build_visible_geometry_lens(*_inputs())
    assert result["status"] == "PASS"
    assert result["team_period_geometry_row_count"] == 2
    assert result["player_period_geometry_row_count"] == 2
    assert result["coordinate_missing_or_unadmitted_trace_count"] == 1
    alpha = next(row for row in result["team_period_geometry_rows"] if row["team_identity_candidate_id"] == "ta")
    assert alpha["coordinate_point_count"] == 2
    assert alpha["centroid_x_candidate"] == 15.0
    assert alpha["centroid_y_candidate"] == 15.0
    assert alpha["direction_normalized"] is False
    assert alpha["centroid_is_average_position_or_formation_truth"] is False


def test_geometry_never_opens_tracking_or_formation_claims():
    result = build_visible_geometry_lens(*_inputs())
    assert result["formation_truth"] is False
    assert result["team_shape_truth"] is False
    assert result["compactness_truth"] is False
    assert result["pitch_control_truth"] is False
    assert result["off_ball_movement_truth"] is False


def test_review_required_is_inherited():
    trace, identity = _inputs()
    trace["status"] = "REVIEW_REQUIRED"
    result = build_visible_geometry_lens(trace, identity)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "trace_upstream_review_required" in result["review_hits"]


def test_output_claim_locks(tmp_path: Path):
    result = build_visible_geometry_lens(*_inputs())
    paths = write_outputs(result, tmp_path)
    text = paths["summary"].read_text(encoding="utf-8")
    assert "direction_normalized=false" in text
    assert "formation_truth=false" in text
    assert "production_release=false" in text


def test_no_sample_match_identity_leak():
    root = Path(__file__).resolve().parents[1] / "src"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py")).casefold()
    forbidden = ("genclerbirligi", "fenerbahce", "15.08.2026", "samsunspor", "galatasaray", "besiktas")
    assert not any(token in text for token in forbidden)
