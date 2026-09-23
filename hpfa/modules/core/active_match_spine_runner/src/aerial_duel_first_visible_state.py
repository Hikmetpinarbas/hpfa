from __future__ import annotations

from collections import Counter
from typing import Any


MODULE_ID = "aerial_duel_first_visible_state_context_v1"
CLAIM_CEILING = "MATCH_LOCAL_AERIAL_DUEL_FIRST_VISIBLE_STATE_CANDIDATE_ONLY"


def _float_candidate(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _upper_labels(row: dict[str, Any]) -> set[str]:
    return {
        str(value or "").strip().upper()
        for value in (row.get("raw_labels") or [])
        if str(value or "").strip()
    }


def _aerial_outcome(labels: set[str]) -> str | None:
    won = any("AERIAL CHALLENGES WON" in label for label in labels)
    lost = any("AERIAL CHALLENGES LOST" in label for label in labels)
    if won and not lost:
        return "PROVIDER_REVIEWED_AERIAL_DUEL_WON_CANDIDATE"
    if lost and not won:
        return "PROVIDER_REVIEWED_AERIAL_DUEL_LOST_CANDIDATE"
    return None


def build_aerial_duel_first_visible_state_context(
    trace_payload: dict[str, Any],
    process_participation_payload: dict[str, Any],
) -> dict[str, Any]:
    """Describe what is first visibly observed after reviewed aerial-duel labels.

    The projection never treats provider duel outcome as possession/control truth.
    Same-timestamp records are not internally ordered. No visible follow-up is
    preserved as censoring/absence of observation rather than failure.
    """
    traces = [
        row for row in (
            trace_payload.get("trackable_action_trace_candidates")
            or trace_payload.get("primary_occurrence_trace_candidates")
            or []
        )
        if isinstance(row, dict)
    ]

    intervals: list[dict[str, Any]] = []
    for row in process_participation_payload.get("process_participation_candidates", []) or []:
        if not isinstance(row, dict) or str(row.get("semantic_role") or "") != "CONTEXT_INTERVAL":
            continue
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        family = str(row.get("process_family_candidate") or "").strip()
        period = str(row.get("period_candidate") or "").strip()
        start = _float_candidate(row.get("start_candidate"))
        end = _float_candidate(row.get("end_candidate"))
        if team_id and family and start is not None and end is not None:
            intervals.append({
                "team_identity_candidate_id": team_id,
                "process_family_candidate": family,
                "period_candidate": period,
                "start_candidate": start,
                "end_candidate": end,
            })

    normalized: list[dict[str, Any]] = []
    for row in traces:
        start = _float_candidate(row.get("start_candidate"))
        if start is None:
            continue
        normalized.append({
            **row,
            "_start": start,
            "_period": str(row.get("period_candidate") or "").strip(),
            "_team": str(row.get("team_identity_candidate_id") or "").strip(),
        })
    normalized.sort(key=lambda row: (row["_period"], row["_start"], str(row.get("trackable_action_trace_candidate_id") or "")))

    rows: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    first_team_relation_counts: Counter[str] = Counter()
    next_process_counts: Counter[str] = Counter()

    for anchor in normalized:
        outcome = _aerial_outcome(_upper_labels(anchor))
        if outcome is None:
            continue
        anchor_team = anchor["_team"]
        period = anchor["_period"]
        start = anchor["_start"]

        later = [
            row for row in normalized
            if row["_period"] == period and row["_start"] > start
        ]
        if not later:
            state = "NO_VISIBLE_FOLLOWUP"
            first_time = None
            first_teams: list[str] = []
            team_relation = "UNRESOLVED"
            process_families: list[str] = []
        else:
            first_time = min(row["_start"] for row in later)
            first_layer = [row for row in later if row["_start"] == first_time]
            first_teams = sorted({row["_team"] for row in first_layer if row["_team"]})
            if len(first_teams) != 1:
                state = "REVIEW_REQUIRED_MIXED_TEAM_FIRST_VISIBLE_LAYER"
                team_relation = "UNRESOLVED"
                process_families = []
            else:
                first_team = first_teams[0]
                team_relation = (
                    "SAME_TEAM_FIRST_VISIBLE_ACTION"
                    if anchor_team and first_team == anchor_team
                    else "OPPONENT_TEAM_FIRST_VISIBLE_ACTION"
                    if anchor_team and first_team != anchor_team
                    else "UNRESOLVED"
                )
                process_families = sorted({
                    interval["process_family_candidate"]
                    for interval in intervals
                    if interval["team_identity_candidate_id"] == first_team
                    and interval["period_candidate"] == period
                    and interval["start_candidate"] <= first_time <= interval["end_candidate"]
                })
                state = (
                    "SINGLE_VISIBLE_PROCESS_FAMILY_MATCH"
                    if len(process_families) == 1
                    else "MULTIPLE_VISIBLE_PROCESS_FAMILIES_REVIEW_REQUIRED"
                    if len(process_families) > 1
                    else "FIRST_VISIBLE_TEAM_OBSERVED_PROCESS_NOT_BOUND"
                )

        outcome_counts[outcome] += 1
        state_counts[state] += 1
        first_team_relation_counts[team_relation] += 1
        for family in process_families:
            next_process_counts[family] += 1

        rows.append({
            "source_trackable_action_trace_candidate_id": anchor.get("trackable_action_trace_candidate_id"),
            "team_identity_candidate_id": anchor_team or None,
            "actor_identity_candidate_id": anchor.get("actor_identity_candidate_id"),
            "period_candidate": period,
            "aerial_duel_start_second_candidate": start,
            "provider_aerial_duel_outcome_candidate": outcome,
            "first_strictly_later_visible_time_candidate": first_time,
            "first_visible_team_identity_candidate_ids": first_teams,
            "first_visible_team_relation_to_aerial_actor_team": team_relation,
            "next_visible_process_family_candidates": process_families,
            "binding_state": state,
            "provider_aerial_duel_outcome_is_ball_control_truth": False,
            "first_visible_team_action_is_second_ball_control_truth": False,
            "first_visible_team_action_is_possession_truth": False,
            "same_timestamp_total_order_allowed": False,
            "no_visible_followup_is_failure": False,
            "causal_credit_allowed": False,
        })

    review_n = sum(
        count for state, count in state_counts.items()
        if "REVIEW_REQUIRED" in state
    )
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if review_n else ("PASS" if rows else "NOT_AVAILABLE"),
        "binding_state": "AERIAL_DUEL_TO_FIRST_STRICTLY_LATER_VISIBLE_TEAM_STATE",
        "admitted_aerial_label_trace_context_row_count": len(rows),
        "admitted_aerial_label_trace_outcome_counts": dict(sorted(outcome_counts.items())),
        "first_visible_team_relation_counts": dict(sorted(first_team_relation_counts.items())),
        "binding_state_counts": dict(sorted(state_counts.items())),
        "next_visible_process_family_counts": dict(sorted(next_process_counts.items())),
        "rows": rows,
        "claim_ceiling": CLAIM_CEILING,
        "provider_aerial_duel_outcome_is_ball_control_truth": False,
        "admitted_aerial_label_trace_count_is_physical_duel_count": False,
        "admitted_trace_coverage_is_complete_aerial_duel_inventory": False,
        "provider_pair_completeness_not_assumed": True,
        "first_visible_team_action_is_second_ball_control_truth": False,
        "first_visible_team_action_is_possession_truth": False,
        "same_timestamp_total_order_allowed": False,
        "no_visible_followup_is_failure": False,
        "creates_independent_support": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
