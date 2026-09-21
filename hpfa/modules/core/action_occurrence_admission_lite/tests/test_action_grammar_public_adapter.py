from __future__ import annotations

from hpfa.modules.core.action_occurrence_admission_lite.src.action_grammar_public_adapter import (
    bind_canonical_football_grammar_metadata,
    bind_intra_actor_action_grammar,
    load_canonical_football_grammar_registry,
    resolve_canonical_football_concept,
)
from hpfa.modules.core.action_occurrence_admission_lite.src.action_occurrence_admission import (
    load_registry,
)

BINDING = "msb_" + "p" * 24


def _pass_bundle() -> dict:
    labels = ["Passes accurate", "Passes forward accurate", "Progressive passes accurate"]
    return {
        "action_bundle_candidate_id": "pass_bundle",
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "period_candidate": "1",
        "start_candidate": "21.10",
        "end_candidate": "21.55",
        "pos_x_candidate": "48.00",
        "pos_y_candidate": "39.00",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": "PASS",
        "supporting_evidence_atom_ids": ["ea_pass", "ea_forward", "ea_progressive"],
        "provider_row_id_candidates": ["r_pass", "r_forward", "r_progressive"],
        "raw_labels": labels,
        "normalized_labels": [label.casefold() for label in labels],
        "bundle_status": "PASS",
        "review_hits": [],
        "same_role_exact_grouping": True,
        "source_row_order_is_temporal_truth": False,
        "same_time_order_truth_admitted": False,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def _evidence() -> dict:
    return {
        "evidence_atoms": [
            {"evidence_atom_id": "ea_pass", "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE", "semantic_rule_id": "plvs_v2_passes_accurate"},
            {"evidence_atom_id": "ea_forward", "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE", "semantic_rule_id": "plvs_v2_passes_forward_accurate"},
            {"evidence_atom_id": "ea_progressive", "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE", "semantic_rule_id": "plvs_v2_progressive_passes_accurate"},
        ]
    }


def _base_occurrence() -> dict:
    return {
        "status": "PASS",
        "module_status": "PASS",
        "action_occurrence_candidates": [],
        "action_occurrence_candidate_count": 0,
        "candidate_rejected_provider_semantics_binding_count": 0,
        "admission_class_counts": {},
        "interaction_type_counts": {},
        "review_hits": [],
        "provider_semantics_binding_status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_public_adapter_adds_grammar_candidate_without_inflating_label_count() -> None:
    row = _pass_bundle()
    result = bind_intra_actor_action_grammar(
        _base_occurrence(),
        {"action_bundle_candidates": [row]},
        _evidence(),
        load_registry(),
    )

    assert result["interaction_occurrence_candidate_count"] == 0
    assert result["intra_actor_action_grammar_candidate_count"] == 1
    assert result["action_occurrence_candidate_count"] == 1
    assert result["action_occurrence_candidates"][0]["attributes"]["distinct_semantic_label_count"] == 3
    assert result["provider_semantics_binding_status"] == "PASS"
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_public_adapter_repairs_false_pass_when_existing_candidate_semantics_were_rejected() -> None:
    occurrence = _base_occurrence()
    occurrence["candidate_rejected_provider_semantics_binding_count"] = 1
    occurrence["provider_semantics_binding_status"] = "PASS"
    result = bind_intra_actor_action_grammar(
        occurrence,
        {"action_bundle_candidates": []},
        {"evidence_atoms": []},
        load_registry(),
    )

    assert result["action_occurrence_candidate_count"] == 0
    assert result["candidate_rejected_provider_semantics_binding_count"] == 1
    assert result["provider_semantics_binding_status"] == "REVIEW_REQUIRED"
    assert "candidate_rejected_provider_semantics_binding" in result["review_hits"]


def test_public_adapter_exposes_provider_independent_canonical_grammar() -> None:
    payload = load_canonical_football_grammar_registry()
    assert payload["registry_id"] == "hpfa_football_action_process_grammar_v1"
    assert payload["provider_binding_policy"]["provider_label_is_canonical_truth"] is False
    assert payload["production_release"] is False


def test_public_adapter_resolves_ids_and_declared_aliases_without_fuzzy_provider_mapping() -> None:
    assert resolve_canonical_football_concept("PASS")["class"] == "ACTION"
    dribble = resolve_canonical_football_concept("DRIBBLE")
    assert dribble["id"] == "DRIBBLE_TAKE_ON"
    turnover = resolve_canonical_football_concept("TURNOVER")
    assert turnover["id"] == "TURNOVER_LOSS"
    assert resolve_canonical_football_concept("Passes accurate") is None


def test_canonical_grammar_metadata_binds_only_admitted_semantic_families() -> None:
    occurrence = _base_occurrence()
    occurrence["action_occurrence_candidates"] = [
        {
            "action_occurrence_candidate_id": "aoc_pass",
            "primary_family_candidate": "PASS",
            "admission_class": "EXACT_SINGLE_ACTION_ANCHOR_SEMANTIC_ADMISSION",
            "claim_ceiling": "ACTION_OCCURRENCE_CANDIDATE_ONLY",
            "independent_support_vote_count": 0,
            "raw_labels": ["Passes accurate"],
        },
        {
            "action_occurrence_candidate_id": "aoc_dribble",
            "primary_family_candidate": "DRIBBLE",
            "admission_class": "EXACT_COMPATIBLE",
            "claim_ceiling": "ACTION_OCCURRENCE_CANDIDATE_ONLY",
            "independent_support_vote_count": 0,
            "raw_labels": ["Dribbles"],
        },
        {
            "action_occurrence_candidate_id": "aoc_gk",
            "primary_family_candidate": "GOALKEEPER_ACTION",
            "admission_class": "EXACT_SINGLE_ACTION_ANCHOR_SEMANTIC_ADMISSION",
            "claim_ceiling": "ACTION_OCCURRENCE_CANDIDATE_ONLY",
            "independent_support_vote_count": 0,
            "supporting_semantic_rule_ids": ["plvs_v2_shots_saved"],
            "raw_labels": ["Shots saved"],
        },
    ]
    before = [
        (
            row["action_occurrence_candidate_id"],
            row["admission_class"],
            row["claim_ceiling"],
            row["independent_support_vote_count"],
        )
        for row in occurrence["action_occurrence_candidates"]
    ]

    result = bind_canonical_football_grammar_metadata(occurrence)

    after = [
        (
            row["action_occurrence_candidate_id"],
            row["admission_class"],
            row["claim_ceiling"],
            row["independent_support_vote_count"],
        )
        for row in result["action_occurrence_candidates"]
    ]
    assert after == before
    assert result["canonical_football_grammar_resolved_candidate_count"] == 3
    assert result["canonical_football_grammar_unresolved_candidate_count"] == 0
    assert result["canonical_football_grammar_unresolved_token_counts"] == {}
    assert result["action_occurrence_candidates"][0]["canonical_football_grammar_matches"][0]["canonical_id"] == "PASS"
    assert result["action_occurrence_candidates"][1]["canonical_football_grammar_matches"][0]["canonical_id"] == "DRIBBLE_TAKE_ON"
    assert result["action_occurrence_candidates"][2]["canonical_football_grammar_matches"][0]["canonical_id"] == "GK_SAVE"
    assert result["canonical_football_grammar_binding_changes_admission"] is False
    assert result["canonical_football_grammar_binding_creates_new_evidence"] is False
    assert result["canonical_football_grammar_binding_can_authorize_emit"] is False


def test_public_adapter_exposes_canonical_semantics_after_admission() -> None:
    row = _pass_bundle()
    result = bind_intra_actor_action_grammar(
        _base_occurrence(),
        {"action_bundle_candidates": [row]},
        _evidence(),
        load_registry(),
    )

    candidate = result["action_occurrence_candidates"][0]
    assert candidate["primary_family_candidate"] == "PASS"
    assert candidate["canonical_football_grammar_matches"][0]["canonical_id"] == "PASS"
    assert candidate["canonical_football_grammar_matches"][0]["label_tr"] == "Pas"
    assert candidate["canonical_football_grammar_binding_changes_occurrence_identity"] is False
    assert result["canonical_football_grammar_registry_id"] == "hpfa_football_action_process_grammar_v1"
    assert result["canonical_football_grammar_binding_changes_admission"] is False


def test_specific_restart_subtype_supersedes_generic_restart_container() -> None:
    occurrence = _base_occurrence()
    occurrence["action_occurrence_candidates"] = [
        {
            "action_occurrence_candidate_id": "aoc_goal_kick",
            "interaction_type": "GOAL_KICK_RESTART_PASS_SEMANTIC_CANDIDATE",
            "primary_family_candidate": "RESTART",
            "action_family_candidates": ["PASS", "RESTART"],
            "attributes": {"restart_type_candidate": "GOAL_KICK"},
            "admission_class": "EXACT_GOAL_KICK_RESTART_PASS_SEMANTIC_BINDING",
            "claim_ceiling": "ACTION_OCCURRENCE_CANDIDATE_ONLY",
            "independent_support_vote_count": 0,
        }
    ]

    result = bind_canonical_football_grammar_metadata(occurrence)
    candidate = result["action_occurrence_candidates"][0]
    ids = [row["canonical_id"] for row in candidate["canonical_football_grammar_matches"]]

    assert ids == ["GOAL_KICK", "PASS"]
    assert candidate["canonical_football_grammar_unresolved_tokens"] == []
    assert result["canonical_football_grammar_binding_status"] == "PASS"
