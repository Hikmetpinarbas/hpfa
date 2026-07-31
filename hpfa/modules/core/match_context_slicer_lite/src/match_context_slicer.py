from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "match_context_slicer_lite_v1"
ACTION_MODULE_ID = "selected_action_consequence_surface_lite_v1"
PHASE_MODULE_ID = "event_derived_phase_state_lite_v1"
REFINEMENT_MODULE_ID = "phase_aware_sequence_refinement_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
OUTPUTS = {
    "json": "match_context_slicer_lite_v1.json",
    "summary": "match_context_slicer_lite_v1.txt",
    "analyst": "match_context_slicer_analyst_audit_v1.txt",
}


def clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return None


def digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _validate_upstream(
    payload: dict[str, Any], expected_module: str, binding: str | None
) -> tuple[list[str], list[str], str]:
    blocks: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != expected_module:
        blocks.append(f"{expected_module}_module_id_mismatch")
    upstream_binding = clean(payload.get("match_surface_binding_id"))
    if not upstream_binding:
        blocks.append(f"{expected_module}_binding_missing")
    elif binding and upstream_binding != binding:
        blocks.append(f"{expected_module}_binding_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{expected_module}_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{expected_module}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{expected_module}_hard_blocks_present")
    status = clean(payload.get("module_status") or payload.get("status"))
    if status != "PASS":
        reviews.append(f"{expected_module}_status_review:{status or 'UNKNOWN'}")
    return blocks, reviews, upstream_binding


def _labels(node: dict[str, Any]) -> set[str]:
    raw = node.get("support_normalized_labels")
    if not isinstance(raw, list):
        return set()
    return {clean(value).casefold() for value in raw if clean(value)}


def _is_goal_candidate(node: dict[str, Any]) -> bool:
    families = node.get("action_family_candidates")
    return (
        isinstance(families, list)
        and "SHOT" in families
        and node.get("terminal_outcome_support_visible") is True
        and "goals" in _labels(node)
    )


def _minute_display(seconds: float) -> str:
    minute = int(seconds // 60) + 1
    return f"{minute}'"


def _time_bucket(seconds: float) -> str:
    minute = int(seconds // 60)
    lower = (minute // 15) * 15
    upper = lower + 15
    return f"MIN_{lower:02d}_{upper:02d}_CANDIDATE"


def _score_state(team_goals: int, opponent_goals: int) -> str:
    if team_goals > opponent_goals:
        return "LEADING_CANDIDATE"
    if team_goals < opponent_goals:
        return "TRAILING_CANDIDATE"
    return "DRAWING_CANDIDATE"


def build_match_context_slicer(
    action_payload: dict[str, Any],
    phase_payload: dict[str, Any],
    refinement_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    binding: str | None = None
    for payload, module_id in (
        (action_payload, ACTION_MODULE_ID),
        (phase_payload, PHASE_MODULE_ID),
        (refinement_payload, REFINEMENT_MODULE_ID),
    ):
        new_blocks, new_reviews, upstream_binding = _validate_upstream(
            payload, module_id, binding
        )
        blocks.extend(new_blocks)
        reviews.extend(new_reviews)
        if binding is None and upstream_binding:
            binding = upstream_binding

    nodes = action_payload.get("selected_action_nodes")
    phases = phase_payload.get("event_derived_phase_segments")
    decisions = refinement_payload.get("phase_refinement_decisions")
    if not isinstance(nodes, list):
        blocks.append("selected_action_node_inventory_invalid")
        nodes = []
    if not isinstance(phases, list):
        blocks.append("phase_segment_inventory_invalid")
        phases = []
    if not isinstance(decisions, list):
        blocks.append("phase_refinement_decision_inventory_invalid")
        decisions = []
    if action_payload.get("selected_action_node_count") != len(nodes):
        blocks.append("selected_action_node_count_mismatch")
    if phase_payload.get("event_derived_phase_segment_count") != len(phases):
        blocks.append("phase_segment_count_mismatch")
    if refinement_payload.get("phase_refinement_decision_count") != len(decisions):
        blocks.append("phase_refinement_decision_count_mismatch")

    teams = sorted(
        {
            clean(node.get("team_identity_candidate_id"))
            for node in nodes
            if isinstance(node, dict) and clean(node.get("team_identity_candidate_id"))
        }
    )
    if len(teams) != 2:
        blocks.append(f"two_team_context_required:observed_{len(teams)}")

    period_times: dict[str, list[float]] = defaultdict(list)
    node_ids: set[str] = set()
    valid_nodes: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            blocks.append("selected_action_node_record_invalid")
            continue
        node_id = clean(node.get("selected_action_node_id"))
        period = clean(node.get("period_candidate"))
        start = number(node.get("start_candidate"))
        if not node_id or node_id in node_ids:
            blocks.append(f"selected_action_node_id_invalid_or_duplicate:{node_id or 'NONE'}")
            continue
        node_ids.add(node_id)
        if start is None or start < 0 or not period:
            blocks.append(f"selected_action_time_or_period_invalid:{node_id}")
            continue
        if clean(node.get("match_surface_binding_id")) != binding:
            blocks.append(f"selected_action_binding_mismatch:{node_id}")
        period_times[period].append(start)
        valid_nodes.append(node)

    ordered_periods = sorted(period_times, key=lambda value: (number(value) is None, number(value), value))
    period_ranges = {
        period: {"min": min(values), "max": max(values), "count": len(values)}
        for period, values in period_times.items()
        if values
    }
    cumulative_axis = all(
        period_ranges[current]["min"] >= period_ranges[previous]["max"]
        for previous, current in zip(ordered_periods, ordered_periods[1:])
    )
    if not cumulative_axis:
        blocks.append("absolute_match_time_axis_not_monotonic_across_periods")

    goal_candidates: list[dict[str, Any]] = []
    seen_goal_keys: set[tuple[str, float, str]] = set()
    for node in sorted(
        valid_nodes,
        key=lambda item: (
            number(item.get("start_candidate")) or 0.0,
            clean(item.get("selected_action_node_id")),
        ),
    ):
        if not _is_goal_candidate(node):
            continue
        team = clean(node.get("team_identity_candidate_id"))
        start = number(node.get("start_candidate"))
        period = clean(node.get("period_candidate"))
        if not team or start is None:
            reviews.append("goal_candidate_missing_team_or_time")
            continue
        key = (period, start, team)
        if key in seen_goal_keys:
            reviews.append("same_team_same_time_goal_reflection_preserved_once")
            continue
        seen_goal_keys.add(key)
        goal_candidates.append(
            {
                "goal_context_candidate_id": "mcs_goal_"
                + digest(binding, period, start, team)[:24],
                "source_selected_action_node_id": node.get("selected_action_node_id"),
                "period_candidate": period,
                "absolute_match_seconds_candidate": start,
                "minute_display_candidate": _minute_display(start),
                "team_identity_candidate_id": team,
                "actor_identity_candidate_id": node.get("actor_identity_candidate_id"),
                "goal_is_scoreboard_truth": False,
                "goal_is_canonical_event_truth": False,
                "evidence": ["SHOT", "terminal_outcome_support_visible", "goals_label"],
            }
        )
    if not goal_candidates:
        reviews.append("no_goal_context_candidate_observed")

    decision_by_segment: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        if not isinstance(decision, dict):
            blocks.append("phase_refinement_decision_record_invalid")
            continue
        segment_id = clean(decision.get("source_event_derived_phase_segment_id"))
        if not segment_id or segment_id in decision_by_segment:
            blocks.append(f"phase_refinement_decision_segment_invalid:{segment_id or 'NONE'}")
            continue
        decision_by_segment[segment_id] = decision

    slices: list[dict[str, Any]] = []
    score_state_counts: Counter[str] = Counter()
    same_time_goal_review_count = 0
    for phase in phases:
        if not isinstance(phase, dict):
            blocks.append("phase_segment_record_invalid")
            continue
        segment_id = clean(phase.get("event_derived_phase_segment_id"))
        period = clean(phase.get("period_candidate"))
        team = clean(phase.get("team_identity_candidate_id"))
        start = number(phase.get("start_time_candidate"))
        end = number(phase.get("end_time_candidate"))
        if not segment_id or start is None or end is None or end < start:
            blocks.append(f"phase_segment_context_invalid:{segment_id or 'NONE'}")
            continue
        if clean(phase.get("match_surface_binding_id")) != binding:
            blocks.append(f"phase_segment_binding_mismatch:{segment_id}")
        decision = decision_by_segment.get(segment_id)
        if decision is None:
            blocks.append(f"phase_refinement_decision_missing:{segment_id}")
            continue
        goals_before = [goal for goal in goal_candidates if goal["absolute_match_seconds_candidate"] < start]
        same_time_goals = [goal for goal in goal_candidates if goal["absolute_match_seconds_candidate"] == start]
        score = {candidate_team: 0 for candidate_team in teams}
        for goal in goals_before:
            goal_team = goal["team_identity_candidate_id"]
            if goal_team in score:
                score[goal_team] += 1
        opponent = next((candidate for candidate in teams if candidate != team), None)
        if same_time_goals:
            relative_state = "SAME_TIME_GOAL_CONTEXT_REVIEW_REQUIRED"
            same_time_goal_review_count += 1
        elif team in score and opponent in score:
            relative_state = _score_state(score[team], score[opponent])
        else:
            relative_state = "SCORE_STATE_UNRESOLVED"
        score_state_counts[relative_state] += 1
        slices.append(
            {
                "match_context_slice_id": "mcs_" + digest(binding, segment_id)[:24],
                "source_event_derived_phase_segment_id": segment_id,
                "source_visible_action_sequence_candidate_id": phase.get(
                    "source_visible_action_sequence_candidate_id"
                ),
                "source_phase_refinement_decision_id": decision.get(
                    "phase_refinement_decision_id"
                ),
                "phase_refinement_decision_class": decision.get("decision_class"),
                "period_candidate": period,
                "absolute_start_seconds_candidate": start,
                "absolute_end_seconds_candidate": end,
                "minute_display_candidate": _minute_display(start),
                "time_bucket_candidate": _time_bucket(start),
                "team_identity_candidate_id": team,
                "phase_class_candidate": phase.get("phase_class_candidate"),
                "score_before_slice_candidate": score,
                "team_relative_score_state_candidate": relative_state,
                "same_time_goal_context_candidate_ids": [
                    goal["goal_context_candidate_id"] for goal in same_time_goals
                ],
                "card_state_candidate": "UNKNOWN_NO_VALIDATED_CARD_SURFACE_IN_CURRENT_INPUT",
                "lineup_state_candidate": "UNKNOWN_NO_VALIDATED_SUBSTITUTION_SURFACE_IN_CURRENT_INPUT",
                "restart_or_open_play_candidate": (
                    "RESTART_CANDIDATE"
                    if phase.get("phase_class_candidate") == "RESTART_VISIBLE_PHASE_CANDIDATE"
                    else "OPEN_PLAY_OR_UNRESOLVED_NON_RESTART_CANDIDATE"
                ),
                "score_state_is_scoreboard_truth": False,
                "match_context_is_tactical_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )

    if blocks:
        slices = []
        goal_candidates = []
        score_state_counts = Counter()
    elif len(slices) != len(phases):
        blocks.append("match_context_slice_reconciliation_failed")
        slices = []
        goal_candidates = []
        score_state_counts = Counter()
    if same_time_goal_review_count:
        reviews.append("same_timestamp_goal_context_not_artificially_ordered")
    reviews.extend(
        [
            "card_state_unresolved_without_validated_card_surface",
            "lineup_state_unresolved_without_validated_substitution_surface",
            "score_state_is_event_derived_candidate_not_scoreboard_truth",
        ]
    )
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "version": "1.0.0",
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding,
        "time_axis_candidate": "CUMULATIVE_ABSOLUTE_SECONDS_CANDIDATE" if cumulative_axis else "UNRESOLVED",
        "period_time_ranges": period_ranges,
        "team_identity_candidate_ids": teams,
        "source_selected_action_node_count": len(nodes),
        "source_event_derived_phase_segment_count": len(phases),
        "source_phase_refinement_decision_count": len(decisions),
        "goal_context_candidates": goal_candidates,
        "goal_context_candidate_count": len(goal_candidates),
        "match_context_slices": slices,
        "match_context_slice_count": len(slices),
        "team_relative_score_state_candidate_counts": dict(sorted(score_state_counts.items())),
        "same_time_goal_context_review_count": same_time_goal_review_count,
        "card_state_status": "UNKNOWN_NO_VALIDATED_CARD_SURFACE_IN_CURRENT_INPUT",
        "lineup_state_status": "UNKNOWN_NO_VALIDATED_SUBSTITUTION_SURFACE_IN_CURRENT_INPUT",
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "scoreboard_truth": False,
        "phase_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "tactical_truth": False,
        "off_ball_structure_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "time_axis_candidate",
        "period_time_ranges",
        "source_selected_action_node_count",
        "source_event_derived_phase_segment_count",
        "source_phase_refinement_decision_count",
        "goal_context_candidate_count",
        "match_context_slice_count",
        "team_relative_score_state_candidate_counts",
        "same_time_goal_context_review_count",
        "card_state_status",
        "lineup_state_status",
        "hard_block_hits",
        "review_hits",
    )
    lines = ["HPFA MATCH CONTEXT SLICER LITE V1"]
    lines.extend(f"{key}={payload.get(key)}" for key in keys)
    lines.extend(["canonical_event_count=UNKNOWN", "production_release=false"])
    return "\n".join(lines) + "\n"


def analyst_audit(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "HPFA ANALYST AUDIT — MATCH CONTEXT SLICER",
            f"Derived time axis: {payload.get('time_axis_candidate')}",
            f"Visible goal-context candidates: {payload.get('goal_context_candidate_count', 0)}",
            f"Contextualized phase slices: {payload.get('match_context_slice_count', 0)}",
            f"Relative score-state distribution: {payload.get('team_relative_score_state_candidate_counts', {})}",
            f"Same-time goal reviews: {payload.get('same_time_goal_context_review_count', 0)}",
            "Card state remains unknown unless a validated card surface is admitted.",
            "Lineup state remains unknown unless a validated substitution surface is admitted.",
            "Analyst-safe meaning: phase evidence can now be compared by period, derived minute bucket and event-derived score-state candidate.",
            "The surface does not prove scoreboard truth, possession, tactical intention or off-ball structure.",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "",
        ]
    )


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {name: output / filename for name, filename in OUTPUTS.items()}
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-action-consequence", required=True)
    parser.add_argument("--event-derived-phase", required=True)
    parser.add_argument("--phase-refinement", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_match_context_slicer(
        load_json(args.selected_action_consequence, "selected_action_input_unreadable_or_malformed"),
        load_json(args.event_derived_phase, "event_derived_phase_input_unreadable_or_malformed"),
        load_json(args.phase_refinement, "phase_refinement_input_unreadable_or_malformed"),
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "time_axis_candidate",
                    "goal_context_candidate_count",
                    "match_context_slice_count",
                    "team_relative_score_state_candidate_counts",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
