from hpfa.modules.core.cross_role_relation_candidate_resolver_lite.src.dependency_topology import (
    PARTIAL_SEMANTIC_PROJECTION,
    ROLE_TRANSFORMATION,
    UNRESOLVED,
    classify_cross_role_dependency,
)


def test_player_team_is_partial_semantic_projection_not_reflection_truth():
    result = classify_cross_role_dependency([
        "PLAYER_SURFACE_CANDIDATE",
        "TEAM_SURFACE_CANDIDATE",
    ])
    assert result["dependency_type"] == PARTIAL_SEMANTIC_PROJECTION
    assert result["independent_support_allowed"] is False
    assert result["reflection_equivalence_truth"] is False
    assert result["event_identity_truth"] is False
    assert result["occurrence_identity_truth"] is False


def test_goalkeeper_team_is_role_transformation_not_reflection_truth():
    result = classify_cross_role_dependency([
        "GOALKEEPER_SURFACE_CANDIDATE",
        "TEAM_SURFACE_CANDIDATE",
    ])
    assert result["dependency_type"] == ROLE_TRANSFORMATION
    assert result["independent_support_allowed"] is False
    assert result["reflection_equivalence_truth"] is False
    assert result["production_release"] is False


def test_unknown_pair_fails_closed_to_unresolved_dependency():
    result = classify_cross_role_dependency([
        "PLAYER_SURFACE_CANDIDATE",
        "GOALKEEPER_SURFACE_CANDIDATE",
    ])
    assert result["dependency_type"] == UNRESOLVED
    assert result["claim_ceiling"] == "DEPENDENCY_DESCRIPTION_ONLY"
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
