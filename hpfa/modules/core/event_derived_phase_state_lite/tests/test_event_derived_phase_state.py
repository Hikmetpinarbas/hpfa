import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))
from event_derived_phase_state import build_event_derived_phase_state, write_outputs

BINDING = "msb_generic"


def node(node_id, team="a", start=10, family="PASS"):
    return {
        "selected_action_node_id": node_id,
        "team_identity_candidate_id": team,
        "start_candidate": str(start),
        "action_family_candidates": [family],
    }


def event(node_id, zone):
    ranks = {"OWN_THIRD_CANDIDATE": 0, "MIDDLE_THIRD_CANDIDATE": 1,
             "FINAL_THIRD_CANDIDATE": 2, "OPPONENT_BOX_CANDIDATE": 3}
    return {
        "anchor_selected_action_node_id": node_id,
        "anchor_zone_candidate": zone,
        "anchor_zone_rank_candidate": ranks[zone],
    }


def payloads(nodes, events, sequences, upstream_status="PASS", boundaries=None):
    common = {
        "status": upstream_status,
        "module_status": upstream_status,
        "match_surface_binding_id": BINDING,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    action = {
        **common,
        "module_id": "selected_action_consequence_surface_lite_v1",
        "selected_action_nodes": nodes,
    }
    event_payload = {
        **common,
        "module_id": "selected_event_consequence_surface_lite_v1",
        "selected_event_consequence_candidates": events,
    }
    boundaries = boundaries or []
    sequence = {
        **common,
        "module_id": "visible_action_sequence_candidate_admission_lite_v1",
        "visible_action_sequence_candidates": sequences,
        "visible_action_sequence_candidate_count": len(sequences),
        "visible_sequence_boundary_candidates": boundaries,
        "visible_sequence_boundary_candidate_count": len(boundaries),
    }
    return sequence, action, event_payload


def sequence(seq_id, node_ids, team="a", start=10, end=20, signals=None):
    return {
        "visible_action_sequence_candidate_id": seq_id,
        "team_identity_candidate_id": team,
        "period_candidate": "1",
        "start_time_candidate": start,
        "end_time_candidate": end,
        "primary_selected_action_node_ids": node_ids,
        "trace_signal_candidates": signals or [],
    }


def handover(from_id="s1", to_id="s2", from_team="a", to_team="b", time=14):
    return {
        "visible_sequence_boundary_candidate_id": f"boundary_{from_id}_{to_id}",
        "boundary_type": "VISIBLE_TEAM_HANDOVER_CANDIDATE",
        "period_candidate": "1",
        "boundary_time_candidate": time,
        "from_team_identity_candidate_id": from_team,
        "to_team_identity_candidate_id": to_team,
        "from_visible_action_sequence_candidate_id": from_id,
        "to_visible_action_sequence_candidate_id": to_id,
    }


def test_zone_progression_creates_distinct_phase_segments():
    nodes = [node("a", start=10), node("b", start=14), node("c", start=18)]
    events = [
        event("a", "OWN_THIRD_CANDIDATE"),
        event("b", "MIDDLE_THIRD_CANDIDATE"),
        event("c", "FINAL_THIRD_CANDIDATE"),
    ]
    result = build_event_derived_phase_state(
        *payloads(nodes, events, [sequence("s1", ["a", "b", "c"])])
    )
    assert [x["phase_class_candidate"] for x in result["event_derived_phase_segments"]] == [
        "BUILD_UP_VISIBLE_PHASE_CANDIDATE",
        "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE",
        "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE",
    ]
    assert result["phase_state_derived_from_event_evidence"] is True


def test_restart_and_finishing_override_zone_label():
    nodes = [
        node("a", start=10, family="RESTART"),
        node("b", start=14, family="PASS"),
        node("c", start=18, family="SHOT"),
    ]
    events = [event("a", "OWN_THIRD_CANDIDATE"), event("b", "FINAL_THIRD_CANDIDATE"),
              event("c", "FINAL_THIRD_CANDIDATE")]
    result = build_event_derived_phase_state(
        *payloads(nodes, events, [sequence("s1", ["a", "b", "c"])])
    )
    assert result["phase_class_candidate_counts"]["RESTART_VISIBLE_PHASE_CANDIDATE"] == 1
    assert result["phase_class_candidate_counts"]["FINISHING_VISIBLE_PHASE_CANDIDATE"] == 1


def test_regain_trace_uses_bounded_hysteresis_transition_prefix():
    nodes = [node("a", start=10, family="RECOVERY"), node("b", start=13), node("c", start=19)]
    events = [event("a", "MIDDLE_THIRD_CANDIDATE"), event("b", "MIDDLE_THIRD_CANDIDATE"),
              event("c", "FINAL_THIRD_CANDIDATE")]
    seq = sequence("s1", ["a", "b", "c"], signals=["REGAIN_TO_VISIBLE_CONTINUATION_CANDIDATE"])
    result = build_event_derived_phase_state(*payloads(nodes, events, [seq]))
    first = result["event_derived_phase_segments"][0]
    assert first["phase_class_candidate"] == "ATTACK_TRANSITION_VISIBLE_PHASE_CANDIDATE"
    assert first["visible_anchor_count"] == 2
    assert result["transition_hysteresis_visible_anchor_count"] == 2


def test_team_handover_creates_context_window_without_claiming_off_ball_actions():
    nodes = [node("a", team="a", start=10), node("b", team="b", start=14)]
    events = [event("a", "MIDDLE_THIRD_CANDIDATE"), event("b", "MIDDLE_THIRD_CANDIDATE")]
    sequences = [
        sequence("s1", ["a"], team="a", start=10, end=10),
        sequence("s2", ["b"], team="b", start=14, end=14),
    ]
    result = build_event_derived_phase_state(
        *payloads(nodes, events, sequences, boundaries=[handover()])
    )
    window = result["event_derived_transition_context_windows"][0]
    assert window["losing_team_defensive_transition_actions_observed"] is False
    assert window["off_ball_response_truth"] is False


def test_missing_node_mapping_fails_closed():
    result = build_event_derived_phase_state(
        *payloads([], [], [sequence("s1", ["missing"])])
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["event_derived_phase_segment_count"] == 0


def test_upstream_review_is_preserved_without_erasing_derived_phase():
    nodes = [node("a")]
    result = build_event_derived_phase_state(
        *payloads(
            nodes,
            [event("a", "MIDDLE_THIRD_CANDIDATE")],
            [sequence("s1", ["a"])],
            upstream_status="REVIEW_REQUIRED",
        )
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["phase_derivation_status"] == "PHASE_DERIVED_WITH_WARNINGS"
    assert result["event_derived_phase_segment_count"] == 1


def test_sequence_context_review_is_preserved_at_segment_level():
    nodes = [node("a")]
    seq = sequence("s1", ["a"])
    seq["sequence_context_status"] = "REVIEW_REQUIRED"
    result = build_event_derived_phase_state(
        *payloads(nodes, [event("a", "MIDDLE_THIRD_CANDIDATE")], [seq])
    )
    assert (
        result["event_derived_phase_segments"][0]["phase_derivation_status"]
        == "PHASE_REVIEW_REQUIRED"
    )


def test_late_mapping_failure_removes_partial_phase_output():
    nodes = [node("a")]
    sequences = [sequence("s1", ["a"]), sequence("s2", ["missing"], start=20, end=20)]
    result = build_event_derived_phase_state(
        *payloads(nodes, [event("a", "MIDDLE_THIRD_CANDIDATE")], sequences)
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["event_derived_phase_segment_count"] == 0


def test_claim_boundaries_stay_closed_at_candidate_upstream_level():
    nodes = [node("a")]
    result = build_event_derived_phase_state(
        *payloads(nodes, [event("a", "MIDDLE_THIRD_CANDIDATE")], [sequence("s1", ["a"])])
    )
    assert result["phase_truth"] is False
    assert result["tactical_truth"] is False
    assert result["off_ball_structure_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_flat_outputs_are_written(tmp_path=None):
    import tempfile
    from pathlib import Path

    nodes = [node("a")]
    result = build_event_derived_phase_state(
        *payloads(nodes, [event("a", "MIDDLE_THIRD_CANDIDATE")], [sequence("s1", ["a"])])
    )
    with tempfile.TemporaryDirectory() as directory:
        paths = write_outputs(result, Path(directory))
        assert all(path.exists() for path in paths.values())
        stored = json.loads(paths["json"].read_text(encoding="utf-8"))
        assert stored["module_id"] == "event_derived_phase_state_lite_v1"

def test_adjacent_cross_team_sequences_without_explicit_handover_do_not_create_window():
    nodes = [node("a", team="a", start=10), node("b", team="b", start=14)]
    events = [event("a", "MIDDLE_THIRD_CANDIDATE"), event("b", "MIDDLE_THIRD_CANDIDATE")]
    sequences = [
        sequence("s1", ["a"], team="a", start=10, end=10),
        sequence("s2", ["b"], team="b", start=14, end=30),
    ]
    result = build_event_derived_phase_state(*payloads(nodes, events, sequences))
    assert result["status"] == "PASS"
    assert result["event_derived_transition_context_window_count"] == 0


def test_explicit_handover_window_is_capped_at_ten_seconds():
    nodes = [node("a", team="a", start=10), node("b", team="b", start=14)]
    events = [event("a", "MIDDLE_THIRD_CANDIDATE"), event("b", "MIDDLE_THIRD_CANDIDATE")]
    sequences = [
        sequence("s1", ["a"], team="a", start=10, end=10),
        sequence("s2", ["b"], team="b", start=14, end=40),
    ]
    result = build_event_derived_phase_state(
        *payloads(nodes, events, sequences, boundaries=[handover()])
    )
    window = result["event_derived_transition_context_windows"][0]
    assert window["start_time_candidate"] == 14
    assert window["end_time_candidate"] == 24
    assert window["source_next_sequence_end_time_candidate"] == 40
    assert window["transition_window_ceiling_applied"] is True


def test_broken_handover_reference_fails_closed_and_clears_outputs():
    nodes = [node("a", team="a", start=10), node("b", team="b", start=14)]
    events = [event("a", "MIDDLE_THIRD_CANDIDATE"), event("b", "MIDDLE_THIRD_CANDIDATE")]
    sequences = [
        sequence("s1", ["a"], team="a", start=10, end=10),
        sequence("s2", ["b"], team="b", start=14, end=20),
    ]
    broken = handover(to_id="missing")
    result = build_event_derived_phase_state(
        *payloads(nodes, events, sequences, boundaries=[broken])
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["event_derived_phase_segment_count"] == 0
    assert result["event_derived_transition_context_window_count"] == 0


def test_duplicate_action_node_identity_fails_closed():
    duplicate_nodes = [node("a"), node("a", start=12)]
    result = build_event_derived_phase_state(
        *payloads(
            duplicate_nodes,
            [event("a", "MIDDLE_THIRD_CANDIDATE")],
            [sequence("s1", ["a"])],
        )
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "selected_action_node_id_duplicate:a" in result["hard_block_hits"]


def test_duplicate_event_anchor_identity_fails_closed():
    nodes = [node("a")]
    duplicate_events = [
        event("a", "MIDDLE_THIRD_CANDIDATE"),
        event("a", "FINAL_THIRD_CANDIDATE"),
    ]
    result = build_event_derived_phase_state(
        *payloads(nodes, duplicate_events, [sequence("s1", ["a"])])
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "selected_event_anchor_node_id_duplicate:a" in result["hard_block_hits"]

