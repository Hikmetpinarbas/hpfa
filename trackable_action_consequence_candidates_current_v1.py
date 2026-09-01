from __future__ import annotations

import argparse
import json
from pathlib import Path

import trackable_action_trace_candidates_current_v1 as current_trace
from hpfa.modules.core.trackable_action_consequence_candidates_lite.src import (
    trackable_action_consequence_candidates as consequence,
)


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = consequence.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    trace_payload = current_trace.runtime_write_outputs(input_dir, output)
    evidence_path = output / "evidence_atom_inventory_lite_v1.json"

    if trace_payload.get("status") == "FAIL_CLOSED" or not evidence_path.is_file():
        return {
            "module_id": consequence.MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "match_surface_binding_id": trace_payload.get("match_surface_binding_id"),
            "trackable_action_consequence_candidates": [],
            "source_trackable_action_trace_candidate_count": trace_payload.get("trackable_action_trace_candidate_count", 0),
            "trackable_action_consequence_candidate_count": 0,
            "classified_consequence_candidate_count": 0,
            "review_required_consequence_candidate_count": 0,
            "support_visible_trace_count": 0,
            "occurrence_bound_consequence_candidate_count": 0,
            "occurrence_with_any_consequence_visible_count": 0,
            "occurrence_with_actor_consequence_visible_count": 0,
            "occurrence_with_opponent_consequence_visible_count": 0,
            "occurrence_with_both_participant_consequences_visible_count": 0,
            "primary_consequence_candidate_counts": {},
            "window_coverage_counts": {},
            "hard_block_hits": ["current_trackable_action_trace_fail_closed_or_evidence_output_missing"],
            "review_hits": [],
            "same_time_link_allowed": False,
            "negative_time_link_allowed": False,
            "cross_period_link_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "consequence_candidate_is_causal_truth": False,
            "continuation_candidate_is_possession_truth": False,
            "window_is_sequence_truth": False,
            "team_response_is_tactical_truth": False,
            "sequence_link_allowed": False,
            "occurrence_binding_is_event_truth": False,
            "event_instance_count": 0,
            "claim_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "current_trace_status": trace_payload.get("status"),
        }

    evidence_payload = _load(evidence_path)
    payload = consequence.build_trackable_action_consequence_candidates(
        trace_payload,
        evidence_payload,
    )

    trace_by_id = {
        str(row.get("trackable_action_trace_candidate_id")): row
        for row in trace_payload.get("trackable_action_trace_candidates") or []
        if isinstance(row, dict) and row.get("trackable_action_trace_candidate_id")
    }
    occurrence_bound_consequence_count = 0
    consequence_occurrence_ids: set[str] = set()
    for record in payload.get("trackable_action_consequence_candidates") or []:
        if not isinstance(record, dict):
            continue
        trace = trace_by_id.get(str(record.get("anchor_trackable_action_trace_candidate_id"))) or {}
        occurrence_ids = sorted(
            {
                str(value)
                for value in trace.get("supporting_action_occurrence_candidate_ids") or []
                if str(value).strip()
            }
        )
        record["supporting_action_occurrence_candidate_ids"] = occurrence_ids
        record["occurrence_bound_consequence_candidate"] = bool(occurrence_ids)
        record["occurrence_binding_is_event_truth"] = False
        record["consequence_candidate_is_causal_truth"] = False
        if occurrence_ids:
            occurrence_bound_consequence_count += 1
            consequence_occurrence_ids.update(occurrence_ids)

    actor_visible = 0
    opponent_visible = 0
    both_visible = 0
    for binding in trace_payload.get("occurrence_trace_binding_records") or []:
        if not isinstance(binding, dict):
            continue
        occurrence_id = str(binding.get("action_occurrence_candidate_id") or "")
        if occurrence_id not in consequence_occurrence_ids:
            continue
        actor_count = int(binding.get("actor_trace_candidate_count") or 0)
        opponent_count = int(binding.get("opponent_trace_candidate_count") or 0)
        if actor_count:
            actor_visible += 1
        if opponent_count:
            opponent_visible += 1
        if actor_count and opponent_count:
            both_visible += 1

    payload["occurrence_bound_consequence_candidate_count"] = occurrence_bound_consequence_count
    payload["occurrence_with_any_consequence_visible_count"] = len(consequence_occurrence_ids)
    payload["occurrence_with_actor_consequence_visible_count"] = actor_visible
    payload["occurrence_with_opponent_consequence_visible_count"] = opponent_visible
    payload["occurrence_with_both_participant_consequences_visible_count"] = both_visible
    payload["occurrence_binding_is_event_truth"] = False
    payload["occurrence_consequence_binding_is_causal_truth"] = False
    payload["current_trace_status"] = trace_payload.get("status")
    payload["current_relation_status"] = trace_payload.get("current_relation_status")
    payload["current_taxonomy_status"] = trace_payload.get("current_taxonomy_status")
    payload["current_semantic_status"] = trace_payload.get("current_semantic_status")
    payload["current_occurrence_status"] = trace_payload.get("current_occurrence_status")
    payload["current_occurrence_candidate_count"] = trace_payload.get("current_occurrence_candidate_count", 0)
    payload["current_content_source_role_bridge_status"] = trace_payload.get(
        "current_content_source_role_bridge_status"
    )
    payload["current_provider_semantics_binding_status"] = trace_payload.get(
        "current_provider_semantics_binding_status"
    )
    payload["active_match_evidence_pass"] = False
    paths = consequence.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current occurrence-aware Trackable Action trace to visible consequence candidates"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": payload.get("status"),
        "current_trace_status": payload.get("current_trace_status"),
        "current_occurrence_status": payload.get("current_occurrence_status"),
        "current_occurrence_candidate_count": payload.get("current_occurrence_candidate_count", 0),
        "source_trackable_action_trace_candidate_count": payload.get("source_trackable_action_trace_candidate_count"),
        "trackable_action_consequence_candidate_count": payload.get("trackable_action_consequence_candidate_count"),
        "occurrence_bound_consequence_candidate_count": payload.get("occurrence_bound_consequence_candidate_count", 0),
        "occurrence_with_any_consequence_visible_count": payload.get("occurrence_with_any_consequence_visible_count", 0),
        "occurrence_with_actor_consequence_visible_count": payload.get("occurrence_with_actor_consequence_visible_count", 0),
        "occurrence_with_opponent_consequence_visible_count": payload.get("occurrence_with_opponent_consequence_visible_count", 0),
        "occurrence_with_both_participant_consequences_visible_count": payload.get("occurrence_with_both_participant_consequences_visible_count", 0),
        "classified_consequence_candidate_count": payload.get("classified_consequence_candidate_count"),
        "review_required_consequence_candidate_count": payload.get("review_required_consequence_candidate_count"),
        "primary_consequence_candidate_counts": payload.get("primary_consequence_candidate_counts") or {},
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
