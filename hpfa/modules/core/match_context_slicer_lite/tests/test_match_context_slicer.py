import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from match_context_slicer import build_match_context_slicer, write_outputs

BINDING = "msb_generic"
TEAM_A = "team_a"
TEAM_B = "team_b"


def node(node_id, team, period, start, *, goal=False):
    return {
        "selected_action_node_id": node_id,
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": f"actor_{node_id}",
        "period_candidate": str(period),
        "start_candidate": str(start),
        "end_candidate": str(start),
        "action_family_candidates": ["SHOT" if goal else "PASS"],
        "terminal_outcome_support_visible": goal,
        "support_normalized_labels": ["chances", "goals"] if goal else [],
    }


def phase(segment_id, team, period, start, end=None):
    return {
        "event_derived_phase_segment_id": segment_id,
        "source_visible_action_sequence_candidate_id": f"seq_{segment_id}",
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": team,
        "period_candidate": str(period),
        "start_time_candidate": start,
        "end_time_candidate": start if end is None else end,
        "phase_class_candidate": "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE",
    }


def decision(segment_id):
    return {
        "phase_refinement_decision_id": f"decision_{segment_id}",
        "source_event_derived_phase_segment_id": segment_id,
        "decision_class": "RETAIN_NO_A_B_A_OSCILLATION",
    }


def payloads(nodes, phases, *, action_status="PASS", phase_status="PASS", refinement_status="PASS"):
    actions = {
        "module_id": "selected_action_consequence_surface_lite_v1",
        "status": action_status,
        "module_status": action_status,
        "match_surface_binding_id": BINDING,
        "selected_action_nodes": nodes,
        "selected_action_node_count": len(nodes),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    phase_payload = {
        "module_id": "event_derived_phase_state_lite_v1",
        "status": phase_status,
        "module_status": phase_status,
        "match_surface_binding_id": BINDING,
        "event_derived_phase_segments": phases,
        "event_derived_phase_segment_count": len(phases),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    decisions = [decision(item["event_derived_phase_segment_id"]) for item in phases]
    refinement = {
        "module_id": "phase_aware_sequence_refinement_lite_v1",
        "status": refinement_status,
        "module_status": refinement_status,
        "match_surface_binding_id": BINDING,
        "phase_refinement_decisions": decisions,
        "phase_refinement_decision_count": len(decisions),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return actions, phase_payload, refinement


def base_nodes():
    return [
        node("n1", TEAM_A, 1, 5),
        node("g1", TEAM_A, 1, 1200, goal=True),
        node("n2", TEAM_B, 1, 2000),
        node("n3", TEAM_A, 2, 3000),
        node("g2", TEAM_B, 2, 4200, goal=True),
        node("n4", TEAM_B, 2, 5000),
    ]


def test_period_minute_and_score_state_are_attached():
    phases = [
        phase("p1", TEAM_A, 1, 600),
        phase("p2", TEAM_A, 1, 1300),
        phase("p3", TEAM_B, 1, 1400),
        phase("p4", TEAM_A, 2, 4300),
    ]
    result = build_match_context_slicer(*payloads(base_nodes(), phases))
    assert result["time_axis_candidate"] == "CUMULATIVE_ABSOLUTE_SECONDS_CANDIDATE"
    assert result["goal_context_candidate_count"] == 2
    assert result["match_context_slice_count"] == 4
    states = [item["team_relative_score_state_candidate"] for item in result["match_context_slices"]]
    assert states == ["DRAWING_CANDIDATE", "LEADING_CANDIDATE", "TRAILING_CANDIDATE", "DRAWING_CANDIDATE"]
    assert result["match_context_slices"][0]["minute_display_candidate"] == "11'"


def test_goal_requires_shot_terminal_and_goals_label():
    candidates = base_nodes()
    fake = node("fake", TEAM_A, 2, 4500)
    fake["support_normalized_labels"] = ["goals"]
    candidates.append(fake)
    result = build_match_context_slicer(*payloads(candidates, [phase("p1", TEAM_A, 2, 4600)]))
    assert result["goal_context_candidate_count"] == 2


def test_same_timestamp_goal_does_not_create_artificial_before_after_order():
    phases = [phase("p1", TEAM_A, 1, 1200)]
    result = build_match_context_slicer(*payloads(base_nodes(), phases))
    item = result["match_context_slices"][0]
    assert item["team_relative_score_state_candidate"] == "SAME_TIME_GOAL_CONTEXT_REVIEW_REQUIRED"
    assert result["same_time_goal_context_review_count"] == 1


def test_card_and_lineup_state_remain_unknown():
    result = build_match_context_slicer(*payloads(base_nodes(), [phase("p1", TEAM_A, 1, 600)]))
    item = result["match_context_slices"][0]
    assert item["card_state_candidate"].startswith("UNKNOWN_")
    assert item["lineup_state_candidate"].startswith("UNKNOWN_")
    assert result["scoreboard_truth"] is False


def test_refinement_decision_is_preserved():
    result = build_match_context_slicer(*payloads(base_nodes(), [phase("p1", TEAM_A, 1, 600)]))
    item = result["match_context_slices"][0]
    assert item["source_phase_refinement_decision_id"] == "decision_p1"
    assert item["phase_refinement_decision_class"] == "RETAIN_NO_A_B_A_OSCILLATION"


def test_cross_period_non_monotonic_axis_fails_closed():
    nodes = [node("n1", TEAM_A, 1, 1000), node("n2", TEAM_B, 1, 2000), node("n3", TEAM_A, 2, 10), node("n4", TEAM_B, 2, 20)]
    result = build_match_context_slicer(*payloads(nodes, [phase("p1", TEAM_A, 1, 1000)]))
    assert result["status"] == "FAIL_CLOSED"
    assert "absolute_match_time_axis_not_monotonic_across_periods" in result["hard_block_hits"]


def test_two_team_context_is_required():
    nodes = [node("n1", TEAM_A, 1, 5), node("n2", TEAM_A, 1, 10)]
    result = build_match_context_slicer(*payloads(nodes, [phase("p1", TEAM_A, 1, 6)]))
    assert result["status"] == "FAIL_CLOSED"
    assert result["match_context_slices"] == []


def test_binding_mismatch_fails_closed():
    actions, phases, refinement = payloads(base_nodes(), [phase("p1", TEAM_A, 1, 600)])
    refinement["match_surface_binding_id"] = "other"
    result = build_match_context_slicer(actions, phases, refinement)
    assert result["status"] == "FAIL_CLOSED"


def test_missing_refinement_decision_fails_closed():
    actions, phases, refinement = payloads(base_nodes(), [phase("p1", TEAM_A, 1, 600)])
    refinement["phase_refinement_decisions"] = []
    refinement["phase_refinement_decision_count"] = 0
    result = build_match_context_slicer(actions, phases, refinement)
    assert result["status"] == "FAIL_CLOSED"


def test_upstream_review_is_preserved():
    result = build_match_context_slicer(
        *payloads(base_nodes(), [phase("p1", TEAM_A, 1, 600)], refinement_status="REVIEW_REQUIRED")
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert any("phase_aware_sequence_refinement_lite_v1_status_review" in hit for hit in result["review_hits"])


def test_nested_phone_output_is_rejected(tmp_path):
    result = build_match_context_slicer(*payloads(base_nodes(), [phase("p1", TEAM_A, 1, 600)]))
    try:
        write_outputs(result, tmp_path / "HPFA" / "nested")
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested phone output should be rejected")


def test_outputs_are_written(tmp_path):
    result = build_match_context_slicer(*payloads(base_nodes(), [phase("p1", TEAM_A, 1, 600)]))
    paths = write_outputs(result, tmp_path)
    assert set(paths) == {"json", "summary", "analyst"}
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["production_release"] is False


def test_no_sample_match_identity_leak():
    source = (SRC / "match_context_slicer.py").read_text(encoding="utf-8")
    for forbidden in ("Australia", "Turkey", "World Cup", "Galatasaray", "6935", "77798"):
        assert forbidden not in source
