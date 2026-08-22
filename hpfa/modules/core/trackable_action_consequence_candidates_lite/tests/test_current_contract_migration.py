from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hpfa.modules.core.trackable_action_consequence_candidates_lite.src.trackable_action_consequence_candidates import (
    build_trackable_action_consequence_candidates,
    validate_out,
)

BINDING = "msb_" + "a" * 24


def trace(trace_id: str, *, team: str = "team_a", actor: str = "actor_a", start: float = 10.0, family: str = "PASS", period: str = "1", role: str = "PLAYER_SURFACE_CANDIDATE", x: float = 10.0, y: float = 20.0) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": period,
        "start_candidate": str(start),
        "end_candidate": str(start + 1.0),
        "pos_x_candidate": str(x),
        "pos_y_candidate": str(y),
        "action_family_candidates": [family],
        "trackable_action_candidate_is_event_truth": False,
        "physical_action_identity_truth": False,
        "sequence_link_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def atom(atom_id: str, *, start: float, atom_class: str = "DERIVED_CONSEQUENCE_ATOM", role: str = "PLAYER_SURFACE_CANDIDATE", x: float = 10.0, y: float = 20.0, period: str = "1") -> dict:
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "atom_class": atom_class,
        "atom_status": "PASS",
        "period_candidate": period,
        "start_candidate": str(start),
        "end_candidate": str(start + 1.0),
        "pos_x_candidate": str(x),
        "pos_y_candidate": str(y),
        "canonical_event_count": "UNKNOWN",
    }


def payloads(traces: list[dict], atoms: list[dict] | None = None) -> tuple[dict, dict]:
    atoms = atoms or []
    t = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": traces,
        "trackable_action_trace_candidate_count": len(traces),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    e = {
        "module_id": "evidence_atom_inventory_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": atoms,
        "evidence_atom_count": len(atoms),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return t, e


def build(traces: list[dict], atoms: list[dict] | None = None) -> dict:
    return build_trackable_action_consequence_candidates(*payloads(traces, atoms))


def test_same_timestamp_is_never_linked() -> None:
    a = trace("a", start=10, actor="actor_a")
    b = trace("b", start=10, actor="actor_b", x=30)
    c = trace("c", start=14, actor="actor_c", x=40)
    result = build([a, b, c])
    by_anchor = {r["anchor_trackable_action_trace_candidate_id"]: r for r in result["trackable_action_consequence_candidates"]}
    assert by_anchor["a"]["visible_follow_up_trace_ids"] == ["c"]
    assert by_anchor["b"]["visible_follow_up_trace_ids"] == ["c"]
    assert by_anchor["a"]["first_visible_follow_up_delta_seconds"] == 4.0


def test_cross_period_is_never_linked() -> None:
    a = trace("a", start=10, period="1")
    b = trace("b", start=11, period="2")
    result = build([a, b])
    assert all(not row["visible_follow_up_trace_ids"] for row in result["trackable_action_consequence_candidates"])


def test_only_three_distinct_future_time_layers_are_used() -> None:
    traces = [trace("a", start=10)] + [trace(f"n{i}", start=start, x=20+i) for i, start in enumerate((14, 17, 21, 22), 1)]
    result = build(traces)
    row = next(r for r in result["trackable_action_consequence_candidates"] if r["anchor_trackable_action_trace_candidate_id"] == "a")
    assert row["follow_up_layer_count"] == 3
    assert row["visible_follow_up_trace_count_5s"] == 1
    assert row["visible_follow_up_trace_count_8s"] == 2
    assert row["visible_follow_up_trace_count_12s"] == 3


def test_same_team_continuation_and_opponent_handover() -> None:
    a = trace("a", start=10, team="A")
    b = trace("b", start=14, team="A", actor="b", x=20)
    c = trace("c", start=18, team="B", actor="c", x=30)
    result = build([a, b, c])
    by_anchor = {r["anchor_trackable_action_trace_candidate_id"]: r for r in result["trackable_action_consequence_candidates"]}
    assert by_anchor["a"]["primary_consequence_candidate"] == "SAME_TEAM_CONTINUATION_CANDIDATE"
    assert by_anchor["b"]["primary_consequence_candidate"] == "OPPONENT_HANDOVER_CANDIDATE"


def test_same_team_shot_follow_up_is_candidate_not_causal_truth() -> None:
    a = trace("a", start=10, team="A")
    s = trace("s", start=14, team="A", actor="s", family="SHOT", x=90)
    result = build([a, s])
    row = next(r for r in result["trackable_action_consequence_candidates"] if r["anchor_trackable_action_trace_candidate_id"] == "a")
    assert row["primary_consequence_candidate"] == "SHOT_FOLLOW_UP_CANDIDATE"
    assert row["consequence_candidate_is_causal_truth"] is False


def test_mixed_team_first_future_layer_stays_review_required() -> None:
    a = trace("a", start=10, team="A")
    b = trace("b", start=14, team="A", actor="b", x=20)
    c = trace("c", start=14, team="B", actor="c", x=30)
    result = build([a, b, c])
    row = next(r for r in result["trackable_action_consequence_candidates"] if r["anchor_trackable_action_trace_candidate_id"] == "a")
    assert row["primary_consequence_candidate"] == "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE"
    assert row["record_status"] == "REVIEW_REQUIRED"


def test_terminal_support_is_exact_core_and_candidate_only() -> None:
    a = trace("a", start=10)
    result = build([a], [atom("term", start=10, atom_class="TERMINAL_OUTCOME_ATOM")])
    row = result["trackable_action_consequence_candidates"][0]
    assert row["terminal_outcome_support_visible"] is True
    assert row["primary_consequence_candidate"] == "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"
    assert row["validated_event_identity"] is False


def test_mismatched_support_atom_does_not_attach() -> None:
    a = trace("a", start=10)
    result = build([a], [atom("derived", start=10, x=99)])
    row = result["trackable_action_consequence_candidates"][0]
    assert row["supporting_consequence_evidence_atom_ids"] == []


def test_trace_requires_actor_bearing_primary_role() -> None:
    bad = trace("team", role="TEAM_SURFACE_CANDIDATE", actor="")
    result = build([bad])
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("trace_source_role_rejected") for hit in result["hard_block_hits"])


def test_duplicate_trace_id_fails_closed() -> None:
    result = build([trace("dup", start=10), trace("dup", start=14, x=30)])
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("duplicate_trace_id") for hit in result["hard_block_hits"])


def test_claim_boundaries_remain_closed() -> None:
    result = build([trace("a", start=10), trace("b", start=14, x=30)])
    assert result["same_time_link_allowed"] is False
    assert result["negative_time_link_allowed"] is False
    assert result["cross_period_link_allowed"] is False
    assert result["source_row_order_is_temporal_truth"] is False
    assert result["consequence_candidate_is_causal_truth"] is False
    assert result["continuation_candidate_is_possession_truth"] is False
    assert result["window_is_sequence_truth"] is False
    assert result["sequence_link_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_input_payloads_are_not_mutated() -> None:
    source = payloads([trace("a")])
    original = copy.deepcopy(source)
    build_trackable_action_consequence_candidates(*source)
    assert source == original


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak() -> None:
    source = Path("hpfa/modules/core/trackable_action_consequence_candidates_lite/src/trackable_action_consequence_candidates.py").read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Galatasaray")
    assert not any(token in source for token in forbidden)
