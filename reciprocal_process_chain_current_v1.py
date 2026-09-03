from __future__ import annotations

import argparse
import json
from pathlib import Path

import visible_action_sequence_candidates_current_v1 as current_sequence
from hpfa.modules.core.reciprocal_process_chain_lite.src import reciprocal_process_chain as reciprocal

TEMPORAL_JSON = "temporal_episode_signature_lite_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = reciprocal.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    sequence_payload = current_sequence.runtime_write_outputs(input_dir, output)
    temporal_path = output / TEMPORAL_JSON
    if sequence_payload.get("status") == "FAIL_CLOSED" or not temporal_path.is_file():
        payload = {
            "module_id": reciprocal.MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "RECIPROCAL_PROCESS_INPUT_REJECTED",
            "claim_ceiling": reciprocal.CLAIM_CEILING,
            "reciprocal_process_chain_candidates": [],
            "reciprocal_process_chain_candidate_count": 0,
            "counter_response_visible_count": 0,
            "episode_bound_chain_count": 0,
            "unknown_episode_binding_count": 0,
            "same_time_response_candidate_block_count": 0,
            "response_family_pair_counts": {},
            "hard_block_hits": ["current_sequence_fail_closed_or_temporal_output_missing"],
            "review_hits": [],
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "response_relation_is_causal_truth": False,
            "response_relation_is_tactical_truth": False,
            "possession_truth": False,
            "sequence_truth": False,
            "phase_truth": False,
            "tactical_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "current_sequence_status": sequence_payload.get("status"),
        }
        reciprocal.write_outputs(payload, output)
        return payload

    temporal_payload = _load(temporal_path)
    payload = reciprocal.build_reciprocal_process_chains(sequence_payload, temporal_payload)
    payload["current_sequence_status"] = sequence_payload.get("status")
    payload["active_match_evidence_pass"] = False
    paths = reciprocal.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA current reciprocal visible process chain candidate runner")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": payload.get("status"),
        "current_sequence_status": payload.get("current_sequence_status"),
        "reciprocal_process_chain_candidate_count": payload.get("reciprocal_process_chain_candidate_count"),
        "counter_response_visible_count": payload.get("counter_response_visible_count"),
        "episode_bound_chain_count": payload.get("episode_bound_chain_count"),
        "same_time_response_candidate_block_count": payload.get("same_time_response_candidate_block_count"),
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
