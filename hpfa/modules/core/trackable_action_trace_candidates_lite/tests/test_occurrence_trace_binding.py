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
                "match_surface_binding_id": "binding_1",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "team_identity_candidate_id": bundle["team_identity_candidate_id"],
                "actor_identity_candidate_id": bundle["actor_identity_candidate_id"],
                "period_candidate": "1",
                "start_candidate": 10.0,
                "end_candidate": 11.0,
                "pos_x_candidate": 50.0,
                "pos_y_candidate": 30.0,
                "action_family_candidates": [bundle.get("action_family_candidate") or "DUEL"],
                "selected_action_bundle_candidate_ids": [bid],
                "supporting_evidence_atom_ids": [],
                "trackable_action_candidate_is_event_truth": False,
                "physical_action_identity_truth": False,
                "sequence_link_allowed": False,
                "canonical_event_count": "UNKNOWN",
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
    common = {
        "match_surface_binding_id": "binding_1",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": 10.0,
        "end_candidate": 11.0,
        "pos_x_candidate": 50.0,
        "pos_y_candidate": 30.0,
        "coordinate_evidence_status": "PASS",
        "supporting_evidence_atom_ids": [],
        "provider_row_id_candidates": [],
        "raw_labels": [],
        "normalized_labels": [],
    }
    action = {
        "action_bundle_candidates": [
            {
                **common,
                "action_bundle_candidate_id": "a_dribble",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_a",
                "bundle_status": "REVIEW_REQUIRED",
                "action_family_candidate": "DRIBBLE",
            },
            {
                **common,
                "action_bundle_candidate_id": "a_duel",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_a",
                "bundle_status": "REVIEW_REQUIRED",
                "action_family_candidate": "DUEL",
            },
            {
                **common,
                "action_bundle_candidate_id": "b_duel",
                "team_identity_candidate_id": "team_b",
                "actor_identity_candidate_id": "actor_b",
                "bundle_status": "REVIEW_REQUIRED",
                "action_family_candidate": "DUEL",
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
                    {
                        "multi_family_review_record_id": "tax_a",
                        "supporting_action_bundle_candidate_ids": ["a_dribble", "a_duel"],
                    }
                ],
            }
        ]
    }
    return action, taxonomy, {}, {}, occurrence


def test_occurrence_admitted_review_bundles_bind_without_taxonomy_promotion() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    result = build_occurrence_aware_trace_payload(
        action, taxonomy, relation, evidence, occurrence, _builder
    )
    assert result["occurrence_both_participants_trace_visible_count"] == 1
    assert result["occurrence_partial_participant_trace_visible_count"] == 0
    assert result["occurrence_no_participant_trace_visible_count"] == 0
    assert result["occurrence_local_taxonomy_rebind_record_count"] == 0
    assert result["occurrence_explicit_review_bundle_trace_candidate_count"] == 1
    bound = [row for row in result["trackable_action_trace_candidates"] if row["occurrence_backed_trace_candidate"]]
    assert len(bound) == 2
    assert all(row["occurrence_binding_is_event_truth"] is False for row in bound)
    explicit = [row for row in bound if row.get("occurrence_binding_scope") == "EXPLICIT_ADMITTED_BUNDLE_ONLY"]
    assert len(explicit) == 1
    assert explicit[0]["occurrence_binding_preserves_taxonomy_review_state"] is True
    assert sorted(explicit[0]["selected_action_bundle_candidate_ids"]) == ["a_dribble", "a_duel"]


def test_occurrence_trace_binding_does_not_mutate_or_promote_upstream_taxonomy() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    before = copy.deepcopy(taxonomy)
    result = build_occurrence_aware_trace_payload(action, taxonomy, relation, evidence, occurrence, _builder)
    assert taxonomy == before
    assert taxonomy["multi_family_review_records"][0]["record_status"] == "REVIEW_REQUIRED"
    assert result["occurrence_local_taxonomy_rebind_record_ids"] == []


def test_unadmitted_review_record_is_not_bound() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    occurrence["action_occurrence_candidates"] = []
    result = build_occurrence_aware_trace_payload(
        action, taxonomy, relation, evidence, occurrence, _builder
    )
    assert result["occurrence_explicit_review_bundle_trace_candidate_count"] == 0
    assert result["trackable_action_trace_candidate_count"] == 1


def test_unrelated_review_bundle_in_same_taxonomy_record_is_not_bound() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    action["action_bundle_candidates"].append({
        **action["action_bundle_candidates"][0],
        "action_bundle_candidate_id": "a_unrelated",
        "action_family_candidate": "PASS",
    })
    taxonomy["multi_family_review_records"][0]["supporting_action_bundle_candidate_ids"].append("a_unrelated")
    result = build_occurrence_aware_trace_payload(action, taxonomy, relation, evidence, occurrence, _builder)
    selected = {
        bundle_id
        for trace in result["trackable_action_trace_candidates"]
        for bundle_id in trace.get("selected_action_bundle_candidate_ids") or []
    }
    assert "a_unrelated" not in selected


def test_no_sample_match_identity_leak_in_occurrence_trace_binding() -> None:
    from pathlib import Path

    source = Path(
        "hpfa/modules/core/trackable_action_trace_candidates_lite/src/occurrence_trace_binding.py"
    ).read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Turkey", "United States")
    assert not any(token in source for token in forbidden)
