from __future__ import annotations

import argparse
import json
from pathlib import Path

import visible_action_sequence_candidates_current_v1 as current_sequence
from hpfa.modules.core.active_match_spine_runner.src.episode_lane_runner import run_current_episode_lane
from hpfa.modules.core.reciprocal_process_chain_lite.src import reciprocal_process_chain as reciprocal

TEMPORAL_JSON = "temporal_episode_signature_lite_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _fail_payload(sequence_payload: dict, reason: str, episode_lane_status: str | None = None) -> dict:
    return {
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
        "hard_block_hits": [reason],
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
        "current_episode_lane_status": episode_lane_status,
    }


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = reciprocal.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    # First build the current visible-sequence surface. This reuses the existing
    # reconstruction spine and emits the shared row-nucleus/bridge artifacts
    # required by the episode lane.
    sequence_payload = current_sequence.runtime_write_outputs(input_dir, output)
    if sequence_payload.get("status") == "FAIL_CLOSED":
        payload = _fail_payload(sequence_payload, "current_sequence_fail_closed")
        reciprocal.write_outputs(payload, output)
        return payload

    # IMPORTANT: never load a temporal artifact merely because it already exists
    # in out_dir. The episode lane clears its owned artifacts, validates the current
    # input-surface snapshot, and regenerates temporal_episode_signature for this
    # invocation. This prevents stale cross-match episode binding.
    execution_root = Path(__file__).resolve().parent
    episode_lane = run_current_episode_lane(input_dir, output, execution_root)
    temporal_path = output / TEMPORAL_JSON
    current_temporal_generated = (
        episode_lane.get("temporal_episode_signature_executed") is True
        and episode_lane.get("surface_snapshot_bound") is True
        and temporal_path.is_file()
        and str(temporal_path) in set(episode_lane.get("current_invocation_artifacts") or [])
    )
    if episode_lane.get("status") == "FAIL_CLOSED" or not current_temporal_generated:
        payload = _fail_payload(
            sequence_payload,
            "current_episode_lane_fail_closed_or_current_temporal_output_missing",
            str(episode_lane.get("status") or "UNKNOWN"),
        )
        reciprocal.write_outputs(payload, output)
        return payload

    temporal_payload = _load(temporal_path)
    payload = reciprocal.build_reciprocal_process_chains(sequence_payload, temporal_payload)
    payload["current_sequence_status"] = sequence_payload.get("status")
    payload["current_episode_lane_status"] = episode_lane.get("status")
    payload["current_temporal_generated"] = current_temporal_generated
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
        "current_episode_lane_status": payload.get("current_episode_lane_status"),
        "current_temporal_generated": payload.get("current_temporal_generated"),
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
