from __future__ import annotations

from hpfa.modules.core.trackable_action_consequence_candidates_lite.src.construct_temporal_consequence_contract import (
    apply_construct_temporal_contract,
)
from hpfa.modules.core.trackable_action_consequence_candidates_lite.src.terminal_driven_consequence_boundary import (
    ANCHOR_TERMINAL,
    ENSUING_TERMINAL,
    NO_TERMINAL,
    UNRESOLVED,
    apply_terminal_driven_consequence_boundary,
)


def _row(
    anchor: str,
    *,
    terminal: bool = False,
    layers: list[list[str]] | None = None,
    admitted: list[str] | None = None,
) -> dict:
    layers = layers or []
    visible = [trace_id for layer in layers for trace_id in layer]
    admitted = admitted or []
    return {
        "anchor_trackable_action_trace_candidate_id": anchor,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "anchor_action_family_candidates": ["PASS"],
        "follow_up_trace_ids_by_layer": layers,
        "follow_up_layer_count": len(layers),
        "visible_follow_up_trace_ids": visible,
        "admitted_after_follow_up_trace_ids": admitted,
        "temporal_relation_states_by_trace_id": {
            trace_id: ("AFTER_CONFIRMED" if trace_id in admitted else "ORDER_INDETERMINATE")
            for trace_id in visible
        },
        "terminal_outcome_support_visible": terminal,
    }


def _payload(rows: list[dict]) -> dict:
    return {
        "status": "PASS",
        "module_status": "PASS",
        "hard_block_hits": [],
        "review_hits": [],
        "window_seconds": [5.0, 8.0, 12.0],
        "trackable_action_consequence_candidates": rows,
    }


def test_anchor_terminal_closes_continuation_search_but_preserves_raw_lineage() -> None:
    out = apply_terminal_driven_consequence_boundary(
        _payload([
            _row(
                "shot",
                terminal=True,
                layers=[["restart"], ["next_pass"]],
                admitted=["restart", "next_pass"],
            ),
            _row("restart"),
            _row("next_pass"),
        ])
    )
    row = out["trackable_action_consequence_candidates"][0]

    assert row["terminal_search_boundary_state"] == ANCHOR_TERMINAL
    assert row["visible_follow_up_trace_ids"] == []
    assert row["admitted_after_follow_up_trace_ids"] == []
    assert row["follow_up_trace_ids_by_layer"] == []
    assert row["pre_terminal_search_admitted_after_follow_up_trace_ids"] == ["restart", "next_pass"]
    assert row["terminal_boundary_excluded_admitted_after_trace_ids"] == ["restart", "next_pass"]
    assert out["anchor_terminal_boundary_count"] == 1


def test_first_admitted_terminal_layer_is_inclusive_and_later_layers_are_excluded() -> None:
    out = apply_terminal_driven_consequence_boundary(
        _payload([
            _row(
                "build",
                layers=[["pass1"], ["shot", "same_time_other"], ["restart"]],
                admitted=["pass1", "shot", "same_time_other", "restart"],
            ),
            _row("pass1"),
            _row("shot", terminal=True),
            _row("same_time_other"),
            _row("restart"),
        ])
    )
    row = out["trackable_action_consequence_candidates"][0]

    assert row["terminal_search_boundary_state"] == ENSUING_TERMINAL
    assert row["terminal_search_boundary_trace_ids"] == ["shot"]
    assert row["follow_up_trace_ids_by_layer"] == [["pass1"], ["shot", "same_time_other"]]
    assert row["admitted_after_follow_up_trace_ids"] == ["pass1", "shot", "same_time_other"]
    assert row["terminal_boundary_excluded_admitted_after_trace_ids"] == ["restart"]
    assert row["terminal_search_boundary_same_time_layer_inclusive"] is True
    assert row["terminal_search_boundary_orders_same_time_action"] is False
    assert out["ensuing_terminal_boundary_count"] == 1


def test_visible_but_not_after_confirmed_terminal_does_not_close_search() -> None:
    out = apply_terminal_driven_consequence_boundary(
        _payload([
            _row(
                "anchor",
                layers=[["terminal_unordered"], ["later"]],
                admitted=["later"],
            ),
            _row("terminal_unordered", terminal=True),
            _row("later"),
        ])
    )
    row = out["trackable_action_consequence_candidates"][0]

    assert row["terminal_search_boundary_state"] == NO_TERMINAL
    assert row["visible_follow_up_trace_ids"] == ["terminal_unordered", "later"]
    assert row["admitted_after_follow_up_trace_ids"] == ["later"]
    assert row["terminal_boundary_excluded_visible_follow_up_trace_ids"] == []


def test_missing_layer_lineage_fails_to_review_instead_of_guessing() -> None:
    row = _row("anchor")
    row["visible_follow_up_trace_ids"] = ["later"]
    row["admitted_after_follow_up_trace_ids"] = ["later"]
    row["follow_up_trace_ids_by_layer"] = []
    out = apply_terminal_driven_consequence_boundary(_payload([row, _row("later")]))
    bounded = out["trackable_action_consequence_candidates"][0]

    assert bounded["terminal_search_boundary_state"] == UNRESOLVED
    assert out["terminal_boundary_unresolved_count"] == 1
    assert "terminal_driven_consequence_boundary_unresolved" in out["review_hits"]
    assert out["status"] == "REVIEW_REQUIRED"


def test_construct_temporal_contract_executes_terminal_boundary_before_contract_metadata() -> None:
    out = apply_construct_temporal_contract(
        _payload([
            _row("anchor", layers=[["terminal"], ["restart"]], admitted=["terminal", "restart"]),
            _row("terminal", terminal=True),
            _row("restart"),
        ])
    )
    row = out["trackable_action_consequence_candidates"][0]

    assert out["terminal_driven_consequence_search_enabled"] is True
    assert row["terminal_search_boundary_state"] == ENSUING_TERMINAL
    assert row["admitted_after_follow_up_trace_ids"] == ["terminal"]
    assert row["temporal_consequence_contract_state"] == "CALIBRATION_REQUIRED"
    assert row["diagnostic_window_can_authorize_claim"] is False
    assert row["terminal_search_boundary_can_authorize_claim"] is False
    assert out["production_release"] is False
