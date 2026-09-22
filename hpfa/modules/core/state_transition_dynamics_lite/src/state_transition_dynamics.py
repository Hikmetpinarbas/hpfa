from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

MODULE_ID = "state_transition_dynamics_lite_v1"
SPATIAL_MODULE_ID = "spatial_transition_candidate_lite_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "SEMANTIC_SPATIAL_CONSEQUENCE_ASSOCIATION_ONLY"

DIRECTIONAL_CONSEQUENCES = {
    "SHOT_FOLLOW_UP_CANDIDATE",
    "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE",
    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
    "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE",
    "RESTART_OR_RESET_CANDIDATE",
    "SAME_TEAM_CONTINUATION_CANDIDATE",
    "OPPONENT_HANDOVER_CANDIDATE",
}
ADVERSE_CONSEQUENCES = {
    "OPPONENT_HANDOVER_CANDIDATE",
    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
}
REVIEW_CONSEQUENCES = {
    "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE",
    "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE",
    "PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE",
    "BREAKDOWN_WITH_UNCERTAIN_VISIBLE_RESPONSE_CANDIDATE",
}
OUTPUTS = {
    "json": "state_transition_dynamics_lite_v1.json",
    "summary": "state_transition_dynamics_lite_v1.txt",
    "analyst": "state_transition_dynamics_analyst_audit_v1.txt",
}


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


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def _visible_state_change_function(
    spatial: dict[str, Any],
    consequence_class: str,
) -> str:
    """Describe visible state development without promoting tactical or causal truth."""
    progression = bool(spatial.get("provider_progression_candidates"))
    zones = set(spatial.get("provider_zone_candidates") or [])
    directions = {
        _clean(value).upper()
        for value in (spatial.get("provider_direction_candidates") or [])
        if _clean(value)
    }

    if consequence_class == "SHOT_FOLLOW_UP_CANDIDATE":
        return "VISIBLE_ADVANTAGE_EXPLOITATION_CANDIDATE"
    if progression and consequence_class in {
        "SAME_TEAM_CONTINUATION_CANDIDATE",
        "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE",
    }:
        return "VISIBLE_STATE_ADVANCEMENT_CONTINUATION_CANDIDATE"
    if "FINAL_THIRD" in zones and consequence_class == "SAME_TEAM_CONTINUATION_CANDIDATE":
        return "VISIBLE_ADVANCED_ACCESS_CONTINUATION_CANDIDATE"
    if consequence_class in ADVERSE_CONSEQUENCES:
        return "VISIBLE_ADVANTAGE_LOSS_OR_HANDOVER_CANDIDATE"
    if consequence_class == "RESTART_OR_RESET_CANDIDATE":
        return "VISIBLE_RESET_STATE_CANDIDATE"
    if consequence_class == "SAME_TEAM_CONTINUATION_CANDIDATE":
        if "BACKWARD" in directions or "LATERAL" in directions or "SIDEWAYS" in directions:
            return "BACKWARD_OR_LATERAL_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
        return "VISIBLE_SAME_TEAM_CONTINUATION_CANDIDATE"
    if consequence_class == "NO_VISIBLE_FOLLOW_UP_CANDIDATE":
        return "VISIBLE_STATE_CHANGE_UNRESOLVED_NO_FOLLOW_UP_CANDIDATE"
    return "VISIBLE_STATE_CHANGE_REVIEW_REQUIRED_CANDIDATE"


def _transition_class(spatial: dict[str, Any], consequence: dict[str, Any]) -> str:
    progression = bool(spatial.get("provider_progression_candidates"))
    zones = set(spatial.get("provider_zone_candidates") or [])
    consequence_class = _clean(consequence.get("primary_consequence_candidate"))
    if progression and consequence_class == "SHOT_FOLLOW_UP_CANDIDATE":
        return "PROGRESSIVE_TO_SHOT_FOLLOW_UP_CANDIDATE"
    if progression and consequence_class in {"SAME_TEAM_CONTINUATION_CANDIDATE", "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"}:
        return "PROGRESSIVE_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
    if progression and consequence_class in ADVERSE_CONSEQUENCES:
        return "PROGRESSIVE_TO_ADVERSE_HANDOVER_CANDIDATE"
    if "OPPONENT_HALF" in zones and consequence_class == "SAME_TEAM_CONTINUATION_CANDIDATE":
        return "OPPONENT_HALF_ACTION_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
    if "FINAL_THIRD" in zones and consequence_class == "SHOT_FOLLOW_UP_CANDIDATE":
        return "FINAL_THIRD_ACTION_TO_SHOT_FOLLOW_UP_CANDIDATE"
    if consequence_class in DIRECTIONAL_CONSEQUENCES:
        return "VISIBLE_DIRECTIONAL_CONSEQUENCE_TRANSITION_CANDIDATE"
    if consequence_class == "TERMINAL_OUTCOME_SUPPORT_CANDIDATE":
        return "TERMINAL_SUPPORT_ASSOCIATION_CANDIDATE"
    if consequence_class == "NO_VISIBLE_FOLLOW_UP_CANDIDATE":
        return "NO_VISIBLE_FOLLOW_UP_ASSOCIATION_CANDIDATE"
    return "REVIEW_REQUIRED_TRANSITION_CANDIDATE"


def build_state_transition_dynamics(
    spatial_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    if spatial_payload.get("module_id") != SPATIAL_MODULE_ID:
        blocks.append("spatial_input_module_id_mismatch")
    if consequence_payload.get("module_id") != CONSEQUENCE_MODULE_ID:
        blocks.append("consequence_input_module_id_mismatch")
    for prefix, payload in (("spatial", spatial_payload), ("consequence", consequence_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{prefix}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{prefix}_hard_blocks_present")

    spatial_binding = _clean(spatial_payload.get("match_surface_binding_id"))
    consequence_binding = _clean(consequence_payload.get("match_surface_binding_id"))
    if not spatial_binding or spatial_binding != consequence_binding:
        blocks.append("match_surface_binding_mismatch")

    spatial_rows = spatial_payload.get("spatial_transition_candidates") or []
    consequence_rows = consequence_payload.get("trackable_action_consequence_candidates") or []
    if not isinstance(spatial_rows, list):
        blocks.append("spatial_transition_candidates_invalid")
        spatial_rows = []
    if not isinstance(consequence_rows, list):
        blocks.append("consequence_candidates_invalid")
        consequence_rows = []
    if spatial_payload.get("spatial_transition_candidate_count") != len(spatial_rows):
        blocks.append("spatial_candidate_count_mismatch")
    if consequence_payload.get("trackable_action_consequence_candidate_count") != len(consequence_rows):
        blocks.append("consequence_candidate_count_mismatch")

    spatial_by_trace: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(spatial_rows):
        if not isinstance(row, dict):
            blocks.append(f"spatial_record_invalid:{index}")
            continue
        trace_id = _clean(row.get("trackable_action_trace_candidate_id"))
        if not trace_id or trace_id in spatial_by_trace:
            blocks.append(f"spatial_trace_id_invalid_or_duplicate:{index}")
            continue
        spatial_by_trace[trace_id] = row

    consequence_by_trace: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(consequence_rows):
        if not isinstance(row, dict):
            blocks.append(f"consequence_record_invalid:{index}")
            continue
        trace_id = _clean(row.get("anchor_trackable_action_trace_candidate_id"))
        if not trace_id or trace_id in consequence_by_trace:
            blocks.append(f"consequence_trace_id_invalid_or_duplicate:{index}")
            continue
        consequence_by_trace[trace_id] = row

    if set(spatial_by_trace) != set(consequence_by_trace):
        blocks.append("spatial_consequence_trace_coverage_mismatch")

    records: list[dict[str, Any]] = []
    if not blocks:
        for trace_id in sorted(spatial_by_trace):
            spatial = spatial_by_trace[trace_id]
            consequence = consequence_by_trace[trace_id]
            consequence_class = _clean(consequence.get("primary_consequence_candidate"))
            transition_class = _transition_class(spatial, consequence)
            state_change_function = _visible_state_change_function(spatial, consequence_class)
            temporal_admitted = bool(consequence.get("admitted_after_follow_up_trace_ids"))
            directional = consequence_class in DIRECTIONAL_CONSEQUENCES
            if directional and not temporal_admitted:
                blocks.append(f"directional_consequence_without_after_admission:{trace_id}")
                continue

            record_reviews: list[str] = []
            if consequence.get("record_status") == "REVIEW_REQUIRED" or consequence_class in REVIEW_CONSEQUENCES:
                record_reviews.append("consequence_review_required")
            if spatial.get("spatial_admission_state") == "REVIEW_REQUIRED":
                record_reviews.append("spatial_review_required")
            if transition_class == "REVIEW_REQUIRED_TRANSITION_CANDIDATE":
                record_reviews.append("transition_class_review_required")

            progression = list(spatial.get("provider_progression_candidates") or [])
            zones = list(spatial.get("provider_zone_candidates") or [])
            contexts = list(spatial.get("provider_context_candidates") or [])
            directions = list(spatial.get("provider_direction_candidates") or [])
            outcomes = list(spatial.get("provider_outcome_candidates") or [])
            support = []
            if progression:
                support.append("PROVIDER_PROGRESSION_SEMANTIC_VISIBLE")
            if zones:
                support.append("PROVIDER_ZONE_SEMANTIC_VISIBLE")
            if contexts:
                support.append("PROVIDER_CONTEXT_SEMANTIC_VISIBLE")
            if directions:
                support.append("PROVIDER_DIRECTION_SEMANTIC_VISIBLE")
            if consequence_class:
                support.append("VISIBLE_CONSEQUENCE_CANDIDATE_PRESENT")
            if temporal_admitted:
                support.append("AFTER_CONFIRMED_FOLLOW_UP_PRESENT")

            adverse = []
            if consequence_class in ADVERSE_CONSEQUENCES:
                adverse.append(consequence_class)

            records.append({
                "state_transition_dynamics_candidate_id": "std_" + _digest(spatial_binding, trace_id, transition_class)[:24],
                "trackable_action_trace_candidate_id": trace_id,
                "spatial_transition_candidate_id": spatial.get("spatial_transition_candidate_id"),
                "trackable_action_consequence_candidate_id": consequence.get("trackable_action_consequence_candidate_id"),
                "match_surface_binding_id": spatial_binding,
                "team_identity_candidate_id": spatial.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": spatial.get("actor_identity_candidate_id"),
                "action_family_candidates": spatial.get("action_family_candidates") or [],
                "provider_progression_candidates": progression,
                "provider_zone_candidates": zones,
                "provider_context_candidates": contexts,
                "provider_direction_candidates": directions,
                "provider_outcome_candidates": outcomes,
                "primary_consequence_candidate": consequence_class,
                "admitted_after_follow_up_trace_ids": consequence.get("admitted_after_follow_up_trace_ids") or [],
                "transition_class_candidate": transition_class,
                "visible_state_change_function_candidate": state_change_function,
                "visible_state_before_candidate": "SOURCE_ACTION_CONTEXT_ONLY_NOT_FULL_GAME_STATE",
                "visible_state_after_candidate": consequence_class or "UNRESOLVED_VISIBLE_CONSEQUENCE",
                "time_to_first_admitted_visible_state_change_seconds_candidate": consequence.get(
                    "time_to_first_admitted_visible_state_change_seconds_candidate"
                ),
                "time_to_first_admitted_visible_state_change_observation_state": consequence.get(
                    "time_to_first_admitted_visible_state_change_observation_state"
                ),
                "time_to_first_admitted_visible_state_change_basis": consequence.get(
                    "time_to_first_admitted_visible_state_change_basis"
                ),
                "state_change_function_is_player_causal_credit": False,
                "state_change_function_is_opponent_organization_truth": False,
                "state_change_function_is_physical_space_creation_truth": False,
                "state_change_function_is_value_model_output": False,
                "backward_or_lateral_action_is_automatically_negative": False,
                "support_candidates": support,
                "adverse_consequence_candidates": adverse,
                "record_status": "REVIEW_REQUIRED" if record_reviews else "PASS_CANDIDATE_CLASSIFICATION",
                "review_hits": sorted(set(record_reviews)),
                "provider_semantic_progression_is_measured_displacement_truth": False,
                "directional_consequence_requires_after_confirmed": True,
                "transition_is_possession_truth": False,
                "transition_is_sequence_truth": False,
                "transition_is_tactical_pattern_truth": False,
                "transition_is_causal_truth": False,
                "coach_intention_truth": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    blocks = sorted(set(blocks))
    if blocks:
        records = []
    if spatial_payload.get("status") == "REVIEW_REQUIRED":
        reviews.append("spatial_input_review_required")
    if consequence_payload.get("status") == "REVIEW_REQUIRED":
        reviews.append("consequence_input_review_required")
    if any(row.get("record_status") == "REVIEW_REQUIRED" for row in records):
        reviews.append("transition_records_review_required")
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    counts = Counter(row.get("transition_class_candidate") for row in records)
    timing_by_function: dict[str, list[float]] = defaultdict(list)
    timing_state_by_function: dict[str, Counter[str]] = defaultdict(Counter)
    eligible_by_function: Counter[str] = Counter()
    for row in records:
        function = _clean(row.get("visible_state_change_function_candidate")) or "UNRESOLVED"
        eligible_by_function[function] += 1
        timing_state = _clean(
            row.get("time_to_first_admitted_visible_state_change_observation_state")
        ) or "NOT_EVALUATED"
        timing_state_by_function[function][timing_state] += 1
        timing_value = row.get("time_to_first_admitted_visible_state_change_seconds_candidate")
        if (
            timing_state == "OBSERVED_ADMITTED_AFTER"
            and isinstance(timing_value, (int, float))
            and not isinstance(timing_value, bool)
        ):
            timing_by_function[function].append(float(timing_value))

    timing_contract = consequence_payload.get(
        "time_to_first_admitted_visible_state_change_profile"
    ) or {}
    state_change_timing_profiles: list[dict[str, Any]] = []
    for function in sorted(eligible_by_function):
        values = sorted(timing_by_function.get(function) or [])
        state_counts = dict(sorted(timing_state_by_function[function].items()))
        state_change_timing_profiles.append({
            "visible_state_change_function_candidate": function,
            "eligible_transition_n": int(eligible_by_function[function]),
            "observed_timing_n": len(values),
            "observation_state_counts": state_counts,
            "median_seconds_candidate": median(values) if values else None,
            "min_seconds_candidate": min(values) if values else None,
            "max_seconds_candidate": max(values) if values else None,
            "distribution_values_seconds_candidate": values,
            "diagnostic_observation_horizon_seconds": timing_contract.get(
                "diagnostic_observation_horizon_seconds"
            ),
            "distribution_is_truncated_by_diagnostic_horizon": timing_contract.get(
                "distribution_is_truncated_by_diagnostic_horizon"
            ) is True,
            "distribution_is_descriptive_not_first_passage_model": True,
            "no_admitted_after_within_horizon_is_failure": False,
            "timing_is_physical_space_open_duration_truth": False,
            "timing_is_causal_advantage_truth": False,
            "graphability_state": (
                "GRAPH_READY_WITH_REVIEW" if values else "NOT_GRAPH_READY_NO_ADMITTED_TIMING"
            ),
            "recommended_graphs": [
                "STATE_CHANGE_FUNCTION_TIME_DISTRIBUTION",
                "STATE_CHANGE_FUNCTION_TIME_ECDF",
            ],
            "claim_ceiling": CLAIM_CEILING,
        })
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": spatial_binding or None,
        "state_transition_dynamics_candidates": records,
        "state_transition_dynamics_candidate_count": len(records),
        "transition_class_counts": dict(sorted(counts.items())),
        "visible_state_change_function_counts": dict(sorted(Counter(
            row.get("visible_state_change_function_candidate") for row in records
        ).items())),
        "visible_state_change_timing_profiles": state_change_timing_profiles,
        "state_change_timing_profile_count": len(state_change_timing_profiles),
        "state_change_timing_is_first_passage_model_output": False,
        "state_change_timing_is_physical_advantage_window_truth": False,
        "admitted_directional_transition_count": sum(
            bool(row.get("admitted_after_follow_up_trace_ids")) for row in records
        ),
        "provider_progression_semantic_transition_count": sum(
            bool(row.get("provider_progression_candidates")) for row in records
        ),
        "adverse_consequence_transition_count": sum(
            bool(row.get("adverse_consequence_candidates")) for row in records
        ),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "metric_value_output_allowed": False,
        "state_transition_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_pattern_truth": False,
        "causality_truth": False,
        "state_change_function_is_opponent_organization_truth": False,
        "state_change_function_is_player_causal_credit": False,
        "state_change_function_is_value_model_output": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _summary(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA STATE TRANSITION DYNAMICS LITE V1",
        f"status={payload.get('status')}",
        f"candidate_count={payload.get('state_transition_dynamics_candidate_count')}",
        f"admitted_directional_transition_count={payload.get('admitted_directional_transition_count')}",
        f"provider_progression_semantic_transition_count={payload.get('provider_progression_semantic_transition_count')}",
        f"adverse_consequence_transition_count={payload.get('adverse_consequence_transition_count')}",
        f"visible_state_change_function_counts={payload.get('visible_state_change_function_counts')}",
        f"review_hits={payload.get('review_hits')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ])


def _analyst(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA ANALYST AUDIT — STATE TRANSITION DYNAMICS",
        f"WHAT_VISIBLE: {payload.get('state_transition_dynamics_candidate_count', 0)} semantic-spatial/consequence associations projected.",
        f"SUPPORT: {payload.get('admitted_directional_transition_count', 0)} candidates include admitted AFTER_CONFIRMED follow-up evidence.",
        f"COUNTEREVIDENCE: {payload.get('adverse_consequence_transition_count', 0)} candidates carry explicit adverse visible consequence; absence is not counterevidence.",
        "SAFE_MEANING: provider-admitted progression/zone/context semantics may be associated with admitted visible consequence candidates and a bounded visible state-change function at trace level.",
        "STATE_CHANGE_SCOPE: backward/lateral action is not automatically negative; any value meaning comes only from admitted downstream visible state/consequence context.",
        "FORBIDDEN_INFERENCE: this does not prove measured displacement, possession, sequence truth, tactical pattern, dominance, adaptation, intention or causality.",
        "ANALYST_ACTION: drill into repeated transition classes and compare favorable/adverse consequence distributions before promoting a finding.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
    ])


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(_analyst(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spatial-transition", required=True)
    parser.add_argument("--consequence", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = build_state_transition_dynamics(
        load_json(args.spatial_transition, "spatial_transition_input_unreadable"),
        load_json(args.consequence, "consequence_input_unreadable"),
    )
    write_outputs(payload, args.out_dir)
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
