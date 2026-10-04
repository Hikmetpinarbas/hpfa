from __future__ import annotations

from hpfa.modules.core.action_occurrence_admission_lite.src.single_action_anchor_admission import (
    build_single_action_anchor_candidates,
    load_single_anchor_registry,
)

BINDING = "msb_" + "s" * 24


def _bundle() -> dict:
    return {
        "action_bundle_candidate_id": "bundle_single",
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "period_candidate": "1",
        "start_candidate": "10.00",
        "end_candidate": "16.00",
        "pos_x_candidate": "40.00",
        "pos_y_candidate": "32.00",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": "PASS",
        "supporting_evidence_atom_ids": ["ea_single"],
        "provider_row_id_candidates": ["17"],
        "raw_labels": ["Passes accurate"],
        "normalized_labels": ["passes accurate"],
        "bundle_status": "PASS",
        "same_role_exact_grouping": True,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def _atom() -> dict:
    return {
        "evidence_atom_id": "ea_single",
        "atom_class": "ACTION_ANCHOR_ATOM",
        "atom_status": "PASS",
        "semantic_role_candidate": "ACTION_ANCHOR",
        "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE",
        "semantic_rule_id": "plvs_v2_passes_accurate",
        "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
        "action_eligible": True,
        "action_family_candidates": ["PASS"],
        "outcome_candidates": ["SUCCESS"],
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": "10.00",
        "end_candidate": "16.00",
        "pos_x_candidate": "40.00",
        "pos_y_candidate": "32.00",
        "raw_label": "Passes accurate",
        "normalized_label": "passes accurate",
        "independent_source_vote_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "physical_action_identity_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_exact_reviewed_single_action_anchor_is_admitted_as_candidate_only() -> None:
    result = build_single_action_anchor_candidates(
        {"action_bundle_candidates": [_bundle()]},
        {"evidence_atoms": [_atom()]},
        [],
        load_single_anchor_registry(),
    )
    assert result["action_occurrence_candidate_count"] == 1
    row = result["action_occurrence_candidates"][0]
    assert row["admission_class"] == "EXACT_SINGLE_ACTION_ANCHOR_SEMANTIC_ADMISSION"
    assert row["occurrence_topology"] == "SINGLE_ACTOR_ACTION"
    assert row["primary_family_candidate"] == "PASS"
    assert row["semantic_dimensions"]["outcome_candidate"] == ["SUCCESS"]
    assert row["semantic_consumer_coverage"]["outcome_candidate"]["consumer_state"] == "CONSUMED"
    assert row["semantic_consumer_coverage"]["consequence_consumer"]["consumer_state"] == "DOWNSTREAM_USAGE_UNKNOWN"
    assert row["single_provider_label_is_physical_action_truth"] is False
    assert row["action_occurrence_candidate_is_event_truth"] is False
    assert row["canonical_event_count"] == "UNKNOWN"
    assert row["true_action_count"] == "UNKNOWN"
    assert row["production_release"] is False


def test_unreviewed_semantic_mapping_is_not_admitted_with_reason() -> None:
    atom = _atom()
    atom["semantic_mapping_status"] = "REVIEW_REQUIRED"
    result = build_single_action_anchor_candidates(
        {"action_bundle_candidates": [_bundle()]},
        {"evidence_atoms": [atom]},
        [],
    )
    assert result["action_occurrence_candidate_count"] == 0
    assert result["not_admitted_with_reason_counts"]["semantic_mapping_status"] == 1


def test_multi_label_bundle_is_not_promoted_by_single_anchor_path() -> None:
    bundle = _bundle()
    bundle["raw_labels"] = ["Passes accurate", "Passes forward accurate"]
    bundle["normalized_labels"] = ["passes accurate", "passes forward accurate"]
    result = build_single_action_anchor_candidates(
        {"action_bundle_candidates": [bundle]},
        {"evidence_atoms": [_atom()]},
        [],
    )
    assert result["action_occurrence_candidate_count"] == 0


def test_bundle_already_represented_by_occurrence_is_not_double_counted() -> None:
    existing = [{"supporting_action_bundle_candidate_ids": ["bundle_single"]}]
    result = build_single_action_anchor_candidates(
        {"action_bundle_candidates": [_bundle()]},
        {"evidence_atoms": [_atom()]},
        existing,
    )
    assert result["action_occurrence_candidate_count"] == 0


def test_goalkeeper_surface_is_allowed_but_team_surface_is_not() -> None:
    gk_bundle = _bundle()
    gk_bundle["source_role"] = "GOALKEEPER_SURFACE_CANDIDATE"
    gk_atom = _atom()
    gk_atom["source_role"] = "GOALKEEPER_SURFACE_CANDIDATE"
    admitted = build_single_action_anchor_candidates(
        {"action_bundle_candidates": [gk_bundle]},
        {"evidence_atoms": [gk_atom]},
        [],
    )
    assert admitted["action_occurrence_candidate_count"] == 1

    team_bundle = _bundle()
    team_bundle["source_role"] = "TEAM_SURFACE_CANDIDATE"
    team_atom = _atom()
    team_atom["source_role"] = "TEAM_SURFACE_CANDIDATE"
    rejected = build_single_action_anchor_candidates(
        {"action_bundle_candidates": [team_bundle]},
        {"evidence_atoms": [team_atom]},
        [],
    )
    assert rejected["action_occurrence_candidate_count"] == 0


def test_consumer_state_vocabulary_preserves_unknown_not_unused() -> None:
    result = build_single_action_anchor_candidates(
        {"action_bundle_candidates": [_bundle()]},
        {"evidence_atoms": [_atom()]},
        [],
    )
    states = set(result["consumer_coverage_state_vocabulary"])
    assert states == {
        "CONSUMED",
        "NOT_ADMITTED_WITH_REASON",
        "NOT_APPLICABLE",
        "DOWNSTREAM_USAGE_UNKNOWN",
    }
    assert result["unknown_downstream_usage_is_not_non_use"] is True
    assert "UNUSED" not in states
