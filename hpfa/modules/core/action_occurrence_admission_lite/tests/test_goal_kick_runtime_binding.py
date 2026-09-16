from __future__ import annotations

from hpfa.modules.core.action_occurrence_admission_lite.src.action_grammar_public_adapter import (
    bind_intra_actor_action_grammar,
)
from hpfa.modules.core.action_occurrence_admission_lite.src.action_occurrence_admission import (
    load_registry,
)

ROLE = "GOALKEEPER_SURFACE_CANDIDATE"
BINDING = "msb_goal_kick_runtime"


def _bundle(bundle_id: str, family: str, labels: list[str], evidence_ids: list[str]) -> dict:
    return {
        "action_bundle_candidate_id": bundle_id,
        "match_surface_binding_id": BINDING,
        "source_role": ROLE,
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "keeper_a",
        "period_candidate": "1",
        "start_candidate": "100.0",
        "end_candidate": "112.0",
        "pos_x_candidate": "3.0",
        "pos_y_candidate": "34.0",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": evidence_ids,
        "provider_row_id_candidates": [bundle_id + "_row"],
        "raw_labels": labels,
        "normalized_labels": labels,
        "bundle_status": "REVIEW_REQUIRED",
        "review_hits": ["same_surface_multiple_action_families"],
        "same_role_exact_grouping": True,
        "source_row_order_is_temporal_truth": False,
        "same_time_order_truth_admitted": False,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def _atom(evidence_id: str, rule_id: str) -> dict:
    return {
        "evidence_atom_id": evidence_id,
        "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE",
        "semantic_rule_id": rule_id,
        "source_role": ROLE,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "physical_action_identity_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def _base_occurrence() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "action_occurrence_candidates": [],
        "action_occurrence_candidate_count": 0,
        "candidate_rejected_provider_semantics_binding_count": 0,
        "admission_class_counts": {},
        "interaction_type_counts": {},
        "review_hits": ["ineligible_or_unreviewed_action_bundles_preserved"],
        "provider_semantics_binding_status": "PASS",
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_public_runtime_binds_exact_goal_kick_restart_pass_candidate() -> None:
    action = {
        "action_bundle_candidates": [
            _bundle("pass_bundle", "PASS", ["Passes accurate"], ["e_pass"]),
            _bundle(
                "restart_bundle",
                "RESTART",
                ["Goal kicks", "Goal kicks medium (15-40 m)"],
                ["e_goal", "e_medium"],
            ),
        ]
    }
    evidence = {
        "evidence_atoms": [
            _atom("e_pass", "plvs_v2_passes_accurate"),
            _atom("e_goal", "plvs_v2_goal_kicks_gk_surface"),
            _atom("e_medium", "plvs_v2_goal_kicks_medium_gk_surface"),
        ]
    }

    result = bind_intra_actor_action_grammar(
        _base_occurrence(),
        action,
        evidence,
        load_registry(),
    )

    assert result["goal_kick_restart_pass_candidate_count"] == 1
    assert result["action_occurrence_candidate_count"] == 1
    assert result["goal_kick_provider_distance_bucket_counts"] == {"MEDIUM": 1}
    assert result["goal_kick_pass_outcome_counts"] == {"SUCCESS": 1}

    row = result["goal_kick_restart_pass_candidates"][0]
    assert row["primary_family_candidate"] == "RESTART"
    assert row["action_family_candidates"] == ["PASS", "RESTART"]
    assert row["attributes"]["restart_type_candidate"] == "GOAL_KICK"
    assert row["attributes"]["provider_distance_bucket_candidate"] == "MEDIUM"
    assert row["attributes"]["provider_distance_bucket_text"] == "15-40 m"
    assert row["attributes"]["pass_outcome_candidate"] == "SUCCESS"
    assert row["attributes"]["provider_distance_bucket_is_measured_physical_distance"] is False
    assert row["attributes"]["provider_distance_bucket_is_tactical_strategy_truth"] is False
    assert row["observation_occurrence_cardinality"]["cardinality_pattern"] == "MULTIPLE_OBSERVATIONS_ONE_OCCURRENCE"
    assert row["same_timestamp_alone_is_merge_authority"] is False
    assert row["action_occurrence_candidate_is_event_truth"] is False
    assert row["physical_action_identity_truth"] is False
    assert row["canonical_event_count"] == "UNKNOWN"
    assert row["true_action_count"] == "UNKNOWN"
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
