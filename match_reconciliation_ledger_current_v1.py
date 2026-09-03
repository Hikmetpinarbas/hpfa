from __future__ import annotations

import argparse
import json
from pathlib import Path

import reciprocal_process_chain_current_v1 as current_reciprocal
from hpfa.modules.core.match_reconciliation_ledger_lite.src import match_reconciliation_ledger as ledger


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = ledger.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    reciprocal_payload = current_reciprocal.runtime_write_outputs(input_dir, output)
    if reciprocal_payload.get("status") == "FAIL_CLOSED":
        payload = {
            "module_id": ledger.MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "BIDIRECTIONAL_RECONCILIATION_INPUT_REJECTED",
            "claim_ceiling": ledger.CLAIM_CEILING,
            "reciprocal_consistency_edges": [],
            "reciprocal_consistency_edge_count": 0,
            "cross_side_consistency_pass": False,
            "team_episode_union_rows": [],
            "supporting_unique_trace_candidate_count": 0,
            "player_episode_membership_reconciliation_status": "NOT_EVALUATED_UPSTREAM_FAIL_CLOSED",
            "role_conditioned_player_contribution_status": "NOT_EVALUATED_UPSTREAM_FAIL_CLOSED",
            "loss_recovery_reconciliation_status": "NOT_EVALUATED_UPSTREAM_FAIL_CLOSED",
            "shot_gk_reconciliation_status": "NOT_EVALUATED_UPSTREAM_FAIL_CLOSED",
            "hard_block_hits": ["current_reciprocal_fail_closed"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "possession_truth": False,
            "phase_truth": False,
            "sequence_truth": False,
            "tactical_truth": False,
            "causal_truth": False,
        }
    else:
        payload = ledger.build_match_reconciliation_ledger(reciprocal_payload)
        payload["current_reciprocal_status"] = reciprocal_payload.get("status")
        payload["active_match_evidence_pass"] = False
    paths = ledger.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA current bidirectional match reconciliation ledger V1")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": payload.get("status"),
        "current_reciprocal_status": payload.get("current_reciprocal_status"),
        "reciprocal_consistency_edge_count": payload.get("reciprocal_consistency_edge_count"),
        "cross_side_consistency_pass": payload.get("cross_side_consistency_pass"),
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
