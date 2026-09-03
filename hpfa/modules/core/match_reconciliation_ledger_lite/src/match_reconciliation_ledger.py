from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "match_reconciliation_ledger_lite_v2"
RECIPROCAL_MODULE_ID = "reciprocal_process_chain_lite_v1"
SEQUENCE_MODULE_ID = "visible_action_sequence_candidates_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
IDENTITY_MODULE_ID = "match_local_identity_candidates_lite_v1"
CLAIM_CEILING = "BIDIRECTIONAL_PLAYER_TEAM_PROCESS_RECONCILIATION_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "match_reconciliation_ledger_lite_v2.json"
OUTPUT_TXT = "match_reconciliation_ledger_lite_v2.txt"
ANALYST_TXT = "match_reconciliation_ledger_analyst_audit_v2.txt"

ROLE_FIELDS = {
    "anchor": (
        "anchor_visible_action_sequence_candidate_id",
        "anchor_team_identity_candidate_id",
        "anchor_episode_candidate_id",
    ),
    "response": (
        "response_visible_action_sequence_candidate_id",
        "response_team_identity_candidate_id",
        "response_episode_candidate_id",
    ),
    "counter_response": (
        "counter_response_visible_action_sequence_candidate_id",
        "counter_response_team_identity_candidate_id",
        "counter_response_episode_candidate_id",
    ),
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _validate_lock(payload: dict[str, Any], name: str, blocks: list[str]) -> None:
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{name}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append(f"{name}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{name}_production_release_claimed")


def _index_unique(
    rows: Any,
    key: str,
    label: str,
    blocks: list[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        blocks.append(f"{label}_collection_invalid")
        return {}
    out: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"{label}_record_invalid:{index}")
            continue
        value = _clean(row.get(key))
        if not value:
            blocks.append(f"{label}_id_missing:{index}")
            continue
        if value in out:
            blocks.append(f"{label}_duplicate_id:{value}")
            continue
        out[value] = row
    return out


def build_match_reconciliation_ledger(
    reciprocal_payload: dict[str, Any],
    sequence_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    identity_payload: dict[str, Any],
) -> dict[str, Any]:
    """Reconcile visible process candidates from team -> player -> team.

    The ledger reuses current reciprocal, sequence, trace and match-local identity
    candidate surfaces. It creates no action, episode, possession, phase, causal,
    tactical or canonical-event truth. A player may have many traces in one
    process; those traces never inflate process or episode counts.
    """
    blocks: list[str] = []
    reviews: list[str] = []

    expected_ids = (
        ("reciprocal", reciprocal_payload, RECIPROCAL_MODULE_ID),
        ("sequence", sequence_payload, SEQUENCE_MODULE_ID),
        ("trace", trace_payload, TRACE_MODULE_ID),
        ("identity", identity_payload, IDENTITY_MODULE_ID),
    )
    for name, payload, expected in expected_ids:
        if payload.get("module_id") != expected:
            blocks.append(f"{name}_module_id_mismatch")
        _validate_lock(payload, name, blocks)
        if _status(payload.get("status") or payload.get("module_status")) == "FAIL_CLOSED":
            blocks.append(f"{name}_input_fail_closed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_input_hard_blocked")

    chains = reciprocal_payload.get("reciprocal_process_chain_candidates") or []
    if not isinstance(chains, list):
        blocks.append("reciprocal_chain_collection_invalid")
        chains = []
    if reciprocal_payload.get("reciprocal_process_chain_candidate_count") != len(chains):
        blocks.append("reciprocal_chain_count_mismatch")

    sequence_by_id = _index_unique(
        sequence_payload.get("visible_action_sequence_candidates") or [],
        "visible_action_sequence_candidate_id",
        "sequence",
        blocks,
    )
    trace_by_id = _index_unique(
        trace_payload.get("trackable_action_trace_candidates") or [],
        "trackable_action_trace_candidate_id",
        "trace",
        blocks,
    )
    actor_by_id = _index_unique(
        identity_payload.get("actor_identity_candidates") or [],
        "actor_identity_candidate_id",
        "actor_identity",
        blocks,
    )
    team_by_id = _index_unique(
        identity_payload.get("team_identity_candidates") or [],
        "team_identity_candidate_id",
        "team_identity",
        blocks,
    )

    edge_rows: list[dict[str, Any]] = []
    seen_edges: set[str] = set()
    team_episode_sets: dict[str, set[str]] = defaultdict(set)
    team_process_role_memberships: dict[str, Counter[str]] = defaultdict(Counter)
    player_state: dict[str, dict[str, Any]] = {}
    supporting_trace_ids: set[str] = set()

    if not blocks:
        for index, chain in enumerate(chains):
            if not isinstance(chain, dict):
                blocks.append(f"reciprocal_chain_record_invalid:{index}")
                continue
            chain_id = _clean(chain.get("reciprocal_process_chain_candidate_id"))
            anchor_sequence = _clean(chain.get("anchor_visible_action_sequence_candidate_id"))
            response_sequence = _clean(chain.get("response_visible_action_sequence_candidate_id"))
            if not chain_id or not anchor_sequence or not response_sequence:
                blocks.append(f"reciprocal_core_identity_missing:{index}")
                continue
            edge_id = "rce_" + _digest(anchor_sequence, response_sequence)[:24]
            if edge_id in seen_edges:
                blocks.append(f"duplicate_reciprocal_edge:{edge_id}")
                continue
            seen_edges.add(edge_id)

            edge_roles: dict[str, Any] = {}
            for role, (sequence_field, team_field, episode_field) in ROLE_FIELDS.items():
                if role == "counter_response" and not chain.get("counter_response_visible"):
                    continue
                sequence_id = _clean(chain.get(sequence_field))
                team_id = _clean(chain.get(team_field))
                episode_id = _clean(chain.get(episode_field))
                if not sequence_id or not team_id:
                    blocks.append(f"{role}_sequence_or_team_missing:{chain_id}")
                    continue
                sequence_row = sequence_by_id.get(sequence_id)
                if sequence_row is None:
                    blocks.append(f"{role}_sequence_not_found:{chain_id}:{sequence_id}")
                    continue
                sequence_team = _clean(sequence_row.get("team_identity_candidate_id"))
                if sequence_team != team_id:
                    blocks.append(f"{role}_sequence_team_mismatch:{chain_id}:{sequence_id}")
                    continue
                if team_id not in team_by_id:
                    reviews.append(
                        f"{role}_team_identity_candidate_not_in_identity_surface:{chain_id}:{team_id}"
                    )

                team_process_role_memberships[team_id][role] += 1
                if episode_id:
                    team_episode_sets[team_id].add(episode_id)
                else:
                    reviews.append(f"{role}_episode_binding_incomplete:{chain_id}")

                role_actor_ids: set[str] = set()
                role_trace_ids: set[str] = set()
                for raw_trace_id in sequence_row.get("trackable_action_trace_candidate_ids") or []:
                    trace_id = _clean(raw_trace_id)
                    if not trace_id:
                        continue
                    trace_row = trace_by_id.get(trace_id)
                    if trace_row is None:
                        blocks.append(f"{role}_trace_not_found:{chain_id}:{trace_id}")
                        continue
                    trace_team = _clean(trace_row.get("team_identity_candidate_id"))
                    if trace_team != team_id:
                        blocks.append(f"{role}_trace_team_mismatch:{chain_id}:{trace_id}")
                        continue
                    role_trace_ids.add(trace_id)
                    supporting_trace_ids.add(trace_id)
                    actor_id = _clean(trace_row.get("actor_identity_candidate_id"))
                    if actor_id:
                        role_actor_ids.add(actor_id)

                for actor_id in sorted(role_actor_ids):
                    identity_row = actor_by_id.get(actor_id)
                    if identity_row is None:
                        reviews.append(
                            f"actor_identity_candidate_not_in_identity_surface:{chain_id}:{actor_id}"
                        )
                    else:
                        identity_team = _clean(identity_row.get("team_identity_candidate_id"))
                        if identity_team and identity_team != team_id:
                            blocks.append(f"actor_team_mismatch:{chain_id}:{actor_id}")
                            continue

                    state = player_state.setdefault(
                        actor_id,
                        {
                            "team_identity_candidate_id": team_id,
                            "process_ids": set(),
                            "episode_ids": set(),
                            "sequence_ids": set(),
                            "trace_ids": set(),
                            "role_membership_counts": Counter(),
                        },
                    )
                    if state["team_identity_candidate_id"] != team_id:
                        blocks.append(f"actor_multi_team_conflict:{actor_id}")
                        continue
                    state["process_ids"].add(chain_id)
                    if episode_id:
                        state["episode_ids"].add(episode_id)
                    state["sequence_ids"].add(sequence_id)
                    state["role_membership_counts"][role] += 1
                    for trace_id in role_trace_ids:
                        trace_row = trace_by_id.get(trace_id) or {}
                        if _clean(trace_row.get("actor_identity_candidate_id")) == actor_id:
                            state["trace_ids"].add(trace_id)

                edge_roles[role] = {
                    "sequence_candidate_id": sequence_id,
                    "team_identity_candidate_id": team_id,
                    "episode_candidate_id": episode_id or None,
                    "actor_identity_candidate_ids": sorted(role_actor_ids),
                    "actor_membership_count": len(role_actor_ids),
                    "supporting_trace_candidate_ids": sorted(role_trace_ids),
                }

            edge_rows.append(
                {
                    "reciprocal_consistency_edge_id": edge_id,
                    "reciprocal_process_chain_candidate_id": chain_id,
                    "roles": edge_roles,
                    "shared_edge_identity": True,
                    "response_relation_is_causal_truth": False,
                    "response_relation_is_tactical_truth": False,
                    "claim_ceiling": CLAIM_CEILING,
                }
            )

    team_process_totals = {
        team_id: int(sum(counter.values()))
        for team_id, counter in team_process_role_memberships.items()
    }

    player_rows: list[dict[str, Any]] = []
    team_player_episode_sets: dict[str, set[str]] = defaultdict(set)
    for actor_id in sorted(player_state):
        state = player_state[actor_id]
        team_id = state["team_identity_candidate_id"]
        episode_ids = sorted(state["episode_ids"])
        team_player_episode_sets[team_id].update(episode_ids)
        identity_row = actor_by_id.get(actor_id) or {}
        team_memberships = team_process_totals.get(team_id, 0)
        process_count = len(state["process_ids"])
        team_episode_count = len(team_episode_sets.get(team_id, set()))
        player_rows.append(
            {
                "actor_identity_candidate_id": actor_id,
                "actor_normalized_key_candidate": identity_row.get("actor_normalized_key"),
                "team_identity_candidate_id": team_id,
                "unique_process_candidate_count": process_count,
                "unique_process_candidate_ids": sorted(state["process_ids"]),
                "unique_episode_candidate_count": len(episode_ids),
                "unique_episode_candidate_ids": episode_ids,
                "unique_sequence_candidate_count": len(state["sequence_ids"]),
                "supporting_unique_trace_candidate_count": len(state["trace_ids"]),
                "role_membership_counts": dict(sorted(state["role_membership_counts"].items())),
                "visible_process_membership_share_of_team_candidate": (
                    round(process_count / team_memberships, 6) if team_memberships else None
                ),
                "visible_episode_membership_share_of_team_candidate": (
                    round(len(episode_ids) / team_episode_count, 6)
                    if team_episode_count
                    else None
                ),
                "membership_share_is_quality_truth": False,
                "membership_share_is_tactical_importance_truth": False,
                "validated_player_identity": False,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    team_rows: list[dict[str, Any]] = []
    all_team_ids = sorted(
        set(team_episode_sets)
        | set(team_process_role_memberships)
        | set(team_player_episode_sets)
    )
    all_team_unions_match = bool(all_team_ids)
    for team_id in all_team_ids:
        team_episode_ids = set(team_episode_sets.get(team_id, set()))
        player_union_ids = set(team_player_episode_sets.get(team_id, set()))
        missing = sorted(team_episode_ids - player_union_ids)
        extra = sorted(player_union_ids - team_episode_ids)
        union_matches = bool(team_episode_ids) and not missing and not extra
        all_team_unions_match = all_team_unions_match and union_matches
        if missing or extra:
            reviews.append(f"team_player_episode_union_mismatch:{team_id}")
        identity_row = team_by_id.get(team_id) or {}
        team_rows.append(
            {
                "team_identity_candidate_id": team_id,
                "team_normalized_key_candidate": identity_row.get("team_normalized_key"),
                "unique_team_episode_candidate_count": len(team_episode_ids),
                "unique_team_episode_candidate_ids": sorted(team_episode_ids),
                "player_episode_union_candidate_count": len(player_union_ids),
                "player_episode_union_candidate_ids": sorted(player_union_ids),
                "missing_from_player_union_episode_candidate_ids": missing,
                "extra_in_player_union_episode_candidate_ids": extra,
                "player_episode_union_matches_team_episode_union_candidate": union_matches,
                "reciprocal_process_role_membership_counts": dict(
                    sorted(team_process_role_memberships.get(team_id, Counter()).items())
                ),
                "reciprocal_process_role_membership_count": team_process_totals.get(team_id, 0),
                "episode_count_is_unique_union_not_player_membership_sum": True,
                "validated_team_identity": False,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    for payload_name, payload in (
        ("reciprocal", reciprocal_payload),
        ("sequence", sequence_payload),
        ("trace", trace_payload),
        ("identity", identity_payload),
    ):
        if _status(payload.get("status") or payload.get("module_status")) == "REVIEW_REQUIRED":
            reviews.append(f"{payload_name}_upstream_review_required")

    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": (
            "BIDIRECTIONAL_PLAYER_TEAM_PROCESS_RECONCILIATION_BUILT"
            if status != "FAIL_CLOSED"
            else "BIDIRECTIONAL_PLAYER_TEAM_PROCESS_RECONCILIATION_REJECTED"
        ),
        "claim_ceiling": CLAIM_CEILING,
        "reciprocal_consistency_edges": edge_rows if not blocks else [],
        "reciprocal_consistency_edge_count": len(edge_rows) if not blocks else 0,
        "cross_side_consistency_candidate": bool(edge_rows) and not blocks,
        "team_reconciliation_rows": team_rows if not blocks else [],
        "player_process_membership_rows": player_rows if not blocks else [],
        "player_process_membership_row_count": len(player_rows) if not blocks else 0,
        "player_team_episode_reconciliation_state": (
            "CONSISTENT_CANDIDATE"
            if all_team_unions_match and not blocks
            else "REVIEW_REQUIRED"
        ),
        "player_team_episode_union_consistent_team_count": (
            sum(
                row["player_episode_union_matches_team_episode_union_candidate"]
                for row in team_rows
            )
            if not blocks
            else 0
        ),
        "supporting_unique_trace_candidate_count": (
            len(supporting_trace_ids) if not blocks else 0
        ),
        "loss_recovery_reconciliation_status": (
            "NOT_EVALUATED_EXPLICIT_RELATION_SURFACE_NOT_BOUND"
        ),
        "shot_gk_reconciliation_status": (
            "NOT_EVALUATED_EXPLICIT_RELATION_SURFACE_NOT_BOUND"
        ),
        "phase_reconciliation_status": (
            "NOT_EVALUATED_TEAM_CONDITIONED_PHASE_ACTIVITY_SURFACE_NOT_BOUND"
        ),
        "accounting_invariants": {
            "one_player_many_traces_does_not_create_many_processes": True,
            "team_episode_count_uses_unique_episode_union": True,
            "player_episode_union_compares_sets_not_membership_sums": True,
            "forward_reverse_views_share_one_reciprocal_edge": True,
            "membership_share_is_not_quality_or_tactical_importance": True,
        },
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "possession_truth": False,
        "phase_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "causal_truth": False,
    }


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _analyst(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "HPFA ANALYST AUDIT — PLAYER ↔ TEAM PROCESS RECONCILIATION V2",
            f"status={payload.get('status')}",
            f"reciprocal_edges={payload.get('reciprocal_consistency_edge_count', 0)}",
            (
                "players_with_visible_process_membership="
                f"{payload.get('player_process_membership_row_count', 0)}"
            ),
            (
                "teams_with_exact_player_episode_union="
                f"{payload.get('player_team_episode_union_consistent_team_count', 0)}"
            ),
            (
                "player_team_episode_state="
                f"{payload.get('player_team_episode_reconciliation_state')}"
            ),
            "",
            (
                "Safe meaning: visible team process episodes can be projected down to actor "
                "candidates and unioned back to the same team episode set where the evidence "
                "graph is complete."
            ),
            (
                "This is participation/accounting evidence only; it is not player quality, "
                "tactical importance, causality, possession, phase or canonical-event truth."
            ),
            "",
        ]
    )


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    analyst_path = output / ANALYST_TXT
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    txt_path.write_text(
        "\n".join(
            [
                "HPFA MATCH RECONCILIATION LEDGER LITE V2",
                f"status={payload.get('status')}",
                (
                    "reciprocal_consistency_edge_count="
                    f"{payload.get('reciprocal_consistency_edge_count', 0)}"
                ),
                (
                    "player_process_membership_row_count="
                    f"{payload.get('player_process_membership_row_count', 0)}"
                ),
                (
                    "player_team_episode_reconciliation_state="
                    f"{payload.get('player_team_episode_reconciliation_state')}"
                ),
                "canonical_event_count=UNKNOWN",
                "true_action_count=UNKNOWN",
                "production_release=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    analyst_path.write_text(_analyst(payload), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
