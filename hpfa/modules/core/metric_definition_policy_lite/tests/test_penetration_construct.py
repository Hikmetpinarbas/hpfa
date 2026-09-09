from __future__ import annotations

import copy
import json
from pathlib import Path

from hpfa.modules.core.metric_definition_policy_lite.src.penetration_construct import (
    build_penetration_construct,
)

ROOT = Path(__file__).resolve().parents[5]
GUARD = json.loads((ROOT / "configs/metrics/construct_context_guard_v1.json").read_text(encoding="utf-8"))
BINDING = "msb_" + "p" * 24


def _progression(refs: list[str]) -> dict:
    return {
        "module_id": "progression_effectiveness_construct_v1",
        "status": "PASS_CANDIDATE",
        "construct_candidate": {
            "construct_candidate_id": "pec_test",
            "provenance_root": BINDING,
            "entity_scope": "PLAYER_OR_GOALKEEPER_ACTOR_BEARING_TRACE",
            "team_scope": "MATCH_LOCAL_TEAM_IDENTITY_CANDIDATES",
            "period_scope": "TRACE_DECLARED_PERIOD_SCOPE",
            "source_surface_roles": ["PLAYER_SURFACE_CANDIDATE"],
            "eligible_progression_trace_candidate_count": len(refs),
            "eligible_progression_trace_candidate_refs": refs,
        },
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence(trace_id: str, primary: str, *, status: str = "PASS_CANDIDATE_CLASSIFICATION") -> dict:
    return {
        "trackable_action_consequence_candidate_id": f"c_{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "record_status": status,
        "primary_consequence_candidate": primary,
    }


def _consequence_payload(rows: list[dict]) -> dict:
    return {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "status": "PASS",
        "match_surface_binding_id": BINDING,
        "trackable_action_consequence_candidates": rows,
        "trackable_action_consequence_candidate_count": len(rows),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_terminal_penetration_uses_only_admitted_progression_denominator():
    progression = _progression(["t1", "t2", "t3"])
    consequence = _consequence_payload([
        _consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE"),
        _consequence("t2", "SAME_TEAM_CONTINUATION_CANDIDATE"),
        _consequence("t3", "OPPONENT_HANDOVER_CANDIDATE"),
        _consequence("outside", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
    ])
    result = build_penetration_construct(progression, consequence, GUARD)
    construct = result["construct_candidate"]
    assert construct["eligible_progression_trace_candidate_count"] == 3
    assert construct["penetration_evaluable_progression_candidate_count"] == 3
    assert construct["visible_terminal_penetration_support_candidate_count"] == 1
    assert construct["visible_nonterminal_continuation_candidate_count"] == 1
    assert construct["visible_adverse_handover_candidate_count"] == 1
    assert construct["terminal_penetration_rate_among_evaluable_candidate"] == 0.333333


def test_missing_followup_is_unknown_not_failure_or_counterevidence():
    result = build_penetration_construct(_progression(["t1"]), _consequence_payload([]), GUARD)
    construct = result["construct_candidate"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert construct["penetration_evaluable_progression_candidate_count"] == 0
    assert construct["unresolved_or_missing_followup_candidate_count"] == 1
    assert construct["visible_adverse_handover_candidate_count"] == 0
    assert construct["missing_followup_is_counterevidence"] is False


def test_shot_followup_does_not_manufacture_box_access_truth():
    result = build_penetration_construct(
        _progression(["t1"]),
        _consequence_payload([_consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE")]),
        GUARD,
    )
    construct = result["construct_candidate"]
    assert construct["visible_shot_followup_candidate_count"] == 1
    assert construct["box_access_surface_available"] is False
    assert construct["box_access_rate_candidate"] is None
    assert construct["box_access_not_inferred_from_shot"] is True
    assert result["box_access_truth"] is False


def test_review_required_consequence_is_not_evaluable_penetration():
    result = build_penetration_construct(
        _progression(["t1"]),
        _consequence_payload([_consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE", status="REVIEW_REQUIRED")]),
        GUARD,
    )
    construct = result["construct_candidate"]
    assert construct["visible_terminal_penetration_support_candidate_count"] == 0
    assert construct["unresolved_or_missing_followup_candidate_count"] == 1


def test_upstream_truth_escalation_fails_closed():
    progression = _progression(["t1"])
    progression["canonical_event_count"] = 1
    result = build_penetration_construct(
        progression,
        _consequence_payload([_consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE")]),
        GUARD,
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["construct_candidate"] is None


def test_penetration_truth_locks_and_provider_dependency_are_preserved():
    result = build_penetration_construct(
        _progression(["t1"]),
        _consequence_payload([_consequence("t1", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE")]),
        GUARD,
    )
    construct = result["construct_candidate"]
    assert construct["same_provider_reflection_adds_independent_vote"] is False
    assert construct["independent_support_vote_count"] == 0
    assert construct["penetration_score_emitted"] is False
    assert construct["professional_finding_emitted"] is False
    assert result["penetration_truth"] is False
    assert result["causal_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_context_guard_failure_fails_closed():
    bad_guard = copy.deepcopy(GUARD)
    bad_guard["required_comparability_dimensions"] = ["missing_dimension"]
    result = build_penetration_construct(
        _progression(["t1"]),
        _consequence_payload([_consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE")]),
        bad_guard,
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "construct_context_guard_not_admitted" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    text = Path(__file__).read_text(encoding="utf-8")
    assert "Galatasaray" not in text
    assert "Fenerbahce" not in text
    assert "Besiktas" not in text
    assert "Trabzonspor" not in text
