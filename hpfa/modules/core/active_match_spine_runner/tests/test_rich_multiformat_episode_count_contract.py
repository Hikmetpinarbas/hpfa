from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rich_multiformat_analysis_lane import _construct_c01, _phase_state_candidates, _primitive_metrics


def _features(**overrides):
    card = {
        "shot_candidate_count": 1,
        "turnover_candidate_count": 0,
        "recovery_candidate_count": 0,
        "eligible_action_zone_counts": {"FINAL_THIRD": 1},
        "action_family_counts": {"PASS": 2},
    }
    card.update(overrides)
    payload = {
        "episode_feature_vectors": [card],
        "total_eligible_action_candidate_count": 3,
        "eligible_action_family_candidate_counts": {"PASS": 2, "SHOT": 1},
    }
    return payload


def _progression_row():
    return {
        "row_projection_id": "xrp_contract",
        "source_sha256": "sha_contract",
        "identity_candidates": {"team_raw_candidate": "Team Generic"},
        "metric_values": {
            "progressive_passes": {
                "value_status": "OBSERVED",
                "value_kind": "number",
                "raw_metric_label": "Progressive passes",
                "raw_value": 4,
            },
            "shots": {
                "value_status": "OBSERVED",
                "value_kind": "number",
                "raw_metric_label": "Shots",
                "raw_value": 2,
            },
        },
    }


def _entity_views():
    return {"observed_metric_cell_count": 2}


def test_invalid_numeric_shapes_do_not_emit_phase_activity_labels():
    for invalid in (True, "1", 1.0, -1):
        result = _phase_state_candidates(_features(shot_candidate_count=invalid))
        assert len(result) == 1
        row = result[0]
        assert row["count_contract_review_required"] is True
        assert row["invalid_count_fields"] == ["shot_candidate_count"]
        assert row["support"]["shot_candidate_count"] == 0
        assert row["labels"] == ["UNRESOLVED_ACTIVITY_STATE"]
        assert row["phase_truth"] is False
        assert row["tactical_truth"] is False


def test_invalid_shot_count_blocks_c01_packet_instead_of_coercing_support():
    for invalid in (True, "1", 1.0, -1):
        result = _construct_c01([_progression_row()], _features(shot_candidate_count=invalid))
        assert result["status"] == "REVIEW_REQUIRED"
        assert result["count_contract_review_required"] is True
        assert result["invalid_shot_count_episode_indices"] == [0]
        assert result["visible_shot_candidate_count"] == 0
        assert result["packet_candidate"] is None
        assert result["review_reason"] == "episode_feature_shot_count_contract_invalid"
        assert result["construct_truth"] is False


def test_invalid_total_count_cannot_create_visible_volume_primitive():
    for invalid in (True, "3", 3.0, -1):
        features = _features()
        features["total_eligible_action_candidate_count"] = invalid
        result = _primitive_metrics(features, _entity_views())
        metric_ids = {item["metric_id"] for item in result["metrics"]}
        assert "primitive_visible_action_candidate_volume" not in metric_ids
        assert result["count_contract_review_required"] is True
        assert "total_eligible_action_candidate_count" in result["invalid_count_fields"]
        assert result["admitted_action_family_candidate_counts"] == {"PASS": 2, "SHOT": 1}


def test_any_invalid_family_count_withdraws_family_primitives_and_macro_projection():
    for invalid in (True, "2", 2.0, -1):
        features = _features()
        features["eligible_action_family_candidate_counts"] = {"PASS": 2, "SHOT": invalid}
        result = _primitive_metrics(features, _entity_views())
        metric_ids = {item["metric_id"] for item in result["metrics"]}
        assert not any(metric_id.startswith("primitive_action_family_") for metric_id in metric_ids)
        assert result["count_contract_review_required"] is True
        assert result["invalid_count_fields"] == ["eligible_action_family_candidate_counts.SHOT"]
        assert result["admitted_action_family_candidate_counts"] == {}


def test_strict_integer_counts_preserve_count_semantics_without_label_support_promotion():
    phase = _phase_state_candidates(_features())[0]
    assert phase["count_contract_review_required"] is False
    assert phase["invalid_count_fields"] == []
    assert "TERMINAL_ACTIVITY_CANDIDATE" in phase["labels"]
    assert "ADVANCED_ACCESS_ACTIVITY_CANDIDATE" in phase["labels"]
    assert "CIRCULATION_ACTIVITY_CANDIDATE" in phase["labels"]

    c01 = _construct_c01([_progression_row()], _features())
    assert c01["count_contract_review_required"] is False
    assert c01["visible_shot_candidate_count"] == 1
    assert c01["progression_label_navigation_ref_count"] == 1
    assert c01["terminal_label_navigation_ref_count"] == 1
    assert c01["progression_aggregate_ref_count"] == 0
    assert c01["terminal_aggregate_ref_count"] == 0
    assert c01["packet_candidate"] is None
    assert c01["construct_semantic_authority_admitted"] is False
    assert c01["xlsx_metric_label_match_is_construct_semantic_authority"] is False
    assert c01["construct_truth"] is False

    primitives = _primitive_metrics(_features(), _entity_views())
    assert primitives["count_contract_review_required"] is False
    assert primitives["invalid_count_fields"] == []
    assert primitives["admitted_action_family_candidate_counts"] == {"PASS": 2, "SHOT": 1}
    metric_ids = {item["metric_id"] for item in primitives["metrics"]}
    assert "primitive_visible_action_candidate_volume" in metric_ids
    assert "primitive_action_family_pass" in metric_ids
    assert "primitive_action_family_shot" in metric_ids
