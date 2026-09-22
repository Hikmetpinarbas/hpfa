from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median

import trackable_action_trace_candidates_current_v1 as current_trace
from hpfa.modules.core.trackable_action_consequence_candidates_lite.src import (
    trackable_action_consequence_candidates as consequence,
)
from hpfa.modules.core.trackable_action_consequence_candidates_lite.src.construct_temporal_consequence_contract import (
    apply_construct_temporal_contract,
)


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _record_has_visible_consequence(record: dict) -> bool:
    if record.get("visible_follow_up_trace_ids"):
        return True
    if record.get("terminal_outcome_support_visible") is True:
        return True
    if record.get("derived_consequence_support_visible") is True:
        return True
    return False


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _family_set(trace: dict) -> set[str]:
    return {
        _clean(value)
        for value in trace.get("action_family_candidates") or []
        if _clean(value)
    }


def _team_relation(anchor_team: str, traces: list[dict]) -> str:
    teams = {_clean(trace.get("team_identity_candidate_id")) for trace in traces}
    if not traces or not anchor_team or "" in teams:
        return "UNKNOWN"
    has_same = anchor_team in teams
    has_opponent = any(team != anchor_team for team in teams)
    if has_same and has_opponent:
        return "MIXED"
    if has_same:
        return "SAME_TEAM"
    if has_opponent:
        return "OPPONENT"
    return "UNKNOWN"


def _families_by_team_relation(anchor_team: str, traces: list[dict]) -> dict[str, list[str]]:
    buckets: dict[str, set[str]] = {
        "SAME_TEAM": set(),
        "OPPONENT": set(),
        "UNKNOWN": set(),
    }
    for trace in traces:
        team = _clean(trace.get("team_identity_candidate_id"))
        if not anchor_team or not team:
            relation = "UNKNOWN"
        elif team == anchor_team:
            relation = "SAME_TEAM"
        else:
            relation = "OPPONENT"
        buckets[relation].update(_family_set(trace))
    return {key: sorted(values) for key, values in buckets.items()}


def _bind_first_eligible_vs_horizon_semantics(payload: dict, trace_payload: dict) -> dict:
    """Separate earliest admitted action consequence from later horizon family presence.

    The existing legacy classifier may select a salient family (for example SHOT) found
    anywhere in the admitted follow-up horizon. For football analysis that is a different
    question from "what was the first admitted continuation?". This binding makes the
    distinction explicit without inventing a target-consequence query or production time
    threshold. Same-time first layers stay unordered.
    """
    if payload.get("status") == "FAIL_CLOSED":
        return payload

    trace_by_id = {
        _clean(row.get("trackable_action_trace_candidate_id")): row
        for row in trace_payload.get("trackable_action_trace_candidates") or []
        if isinstance(row, dict) and _clean(row.get("trackable_action_trace_candidate_id"))
    }

    reclassified = 0
    first_eligible_visible = 0
    horizon_family_presence_visible = 0
    semantic_unresolved = 0
    records = payload.get("trackable_action_consequence_candidates") or []
    for record in records:
        if not isinstance(record, dict):
            continue

        anchor_id = _clean(record.get("anchor_trackable_action_trace_candidate_id"))
        anchor = trace_by_id.get(anchor_id)
        admitted_ids = [
            _clean(value)
            for value in record.get("admitted_after_follow_up_trace_ids") or []
            if _clean(value)
        ]
        admitted_rows = [trace_by_id[value] for value in admitted_ids if value in trace_by_id]
        missing_admitted_ids = sorted(set(admitted_ids) - set(trace_by_id))

        legacy_primary = _clean(record.get("primary_consequence_candidate")) or None
        record["legacy_horizon_mixed_primary_consequence_candidate"] = legacy_primary
        record["target_consequence_query_state"] = "NOT_SPECIFIED_BY_CONSTRUCT"
        record["target_consequence_within_horizon"] = None
        record["target_consequence_query_required_for_target_claim"] = True
        record["target_consequence_query_can_be_inferred_from_primary"] = False
        record["horizon_family_presence_is_target_consequence_truth"] = False
        record["first_eligible_action_is_target_consequence_truth"] = False
        record["diagnostic_horizon_family_presence_can_authorize_claim"] = False
        record["same_timestamp_first_layer_internal_ordering_allowed"] = False
        record["time_to_first_admitted_visible_state_change_seconds_candidate"] = None
        record["time_to_first_admitted_visible_state_change_observation_state"] = "NOT_EVALUATED"
        record["time_to_first_admitted_visible_state_change_basis"] = "AFTER_CONFIRMED_FIRST_ELIGIBLE_VISIBLE_LAYER"
        record["time_to_first_admitted_visible_state_change_is_physical_advantage_window_truth"] = False
        record["time_to_first_admitted_visible_state_change_is_causal_timing_truth"] = False
        record["time_to_first_admitted_visible_state_change_is_first_passage_model_output"] = False

        if anchor is None or missing_admitted_ids:
            semantic_unresolved += 1
            record["first_eligible_consequence_binding_state"] = "UNRESOLVED_TRACE_LINEAGE"
            record["first_eligible_follow_up_trace_ids"] = []
            record["first_eligible_action_family_candidates"] = []
            record["first_eligible_team_relation"] = "UNKNOWN"
            record["admitted_horizon_action_family_candidates_by_team_relation"] = {
                "SAME_TEAM": [],
                "OPPONENT": [],
                "UNKNOWN": [],
            }
            record["first_eligible_consequence_signal_candidates"] = []
            record["primary_consequence_semantics"] = "LEGACY_PRESERVED_LINEAGE_UNRESOLVED"
            record["time_to_first_admitted_visible_state_change_observation_state"] = "UNRESOLVED_TRACE_LINEAGE"
            continue

        anchor_team = _clean(anchor.get("team_identity_candidate_id"))
        horizon_buckets = _families_by_team_relation(anchor_team, admitted_rows)
        record["admitted_horizon_action_family_candidates_by_team_relation"] = horizon_buckets
        if any(horizon_buckets.values()):
            horizon_family_presence_visible += 1

        if not admitted_rows:
            record["first_eligible_consequence_binding_state"] = "NO_ADMITTED_AFTER_FOLLOWUP"
            record["first_eligible_follow_up_trace_ids"] = []
            record["first_eligible_action_family_candidates"] = []
            record["first_eligible_team_relation"] = "NONE"
            record["first_eligible_consequence_signal_candidates"] = []
            record["primary_consequence_semantics"] = (
                "NON_ACTION_OR_REVIEW_SEMANTICS_PRESERVED_WITHOUT_ADMITTED_FIRST_FOLLOWUP"
            )
            record["time_to_first_admitted_visible_state_change_observation_state"] = "NO_ADMITTED_AFTER_FOLLOWUP"
            continue

        starts = [_number(row.get("start_candidate")) for row in admitted_rows]
        if any(value is None for value in starts):
            semantic_unresolved += 1
            record["first_eligible_consequence_binding_state"] = "UNRESOLVED_FOLLOWUP_TIME"
            record["first_eligible_follow_up_trace_ids"] = []
            record["first_eligible_action_family_candidates"] = []
            record["first_eligible_team_relation"] = "UNKNOWN"
            record["first_eligible_consequence_signal_candidates"] = []
            record["primary_consequence_semantics"] = "LEGACY_PRESERVED_TIME_UNRESOLVED"
            record["time_to_first_admitted_visible_state_change_observation_state"] = "UNRESOLVED_FOLLOWUP_TIME"
            continue

        first_start = min(value for value in starts if value is not None)
        anchor_start = _number(anchor.get("start_candidate"))
        if anchor_start is None:
            semantic_unresolved += 1
            record["first_eligible_consequence_binding_state"] = "UNRESOLVED_ANCHOR_TIME"
            record["first_eligible_follow_up_trace_ids"] = []
            record["first_eligible_action_family_candidates"] = []
            record["first_eligible_team_relation"] = "UNKNOWN"
            record["first_eligible_consequence_signal_candidates"] = []
            record["primary_consequence_semantics"] = "LEGACY_PRESERVED_ANCHOR_TIME_UNRESOLVED"
            record["time_to_first_admitted_visible_state_change_observation_state"] = "UNRESOLVED_ANCHOR_TIME"
            continue
        elapsed = round(first_start - anchor_start, 6)
        if elapsed <= 0:
            semantic_unresolved += 1
            record["first_eligible_consequence_binding_state"] = "UNRESOLVED_NONPOSITIVE_ADMITTED_TIME_DELTA"
            record["first_eligible_follow_up_trace_ids"] = []
            record["first_eligible_action_family_candidates"] = []
            record["first_eligible_team_relation"] = "UNKNOWN"
            record["first_eligible_consequence_signal_candidates"] = []
            record["primary_consequence_semantics"] = "LEGACY_PRESERVED_TEMPORAL_CONFLICT"
            record["time_to_first_admitted_visible_state_change_observation_state"] = "UNRESOLVED_NONPOSITIVE_ADMITTED_TIME_DELTA"
            continue
        record["time_to_first_admitted_visible_state_change_seconds_candidate"] = elapsed
        record["time_to_first_admitted_visible_state_change_observation_state"] = "OBSERVED_ADMITTED_AFTER"
        first_rows = [
            row for row in admitted_rows if _number(row.get("start_candidate")) == first_start
        ]
        first_ids = sorted(
            _clean(row.get("trackable_action_trace_candidate_id"))
            for row in first_rows
            if _clean(row.get("trackable_action_trace_candidate_id"))
        )
        first_families = sorted(set().union(*(_family_set(row) for row in first_rows))) if first_rows else []
        first_relation = _team_relation(anchor_team, first_rows)
        first_state = (
            "SAME_TIME_UNORDERED_FIRST_LAYER"
            if len(first_rows) > 1
            else "SINGLE_FIRST_ELIGIBLE_FOLLOWUP"
        )
        first_eligible_visible += 1

        first_primary, first_signals = consequence._classify_consequence(
            anchor,
            first_rows,
            first_rows,
            record.get("terminal_outcome_support_visible") is True,
            record.get("derived_consequence_support_visible") is True,
        )
        if first_primary != legacy_primary:
            reclassified += 1

        record["first_eligible_consequence_binding_state"] = first_state
        record["first_eligible_follow_up_trace_ids"] = first_ids
        record["first_eligible_action_family_candidates"] = first_families
        record["first_eligible_team_relation"] = first_relation
        record["first_eligible_consequence_signal_candidates"] = first_signals
        record["primary_consequence_candidate"] = first_primary
        record["primary_consequence_semantics"] = "FIRST_ELIGIBLE_ADMITTED_ACTION_LAYER"
        record["record_status"] = (
            "REVIEW_REQUIRED"
            if first_primary in consequence.REVIEW_CLASSES
            else "PASS_CANDIDATE_CLASSIFICATION"
        )

    primary_counts = Counter(
        record.get("primary_consequence_candidate")
        for record in records
        if isinstance(record, dict) and record.get("primary_consequence_candidate")
    )
    review_required_count = sum(
        isinstance(record, dict) and record.get("record_status") == "REVIEW_REQUIRED"
        for record in records
    )
    payload["primary_consequence_candidate_counts"] = dict(sorted(primary_counts.items()))
    payload["review_required_consequence_candidate_count"] = review_required_count
    payload["classified_consequence_candidate_count"] = len(records) - review_required_count
    payload["first_eligible_vs_target_consequence_separated"] = True
    payload["first_eligible_action_followup_record_count"] = first_eligible_visible
    payload["first_eligible_primary_reclassification_count"] = reclassified
    payload["admitted_horizon_family_presence_record_count"] = horizon_family_presence_visible
    payload["first_eligible_semantics_unresolved_record_count"] = semantic_unresolved
    payload["target_consequence_query_required_for_target_claim"] = True
    payload["target_consequence_query_state"] = "NOT_GLOBALLY_SPECIFIED"
    payload["target_consequence_result_emitted"] = False
    payload["horizon_family_presence_is_target_consequence_truth"] = False
    payload["diagnostic_horizon_family_presence_can_authorize_claim"] = False
    payload["same_timestamp_first_layer_internal_ordering_allowed"] = False
    timing_values = sorted(
        float(record["time_to_first_admitted_visible_state_change_seconds_candidate"])
        for record in records
        if isinstance(record, dict)
        and record.get("time_to_first_admitted_visible_state_change_observation_state") == "OBSERVED_ADMITTED_AFTER"
        and isinstance(record.get("time_to_first_admitted_visible_state_change_seconds_candidate"), (int, float))
    )
    timing_states = Counter(
        str(record.get("time_to_first_admitted_visible_state_change_observation_state") or "UNKNOWN")
        for record in records
        if isinstance(record, dict)
    )
    payload["time_to_first_admitted_visible_state_change_profile"] = {
        "eligible_observed_n": len(timing_values),
        "observation_state_counts": dict(sorted(timing_states.items())),
        "median_seconds_candidate": median(timing_values) if timing_values else None,
        "min_seconds_candidate": min(timing_values) if timing_values else None,
        "max_seconds_candidate": max(timing_values) if timing_values else None,
        "distribution_values_seconds_candidate": timing_values,
        "distribution_is_descriptive_not_first_passage_model": True,
        "right_censoring_model_applied": False,
        "no_admitted_after_is_failure": False,
        "global_5_8_12_window_is_production_threshold": False,
        "graphability_state": "GRAPH_READY_WITH_REVIEW" if timing_values else "NOT_GRAPH_READY_NO_ADMITTED_TIMING",
        "recommended_graphs": [
            "TIME_TO_FIRST_ADMITTED_VISIBLE_STATE_CHANGE_ECDF",
            "TIME_TO_FIRST_ADMITTED_VISIBLE_STATE_CHANGE_DISTRIBUTION",
        ],
        "creates_new_evidence": False,
        "can_authorize_emit": False,
    }

    reviews = set(payload.get("review_hits") or [])
    reviews.discard("review_required_visible_consequence_candidates_present")
    if review_required_count:
        reviews.add("review_required_visible_consequence_candidates_present")
    if semantic_unresolved:
        reviews.add("first_eligible_consequence_semantics_unresolved")
    payload["review_hits"] = sorted(reviews)
    hard_blocks = payload.get("hard_block_hits") or []
    payload["status"] = (
        "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    )
    payload["module_status"] = payload["status"]
    return payload


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
            "global_window_is_production_temporal_contract": False,
            "construct_specific_temporal_contract_required": True,
            "construct_specific_temporal_contract_state": "UNAVAILABLE_FAIL_CLOSED",
            "production_temporal_window_thresholds_admitted": False,
            "single_match_observed_latency_can_set_production_threshold": False,
            "first_eligible_vs_target_consequence_separated": False,
            "target_consequence_query_required_for_target_claim": True,
            "target_consequence_query_state": "UNAVAILABLE_FAIL_CLOSED",
            "target_consequence_result_emitted": False,
            "horizon_family_presence_is_target_consequence_truth": False,
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
    payload = apply_construct_temporal_contract(payload)
    payload = _bind_first_eligible_vs_horizon_semantics(payload, trace_payload)

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
        visible = _record_has_visible_consequence(record)
        record["supporting_action_occurrence_candidate_ids"] = occurrence_ids
        record["occurrence_bound_consequence_candidate"] = bool(occurrence_ids)
        record["occurrence_visible_consequence_support"] = visible
        record["occurrence_binding_is_event_truth"] = False
        record["consequence_candidate_is_causal_truth"] = False
        if occurrence_ids:
            occurrence_bound_consequence_count += 1
        if occurrence_ids and visible:
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
        "first_eligible_vs_target_consequence_separated": payload.get(
            "first_eligible_vs_target_consequence_separated", False
        ),
        "first_eligible_action_followup_record_count": payload.get(
            "first_eligible_action_followup_record_count", 0
        ),
        "first_eligible_primary_reclassification_count": payload.get(
            "first_eligible_primary_reclassification_count", 0
        ),
        "target_consequence_query_state": payload.get("target_consequence_query_state"),
        "construct_specific_temporal_contract_state": payload.get("construct_specific_temporal_contract_state"),
        "construct_temporal_contract_key_count": payload.get("construct_temporal_contract_key_count", 0),
        "production_temporal_window_thresholds_admitted": payload.get("production_temporal_window_thresholds_admitted", False),
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
