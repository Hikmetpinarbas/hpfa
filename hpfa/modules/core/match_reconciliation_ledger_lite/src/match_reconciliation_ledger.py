from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "match_reconciliation_ledger_lite_v1"
INPUT_MODULE_ID = "reciprocal_process_chain_lite_v1"
CLAIM_CEILING = "BIDIRECTIONAL_EVIDENCE_CONSISTENCY_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "match_reconciliation_ledger_lite_v1.json"
OUTPUT_TXT = "match_reconciliation_ledger_lite_v1.txt"
ANALYST_TXT = "match_reconciliation_ledger_analyst_audit_v1.txt"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _edge_id(anchor_id: str, response_id: str) -> str:
    return "rce_" + _digest("reciprocal_edge_v1", anchor_id, response_id)[:24]


def build_match_reconciliation_ledger(reciprocal_payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    if reciprocal_payload.get("module_id") != INPUT_MODULE_ID:
        blocks.append("reciprocal_module_id_mismatch")
    if reciprocal_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed_by_input")
    if reciprocal_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("true_action_count_claimed_by_input")
    if reciprocal_payload.get("production_release") is True:
        blocks.append("production_release_claimed_by_input")
    if reciprocal_payload.get("status") == "FAIL_CLOSED" or reciprocal_payload.get("hard_block_hits"):
        blocks.append("reciprocal_input_fail_closed")

    chains = reciprocal_payload.get("reciprocal_process_chain_candidates") or []
    if not isinstance(chains, list):
        blocks.append("reciprocal_chain_collection_invalid")
        chains = []
    if reciprocal_payload.get("reciprocal_process_chain_candidate_count") != len(chains):
        blocks.append("reciprocal_chain_count_mismatch")

    edges: list[dict[str, Any]] = []
    seen_edge_ids: set[str] = set()
    team_episode_sets: dict[str, set[str]] = defaultdict(set)
    team_process_membership_counts: Counter[str] = Counter()
    trace_ids: set[str] = set()

    if not blocks:
        for index, chain in enumerate(chains):
            if not isinstance(chain, dict):
                blocks.append(f"reciprocal_chain_record_invalid:{index}")
                continue
            anchor_id = _clean(chain.get("anchor_visible_action_sequence_candidate_id"))
            response_id = _clean(chain.get("response_visible_action_sequence_candidate_id"))
            anchor_team = _clean(chain.get("anchor_team_identity_candidate_id"))
            response_team = _clean(chain.get("response_team_identity_candidate_id"))
            if not anchor_id or not response_id or not anchor_team or not response_team:
                blocks.append(f"reciprocal_edge_identity_missing:{index}")
                continue
            if anchor_team == response_team:
                blocks.append(f"reciprocal_edge_same_team:{index}")
                continue
            edge_id = _edge_id(anchor_id, response_id)
            if edge_id in seen_edge_ids:
                blocks.append(f"duplicate_reciprocal_edge:{edge_id}")
                continue
            seen_edge_ids.add(edge_id)

            anchor_episode = _clean(chain.get("anchor_episode_candidate_id"))
            response_episode = _clean(chain.get("response_episode_candidate_id"))
            if anchor_episode:
                team_episode_sets[anchor_team].add(anchor_episode)
            if response_episode:
                team_episode_sets[response_team].add(response_episode)
            if not anchor_episode or not response_episode:
                reviews.append(f"edge_episode_binding_incomplete:{edge_id}")

            for trace_id in chain.get("supporting_trackable_action_trace_candidate_ids") or []:
                cleaned = _clean(trace_id)
                if cleaned:
                    trace_ids.add(cleaned)

            team_process_membership_counts[anchor_team] += 1
            team_process_membership_counts[response_team] += 1
            edges.append({
                "reciprocal_consistency_edge_id": edge_id,
                "anchor_team_identity_candidate_id": anchor_team,
                "anchor_sequence_candidate_id": anchor_id,
                "anchor_episode_candidate_id": anchor_episode or None,
                "response_team_identity_candidate_id": response_team,
                "response_sequence_candidate_id": response_id,
                "response_episode_candidate_id": response_episode or None,
                "forward_projection": f"{anchor_team}:{anchor_id} -> {response_team}:{response_id}",
                "reverse_projection": f"{response_team}:{response_id} <- {anchor_team}:{anchor_id}",
                "shared_edge_identity": True,
                "response_relation_is_causal_truth": False,
                "response_relation_is_tactical_truth": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    cross_side_consistency_pass = not blocks and all(row.get("shared_edge_identity") is True for row in edges)
    if reciprocal_payload.get("status") == "REVIEW_REQUIRED":
        reviews.append("reciprocal_upstream_review_required")

    team_rows = []
    for team in sorted(set(team_episode_sets) | set(team_process_membership_counts)):
        episode_ids = sorted(team_episode_sets.get(team, set()))
        team_rows.append({
            "team_identity_candidate_id": team,
            "unique_episode_candidate_count": len(episode_ids),
            "unique_episode_candidate_ids": episode_ids,
            "reciprocal_process_membership_count": int(team_process_membership_counts.get(team, 0)),
            "episode_count_is_union_not_membership_sum": True,
        })

    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "BIDIRECTIONAL_RECONCILIATION_LEDGER_BUILT" if status != "FAIL_CLOSED" else "BIDIRECTIONAL_RECONCILIATION_INPUT_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "reciprocal_consistency_edges": edges if not blocks else [],
        "reciprocal_consistency_edge_count": len(edges) if not blocks else 0,
        "cross_side_consistency_pass": cross_side_consistency_pass if not blocks else False,
        "team_episode_union_rows": team_rows if not blocks else [],
        "supporting_unique_trace_candidate_count": len(trace_ids) if not blocks else 0,
        "player_episode_membership_reconciliation_status": "NOT_EVALUATED_UPSTREAM_MEMBERSHIP_SURFACE_MISSING",
        "role_conditioned_player_contribution_status": "NOT_EVALUATED_UPSTREAM_ROLE_MEMBERSHIP_SURFACE_MISSING",
        "loss_recovery_reconciliation_status": "NOT_EVALUATED_EXPLICIT_RELATION_SURFACE_NOT_BOUND",
        "shot_gk_reconciliation_status": "NOT_EVALUATED_EXPLICIT_RELATION_SURFACE_NOT_BOUND",
        "accounting_invariants": {
            "annotation_count_does_not_equal_occurrence_count": True,
            "episode_count_uses_unique_union": True,
            "player_membership_sum_must_not_be_equated_to_team_episode_count": True,
            "reciprocal_forward_reverse_views_share_one_edge_id": True,
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


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    analyst_path = output / ANALYST_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_path.write_text("\n".join([
        "HPFA MATCH RECONCILIATION LEDGER LITE V1",
        f"status={payload.get('status')}",
        f"reciprocal_consistency_edge_count={payload.get('reciprocal_consistency_edge_count')}",
        f"cross_side_consistency_pass={payload.get('cross_side_consistency_pass')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    analyst_path.write_text(
        "HPFA ANALYST AUDIT — BIDIRECTIONAL EVIDENCE CONSISTENCY\n"
        "Forward and reverse reciprocal views share one evidence edge; team episode accounting uses unique episode-ID union.\n"
        "Player/team, loss/recovery, shot/GK and phase reconciliation remain explicitly unevaluated until upstream relation surfaces are bound.\n",
        encoding="utf-8",
    )
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
