from __future__ import annotations

import copy

from hpfa.modules.core.action_occurrence_admission_lite.src.action_occurrence_admission import (
    build_action_occurrence_admission,
)
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
                "match_surface_binding_id": bundle.get("match_surface_binding_id") or "binding_1",
                "source_role": bundle.get("source_role") or "PLAYER_SURFACE_CANDIDATE",
                "team_identity_candidate_id": bundle["team_identity_candidate_id"],
                "actor_identity_candidate_id": bundle["actor_identity_candidate_id"],
                "period_candidate": bundle.get("period_candidate") or "1",
                "start_candidate": bundle.get("start_candidate", 10.0),
                "end_candidate": bundle.get("end_candidate", 11.0),
                "pos_x_candidate": bundle.get("pos_x_candidate", 50.0),
                "pos_y_candidate": bundle.get("pos_y_candidate", 30.0),
                "action_family_candidates": [bundle.get("action_family_candidate") or "DUEL"],
                "selected_action_bundle_candidate_ids": [bid],
                "supporting_evidence_atom_ids": [],
                "reflection_context_action_bundle_candidate_ids": list(bundle.get("reflection_context_action_bundle_candidate_ids") or []),
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


def _production_occurrence_fixture_with_goalkeeper():
    binding = "binding_real"

    def bundle(bid, family, label, team, actor, *, role="PLAYER_SURFACE_CANDIDATE", status="REVIEW_REQUIRED"):
        return {
            "action_bundle_candidate_id": bid,
            "match_surface_binding_id": binding,
            "source_role": role,
            "team_identity_candidate_id": team,
            "actor_identity_candidate_id": actor,
            "period_candidate": "1",
            "start_candidate": "18.42",
            "end_candidate": "30.42",
            "pos_x_candidate": "78.04",
            "pos_y_candidate": "64.76",
            "coordinate_evidence_status": "COORDINATE_PRESENT",
            "action_family_candidate": family,
            "supporting_evidence_atom_ids": ["ea_" + bid],
            "provider_row_id_candidates": [bid],
            "raw_labels": [label],
            "normalized_labels": [label.casefold()],
            "bundle_status": status,
            "cross_role_fusion_allowed": False,
            "validated_event_identity": False,
            "event_instance_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "same_time_order_truth_admitted": False,
            "canonical_event_count": "UNKNOWN",
        }

    bundles = [
        bundle("a_dribble", "DRIBBLE", "Dribbles successful", "team_a", "actor_a"),
        bundle("a_duel", "DUEL", "Challenges won", "team_a", "actor_a"),
        bundle("a_final", "DRIBBLE", "Dribbling in the final third successful", "team_a", "actor_a"),
        bundle("b_duel", "DUEL", "Challenges unsuccessful", "team_b", "actor_b"),
        bundle("b_tackle", "TACKLE", "Tackles unsuccessful", "team_b", "actor_b"),
        bundle("gk_context", "SAVE", "Save candidate", "team_b", "keeper_b", role="GOALKEEPER_SURFACE_CANDIDATE", status="PASS"),
    ]

    def tax(rid, ids, families, team, actor):
        return {
            "multi_family_review_record_id": rid,
            "match_surface_binding_id": binding,
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "team_identity_candidate_id": team,
            "actor_identity_candidate_id": actor,
            "period_candidate": "1",
            "start_candidate": "18.42",
            "end_candidate": "30.42",
            "pos_x_candidate": "78.04",
            "pos_y_candidate": "64.76",
            "coordinate_evidence_status": "COORDINATE_PRESENT",
            "family_set": sorted(families),
            "family_count": len(set(families)),
            "classification": "HIERARCHICAL_SUBTYPE_CANDIDATE",
            "supporting_action_bundle_candidate_ids": ids,
            "supporting_evidence_atom_ids": ["ea_" + value for value in ids],
            "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            "review_hits": [],
            "classification_is_event_truth": False,
            "cross_role_fusion_allowed": False,
            "event_instance_allowed": False,
            "validated_event_identity": False,
            "canonical_event_count": "UNKNOWN",
        }

    taxonomy_records = [
        tax("tax_a", ["a_dribble", "a_duel", "a_final"], ["DRIBBLE", "DUEL"], "team_a", "actor_a"),
        tax("tax_b", ["b_duel", "b_tackle"], ["DUEL", "TACKLE"], "team_b", "actor_b"),
    ]
    action = {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": binding,
        "action_bundle_candidates": bundles,
        "action_bundle_candidate_count": len(bundles),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    taxonomy = {
        "module_id": "action_bundle_multi_family_review_taxonomy_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": binding,
        "multi_family_review_records": taxonomy_records,
        "multi_family_review_core_count": len(taxonomy_records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    relation = {
        "module_id": "cross_role_relation_candidate_resolver_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": binding,
        "resolved_relation_candidates": [],
        "resolved_relation_candidate_count": 0,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    occurrence = build_action_occurrence_admission(action, taxonomy, relation)
    return action, taxonomy, relation, occurrence


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


def test_player_team_views_do_not_double_count_underlying_occurrence() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    result = build_occurrence_aware_trace_payload(action, taxonomy, relation, evidence, occurrence, _builder)
    binding = result["occurrence_trace_binding_records"][0]
    assert len(binding["trace_refs"]) == 2
    assert binding["underlying_occurrence_root_count_contribution"] == 1
    assert binding["object_view_count_is_independent_support_count"] is False
    assert binding["independence_proven"] is False
    assert binding["dependency_group"] == "occurrence:aoc_1"
    assert binding["player_refs"] == ["actor_a", "actor_b"]
    assert binding["team_refs"] == ["team_a", "team_b"]
    assert "DERIVED_FROM_SAME_OCCURRENCE" in binding["relation_types"]
    assert "OCCURRENCE_HAS_PLAYER" in binding["relation_types"]
    assert "OCCURRENCE_HAS_TEAM" in binding["relation_types"]


def test_goalkeeper_team_view_dependency_preserved() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    for bundle in action["action_bundle_candidates"]:
        if bundle["action_bundle_candidate_id"] == "b_duel":
            bundle["source_role"] = "GOALKEEPER_SURFACE_CANDIDATE"
    result = build_occurrence_aware_trace_payload(action, taxonomy, relation, evidence, occurrence, _builder)
    binding = result["occurrence_trace_binding_records"][0]
    assert binding["goalkeeper_refs"] == ["actor_b"]
    assert "OCCURRENCE_HAS_GOALKEEPER" in binding["relation_types"]
    assert "GOALKEEPER_PARTICIPATES_IN_TRACE" in binding["relation_types"]
    assert binding["dependency_group"] == "occurrence:aoc_1"
    assert binding["independence_group"] is None


def test_production_occurrence_can_bind_exact_core_goalkeeper_context_without_new_participant() -> None:
    action, taxonomy, relation, occurrence = _production_occurrence_fixture_with_goalkeeper()
    assert occurrence["action_occurrence_candidate_count"] == 1
    candidate = occurrence["action_occurrence_candidates"][0]
    assert "gk_context" not in candidate["supporting_action_bundle_candidate_ids"]

    result = build_occurrence_aware_trace_payload(action, taxonomy, relation, {}, occurrence, _builder)
    binding = result["occurrence_trace_binding_records"][0]
    assert binding["goalkeeper_refs"] == ["keeper_b"]
    assert binding["goalkeeper_context_bundle_refs"] == ["gk_context"]
    assert binding["goalkeeper_context_is_occurrence_participant_truth"] is False
    assert "OCCURRENCE_HAS_GOALKEEPER" in binding["relation_types"]
    assert "GOALKEEPER_PARTICIPATES_IN_TRACE" in binding["relation_types"]
    assert binding["actor_trace_candidate_count"] >= 1
    assert binding["opponent_trace_candidate_count"] >= 1
    assert binding["binding_state"] == "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE"
    assert binding["underlying_occurrence_root_count_contribution"] == 1
    assert binding["independence_proven"] is False
    assert result["occurrence_goalkeeper_context_bundle_binding_count"] == 1
    assert result["goalkeeper_context_binding_creates_occurrence"] is False
    assert result["goalkeeper_context_binding_creates_independent_support"] is False
    assert "occurrence_goalkeeper_context_binding_used" in result["review_hits"]


def test_explicit_reflection_stays_same_occurrence_dependency_not_new_support() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    for bundle in action["action_bundle_candidates"]:
        if bundle["action_bundle_candidate_id"] == "b_duel":
            bundle["reflection_context_action_bundle_candidate_ids"] = ["xml_ref_b_duel"]
    result = build_occurrence_aware_trace_payload(action, taxonomy, relation, evidence, occurrence, _builder)
    binding = result["occurrence_trace_binding_records"][0]
    assert binding["reflection_context_refs"] == ["xml_ref_b_duel"]
    assert "SAME_UNDERLYING_OCCURRENCE_REFLECTION" in binding["relation_types"]
    assert binding["underlying_occurrence_root_count_contribution"] == 1
    assert result["object_views_create_independent_support"] is False


def test_entity_view_requires_occurrence_binding() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    occurrence["action_occurrence_candidates"] = []
    result = build_occurrence_aware_trace_payload(action, taxonomy, relation, evidence, occurrence, _builder)
    assert result["occurrence_trace_binding_record_count"] == 0
    assert result["object_centric_trace_binding_record_count"] == 0


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


def test_object_binding_never_creates_event_truth() -> None:
    action, taxonomy, relation, evidence, occurrence = _fixture()
    result = build_occurrence_aware_trace_payload(action, taxonomy, relation, evidence, occurrence, _builder)
    binding = result["occurrence_trace_binding_records"][0]
    assert binding["object_view_creates_event"] is False
    assert binding["binding_is_event_truth"] is False
    assert binding["canonical_event_count"] == "UNKNOWN"
    assert result["occurrence_binding_is_event_truth"] is False
    assert result["production_release"] is False


def test_no_sample_match_identity_leak_in_occurrence_trace_binding() -> None:
    from pathlib import Path

    source = Path(
        "hpfa/modules/core/trackable_action_trace_candidates_lite/src/occurrence_trace_binding.py"
    ).read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Turkey", "United States")
    assert not any(token in source for token in forbidden)
