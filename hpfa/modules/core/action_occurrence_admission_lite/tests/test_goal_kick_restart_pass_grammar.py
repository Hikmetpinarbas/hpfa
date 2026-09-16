from __future__ import annotations

from copy import deepcopy

from hpfa.modules.core.action_occurrence_admission_lite.src.goal_kick_restart_pass_grammar import (
    build_goal_kick_restart_pass_candidates,
)


ROLE = "GOALKEEPER_SURFACE_CANDIDATE"


def _bundle(
    bundle_id: str,
    family: str,
    labels: list[str],
    evidence_ids: list[str],
    *,
    source_role: str = ROLE,
    x: str = "3.0",
) -> dict:
    return {
        "action_bundle_candidate_id": bundle_id,
        "action_family_candidate": family,
        "source_role": source_role,
        "same_role_exact_grouping": True,
        "cross_role_fusion_allowed": False,
        "bundle_status": "REVIEW_REQUIRED",
        "review_hits": ["same_surface_multiple_action_families"],
        "match_surface_binding_id": "msb_test",
        "team_identity_candidate_id": "team_test",
        "actor_identity_candidate_id": "keeper_test",
        "period_candidate": "1",
        "start_candidate": "100.0",
        "end_candidate": "112.0",
        "pos_x_candidate": x,
        "pos_y_candidate": "34.0",
        "raw_labels": labels,
        "normalized_labels": labels,
        "supporting_evidence_atom_ids": evidence_ids,
        "provider_row_id_candidates": [bundle_id + "_row"],
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def _atom(evidence_id: str, rule_id: str, *, source_role: str = ROLE) -> dict:
    return {
        "evidence_atom_id": evidence_id,
        "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE",
        "semantic_rule_id": rule_id,
        "source_role": source_role,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "physical_action_identity_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def _payload(distance: str = "MEDIUM", outcome: str = "SUCCESS") -> tuple[dict, dict]:
    distance_labels = {
        "SHORT": ("Goal kicks short (0-15 m)", "plvs_v2_goal_kicks_short_gk_surface"),
        "MEDIUM": ("Goal kicks medium (15-40 m)", "plvs_v2_goal_kicks_medium_gk_surface"),
        "LONG": ("Goal kicks long (40+ m)", "plvs_v2_goal_kicks_long_gk_surface"),
    }
    distance_label, distance_rule = distance_labels[distance]
    if outcome == "FAILURE":
        pass_labels = ["Incomplete long passes", "Inaccurate passes"]
        pass_atoms = [
            _atom("e_pass_1", "plvs_v2_incomplete_long_passes"),
            _atom("e_pass_2", "plvs_v2_inaccurate_passes"),
        ]
    elif distance == "LONG":
        pass_labels = ["Long passes", "Passes accurate"]
        pass_atoms = [
            _atom("e_pass_1", "plvs_v2_long_passes"),
            _atom("e_pass_2", "plvs_v2_passes_accurate"),
        ]
    else:
        pass_labels = ["Passes accurate"]
        pass_atoms = [_atom("e_pass_1", "plvs_v2_passes_accurate")]

    restart_atoms = [
        _atom("e_restart_1", "plvs_v2_goal_kicks_gk_surface"),
        _atom("e_restart_2", distance_rule),
    ]
    action = {
        "action_bundle_candidates": [
            _bundle("pass_bundle", "PASS", pass_labels, [x["evidence_atom_id"] for x in pass_atoms]),
            _bundle(
                "restart_bundle",
                "RESTART",
                ["Goal kicks", distance_label],
                [x["evidence_atom_id"] for x in restart_atoms],
            ),
        ]
    }
    evidence = {"evidence_atoms": restart_atoms + pass_atoms}
    return action, evidence


def test_exact_medium_goal_kick_binds_restart_and_pass_without_physical_distance_claim() -> None:
    action, evidence = _payload("MEDIUM", "SUCCESS")
    out = build_goal_kick_restart_pass_candidates(action, evidence)

    assert out["action_occurrence_candidate_count"] == 1
    row = out["action_occurrence_candidates"][0]
    assert row["primary_family_candidate"] == "RESTART"
    assert row["action_family_candidates"] == ["PASS", "RESTART"]
    assert row["attributes"]["restart_type_candidate"] == "GOAL_KICK"
    assert row["attributes"]["provider_distance_bucket_candidate"] == "MEDIUM"
    assert row["attributes"]["provider_distance_bucket_text"] == "15-40 m"
    assert row["attributes"]["pass_outcome_candidate"] == "SUCCESS"
    assert row["attributes"]["provider_distance_bucket_is_measured_physical_distance"] is False
    assert row["attributes"]["provider_distance_bucket_is_tactical_strategy_truth"] is False
    assert row["physical_action_identity_truth"] is False
    assert row["action_occurrence_candidate_is_event_truth"] is False
    assert row["independent_support_vote_count"] == 0
    assert row["canonical_event_count"] == "UNKNOWN"
    assert row["true_action_count"] == "UNKNOWN"


def test_exact_long_failed_goal_kick_preserves_failure_as_provider_semantic_outcome() -> None:
    action, evidence = _payload("LONG", "FAILURE")
    out = build_goal_kick_restart_pass_candidates(action, evidence)

    assert out["action_occurrence_candidate_count"] == 1
    row = out["action_occurrence_candidates"][0]
    assert row["attributes"]["provider_distance_bucket_candidate"] == "LONG"
    assert row["attributes"]["pass_outcome_candidate"] == "FAILURE"
    assert out["provider_distance_bucket_counts"] == {"LONG": 1}
    assert out["pass_outcome_counts"] == {"FAILURE": 1}


def test_same_timestamp_with_different_annotation_anchor_does_not_merge() -> None:
    action, evidence = _payload("LONG", "SUCCESS")
    action = deepcopy(action)
    action["action_bundle_candidates"][0]["pos_x_candidate"] = "4.0"

    out = build_goal_kick_restart_pass_candidates(action, evidence)

    assert out["action_occurrence_candidate_count"] == 0
    assert out["same_timestamp_alone_is_merge_authority"] is False


def test_team_surface_goal_kick_labels_do_not_create_occurrence() -> None:
    action, evidence = _payload("SHORT", "SUCCESS")
    action = deepcopy(action)
    for bundle in action["action_bundle_candidates"]:
        bundle["source_role"] = "TEAM_SURFACE_CANDIDATE"
    for atom in evidence["evidence_atoms"]:
        atom["source_role"] = "TEAM_SURFACE_CANDIDATE"

    out = build_goal_kick_restart_pass_candidates(action, evidence)

    assert out["action_occurrence_candidate_count"] == 0


def test_missing_reviewed_provider_semantic_binding_is_withheld() -> None:
    action, evidence = _payload("MEDIUM", "SUCCESS")
    evidence = deepcopy(evidence)
    evidence["evidence_atoms"][0]["semantic_mapping_status"] = "TOKEN_FALLBACK_REVIEW_REQUIRED"

    out = build_goal_kick_restart_pass_candidates(action, evidence)

    assert out["action_occurrence_candidate_count"] == 0
    assert out["rejected_reason_counts"]["provider_semantics_binding_mismatch"] == 1
    assert "goal_kick_candidate_rejected_provider_semantics_binding" in out["review_hits"]


def test_unreviewed_pass_pattern_is_not_admitted_by_similarity() -> None:
    action, evidence = _payload("MEDIUM", "SUCCESS")
    action = deepcopy(action)
    action["action_bundle_candidates"][0]["raw_labels"] = ["Long passes"]
    action["action_bundle_candidates"][0]["normalized_labels"] = ["Long passes"]

    out = build_goal_kick_restart_pass_candidates(action, evidence)

    assert out["action_occurrence_candidate_count"] == 0
    assert out["near_time_or_space_admission_enabled"] is False
    assert out["global_cross_bundle_action_grammar_merge_allowed"] is False
