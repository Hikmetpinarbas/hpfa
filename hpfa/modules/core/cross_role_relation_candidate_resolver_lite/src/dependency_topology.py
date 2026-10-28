from __future__ import annotations

from typing import Iterable

CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "DEPENDENCY_DESCRIPTION_ONLY"

PLAYER = "PLAYER_SURFACE_CANDIDATE"
TEAM = "TEAM_SURFACE_CANDIDATE"
GOALKEEPER = "GOALKEEPER_SURFACE_CANDIDATE"

SERIALIZATION_REFLECTION = "SERIALIZATION_REFLECTION"
PARTIAL_SEMANTIC_PROJECTION = "PARTIAL_SEMANTIC_PROJECTION"
ROLE_TRANSFORMATION = "ROLE_TRANSFORMATION"
UNRESOLVED = "UNRESOLVED"


def classify_cross_role_dependency(source_roles: Iterable[str]) -> dict[str, object]:
    """Classify an already-observed cross-role overlap without promoting it to event truth.

    This helper deliberately answers only the dependency question.  It does not
    establish occurrence identity, independent support, or reflection equivalence.
    """
    roles = tuple(sorted({str(role or "").strip() for role in source_roles if str(role or "").strip()}))

    if roles == tuple(sorted((PLAYER, TEAM))):
        dependency_type = PARTIAL_SEMANTIC_PROJECTION
        rationale = "player_surface_carries_actor_semantics_while_team_surface_is_not_proven_equivalent"
    elif roles == tuple(sorted((GOALKEEPER, TEAM))):
        dependency_type = ROLE_TRANSFORMATION
        rationale = "goalkeeper_surface_may_encode_role_transformed_or_opponent_referenced_semantics"
    else:
        dependency_type = UNRESOLVED
        rationale = "cross_role_dependency_not_covered_by_closed_pair_taxonomy"

    return {
        "source_roles": list(roles),
        "dependency_type": dependency_type,
        "dependency_rationale": rationale,
        "independent_support_allowed": False,
        "reflection_equivalence_truth": False,
        "event_identity_truth": False,
        "occurrence_identity_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "claim_ceiling": CLAIM_CEILING,
        "production_release": False,
    }
