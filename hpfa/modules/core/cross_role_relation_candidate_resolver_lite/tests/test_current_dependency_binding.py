import cross_role_relation_candidate_resolver_current_v1 as current


def test_current_binding_types_player_and_goalkeeper_relations_without_independent_support():
    payload = {
        "resolved_relation_candidates": [
            {
                "source_roles": [
                    "PLAYER_SURFACE_CANDIDATE",
                    "TEAM_SURFACE_CANDIDATE",
                ]
            },
            {
                "source_roles": [
                    "GOALKEEPER_SURFACE_CANDIDATE",
                    "TEAM_SURFACE_CANDIDATE",
                ]
            },
        ]
    }

    out = current._bind_dependency_topology(payload)

    assert out["dependency_type_counts"] == {
        "PARTIAL_SEMANTIC_PROJECTION": 1,
        "ROLE_TRANSFORMATION": 1,
    }
    assert out["typed_dependency_candidate_count"] == 2
    assert out["typed_dependency_independent_support_allowed"] is False
    assert out["typed_dependency_event_identity_truth"] is False
    assert out["typed_dependency_occurrence_identity_truth"] is False
    assert all(
        row["independent_support_allowed"] is False
        for row in out["resolved_relation_candidates"]
    )
