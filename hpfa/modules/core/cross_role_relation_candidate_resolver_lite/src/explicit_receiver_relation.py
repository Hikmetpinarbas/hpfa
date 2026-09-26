from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

CLAIM_CEILING = "MATCH_LOCAL_EXPLICIT_TYPED_RECEIVER_RELATION_ONLY"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _relation_id(row_ref: str, team_id: str, passer_id: str, receiver_id: str) -> str:
    payload = json.dumps(
        [row_ref, team_id, passer_id, receiver_id],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "receiver_relation:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def build_explicit_receiver_relations(
    rows: Iterable[dict[str, Any]],
    *,
    eligible_action_families: set[str],
) -> dict[str, Any]:
    """Admit only provider-explicit, semantically verified passer→receiver relations.

    The function never infers a receiver from row order, the next player, same-team
    continuation, or temporal proximity. Output remains a match-local typed relation
    candidate surface; it does not establish possession, team shape, player quality,
    or causal influence.
    """
    eligible = {str(value).strip().upper() for value in eligible_action_families if str(value).strip()}
    admitted: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    eligible_row_n = 0

    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        family = _clean(raw.get("action_family_candidate")).upper()
        if family not in eligible:
            continue
        eligible_row_n += 1

        row_ref = _clean(raw.get("source_row_ref")) or f"row:{index}"
        team_id = _clean(raw.get("team_identity_candidate_id"))
        passer_id = _clean(raw.get("actor_identity_candidate_id"))
        receiver_id = _clean(raw.get("receiver_identity_candidate_id"))
        source_field = _clean(raw.get("receiver_relation_source_field"))
        semantics_verified = raw.get("receiver_relation_semantics_verified") is True

        reasons: list[str] = []
        if not semantics_verified:
            reasons.append("RECEIVER_FIELD_SEMANTICS_UNVERIFIED")
        if not team_id:
            reasons.append("TEAM_IDENTITY_MISSING")
        if not passer_id:
            reasons.append("PASSER_IDENTITY_MISSING")
        if not receiver_id:
            reasons.append("RECEIVER_IDENTITY_MISSING")
        if not source_field:
            reasons.append("RECEIVER_SOURCE_FIELD_MISSING")
        if passer_id and receiver_id and passer_id == receiver_id:
            reasons.append("SELF_RECEIVER_RELATION_REJECTED")

        if reasons:
            blocked.append(
                {
                    "source_row_ref": row_ref,
                    "action_family_candidate": family,
                    "block_reasons": reasons,
                }
            )
            continue

        admitted.append(
            {
                "explicit_receiver_relation_candidate_id": _relation_id(
                    row_ref, team_id, passer_id, receiver_id
                ),
                "source_row_ref": row_ref,
                "team_identity_candidate_id": team_id,
                "passer_actor_identity_candidate_id": passer_id,
                "receiver_actor_identity_candidate_id": receiver_id,
                "action_family_candidate": family,
                "receiver_relation_source_field": source_field,
                "receiver_relation_admitted": True,
                "relation_is_possession_truth": False,
                "relation_is_team_shape_truth": False,
                "relation_is_causal_influence_truth": False,
                "creates_independent_support": False,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    if admitted:
        status = "PASS" if not blocked else "REVIEW_REQUIRED"
    else:
        status = "REVIEW_REQUIRED" if eligible_row_n else "NOT_EVALUATED"

    return {
        "status": status,
        "eligible_action_families": sorted(eligible),
        "eligible_row_n": eligible_row_n,
        "admitted_relation_n": len(admitted),
        "blocked_row_n": len(blocked),
        "relations": admitted,
        "blocked_rows": blocked,
        "next_player_receiver_heuristic_used": False,
        "same_team_continuation_receiver_heuristic_used": False,
        "temporal_proximity_receiver_heuristic_used": False,
        "claim_ceiling": CLAIM_CEILING,
        "forbidden_inference": [
            "EXPLICIT_RECEIVER_RELATION_EQUALS_POSSESSION_TRUTH",
            "PASS_NETWORK_EQUALS_TEAM_SHAPE",
            "EDGE_FREQUENCY_EQUALS_PLAYER_QUALITY",
            "EDGE_RELATION_EQUALS_CAUSAL_INFLUENCE",
        ],
    }
