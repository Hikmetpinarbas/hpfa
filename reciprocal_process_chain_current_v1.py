from __future__ import annotations

import argparse
import json
from pathlib import Path

import visible_action_sequence_candidates_current_v1 as current_sequence
from hpfa.modules.core.active_match_spine_runner.src.episode_lane_runner import run_current_episode_lane
from hpfa.modules.core.match_reconciliation_ledger_lite.src.match_reconciliation_ledger import (
    ANALYST_TXT as RECONCILIATION_ANALYST_TXT,
    OUTPUT_JSON as RECONCILIATION_JSON,
    OUTPUT_TXT as RECONCILIATION_TXT,
    build_match_reconciliation_ledger,
    write_outputs as write_match_reconciliation_outputs,
)
from hpfa.modules.core.reciprocal_process_chain_lite.src import reciprocal_process_chain as reciprocal
from hpfa.modules.core.reciprocal_process_chain_lite.src.outcome_contrast import attach_outcome_contrast
from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_profile import (
    build_process_variant_profiles,
)
from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_profile_outputs import (
    clear_outputs as clear_process_variant_profile_outputs,
    write_outputs as write_process_variant_profile_outputs,
)

TEMPORAL_JSON = "temporal_episode_signature_lite_v1.json"
TRACE_JSON = "trackable_action_trace_candidates_lite_v1.json"
IDENTITY_JSON = "match_local_identity_candidates_lite_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _clear_reconciliation_outputs(output: Path) -> list[str]:
    cleared: list[str] = []
    for name in (RECONCILIATION_JSON, RECONCILIATION_TXT, RECONCILIATION_ANALYST_TXT):
        path = output / name
        if path.is_file():
            path.unlink()
            cleared.append(name)
    return cleared


def _attach_variant_projection(parent_payload: dict, variant_payload: dict) -> dict:
    """Attach dependent variant fields without overwriting parent producer identity."""
    parent_module_id = parent_payload.get("module_id")
    for key, value in variant_payload.items():
        if key == "module_id":
            continue
        parent_payload[key] = value
    parent_payload["process_variant_profile_module_id"] = variant_payload.get("module_id")
    parent_payload["module_id"] = parent_module_id
    return parent_payload


def _attach_reconciliation_projection(parent_payload: dict, reconciliation: dict) -> dict:
    """Attach reconciliation accounting without replacing reciprocal producer truth."""
    parent_payload["match_reconciliation_module_id"] = reconciliation.get("module_id")
    parent_payload["match_reconciliation_status"] = reconciliation.get("status")
    parent_payload["reciprocal_consistency_edge_count"] = reconciliation.get(
        "reciprocal_consistency_edge_count", 0
    )
    parent_payload["player_process_membership_row_count"] = reconciliation.get(
        "player_process_membership_row_count", 0
    )
    parent_payload["player_team_episode_reconciliation_state"] = reconciliation.get(
        "player_team_episode_reconciliation_state"
    )
    parent_payload["player_team_episode_union_consistent_team_count"] = reconciliation.get(
        "player_team_episode_union_consistent_team_count", 0
    )
    parent_payload["match_reconciliation_claim_ceiling"] = reconciliation.get("claim_ceiling")
    parent_payload["match_reconciliation_is_player_quality_truth"] = False
    parent_payload["match_reconciliation_is_tactical_truth"] = False
    return parent_payload


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
        "outcome_contrast_candidates": [],
        "outcome_contrast_candidate_count": 0,
        "different_outcome_analogue_link_count": 0,
        "same_outcome_support_link_count": 0,
        "outcome_contrast_status": "FAIL_CLOSED",
        "outcome_contrast_is_independent_evidence": False,
        "defeasible_process_finding_inputs": [],
        "defeasible_process_finding_input_count": 0,
        "finding_input_status": "FAIL_CLOSED",
        "finding_input_is_final_finding": False,
        "finding_input_is_independent_evidence": False,
        "reciprocal_c4_packet_candidates": [],
        "reciprocal_c4_packet_candidate_count": 0,
        "reciprocal_c4_adapter_status": "FAIL_CLOSED",
        "reciprocal_c4_adapter_creates_new_engine": False,
        "reciprocal_c4_adapter_creates_independent_evidence": False,
        "reciprocal_c4_adapter_emits_final_finding": False,
        "process_variant_profiles": [],
        "process_variant_profile_count": 0,
        "repeated_process_variant_profile_count": 0,
        "multi_episode_process_variant_profile_count": 0,
        "single_episode_repeat_risk_profile_count": 0,
        "outcome_variation_profile_count": 0,
        "incomplete_episode_binding_profile_count": 0,
        "process_variant_profile_status": "FAIL_CLOSED",
        "process_variant_profile_is_recurrence_truth": False,
        "process_variant_profile_is_tactical_truth": False,
        "process_variant_profile_creates_independent_evidence": False,
        "match_reconciliation_status": "FAIL_CLOSED",
        "player_process_membership_row_count": 0,
        "player_team_episode_reconciliation_state": "NOT_EVALUATED_UPSTREAM_FAIL_CLOSED",
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

    clear_process_variant_profile_outputs(output)
    cleared_reconciliation_outputs = _clear_reconciliation_outputs(output)

    sequence_payload = current_sequence.runtime_write_outputs(input_dir, output)
    if sequence_payload.get("status") == "FAIL_CLOSED":
        payload = _fail_payload(sequence_payload, "current_sequence_fail_closed")
        reciprocal.write_outputs(payload, output)
        return payload

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
    payload = attach_outcome_contrast(payload)

    variant_payload = build_process_variant_profiles(payload)
    payload = _attach_variant_projection(payload, variant_payload)
    variant_paths = write_process_variant_profile_outputs(variant_payload, output)
    payload["process_variant_profile_outputs"] = {
        key: str(path) for key, path in variant_paths.items()
    }

    trace_payload = _load(output / TRACE_JSON)
    identity_payload = _load(output / IDENTITY_JSON)
    reconciliation_payload = build_match_reconciliation_ledger(
        payload,
        sequence_payload,
        trace_payload,
        identity_payload,
    )
    reconciliation_paths = write_match_reconciliation_outputs(reconciliation_payload, output)
    payload = _attach_reconciliation_projection(payload, reconciliation_payload)
    payload["match_reconciliation_outputs"] = {
        key: str(path) for key, path in reconciliation_paths.items()
    }
    payload["cleared_stale_match_reconciliation_outputs"] = cleared_reconciliation_outputs
    if reconciliation_payload.get("status") == "FAIL_CLOSED":
        payload.setdefault("review_hits", []).append("match_reconciliation_fail_closed_dependent_surface")

    payload["current_sequence_status"] = sequence_payload.get("status")
    payload["current_episode_lane_status"] = episode_lane.get("status")
    payload["current_temporal_generated"] = current_temporal_generated
    payload["active_match_evidence_pass"] = False
    paths = reciprocal.write_outputs(payload, output)
    payload["outputs"] = {
        **{key: str(path) for key, path in paths.items()},
        **{f"process_variant_{key}": str(path) for key, path in variant_paths.items()},
        **{f"match_reconciliation_{key}": str(path) for key, path in reconciliation_paths.items()},
    }
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
        "outcome_contrast_candidate_count": payload.get("outcome_contrast_candidate_count"),
        "different_outcome_analogue_link_count": payload.get("different_outcome_analogue_link_count"),
        "defeasible_process_finding_input_count": payload.get("defeasible_process_finding_input_count"),
        "finding_input_status": payload.get("finding_input_status"),
        "reciprocal_c4_packet_candidate_count": payload.get("reciprocal_c4_packet_candidate_count"),
        "reciprocal_c4_adapter_status": payload.get("reciprocal_c4_adapter_status"),
        "process_variant_profile_count": payload.get("process_variant_profile_count"),
        "repeated_process_variant_profile_count": payload.get("repeated_process_variant_profile_count"),
        "multi_episode_process_variant_profile_count": payload.get("multi_episode_process_variant_profile_count"),
        "single_episode_repeat_risk_profile_count": payload.get("single_episode_repeat_risk_profile_count"),
        "outcome_variation_profile_count": payload.get("outcome_variation_profile_count"),
        "match_reconciliation_status": payload.get("match_reconciliation_status"),
        "player_process_membership_row_count": payload.get("player_process_membership_row_count"),
        "player_team_episode_reconciliation_state": payload.get("player_team_episode_reconciliation_state"),
        "player_team_episode_union_consistent_team_count": payload.get("player_team_episode_union_consistent_team_count"),
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
