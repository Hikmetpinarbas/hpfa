from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
sys.path.insert(0, str(SRC))

from visible_action_sequence_candidate_admission import (  # noqa: E402
    build_visible_action_sequence_candidate_admission,
    validate_out,
    write_outputs,
)

BINDING = "msb_generic_surface"
TEAM_A = "teamc_a"
TEAM_B = "teamc_b"
ACTOR_A = "actorc_a"
ACTOR_B = "actorc_b"


def node(
    node_id: str,
    *,
    role: str = "PLAYER_SURFACE_CANDIDATE",
    team: str = TEAM_A,
    actor: str | None = ACTOR_A,
    actor_applicability: str | None = None,
    period: str = "1",
    start: float = 10.0,
    family: str = "PASS",
    terminal: bool = False,
) -> dict:
    if actor_applicability is None:
        actor_applicability = (
            "NOT_APPLICABLE_TEAM_SURFACE"
            if role == "TEAM_SURFACE_CANDIDATE"
            else "APPLICABLE_BOUND_CANDIDATE"
        )
    return {
        "selected_action_node_id": node_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "actor_identity_applicability": actor_applicability,
        "period_candidate": period,
        "start_candidate": str(start),
        "end_candidate": str(start + 12.0),
        "pos_x_candidate": "10",
        "pos_y_candidate": "20",
        "action_family_candidates": [family],
        "terminal_outcome_support_visible": terminal,
        "selected_surface_is_canonical_event": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def action_consequence(n: dict) -> dict:
    return {
        "selected_action_consequence_candidate_id": f"sacc_{n['selected_action_node_id']}",
        "anchor_selected_action_node_id": n["selected_action_node_id"],
        "match_surface_binding_id": BINDING,
        "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
        "canonical_event_count": "UNKNOWN",
    }


def event_consequence(
    n: dict,
    *,
    consequence: str = "NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE",
    zone: str = "NO_ZONE_CHANGE_CANDIDATE",
    zone_rank: int | None = 1,
    turnover: str = "NOT_APPLICABLE",
    false_progression: str = "NOT_APPLICABLE_NO_VISIBLE_ZONE_GAIN",
) -> dict:
    return {
        "selected_event_consequence_candidate_id": f"secs_{n['selected_action_node_id']}",
        "source_selected_action_consequence_candidate_id": f"sacc_{n['selected_action_node_id']}",
        "anchor_selected_action_node_id": n["selected_action_node_id"],
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": n["team_identity_candidate_id"],
        "actor_identity_candidate_id": n["actor_identity_candidate_id"],
        "source_role": n["source_role"],
        "period_candidate": n["period_candidate"],
        "anchor_action_family_candidates": n["action_family_candidates"],
        "anchor_zone_candidate": "MIDDLE_THIRD_CANDIDATE",
        "anchor_zone_rank_candidate": zone_rank,
        "zone_delta_class": zone,
        "turnover_window_class": turnover,
        "false_progression_candidate": false_progression,
        "consequence_class_candidate": consequence,
        "canonical_event_count": "UNKNOWN",
    }


def payloads(nodes: list[dict], event_overrides: dict[str, dict] | None = None):
    event_overrides = event_overrides or {}
    action_records = [action_consequence(n) for n in nodes]
    event_records = []
    for n in nodes:
        kwargs = event_overrides.get(n["selected_action_node_id"], {})
        event_records.append(event_consequence(n, **kwargs))
    action = {
        "module_id": "selected_action_consequence_surface_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "selected_action_nodes": nodes,
        "selected_action_node_count": len(nodes),
        "selected_action_consequence_candidates": action_records,
        "selected_action_consequence_candidate_count": len(action_records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    event = {
        "module_id": "selected_event_consequence_surface_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "source_module_id": "selected_action_consequence_surface_lite_v1",
        "selected_event_consequence_candidates": event_records,
        "selected_event_consequence_candidate_count": len(event_records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return action, event


def build(nodes: list[dict], event_overrides: dict[str, dict] | None = None):
    return build_visible_action_sequence_candidate_admission(
        *payloads(nodes, event_overrides)
    )


def test_same_team_strict_time_layers_form_multi_layer_sequence():
    rows = [
        node("a", start=10),
        node("b", actor=ACTOR_B, start=14, family="CARRY"),
        node("c", start=18, family="SHOT"),
    ]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 1
    sequence = result["visible_action_sequence_candidates"][0]
    assert sequence["time_layer_count"] == 3
    assert sequence["sequence_admission_status"] == "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE"
    assert sequence["duration_between_anchor_times_seconds_candidate"] == 8.0


def test_team_context_nodes_attach_without_becoming_primary_sequence_nodes():
    rows = [
        node("a", start=10),
        node(
            "team",
            role="TEAM_SURFACE_CANDIDATE",
            actor=None,
            start=10,
            family="RESTART",
        ),
        node("b", actor=ACTOR_B, start=14),
    ]
    result = build(rows)
    sequence = result["visible_action_sequence_candidates"][0]
    assert sequence["primary_node_count"] == 2
    assert sequence["team_context_support_node_count"] == 1
    assert result["primary_sequence_eligible_node_count"] == 2
    assert result["team_context_support_node_count"] == 1


def test_team_context_restart_does_not_split_primary_sequence():
    rows = [
        node("a", start=10),
        node(
            "team",
            role="TEAM_SURFACE_CANDIDATE",
            actor=None,
            start=14,
            family="RESTART",
        ),
        node("b", actor=ACTOR_B, start=14),
        node("c", start=18),
    ]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 1
    assert result["visible_action_sequence_candidates"][0]["time_layer_count"] == 3


def test_actor_bound_restart_starts_new_sequence():
    rows = [
        node("a", start=10),
        node("restart", actor=ACTOR_B, start=14, family="RESTART"),
        node("b", start=18),
    ]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["sequence_start_reason_candidate_counts"]["RESTART_PRIMARY_LAYER_START"] == 1


def test_team_handover_splits_and_emits_boundary():
    rows = [
        node("a", start=10, team=TEAM_A),
        node("b", start=14, team=TEAM_B, actor=ACTOR_B),
    ]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["visible_sequence_boundary_candidate_count"] == 1
    boundary = result["visible_sequence_boundary_candidates"][0]
    assert boundary["boundary_type"] == "VISIBLE_TEAM_HANDOVER_CANDIDATE"
    assert boundary["boundary_is_possession_change_truth"] is False


def test_gap_above_twelve_seconds_splits_sequence():
    rows = [node("a", start=10), node("b", start=23, actor=ACTOR_B)]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["sequence_start_reason_candidate_counts"]["AFTER_TIME_GAP"] == 1


def test_exact_twelve_second_gap_is_admitted():
    rows = [node("a", start=10), node("b", start=22, actor=ACTOR_B)]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 1


def test_cross_period_sequence_is_blocked_by_period_boundary():
    rows = [node("a", start=100, period="1"), node("b", start=101, period="2")]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 2
    assert all(sequence["time_layer_count"] == 1 for sequence in result["visible_action_sequence_candidates"])


def test_mixed_team_same_time_layer_is_review_and_not_ordered():
    rows = [
        node("a", start=10, team=TEAM_A),
        node("b", start=10, team=TEAM_B, actor=ACTOR_B),
    ]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 0
    assert result["time_layer_state_counts"]["MIXED_TEAM_PRIMARY_LAYER_REVIEW_REQUIRED"] == 1
    assert result["review_or_context_only_time_layer_count"] == 1
    layer = result["review_or_context_only_time_layers"][0]
    assert layer["same_timestamp_internal_ordering_allowed"] is False


def test_team_context_only_layer_is_preserved_and_splits():
    rows = [
        node("a", start=10),
        node(
            "team",
            role="TEAM_SURFACE_CANDIDATE",
            actor=None,
            start=14,
            family="SHOT",
        ),
        node("b", actor=ACTOR_B, start=18),
    ]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["time_layer_state_counts"]["TEAM_CONTEXT_ONLY_LAYER"] == 1
    assert result["node_assignment_type_counts"]["TEAM_CONTEXT_ONLY_LAYER_SUPPORT"] == 1


def test_terminal_support_closes_sequence():
    rows = [
        node("a", start=10, terminal=True),
        node("b", actor=ACTOR_B, start=14),
    ]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["sequence_start_reason_candidate_counts"]["AFTER_TERMINAL_OUTCOME_SUPPORT"] == 1


def test_every_node_is_assigned_exactly_once():
    rows = [
        node("a", start=10),
        node("b", actor=ACTOR_B, start=14),
        node(
            "team",
            role="TEAM_SURFACE_CANDIDATE",
            actor=None,
            start=14,
            family="PASS",
        ),
        node("mix_a", start=20, team=TEAM_A),
        node("mix_b", start=20, team=TEAM_B, actor=ACTOR_B),
    ]
    result = build(rows)
    assignments = result["node_assignment_records"]
    ids = [item["selected_action_node_id"] for item in assignments]
    assert len(ids) == len(rows)
    assert len(set(ids)) == len(rows)
    assert set(ids) == {row["selected_action_node_id"] for row in rows}


def test_trace_signals_aggregate_without_truth_claim():
    rows = [
        node("recovery", start=10, family="RECOVERY"),
        node("pass", actor=ACTOR_B, start=14, family="PASS"),
        node("shot", start=18, family="SHOT"),
    ]
    overrides = {
        "pass": {
            "consequence": "RISKY_CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE",
            "zone": "ZONE_GAIN_CANDIDATE",
            "false_progression": "FALSE_PROGRESSION_CANDIDATE",
        }
    }
    result = build(rows, overrides)
    sequence = result["visible_action_sequence_candidates"][0]
    assert "REGAIN_TO_VISIBLE_CONTINUATION_CANDIDATE" in sequence["trace_signal_candidates"]
    assert "SHOT_CHAIN_CANDIDATE" in sequence["trace_signal_candidates"]
    assert "PROGRESSION_TO_HANDOVER_TRACE_CANDIDATE" in sequence["trace_signal_candidates"]
    assert sequence["visible_sequence_candidate_is_sequence_truth"] is False


def test_unresolved_consequence_marks_context_review_without_blocking_admission():
    rows = [node("a", start=10), node("b", actor=ACTOR_B, start=14)]
    overrides = {
        "b": {
            "consequence": "UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED",
            "zone": "UNRESOLVED_ZONE_DELTA_REVIEW_REQUIRED",
        }
    }
    result = build(rows, overrides)
    assert result["visible_action_sequence_candidate_count"] == 1
    assert result["sequence_context_review_required_count"] == 1
    assert result["visible_action_sequence_candidates"][0]["sequence_context_status"] == "REVIEW_REQUIRED"


def test_cross_team_team_context_support_is_reviewed_not_recounted():
    rows = [
        node("a", start=10, team=TEAM_A),
        node(
            "team",
            role="TEAM_SURFACE_CANDIDATE",
            team=TEAM_B,
            actor=None,
            start=10,
        ),
    ]
    result = build(rows)
    sequence = result["visible_action_sequence_candidates"][0]
    assert sequence["cross_team_context_support_review_count"] == 1
    assert result["cross_team_context_support_review_count"] == 1
    assert result["node_assignment_count"] == 2


def test_invalid_binding_fails_closed():
    rows = [node("a")]
    action, event = payloads(rows)
    event["match_surface_binding_id"] = "other"
    result = build_visible_action_sequence_candidate_admission(action, event)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_surface_binding_mismatch" in result["hard_block_hits"]


def test_claim_boundaries_remain_closed():
    result = build([node("a")])
    assert result["event_instance_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["sequence_truth"] is False
    assert result["possession_truth"] is False
    assert result["phase_truth"] is False
    assert result["tactical_truth"] is False
    assert result["production_release"] is False


def test_nested_phone_output_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(tmp_path / "HPFA" / "nested")


def test_outputs_are_written(tmp_path: Path):
    result = build([node("a")])
    paths = write_outputs(result, tmp_path)
    assert all(path.exists() for path in paths.values())
    stored = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert stored["module_id"] == "visible_action_sequence_candidate_admission_lite_v1"


def test_no_sample_match_identity_leak():
    text = "\n".join(path.read_text(encoding="utf-8") for path in (MODULE_ROOT / "src").glob("*.py"))
    forbidden = ["Australia", "Turkey", "World Cup", "Galatasaray", "Juventus", "6935", "77798"]
    assert not any(item in text for item in forbidden)
