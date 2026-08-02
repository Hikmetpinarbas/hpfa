from __future__ import annotations

from pathlib import Path

import pytest

from hpfa.modules.core.eventonly_sequence_consequence_engine_lite.src.eventonly_sequence_consequence_engine import (
    build_eventonly_sequence_consequence,
    validate_out,
)

BINDING = "binding_candidate"
TEAM = "team_candidate_a"


def node(
    node_id: str,
    family: str,
    *,
    period: str = "1",
    start: str = "10.0",
    role: str = "PLAYER_SURFACE_CANDIDATE",
    bundle: str | None = None,
) -> dict:
    return {
        "selected_action_node_id": node_id,
        "action_family_candidates": [family],
        "team_identity_candidate_id": TEAM,
        "actor_identity_candidate_id": "actor_candidate_a",
        "actor_identity_applicability": "APPLICABLE_BOUND_CANDIDATE",
        "source_role": role,
        "period_candidate": period,
        "start_candidate": start,
        "match_surface_binding_id": BINDING,
        "selected_action_bundle_candidate_ids": [bundle or f"bundle_{node_id}"],
    }


def candidate(
    candidate_id: str,
    anchor_id: str,
    family: str,
    *,
    period: str = "1",
    start: str = "10.0",
    follow_ids: list[str] | None = None,
    retention: str = "SAME_TEAM_VISIBLE_RETENTION_CANDIDATE",
    primary: str = "SAME_TEAM_CONTINUATION_CANDIDATE",
    signals: list[str] | None = None,
    role: str = "PLAYER_SURFACE_CANDIDATE",
) -> dict:
    return {
        "selected_action_consequence_candidate_id": candidate_id,
        "anchor_selected_action_node_id": anchor_id,
        "anchor_action_family_candidates": [family],
        "team_identity_candidate_id": TEAM,
        "actor_identity_candidate_id": "actor_candidate_a",
        "actor_identity_applicability": "APPLICABLE_BOUND_CANDIDATE",
        "source_role": role,
        "period_candidate": period,
        "anchor_start_candidate": start,
        "match_surface_binding_id": BINDING,
        "visible_follow_up_node_ids": follow_ids or [],
        "retention_after_action_candidate": retention,
        "primary_consequence_candidate": primary,
        "consequence_signal_candidates": signals or [],
    }


def payload(nodes: list[dict], candidates: list[dict]) -> dict:
    return {
        "module_id": "selected_action_consequence_surface_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "selected_action_node_count": len(nodes),
        "selected_action_nodes": nodes,
        "selected_action_consequence_candidate_count": len(candidates),
        "selected_action_consequence_candidates": candidates,
    }


def metric(result: dict, metric_id: str, family: str | None) -> dict:
    return next(
        item
        for item in result["metric_records"]
        if item["metric_id"] == metric_id
        and item["team_identity_candidate_id"] == TEAM
        and item["anchor_action_family"] == family
    )


def run(nodes: list[dict], candidates: list[dict]) -> dict:
    return build_eventonly_sequence_consequence(payload(nodes, candidates))


def test_denominator_gated_survival_and_restart_yield() -> None:
    nodes = [
        node("pass", "PASS"),
        node("pass_next", "PASS", start="12"),
        node("restart", "RESTART", start="20", role="TEAM_SURFACE_CANDIDATE"),
        node("restart_next", "PASS", start="22"),
    ]
    result = run(
        nodes,
        [
            candidate("c_pass", "pass", "PASS", follow_ids=["pass_next"]),
            candidate(
                "c_restart",
                "restart",
                "RESTART",
                start="20",
                follow_ids=["restart_next"],
                role="TEAM_SURFACE_CANDIDATE",
            ),
        ],
    )
    assert metric(result, "sequence_survival_rate", "PASS")["value_candidate"] == 1.0
    assert metric(result, "restart_trace_yield", "RESTART")["value_candidate"] == 1.0


def test_duplicate_reflection_same_bundle_is_counted_once() -> None:
    nodes = [
        node("player", "PASS", bundle="same"),
        node("team", "PASS", bundle="same", role="TEAM_SURFACE_CANDIDATE"),
    ]
    result = run(
        nodes,
        [
            candidate("c_player", "player", "PASS"),
            candidate("c_team", "team", "PASS", role="TEAM_SURFACE_CANDIDATE"),
        ],
    )
    assert result["eligible_anchor_count"] == 1
    assert result["suppressed_duplicate_reflection_count"] == 1


def test_distinct_bundle_ids_at_same_time_are_not_collapsed() -> None:
    result = run(
        [node("a", "PASS", bundle="a"), node("b", "PASS", bundle="b")],
        [candidate("ca", "a", "PASS"), candidate("cb", "b", "PASS")],
    )
    assert result["eligible_anchor_count"] == 2
    assert result["suppressed_duplicate_reflection_count"] == 0


def test_missing_denominator_blocks_recovery_metric() -> None:
    result = run([node("pass", "PASS")], [candidate("c", "pass", "PASS")])
    recovery = metric(result, "regain_stabilization_rate", "RECOVERY")
    assert recovery["status"] == "BLOCKED_DENOMINATOR_MISSING"
    assert recovery["value_candidate"] is None


def test_progression_metrics_block_without_semantics_contract() -> None:
    result = run([node("pass", "PASS")], [candidate("c", "pass", "PASS")])
    progression = metric(result, "progression_to_shot_support", "PROGRESSIVE_ACTION")
    assert progression["status"] == "BLOCKED_SEMANTICS_UNAVAILABLE"
    assert progression["denominator"] is None


def test_missing_time_is_quarantined_not_invented() -> None:
    result = run(
        [node("bad", "PASS", start="")],
        [candidate("c_bad", "bad", "PASS", start="")],
    )
    assert result["eligible_anchor_count"] == 0
    assert result["quarantined_record_count"] == 1
    assert "missing_time_blocks_ordered_consequence" in result["review_hits"]


def test_period_boundary_violation_fails_closed() -> None:
    result = run(
        [node("a", "PASS"), node("f", "PASS", period="2", start="11")],
        [candidate("c", "a", "PASS", follow_ids=["f"])],
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any("period_boundary_violation" in hit for hit in result["hard_block_hits"])


def test_adverse_signal_is_candidate_not_causality() -> None:
    result = run(
        [node("a", "TURNOVER")],
        [
            candidate(
                "c",
                "a",
                "TURNOVER",
                retention="OPPONENT_VISIBLE_HANDOVER_CANDIDATE",
                primary="OPPONENT_HANDOVER_CANDIDATE",
            )
        ],
    )
    adverse = metric(result, "adverse_consequence_rate", "TURNOVER")
    assert adverse["value_candidate"] == 1.0
    assert result["adverse_consequence_is_causality_truth"] is False


def test_truth_flags_and_canonical_count_remain_safe() -> None:
    result = run([node("a", "PASS")], [candidate("c", "a", "PASS")])
    for key in (
        "tracking_truth",
        "video_truth",
        "phase_truth",
        "possession_truth",
        "sequence_truth",
        "tactical_truth",
        "causality_truth",
        "production_release",
    ):
        assert result[key] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_nested_output_and_sample_identity_leak_guards() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out("/sdcard/Download/HPFA/nested")
    source = Path(
        "hpfa/modules/core/eventonly_sequence_consequence_engine_lite/src/"
        "eventonly_sequence_consequence_engine.py"
    ).read_text(encoding="utf-8").casefold()
    assert not any(value in source for value in ("galatasaray", "fenerbahce", "sample_match"))
