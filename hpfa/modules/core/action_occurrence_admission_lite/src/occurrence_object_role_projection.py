from __future__ import annotations

from collections import Counter
from typing import Any

CLAIM_CEILING = "OBJECT_ROLE_RELATION_DESCRIPTION_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _binding(object_type: str, object_ref: str, role: str) -> dict[str, Any]:
    return {
        "object_type": object_type,
        "object_ref": object_ref,
        "object_role": role,
        "object_identity_truth": False,
        "independent_support_vote": False,
    }


def project_occurrence_object_roles(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach bounded multi-object refs without duplicating occurrence identity.

    This is an OCEL-like projection only. It does not create case/possession/process
    identity, event truth, or independent evidence votes.
    """
    candidates = payload.get("action_occurrence_candidates") or []
    projected: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    review_hits: list[str] = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        occurrence_ref = _clean(candidate.get("action_occurrence_candidate_id"))
        if not occurrence_ref:
            review_hits.append("object_role_projection_occurrence_ref_missing")
            continue

        bindings: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        for object_type, field, role in (
            ("PLAYER_CANDIDATE", "actor_identity_candidate_id", "PRIMARY_ACTOR"),
            ("TEAM_CANDIDATE", "team_identity_candidate_id", "PRIMARY_TEAM"),
            ("PLAYER_CANDIDATE", "opponent_identity_candidate_id", "COUNTERPART_ACTOR"),
            ("TEAM_CANDIDATE", "opponent_team_identity_candidate_id", "COUNTERPART_TEAM"),
        ):
            ref = _clean(candidate.get(field))
            if not ref:
                continue
            key = (object_type, ref, role)
            if key in seen:
                continue
            seen.add(key)
            bindings.append(_binding(object_type, ref, role))
            counts[f"{object_type}:{role}"] += 1

        relation = candidate.get("relation_bundle") or {}
        relation_type = _clean(relation.get("relation_type"))
        projected.append({
            "action_occurrence_candidate_id": occurrence_ref,
            "object_role_bindings": bindings,
            "object_role_binding_count": len(bindings),
            "relation_type_candidate": relation_type or None,
            "process_object_binding_state": "NOT_AVAILABLE_AT_OCCURRENCE_ADMISSION",
            "spatial_state_object_binding_state": "NOT_AVAILABLE_AT_OCCURRENCE_ADMISSION",
            "consequence_object_binding_state": "NOT_AVAILABLE_AT_OCCURRENCE_ADMISSION",
            "occurrence_duplicated_per_object": False,
            "object_binding_creates_case_identity": False,
            "object_binding_creates_possession_truth": False,
            "object_binding_creates_process_truth": False,
            "object_binding_creates_independent_support": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    payload["occurrence_object_role_projection"] = projected
    payload["occurrence_object_role_projection_count"] = len(projected)
    payload["occurrence_object_role_binding_type_counts"] = dict(sorted(counts.items()))
    payload["occurrence_object_role_projection_review_hits"] = sorted(set(review_hits))
    payload["occurrence_object_binding_creates_case_identity"] = False
    payload["occurrence_object_binding_creates_possession_truth"] = False
    payload["occurrence_object_binding_creates_process_truth"] = False
    payload["occurrence_object_binding_creates_independent_support"] = False
    payload["occurrence_object_role_claim_ceiling"] = CLAIM_CEILING
    return payload
