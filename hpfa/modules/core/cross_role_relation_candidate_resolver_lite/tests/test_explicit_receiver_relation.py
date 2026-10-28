from hpfa.modules.core.cross_role_relation_candidate_resolver_lite.src.explicit_receiver_relation import (
    build_explicit_receiver_relations,
)


def test_explicit_receiver_relation_requires_verified_typed_receiver_identity():
    rows = [
        {
            "source_row_ref": "r1",
            "team_identity_candidate_id": "team_a",
            "actor_identity_candidate_id": "p1",
            "receiver_identity_candidate_id": "p2",
            "action_family_candidate": "PASS",
            "receiver_relation_source_field": "recipient",
            "receiver_relation_semantics_verified": True,
        },
        {
            "source_row_ref": "r2",
            "team_identity_candidate_id": "team_a",
            "actor_identity_candidate_id": "p2",
            "receiver_identity_candidate_id": "p3",
            "action_family_candidate": "PASS",
            "receiver_relation_source_field": "related_player",
            "receiver_relation_semantics_verified": False,
        },
    ]
    out = build_explicit_receiver_relations(rows, eligible_action_families={"PASS"})
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["eligible_row_n"] == 2
    assert out["admitted_relation_n"] == 1
    assert out["blocked_row_n"] == 1
    rel = out["relations"][0]
    assert rel["passer_actor_identity_candidate_id"] == "p1"
    assert rel["receiver_actor_identity_candidate_id"] == "p2"
    assert rel["receiver_relation_admitted"] is True
    assert rel["relation_is_possession_truth"] is False
    assert rel["relation_is_causal_influence_truth"] is False
    assert out["next_player_receiver_heuristic_used"] is False
    assert out["claim_ceiling"] == "MATCH_LOCAL_EXPLICIT_TYPED_RECEIVER_RELATION_ONLY"


def test_explicit_receiver_relation_blocks_missing_receiver_instead_of_inferring_next_player():
    rows = [
        {
            "source_row_ref": "r1",
            "team_identity_candidate_id": "team_a",
            "actor_identity_candidate_id": "p1",
            "action_family_candidate": "PASS",
            "receiver_relation_semantics_verified": True,
        }
    ]
    out = build_explicit_receiver_relations(rows, eligible_action_families={"PASS"})
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["admitted_relation_n"] == 0
    assert out["blocked_row_n"] == 1
    assert out["next_player_receiver_heuristic_used"] is False
