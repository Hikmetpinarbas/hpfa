from __future__ import annotations

import argparse
import json
from pathlib import Path

import trackable_action_consequence_candidates_current_v1 as current_consequence
from hpfa.modules.core.visible_action_sequence_candidates_lite.src import (
    visible_action_sequence_candidates as sequence,
)


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = sequence.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    consequence_payload = current_consequence.runtime_write_outputs(input_dir, output)
    trace_path = output / "trackable_action_trace_candidates_lite_v1.json"

    if consequence_payload.get("status") == "FAIL_CLOSED" or not trace_path.is_file():
        return {
            "module_id": sequence.MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "visible_action_time_layer_candidates": [],
            "visible_action_sequence_candidates": [],
            "visible_sequence_boundary_candidates": [],
            "trace_assignments": [],
            "review_time_layer_candidates": [],
            "source_trackable_action_trace_candidate_count": 0,
            "source_trackable_action_consequence_candidate_count": 0,
            "visible_action_time_layer_candidate_count": 0,
            "single_team_primary_layer_count": 0,
            "mixed_team_primary_layer_review_required_count": 0,
            "visible_action_sequence_candidate_count": 0,
            "primary_sequence_member_trace_count": 0,
            "review_layer_member_trace_count": 0,
            "trace_assignment_count": 0,
            "trace_assignment_complete": False,
            "hard_block_hits": ["current_consequence_fail_closed_or_trace_output_missing"],
            "review_hits": [],
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "visible_sequence_candidate_is_sequence_truth": False,
            "visible_sequence_candidate_is_possession_truth": False,
            "sequence_truth": False,
            "possession_truth": False,
            "phase_truth": False,
            "tactical_truth": False,
            "event_instance_count": 0,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "current_consequence_status": consequence_payload.get("status"),
        }

    trace_payload = _load(trace_path)
    payload = sequence.build_visible_action_sequence_candidates(trace_payload, consequence_payload)
    payload["current_consequence_status"] = consequence_payload.get("status")
    payload["current_trace_status"] = consequence_payload.get("current_trace_status")
    payload["current_content_source_role_bridge_status"] = consequence_payload.get(
        "current_content_source_role_bridge_status"
    )
    payload["active_match_evidence_pass"] = False
    paths = sequence.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA current Trackable Action consequence to visible sequence candidates")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": payload.get("status"),
        "current_consequence_status": payload.get("current_consequence_status"),
        "source_trackable_action_trace_candidate_count": payload.get("source_trackable_action_trace_candidate_count"),
        "visible_action_time_layer_candidate_count": payload.get("visible_action_time_layer_candidate_count"),
        "single_team_primary_layer_count": payload.get("single_team_primary_layer_count"),
        "mixed_team_primary_layer_review_required_count": payload.get("mixed_team_primary_layer_review_required_count"),
        "visible_action_sequence_candidate_count": payload.get("visible_action_sequence_candidate_count"),
        "pass_multi_layer_visible_sequence_candidate_count": payload.get("pass_multi_layer_visible_sequence_candidate_count"),
        "pass_single_layer_visible_trace_candidate_count": payload.get("pass_single_layer_visible_trace_candidate_count"),
        "review_required_sequence_context_count": payload.get("review_required_sequence_context_count"),
        "primary_sequence_member_trace_count": payload.get("primary_sequence_member_trace_count"),
        "review_layer_member_trace_count": payload.get("review_layer_member_trace_count"),
        "trace_assignment_complete": payload.get("trace_assignment_complete"),
        "boundary_reason_counts": payload.get("boundary_reason_counts") or {},
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
