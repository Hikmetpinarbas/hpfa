from __future__ import annotations

import copy

from hpfa.modules.core.trackable_action_trace_candidates_lite.src.occurrence_trace_binding import (
    build_occurrence_aware_trace_payload,
)


def _builder(action, taxonomy, relation, evidence):
    pass_ids = {
        rid
        for row in taxonomy.get("multi_family_review_records") or []
        if row.get("record_status") == "PASS_CANDIDATE_CLASSIFICATION"
        for rid in row.get("supporting_action_bundle_candidate_ids") or []
    }
    traces = []
    for bundle in action.get("action_bundle_candidates") or []:
        bid = bundle["action_bundle_candidate_id"]
        if bundle.get("bundle_status") == "PASS" or bid in pass_ids:
            traces.append({
                "trackable_action_trace_candidate_id": "tat_" + bid,
                "team_identity_candidate_id": bundle["team_identity_candidate_id"],
                "actor_identity_candidate_id": bundle["actor_identity_candidate_id"],
                "selected_action_bundle_candidate_ids": [bid],
            })
    return {
        "status": "PASS",
        "module_status": "PASS",
        "trackable_action_trace_candidates": traces,
        "trackable_action_trace_candidate_count": len(traces),
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def _fixture():
    action = {
        "action_bundle_candidates": [
            {
                "action_bundle_candidate_id": "a_dribble",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_a",
                "bundle_status": "REVIEW_REQUIRED",
            },
            {
                "action_bundle_candidate_id": "a_duel",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_a",
                "bundle_status": "REVIEW_REQUIRED",
            },
            {
                "action_bundle_candidate_id": "b_duel",
                "team_identity_candidate_id": "team_b",
                "actor_identity_candidate_id": "actor_b",
                "bundle_status": "REVIEW_REQUIRED",
            },
        ]
    }
    taxonomy = {
        "multi_family_review_records": [
            {
                "multi_family_review_record_id": "tax_a",
                "record_status": "REVIEW_REQUIRED",
                "supporting_action_bundle_candidate_ids": ["a_dribble", "a_duel"],
            },
            {
                "multi_family_review_record_id": "tax_b",
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
                "supporting_action_bundle_candidate_ids": ["b_duel"],
            },
        ]
    }
    occurrence = {
        "action_occurrence_candidates": [
            {
                "action_occurrence_candidate_id": "aoc_1",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_a",
                "opponent_team_identity_candidate_id": "team_b",
                "opponent_identity_candidate_id": "actor_b",
                "supporting_action_bundle_candidate_ids": ["a_dribble", "a_duel", "b_duel"],
                "conditional_review_passthrough_provenance": [
                    {"multi_family_review_record_id": "tax_a"}
                ],
            }
        ]
    }
    return action, taxonomy, {}, {}, occurrence


def test_occurrence_admitted_review_bundles_become_local_trace_candidates() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    result = build_occurrence_aware_trace_payload(
        action, taxonomy, relation, evidence, occurrence, _builder
    )
    assert result["occurrence_both_participants_trace_visible_count"] == 1
    assert result["occurrence_partial_participant_trace_visible_count"] == 0
    assert result["occurrence_no_participant_trace_visible_count"] == 0
    assert result["occurrence_local_taxonomy_rebind_record_ids"] == ["tax_a"]
    bound = [row for row in result["trackable_action_trace_candidates"] if row["occurrence_backed_trace_candidate"]]
    assert len(bound) == 3
    assert all(row["occurrence_binding_is_event_truth"] is False for row in bound)


def test_occurrence_trace_binding_does_not_mutate_upstream_taxonomy() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    before = copy.deepcopy(taxonomy)
    build_occurrence_aware_trace_payload(action, taxonomy, relation, evidence, occurrence, _builder)
    assert taxonomy == before
    assert taxonomy["multi_family_review_records"][0]["record_status"] == "REVIEW_REQUIRED"


def test_unadmitted_review_record_is_not_rebound() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    occurrence["action_occurrence_candidates"] = []
    result = build_occurrence_aware_trace_payload(
        action, taxonomy, relation, evidence, occurrence, _builder
    )
    assert result["occurrence_local_taxonomy_rebind_record_count"] == 0
    assert result["trackable_action_trace_candidate_count"] == 1


def test_no_sample_match_identity_leak_in_occurrence_trace_binding() -> None:
    from pathlib import Path

    source = Path(
        "hpfa/modules/core/trackable_action_trace_candidates_lite/src/occurrence_trace_binding.py"
    ).read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Turkey", "United States")
    assert not any(token in source for token in forbidden)
