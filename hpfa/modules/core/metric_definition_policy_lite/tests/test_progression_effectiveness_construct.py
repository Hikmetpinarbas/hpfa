from __future__ import annotations

import copy
import json
from pathlib import Path

from hpfa.modules.core.metric_definition_policy_lite.src.progression_effectiveness_construct import (
    build_progression_effectiveness_construct,
)

ROOT = Path(__file__).resolve().parents[5]
GUARD = json.loads((ROOT / "configs/metrics/construct_context_guard_v1.json").read_text(encoding="utf-8"))
BINDING = "msb_" + "a" * 24


def _trace(trace_id: str, label: str, *, actor: str = "actor_a") -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": actor,
        "period_candidate": "1",
        "start_candidate": "10",
        "end_candidate": "10.5",
        "pos_x_candidate": "10",
        "pos_y_candidate": "20",
        "action_family_candidates": ["PASS"],
        "raw_labels": [label],
        "canonical_event_count": "UNKNOWN",
    }


def _consequence(trace_id: str, primary: str, *, status: str = "PASS_CANDIDATE_CLASSIFICATION") -> dict:
    return {
        "trackable_action_consequence_candidate_id": f"c_{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "record_status": status,
        "primary_consequence_candidate": primary,
        "canonical_event_count": "UNKNOWN",
    }


def _payloads(traces, consequences):
    return (
        {
            "module_id": "trackable_action_trace_candidates_lite_v1",
            "status": "PASS",
            "match_surface_binding_id": BINDING,
            "trackable_action_trace_candidates": traces,
            "trackable_action_trace_candidate_count": len(traces),
            "hard_block_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        },
        {
            "module_id": "trackable_action_consequence_candidates_lite_v1",
            "status": "PASS",
            "match_surface_binding_id": BINDING,
            "trackable_action_consequence_candidates": consequences,
            "trackable_action_consequence_candidate_count": len(consequences),
            "hard_block_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        },
    )


def test_progression_denominator_requires_explicit_reviewed_progression_semantics():
    progressive = _trace("t1", "Progressive passes accurate")
    ordinary = _trace("t2", "Passes accurate", actor="actor_b")
    trace_payload, consequence_payload = _payloads(
        [progressive, ordinary],
        [_consequence("t1", "SAME_TEAM_CONTINUATION_CANDIDATE"), _consequence("t2", "SAME_TEAM_CONTINUATION_CANDIDATE")],
    )
    result = build_progression_effectiveness_construct(trace_payload, consequence_payload, GUARD, repo_root=ROOT)
    construct = result["construct_candidate"]
    assert construct["eligible_progression_trace_candidate_count"] == 1
    assert construct["evaluable_progression_consequence_candidate_count"] == 1
    assert construct["positive_follow_up_rate_among_evaluable_candidate"] == 1.0
    assert construct["effectiveness_score_emitted"] is False


def test_missing_consequence_is_unknown_not_counterevidence():
    trace_payload, consequence_payload = _payloads([_trace("t1", "Progressive passes accurate")], [])
    result = build_progression_effectiveness_construct(trace_payload, consequence_payload, GUARD, repo_root=ROOT)
    construct = result["construct_candidate"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert construct["visible_adverse_handover_candidate_count"] == 0
    assert construct["unresolved_or_missing_consequence_candidate_count"] == 1
    assert construct["missing_consequence_is_counterevidence"] is False


def test_visible_opponent_handover_is_counterevidence_candidate():
    trace_payload, consequence_payload = _payloads(
        [_trace("t1", "Progressive passes accurate")],
        [_consequence("t1", "OPPONENT_HANDOVER_CANDIDATE")],
    )
    result = build_progression_effectiveness_construct(trace_payload, consequence_payload, GUARD, repo_root=ROOT)
    construct = result["construct_candidate"]
    assert construct["visible_adverse_handover_candidate_count"] == 1
    assert construct["adverse_handover_rate_among_evaluable_candidate"] == 1.0
    assert construct["counterevidence_consequence_candidate_refs"] == ["c_t1"]


def test_guard_failure_blocks_construct():
    bad_guard = copy.deepcopy(GUARD)
    bad_guard["required_comparability_dimensions"].append("missing_dimension")
    trace_payload, consequence_payload = _payloads(
        [_trace("t1", "Progressive passes accurate")],
        [_consequence("t1", "SAME_TEAM_CONTINUATION_CANDIDATE")],
    )
    result = build_progression_effectiveness_construct(trace_payload, consequence_payload, bad_guard, repo_root=ROOT)
    assert result["status"] == "FAIL_CLOSED"
    assert result["construct_candidate"] is None
    assert "construct_context_guard_not_admitted" in result["hard_block_hits"]


def test_claim_and_zfgv_locks_remain_closed():
    trace_payload, consequence_payload = _payloads(
        [_trace("t1", "Progressive passes accurate")],
        [_consequence("t1", "SHOT_FOLLOW_UP_CANDIDATE")],
    )
    result = build_progression_effectiveness_construct(trace_payload, consequence_payload, GUARD, repo_root=ROOT)
    assert result["observation_model"] == "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
    assert result["event_only_is_product_ceiling"] is False
    assert result["progression_effectiveness_truth"] is False
    assert result["professional_finding_emitted"] is False
    assert result["claim_output_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_same_provider_support_never_becomes_independent_vote():
    trace_payload, consequence_payload = _payloads(
        [_trace("t1", "Progressive passes accurate")],
        [_consequence("t1", "SAME_TEAM_CONTINUATION_CANDIDATE")],
    )
    result = build_progression_effectiveness_construct(trace_payload, consequence_payload, GUARD, repo_root=ROOT)
    construct = result["construct_candidate"]
    assert construct["same_provider_reflection_adds_independent_vote"] is False
    assert construct["independent_support_vote_count"] == 0


def test_no_sample_match_identity_leak():
    source = (ROOT / "hpfa/modules/core/metric_definition_policy_lite/src/progression_effectiveness_construct.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "Galatasaray", "Roma", "Atalanta"):
        assert token not in source
