from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.metric_definition_policy_lite.src.penetration_construct import build_penetration_construct
from hpfa.modules.core.metric_definition_policy_lite.src.penetration_safe_finding_adapter import build_penetration_safe_finding_projection

ROOT = Path(__file__).resolve().parents[5]
GUARD = json.loads((ROOT / "configs/metrics/construct_context_guard_v1.json").read_text(encoding="utf-8"))
BINDING = "msb_" + "r" * 24


def _progression(refs: list[str]) -> dict:
    return {
        "module_id": "progression_effectiveness_construct_v1",
        "status": "PASS_CANDIDATE",
        "construct_candidate": {
            "construct_candidate_id": "pec_recurrence_test",
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


def _consequence(trace_id: str, primary: str) -> dict:
    return {
        "trackable_action_consequence_candidate_id": f"c_{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "record_status": "PASS_CANDIDATE_CLASSIFICATION",
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


def _episode_payload(rows: list[dict]) -> dict:
    return {
        "module_id": "episode_consequence_projection_v1",
        "status": "PASS",
        "episode_consequence_candidates": rows,
        "episode_consequence_candidate_count": len(rows),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _episode_row(trace_id: str, episode_id: str, *, phase: str, process: str) -> dict:
    return {
        "trackable_action_consequence_candidate_id": f"c_{trace_id}",
        "episode_candidate_id": episode_id,
        "episode_binding_state": "SINGLE_EPISODE_NAVIGATION_ASSOCIATION",
        "phase_activity_labels": [phase],
        "process_family_annotation_counts": {process: 1},
    }


def test_terminal_support_recurrence_requires_distinct_bound_episodes():
    progression = _progression(["t1", "t2"])
    consequences = _consequence_payload([
        _consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE"),
        _consequence("t2", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
    ])
    episodes = _episode_payload([
        _episode_row("t1", "ep_1", phase="ATTACK_ACTIVITY_CANDIDATE", process="PROGRESSION_PROCESS_CANDIDATE"),
        _episode_row("t2", "ep_2", phase="ATTACK_ACTIVITY_CANDIDATE", process="PROGRESSION_PROCESS_CANDIDATE"),
    ])
    result = build_penetration_construct(progression, consequences, GUARD, episodes)
    construct = result["construct_candidate"]
    assert construct["terminal_support_episode_binding_coverage_rate_candidate"] == 1.0
    assert construct["terminal_support_episode_candidate_count"] == 2
    assert construct["visible_terminal_penetration_recurrence_candidate"] is True
    assert construct["recurrence_truth"] is False
    assert construct["tactical_pattern_truth"] is False


def test_incomplete_episode_binding_downgrades_recurrence_to_unknown_not_negative():
    progression = _progression(["t1", "t2"])
    consequences = _consequence_payload([
        _consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE"),
        _consequence("t2", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
    ])
    episodes = _episode_payload([
        _episode_row("t1", "ep_1", phase="ATTACK_ACTIVITY_CANDIDATE", process="PROGRESSION_PROCESS_CANDIDATE"),
    ])
    result = build_penetration_construct(progression, consequences, GUARD, episodes)
    construct = result["construct_candidate"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert construct["terminal_support_episode_binding_coverage_rate_candidate"] == 0.5
    assert construct["visible_terminal_penetration_recurrence_candidate"] is None
    assert "terminal_support_episode_context_coverage_incomplete" in result["review_hits"]


def test_safe_finding_exposes_where_when_without_promoting_tactical_intention():
    progression = _progression(["t1", "t2"])
    consequences = _consequence_payload([
        _consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE"),
        _consequence("t2", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
    ])
    episodes = _episode_payload([
        _episode_row("t1", "ep_1", phase="ATTACK_ACTIVITY_CANDIDATE", process="PROGRESSION_PROCESS_CANDIDATE"),
        _episode_row("t2", "ep_2", phase="ATTACK_ACTIVITY_CANDIDATE", process="PROGRESSION_PROCESS_CANDIDATE"),
    ])
    construct_payload = build_penetration_construct(progression, consequences, GUARD, episodes)
    finding = build_penetration_safe_finding_projection(construct_payload)["finding_candidate"]
    assert finding["WHERE_WHEN"]["terminal_support_episode_candidate_refs"] == ["ep_1", "ep_2"]
    assert finding["WHAT_VISIBLE"]["visible_terminal_penetration_recurrence_candidate"] is True
    assert finding["recurrence_truth"] is False
    assert finding["tactical_pattern_truth"] is False
    assert "recurrence as tactical intention" in finding["FORBIDDEN_INFERENCE"]
    assert finding["professional_finding_emitted"] is False


def test_same_episode_repetition_is_not_cross_episode_recurrence():
    progression = _progression(["t1", "t2"])
    consequences = _consequence_payload([
        _consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE"),
        _consequence("t2", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"),
    ])
    episodes = _episode_payload([
        _episode_row("t1", "ep_1", phase="ATTACK_ACTIVITY_CANDIDATE", process="PROGRESSION_PROCESS_CANDIDATE"),
        _episode_row("t2", "ep_1", phase="ATTACK_ACTIVITY_CANDIDATE", process="PROGRESSION_PROCESS_CANDIDATE"),
    ])
    result = build_penetration_construct(progression, consequences, GUARD, episodes)
    construct = result["construct_candidate"]
    assert construct["terminal_support_episode_binding_coverage_rate_candidate"] == 1.0
    assert construct["terminal_support_episode_candidate_count"] == 1
    assert construct["visible_terminal_penetration_recurrence_candidate"] is False


def test_no_sample_match_identity_leak():
    source = (ROOT / "hpfa/modules/core/metric_definition_policy_lite/src/penetration_construct.py").read_text(encoding="utf-8")
    forbidden = ["Gencler" + "birligi", "Fener" + "bahce", "15.08." + "2026"]
    assert all(token not in source for token in forbidden)
