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
from hpfa.modules.core.process_metric_profile_lite.src.process_metric_profile import (
    ANALYST_TXT as METRIC_ANALYST_TXT,
    OUTPUT_JSON as METRIC_JSON,
    OUTPUT_TXT as METRIC_TXT,
    build_process_metric_profile,
    write_outputs as write_process_metric_outputs,
)
from hpfa.modules.core.process_robustness_lens_lite.src.process_robustness_lens import (
    ANALYST_TXT as ROBUSTNESS_ANALYST_TXT,
    OUTPUT_JSON as ROBUSTNESS_JSON,
    OUTPUT_TXT as ROBUSTNESS_TXT,
    build_process_robustness_lens,
    write_outputs as write_process_robustness_outputs,
)
from hpfa.modules.core.professional_finding_candidate_lite.src.professional_finding_candidate import (
    ANALYST_TXT as FINDING_ANALYST_TXT,
    OUTPUT_JSON as FINDING_JSON,
    OUTPUT_TXT as FINDING_TXT,
    build_professional_finding_candidates,
    write_outputs as write_professional_finding_outputs,
)
from hpfa.modules.core.reciprocal_process_chain_lite.src import reciprocal_process_chain as reciprocal
from hpfa.modules.core.reciprocal_process_chain_lite.src.outcome_contrast import attach_outcome_contrast
from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_profile import build_process_variant_profiles
from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_profile_outputs import (
    clear_outputs as clear_process_variant_profile_outputs,
    write_outputs as write_process_variant_profile_outputs,
)
from hpfa.modules.core.team_episode_activity_lens_lite.src.team_episode_activity_lens import (
    ANALYST_TXT as ACTIVITY_ANALYST_TXT,
    OUTPUT_JSON as ACTIVITY_JSON,
    OUTPUT_TXT as ACTIVITY_TXT,
    build_team_episode_activity_lens,
    write_outputs as write_team_episode_activity_outputs,
)
from hpfa.modules.core.visible_geometry_lens_lite.src.visible_geometry_lens import (
    ANALYST_TXT as GEOMETRY_ANALYST_TXT,
    OUTPUT_JSON as GEOMETRY_JSON,
    OUTPUT_TXT as GEOMETRY_TXT,
    build_visible_geometry_lens,
    write_outputs as write_visible_geometry_outputs,
)

TEMPORAL_JSON = "temporal_episode_signature_lite_v1.json"
TRACE_JSON = "trackable_action_trace_candidates_lite_v1.json"
IDENTITY_JSON = "match_local_identity_candidates_lite_v1.json"
CONTEXT_JSON = "minimum_viable_context_lite_v1.json"
SEMANTIC_JSON = "context_action_semantics_rebind_lite_v1.json"
EPISODE_JSON = "analyst_episode_locator_lite_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _clear_owned_outputs(output: Path, names: tuple[str, ...]) -> list[str]:
    cleared: list[str] = []
    for name in names:
        path = output / name
        if path.is_file():
            path.unlink()
            cleared.append(name)
    return cleared


def _attach_variant_projection(parent: dict, child: dict) -> dict:
    parent_module_id = parent.get("module_id")
    for key, value in child.items():
        if key != "module_id":
            parent[key] = value
    parent["process_variant_profile_module_id"] = child.get("module_id")
    parent["module_id"] = parent_module_id
    return parent


def _attach_reconciliation_projection(parent: dict, child: dict) -> dict:
    parent["match_reconciliation_module_id"] = child.get("module_id")
    parent["match_reconciliation_status"] = child.get("status")
    parent["reciprocal_consistency_edge_count"] = child.get("reciprocal_consistency_edge_count", 0)
    parent["player_process_membership_row_count"] = child.get("player_process_membership_row_count", 0)
    parent["player_team_episode_reconciliation_state"] = child.get("player_team_episode_reconciliation_state")
    parent["player_team_episode_union_consistent_team_count"] = child.get("player_team_episode_union_consistent_team_count", 0)
    parent["match_reconciliation_is_player_quality_truth"] = False
    parent["match_reconciliation_is_tactical_truth"] = False
    return parent


def _attach_activity_projection(parent: dict, child: dict) -> dict:
    parent["team_episode_activity_module_id"] = child.get("module_id")
    parent["team_episode_activity_status"] = child.get("status")
    parent["team_episode_activity_row_count"] = child.get("team_episode_activity_row_count", 0)
    parent["known_team_eligible_action_candidate_count"] = child.get("known_team_eligible_action_candidate_count", 0)
    parent["unknown_team_eligible_action_candidate_count"] = child.get("unknown_team_eligible_action_candidate_count", 0)
    parent["known_team_attribution_coverage_candidate"] = child.get("known_team_attribution_coverage_candidate")
    parent["team_episode_activity_is_phase_truth"] = False
    return parent


def _attach_geometry_projection(parent: dict, child: dict) -> dict:
    parent["visible_geometry_module_id"] = child.get("module_id")
    parent["visible_geometry_status"] = child.get("status")
    parent["team_period_geometry_row_count"] = child.get("team_period_geometry_row_count", 0)
    parent["player_period_geometry_row_count"] = child.get("player_period_geometry_row_count", 0)
    parent["visible_geometry_direction_normalized"] = False
    parent["visible_geometry_is_team_shape_truth"] = False
    return parent


def _attach_robustness_projection(parent: dict, child: dict) -> dict:
    parent["process_robustness_module_id"] = child.get("module_id")
    parent["process_robustness_status"] = child.get("status")
    parent["process_robustness_row_count"] = child.get("process_robustness_row_count", 0)
    parent["repeated_process_robustness_row_count"] = child.get("repeated_process_robustness_row_count", 0)
    parent["segment_only_risk_profile_count"] = child.get("segment_only_risk_profile_count", 0)
    parent["leave_one_episode_scope_out_survives_profile_count"] = child.get("leave_one_episode_scope_out_survives_profile_count", 0)
    parent["leave_top_anchor_actor_out_survives_profile_count"] = child.get("leave_top_anchor_actor_out_survives_profile_count", 0)
    parent["process_robustness_is_stable_pattern_truth"] = False
    return parent


def _attach_metric_projection(parent: dict, child: dict) -> dict:
    parent["process_metric_profile_module_id"] = child.get("module_id")
    parent["process_metric_profile_status"] = child.get("status")
    parent["metric_definition_count"] = child.get("metric_definition_count", 0)
    parent["process_metric_row_count"] = child.get("process_metric_row_count", 0)
    parent["team_visible_activity_metric_row_count"] = child.get("team_visible_activity_metric_row_count", 0)
    parent["composite_metrics_are_calibrated"] = False
    parent["statistical_significance_tested"] = False
    return parent


def _attach_finding_projection(parent: dict, child: dict) -> dict:
    parent["professional_finding_candidate_module_id"] = child.get("module_id")
    parent["professional_finding_candidate_status"] = child.get("status")
    parent["professional_finding_candidate_count"] = child.get("professional_finding_candidate_count", 0)
    parent["qualified_multi_episode_candidate_count"] = child.get("qualified_multi_episode_candidate_count", 0)
    parent["fragile_local_repeat_candidate_count"] = child.get("fragile_local_repeat_candidate_count", 0)
    parent["blocked_incomplete_episode_binding_candidate_count"] = child.get("blocked_incomplete_episode_binding_candidate_count", 0)
    parent["professional_finding_claim_output_allowed_count"] = child.get("claim_output_allowed_count", 0)
    parent["professional_finding_emitted_count"] = child.get("professional_finding_emitted_count", 0)
    return parent


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
        "outcome_contrast_candidates": [],
        "outcome_contrast_candidate_count": 0,
        "defeasible_process_finding_inputs": [],
        "defeasible_process_finding_input_count": 0,
        "reciprocal_c4_packet_candidates": [],
        "reciprocal_c4_packet_candidate_count": 0,
        "process_variant_profiles": [],
        "process_variant_profile_count": 0,
        "repeated_process_variant_profile_count": 0,
        "multi_episode_process_variant_profile_count": 0,
        "single_episode_repeat_risk_profile_count": 0,
        "outcome_variation_profile_count": 0,
        "incomplete_episode_binding_profile_count": 0,
        "process_variant_profile_status": "FAIL_CLOSED",
        "match_reconciliation_status": "FAIL_CLOSED",
        "team_episode_activity_status": "FAIL_CLOSED",
        "visible_geometry_status": "FAIL_CLOSED",
        "process_robustness_status": "FAIL_CLOSED",
        "process_metric_profile_status": "FAIL_CLOSED",
        "professional_finding_candidate_status": "FAIL_CLOSED",
        "player_process_membership_row_count": 0,
        "professional_finding_claim_output_allowed_count": 0,
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
    owned_groups = {
        "match_reconciliation": (RECONCILIATION_JSON, RECONCILIATION_TXT, RECONCILIATION_ANALYST_TXT),
        "team_episode_activity": (ACTIVITY_JSON, ACTIVITY_TXT, ACTIVITY_ANALYST_TXT),
        "visible_geometry": (GEOMETRY_JSON, GEOMETRY_TXT, GEOMETRY_ANALYST_TXT),
        "process_robustness": (ROBUSTNESS_JSON, ROBUSTNESS_TXT, ROBUSTNESS_ANALYST_TXT),
        "process_metric_profile": (METRIC_JSON, METRIC_TXT, METRIC_ANALYST_TXT),
        "professional_finding_candidate": (FINDING_JSON, FINDING_TXT, FINDING_ANALYST_TXT),
    }
    cleared = {label: _clear_owned_outputs(output, names) for label, names in owned_groups.items()}

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

    trace_payload = _load(output / TRACE_JSON)
    identity_payload = _load(output / IDENTITY_JSON)
    context_payload = _load(output / CONTEXT_JSON)
    semantic_payload = _load(output / SEMANTIC_JSON)
    analyst_episode_payload = _load(output / EPISODE_JSON)

    reconciliation_payload = build_match_reconciliation_ledger(payload, sequence_payload, trace_payload, identity_payload)
    reconciliation_paths = write_match_reconciliation_outputs(reconciliation_payload, output)
    payload = _attach_reconciliation_projection(payload, reconciliation_payload)

    activity_payload = build_team_episode_activity_lens(
        context_payload,
        semantic_payload,
        analyst_episode_payload,
        identity_payload,
    )
    activity_paths = write_team_episode_activity_outputs(activity_payload, output)
    payload = _attach_activity_projection(payload, activity_payload)

    geometry_payload = build_visible_geometry_lens(trace_payload, identity_payload)
    geometry_paths = write_visible_geometry_outputs(geometry_payload, output)
    payload = _attach_geometry_projection(payload, geometry_payload)

    robustness_payload = build_process_robustness_lens(payload, reconciliation_payload)
    robustness_paths = write_process_robustness_outputs(robustness_payload, output)
    payload = _attach_robustness_projection(payload, robustness_payload)

    metric_payload = build_process_metric_profile(robustness_payload, activity_payload, payload)
    metric_paths = write_process_metric_outputs(metric_payload, output)
    payload = _attach_metric_projection(payload, metric_payload)

    finding_payload = build_professional_finding_candidates(
        payload,
        robustness_payload,
        metric_payload,
        reconciliation_payload,
    )
    finding_paths = write_professional_finding_outputs(finding_payload, output)
    payload = _attach_finding_projection(payload, finding_payload)

    payload["cleared_stale_dependent_outputs"] = cleared
    for label, dependent in (
        ("match_reconciliation", reconciliation_payload),
        ("team_episode_activity", activity_payload),
        ("visible_geometry", geometry_payload),
        ("process_robustness", robustness_payload),
        ("process_metric_profile", metric_payload),
        ("professional_finding_candidate", finding_payload),
    ):
        if dependent.get("status") == "FAIL_CLOSED":
            payload.setdefault("review_hits", []).append(f"{label}_fail_closed_dependent_surface")

    payload["current_sequence_status"] = sequence_payload.get("status")
    payload["current_episode_lane_status"] = episode_lane.get("status")
    payload["current_temporal_generated"] = current_temporal_generated
    payload["active_match_evidence_pass"] = False

    parent_paths = reciprocal.write_outputs(payload, output)
    payload["outputs"] = {
        **{key: str(path) for key, path in parent_paths.items()},
        **{f"process_variant_{key}": str(path) for key, path in variant_paths.items()},
        **{f"match_reconciliation_{key}": str(path) for key, path in reconciliation_paths.items()},
        **{f"team_episode_activity_{key}": str(path) for key, path in activity_paths.items()},
        **{f"visible_geometry_{key}": str(path) for key, path in geometry_paths.items()},
        **{f"process_robustness_{key}": str(path) for key, path in robustness_paths.items()},
        **{f"process_metric_{key}": str(path) for key, path in metric_paths.items()},
        **{f"professional_finding_{key}": str(path) for key, path in finding_paths.items()},
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
        "reciprocal_process_chain_candidate_count": payload.get("reciprocal_process_chain_candidate_count"),
        "process_variant_profile_count": payload.get("process_variant_profile_count"),
        "match_reconciliation_status": payload.get("match_reconciliation_status"),
        "player_process_membership_row_count": payload.get("player_process_membership_row_count"),
        "player_team_episode_reconciliation_state": payload.get("player_team_episode_reconciliation_state"),
        "team_episode_activity_status": payload.get("team_episode_activity_status"),
        "team_episode_activity_row_count": payload.get("team_episode_activity_row_count"),
        "visible_geometry_status": payload.get("visible_geometry_status"),
        "team_period_geometry_row_count": payload.get("team_period_geometry_row_count"),
        "player_period_geometry_row_count": payload.get("player_period_geometry_row_count"),
        "process_robustness_status": payload.get("process_robustness_status"),
        "repeated_process_robustness_row_count": payload.get("repeated_process_robustness_row_count"),
        "segment_only_risk_profile_count": payload.get("segment_only_risk_profile_count"),
        "process_metric_profile_status": payload.get("process_metric_profile_status"),
        "metric_definition_count": payload.get("metric_definition_count"),
        "professional_finding_candidate_status": payload.get("professional_finding_candidate_status"),
        "professional_finding_candidate_count": payload.get("professional_finding_candidate_count"),
        "qualified_multi_episode_candidate_count": payload.get("qualified_multi_episode_candidate_count"),
        "professional_finding_claim_output_allowed_count": payload.get("professional_finding_claim_output_allowed_count"),
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
