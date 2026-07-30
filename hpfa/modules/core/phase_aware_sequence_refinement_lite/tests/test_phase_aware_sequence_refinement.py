import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))
from phase_aware_sequence_refinement import (
    build_phase_aware_sequence_refinement,
    write_outputs,
)

BINDING = "msb_generic"


def segment(
    segment_id,
    phase,
    start,
    end,
    anchors=2,
    sequence_id="s1",
    status="PHASE_DERIVED_WITH_WARNINGS",
):
    return {
        "event_derived_phase_segment_id": segment_id,
        "source_visible_action_sequence_candidate_id": sequence_id,
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": "team_a",
        "period_candidate": "1",
        "phase_class_candidate": phase,
        "phase_derivation_status": status,
        "start_time_candidate": start,
        "end_time_candidate": end,
        "visible_anchor_count": anchors,
    }


def payload(segments, status="PASS"):
    return {
        "module_id": "event_derived_phase_state_lite_v1",
        "status": status,
        "module_status": status,
        "match_surface_binding_id": BINDING,
        "event_derived_phase_segments": segments,
        "event_derived_phase_segment_count": len(segments),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_single_anchor_A_B_A_is_refinement_candidate():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 3, 2),
                segment("b", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 4, 4, 1),
                segment("c", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 5, 7, 2),
            ]
        )
    )
    assert result["A_B_A_phase_oscillation_count"] == 1
    assert result["refinement_candidate_count"] == 1
    assert result["automatic_merge_count"] == 0
    assert result["retained_source_phase_segment_count"] == 3


def test_protected_finishing_phase_is_retained():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("a", "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE", 1, 3, 2),
                segment("b", "FINISHING_VISIBLE_PHASE_CANDIDATE", 4, 4, 1),
                segment("c", "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE", 5, 7, 2),
            ]
        )
    )
    middle = result["phase_refinement_decisions"][1]
    assert middle["decision_class"] == "RETAIN_PROTECTED_PHASE_CHANGE"


def test_multiple_anchor_middle_phase_is_retained():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 3, 2),
                segment("b", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 4, 6, 2),
                segment("c", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 7, 9, 2),
            ]
        )
    )
    assert result["decision_class_counts"]["RETAIN_SUPPORTED_PHASE_CHANGE"] == 1


def test_review_bounded_triplet_is_insufficient_anchor():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 3, 2),
                segment(
                    "b",
                    "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE",
                    4,
                    4,
                    1,
                    status="PHASE_REVIEW_REQUIRED",
                ),
                segment("c", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 5, 7, 2),
            ]
        )
    )
    assert result["insufficient_anchor_review_count"] == 1
    assert result["refinement_candidate_count"] == 0


def test_weak_flanks_are_insufficient_anchor():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 1, 1),
                segment("b", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 2, 2, 1),
                segment("c", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 3, 3, 1),
            ]
        )
    )
    assert result["insufficient_anchor_review_count"] == 1


def test_same_timestamp_triplet_is_not_ordered_as_refinement_candidate():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 2, 2),
                segment("b", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 2, 2, 1),
                segment("c", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 2, 3, 2),
            ]
        )
    )
    assert result["insufficient_anchor_review_count"] == 1
    assert result["refinement_candidate_count"] == 0
    assert result["hard_block_hits"] == []


def test_equal_timestamp_segment_ids_do_not_create_false_order_failure():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("z", "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE", 2, 2, 1),
                segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 2, 2, 1),
            ]
        )
    )
    assert result["hard_block_hits"] == []
    assert result["phase_refinement_decision_count"] == 2
    assert result["same_timestamp_adjacent_phase_pair_count"] == 1


def test_cross_sequence_segments_do_not_form_A_B_A():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 3, 2, "s1"),
                segment("b", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 4, 4, 1, "s2"),
                segment("c", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 5, 7, 2, "s3"),
            ]
        )
    )
    assert result["A_B_A_phase_oscillation_count"] == 0


def test_duplicate_segment_id_fails_closed():
    duplicate = segment("dup", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 2)
    result = build_phase_aware_sequence_refinement(payload([duplicate, dict(duplicate)]))
    assert result["status"] == "FAIL_CLOSED"
    assert result["phase_refinement_decisions"] == []


def test_declared_count_mismatch_fails_closed():
    data = payload([segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 2)])
    data["event_derived_phase_segment_count"] = 2
    result = build_phase_aware_sequence_refinement(data)
    assert result["status"] == "FAIL_CLOSED"


def test_invalid_time_fails_closed():
    result = build_phase_aware_sequence_refinement(
        payload([segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 3, 2)])
    )
    assert result["status"] == "FAIL_CLOSED"


def test_sequence_team_or_period_conflict_fails_closed():
    first = segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 2)
    second = segment("b", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 3, 4)
    second["team_identity_candidate_id"] = "team_b"
    result = build_phase_aware_sequence_refinement(payload([first, second]))
    assert result["status"] == "FAIL_CLOSED"


def test_source_sequence_phase_order_must_be_preserved():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("late", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 5, 6),
                segment("early", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 1, 2),
            ]
        )
    )
    assert result["status"] == "FAIL_CLOSED"


def test_source_sequence_end_time_cannot_move_backwards():
    result = build_phase_aware_sequence_refinement(
        payload(
            [
                segment("first", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 4),
                segment("second", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 2, 3),
            ]
        )
    )
    assert result["status"] == "FAIL_CLOSED"


def test_upstream_review_is_preserved():
    result = build_phase_aware_sequence_refinement(
        payload([segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 2)], "REVIEW_REQUIRED")
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert any("phase_upstream_status_review" in x for x in result["review_hits"])


def test_nested_phone_output_is_rejected(tmp_path):
    data = build_phase_aware_sequence_refinement(
        payload([segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 2)])
    )
    nested = tmp_path / "HPFA" / "nested"
    try:
        write_outputs(data, nested)
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested phone output should be rejected")


def test_outputs_are_written(tmp_path):
    data = build_phase_aware_sequence_refinement(
        payload([segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 2)])
    )
    paths = write_outputs(data, tmp_path)
    assert set(paths) == {"json", "summary", "analyst"}
    assert json.loads(paths["json"].read_text())["production_release"] is False


def test_no_source_segment_is_deleted_or_merged():
    source = [
        segment("a", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 1, 3, 2),
        segment("b", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 4, 4, 1),
        segment("c", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 5, 7, 2),
    ]
    result = build_phase_aware_sequence_refinement(payload(source))
    assert result["phase_refinement_decision_count"] == len(source)
    assert all(x["segment_preserved"] for x in result["phase_refinement_decisions"])
    assert all(not x["automatic_merge_applied"] for x in result["phase_refinement_decisions"])
    assert all(not x["automatic_delete_applied"] for x in result["phase_refinement_decisions"])
