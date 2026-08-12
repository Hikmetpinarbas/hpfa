from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "coordinate_frame_anchor_recheck.py"
SPEC = importlib.util.spec_from_file_location("coordinate_frame_anchor_recheck", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)


def frame_payload() -> dict:
    return {
        "module_id": "coordinate_frame_precondition_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": "binding_generic",
        "coordinate_scale_candidate": "PROVIDER_105X68_SCALE_CANDIDATE",
        "coordinate_bounds_status": "PASS_CANDIDATE_BOUNDS",
        "pitch_length_candidate": 105.0,
        "expected_team_period_group_count": 2,
        "multi_anchor_pass_group_count": 1,
        "team_period_coordinate_frame_candidates": [
            {
                "team_identity_candidate_id": "team_candidate_alpha",
                "period_candidate": "1",
                "shot_direction_candidate": "ATTACK_TOWARD_HIGH_X_CANDIDATE",
                "goalkeeper_goal_kick_anchor_count": 1,
                "goalkeeper_goal_kick_direction_candidate": "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
                "multi_anchor_gate": "INDEPENDENT_PRIMARY_ANCHORS_INSUFFICIENT",
            },
            {
                "team_identity_candidate_id": "team_candidate_beta",
                "period_candidate": "1",
                "shot_direction_candidate": "ATTACK_TOWARD_HIGH_X_CANDIDATE",
                "goalkeeper_goal_kick_anchor_count": 3,
                "goalkeeper_goal_kick_direction_candidate": "ATTACK_TOWARD_HIGH_X_CANDIDATE",
                "multi_anchor_gate": "PASS_MULTI_ANCHOR_CANDIDATE",
            },
        ],
        "review_hits": ["baseline_review_preserved"],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def attachment_payload(xs=(5.0, 7.0), *, team="team_candidate_alpha") -> dict:
    rows = []
    for i, x in enumerate(xs):
        rows.append(
            {
                "action_bundle_candidate_id": f"bundle_{i}",
                "coordinate_attachment_candidate": "EVENT_ACTION_LOCATION_CANDIDATE",
                "cross_format_support_status": "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT",
                "exact_object_action_surface_overlap_count": 0,
                "overlapping_same_coordinate_object_action_count": 0,
                "team_identity_candidate_id": team,
                "period_candidate": "1",
                "pos_x_candidate": str(x),
                "pos_y_candidate": "30.0",
                "validated_provider_semantics": False,
            }
        )
    return {
        "module_id": "provider_coordinate_attachment_semantics_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": "binding_generic",
        "goalkeeper_interception_attachment_status": "EVENT_ACTION_LOCATION_CANDIDATE_SUPPORTED",
        "goalkeeper_interception_primary_direction_anchor_candidate_allowed": True,
        "outcome_stratified_support_pooling_allowed": True,
        "event_fusion_allowed": False,
        "coordinate_attachment_is_validated_provider_truth": False,
        "coordinate_is_goalkeeper_physical_position_truth": False,
        "interception_attachment_records": rows,
        "interception_pass_bundle_count": len(rows),
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_unresolved_baseline_group_can_close_with_admitted_interception():
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment_payload())
    assert result["status"] == "PASS"
    assert result["baseline_multi_anchor_pass_group_count"] == 1
    assert result["recheck_multi_anchor_pass_group_count"] == 2
    assert result["goalkeeper_interception_gap_closure_group_count"] == 1
    assert result["progression_metric_recheck_allowed"] is True


def test_baseline_pass_group_remains_pass_without_interception():
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment_payload())
    row = next(x for x in result["team_period_coordinate_frame_recheck_candidates"] if x["team_identity_candidate_id"] == "team_candidate_beta")
    assert row["recheck_multi_anchor_gate"] == "PASS_MULTI_ANCHOR_RECHECK_CANDIDATE"


def test_insufficient_interception_support_remains_unresolved():
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment_payload(xs=(5.0,)))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["progression_metric_recheck_allowed"] is False


def test_middle_pitch_interception_median_remains_unresolved():
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment_payload(xs=(45.0, 55.0)))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["progression_metric_recheck_allowed"] is False


def test_shot_interception_conflict_closes_progression():
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment_payload(xs=(90.0, 95.0)))
    assert result["primary_anchor_conflict_group_count"] == 1
    assert result["progression_metric_recheck_allowed"] is False


def test_goal_kick_interception_conflict_is_not_silently_ignored():
    frame = frame_payload()
    target = frame["team_period_coordinate_frame_candidates"][0]
    target["goalkeeper_goal_kick_anchor_count"] = 3
    target["goalkeeper_goal_kick_direction_candidate"] = "ATTACK_TOWARD_LOW_X_CANDIDATE"
    result = MOD.build_coordinate_frame_anchor_recheck(frame, attachment_payload())
    assert result["primary_anchor_conflict_group_count"] == 1
    assert result["progression_metric_recheck_allowed"] is False


@pytest.mark.parametrize("field,value", [
    ("status", "REVIEW_REQUIRED"),
    ("goalkeeper_interception_primary_direction_anchor_candidate_allowed", False),
    ("outcome_stratified_support_pooling_allowed", False),
])
def test_attachment_gate_must_be_explicitly_admitted(field, value):
    attachment = attachment_payload()
    attachment[field] = value
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment)
    assert result["status"] == "FAIL_CLOSED"
    assert result["progression_metric_recheck_allowed"] is False


def test_attachment_review_or_hard_block_fails_closed():
    attachment = attachment_payload()
    attachment["review_hits"] = ["review"]
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment)
    assert result["status"] == "FAIL_CLOSED"
    attachment = attachment_payload()
    attachment["hard_block_hits"] = ["block"]
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment)
    assert result["status"] == "FAIL_CLOSED"


def test_binding_mismatch_fails_closed():
    attachment = attachment_payload()
    attachment["match_surface_binding_id"] = "different_binding"
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment)
    assert result["status"] == "FAIL_CLOSED"


def test_reflection_contaminated_record_fails_closed():
    attachment = attachment_payload()
    attachment["interception_attachment_records"][0]["overlapping_same_coordinate_object_action_count"] = 1
    result = MOD.build_coordinate_frame_anchor_recheck(frame_payload(), attachment)
    assert result["status"] == "FAIL_CLOSED"


def test_nested_phone_output_directory_rejected(tmp_path):
    fake = tmp_path / "HPFA" / "nested"
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        MOD.validate_out(fake)


def test_no_sample_match_identity_leak():
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert not re.search(r"teamc_[0-9a-f]{8,}", text, flags=re.I)
    assert not re.search(r"\b20\d{2}[-_.]\d{2}[-_.]\d{2}\b", text)
