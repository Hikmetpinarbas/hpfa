from hpfa.modules.core.action_occurrence_admission_lite.src.occurrence_object_role_projection import (
    project_occurrence_object_roles,
)


def test_occurrence_is_not_duplicated_per_object_and_support_is_not_inflated():
    payload = {
        "action_occurrence_candidates": [
            {
                "action_occurrence_candidate_id": "occ_1",
                "actor_identity_candidate_id": "player_a",
                "team_identity_candidate_id": "team_a",
                "opponent_identity_candidate_id": "player_b",
                "opponent_team_identity_candidate_id": "team_b",
                "relation_bundle": {"relation_type": "DUEL_INTERACTION_CANDIDATE"},
            }
        ]
    }

    out = project_occurrence_object_roles(payload)
    row = out["occurrence_object_role_projection"][0]

    assert out["occurrence_object_role_projection_count"] == 1
    assert row["action_occurrence_candidate_id"] == "occ_1"
    assert row["object_role_binding_count"] == 4
    assert row["occurrence_duplicated_per_object"] is False
    assert row["object_binding_creates_independent_support"] is False
    assert row["object_binding_creates_possession_truth"] is False
    assert row["process_object_binding_state"] == "NOT_AVAILABLE_AT_OCCURRENCE_ADMISSION"


def test_missing_optional_counterpart_does_not_invent_object():
    payload = {
        "action_occurrence_candidates": [
            {
                "action_occurrence_candidate_id": "occ_2",
                "actor_identity_candidate_id": "player_a",
                "team_identity_candidate_id": "team_a",
            }
        ]
    }

    out = project_occurrence_object_roles(payload)
    row = out["occurrence_object_role_projection"][0]
    refs = {(b["object_type"], b["object_ref"], b["object_role"]) for b in row["object_role_bindings"]}

    assert refs == {
        ("PLAYER_CANDIDATE", "player_a", "PRIMARY_ACTOR"),
        ("TEAM_CANDIDATE", "team_a", "PRIMARY_TEAM"),
    }
    assert row["object_binding_creates_case_identity"] is False
    assert row["object_binding_creates_process_truth"] is False
