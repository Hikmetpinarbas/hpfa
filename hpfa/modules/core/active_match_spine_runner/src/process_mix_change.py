from __future__ import annotations

from collections import Counter, defaultdict
import math
from typing import Any


MODULE_ID = "time_window_process_mix_change_context_v1"
CLAIM_CEILING = "MATCH_LOCAL_VISIBLE_PROCESS_MIX_WINDOW_COMPARISON_CANDIDATE_ONLY"


def _float_candidate(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def build_time_window_process_mix_change_context(
    process_participation_payload: dict[str, Any],
    *,
    window_seconds: float = 900.0,
) -> dict[str, Any]:
    """Compare visible process-family composition across fixed match-time windows.

    This is a descriptive event/process-derived surface. It does not infer momentum,
    tactical adaptation, coach intention, causality, possession truth or off-ball state.
    Empty bins are not interpreted as process absence because observation coverage may
    be incomplete.
    """
    width = _float_candidate(window_seconds)
    if width is None or width <= 0:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "binding_state": "INVALID_WINDOW_WIDTH",
            "window_seconds": window_seconds,
            "profiles": [],
            "comparisons": [],
            "hard_block_hits": ["window_seconds_must_be_positive"],
            "review_hits": [],
            "claim_ceiling": CLAIM_CEILING,
            "process_mix_change_is_momentum_truth": False,
            "process_mix_change_is_tactical_change_truth": False,
            "process_mix_change_is_causal_truth": False,
            "empty_window_is_process_absence_truth": False,
            "creates_independent_support": False,
        }

    unique_intervals: dict[tuple[str, str, str, float, float], dict[str, Any]] = {}
    for row in process_participation_payload.get("process_participation_candidates", []) or []:
        if not isinstance(row, dict) or str(row.get("semantic_role") or "") != "CONTEXT_INTERVAL":
            continue
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        family = str(row.get("process_family_candidate") or "").strip()
        period = str(row.get("period_candidate") or "").strip() or "UNKNOWN"
        start = _float_candidate(row.get("start_candidate"))
        end = _float_candidate(row.get("end_candidate"))
        if not team_id or not family or start is None or end is None or end < start:
            continue
        unique_intervals.setdefault(
            (team_id, family, period, start, end),
            {
                "team_identity_candidate_id": team_id,
                "process_family_candidate": family,
                "period_candidate": period,
                "start_candidate": start,
                "end_candidate": end,
            },
        )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for interval in unique_intervals.values():
        grouped[
            (
                interval["team_identity_candidate_id"],
                interval["period_candidate"],
            )
        ].append(interval)

    profiles: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    skipped_gap_pairs = 0

    for (team_id, period), rows in sorted(grouped.items()):
        if not rows:
            continue
        minimum_start = min(float(row["start_candidate"]) for row in rows)
        anchor = math.floor(minimum_start / width) * width
        by_window: dict[int, Counter[str]] = defaultdict(Counter)
        for row in rows:
            index = int(math.floor((float(row["start_candidate"]) - anchor) / width))
            by_window[index][str(row["process_family_candidate"])] += 1

        team_period_profiles: list[dict[str, Any]] = []
        for index in sorted(by_window):
            counts = by_window[index]
            eligible_n = int(sum(counts.values()))
            shares = {
                family: round(count / eligible_n, 6)
                for family, count in sorted(counts.items())
            } if eligible_n else {}
            profile = {
                "team_identity_candidate_id": team_id,
                "period_candidate": period,
                "window_index": index,
                "window_start_second_candidate": anchor + (index * width),
                "window_end_second_candidate": anchor + ((index + 1) * width),
                "window_seconds": width,
                "eligible_visible_process_n": eligible_n,
                "process_family_counts": dict(sorted(counts.items())),
                "process_family_shares": shares,
                "denominator": "eligible_visible_process_candidates_in_window",
                "window_has_visible_process_evidence": eligible_n > 0,
                "empty_window_is_process_absence_truth": False,
            }
            profiles.append(profile)
            team_period_profiles.append(profile)

        for previous, current in zip(team_period_profiles, team_period_profiles[1:]):
            previous_index = int(previous["window_index"])
            current_index = int(current["window_index"])
            if current_index - previous_index != 1:
                skipped_gap_pairs += 1
                continue
            previous_shares = previous.get("process_family_shares") or {}
            current_shares = current.get("process_family_shares") or {}
            families = sorted(set(previous_shares) | set(current_shares))
            share_delta = {
                family: round(
                    float(current_shares.get(family, 0.0))
                    - float(previous_shares.get(family, 0.0)),
                    6,
                )
                for family in families
            }
            previous_counts = previous.get("process_family_counts") or {}
            current_counts = current.get("process_family_counts") or {}
            count_delta = {
                family: int(current_counts.get(family, 0))
                - int(previous_counts.get(family, 0))
                for family in sorted(set(previous_counts) | set(current_counts))
            }
            composition_total_variation_distance_candidate = round(
                0.5 * sum(abs(value) for value in share_delta.values()),
                6,
            )
            comparisons.append({
                "team_identity_candidate_id": team_id,
                "period_candidate": period,
                "previous_window_index": previous_index,
                "current_window_index": current_index,
                "previous_window_start_second_candidate": previous["window_start_second_candidate"],
                "current_window_start_second_candidate": current["window_start_second_candidate"],
                "previous_eligible_visible_process_n": previous["eligible_visible_process_n"],
                "current_eligible_visible_process_n": current["eligible_visible_process_n"],
                "process_family_count_delta": count_delta,
                "process_family_share_delta": share_delta,
                "composition_total_variation_distance_candidate": composition_total_variation_distance_candidate,
                "composition_distance_range": [0.0, 1.0],
                "composition_distance_is_change_point_truth": False,
                "comparison_basis": "ADJACENT_FIXED_TIME_WINDOWS_WITH_VISIBLE_PROCESS_EVIDENCE",
                "comparison_is_change_point_truth": False,
                "comparison_is_momentum_truth": False,
                "comparison_is_tactical_adaptation_truth": False,
                "comparison_is_causal_truth": False,
            })

    status = "PASS" if profiles else "NOT_AVAILABLE"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "binding_state": "VISIBLE_PROCESS_MIX_FIXED_TIME_WINDOW_COMPARISON",
        "window_seconds": width,
        "deduplicated_context_interval_count": len(unique_intervals),
        "profile_count": len(profiles),
        "comparison_count": len(comparisons),
        "skipped_non_adjacent_visible_window_pair_count": skipped_gap_pairs,
        "profiles": profiles,
        "comparisons": comparisons,
        "hard_block_hits": [],
        "review_hits": [],
        "claim_ceiling": CLAIM_CEILING,
        "denominator_is_visible_process_candidates_not_possession": True,
        "process_mix_change_is_momentum_truth": False,
        "process_mix_change_is_tactical_change_truth": False,
        "process_mix_change_is_causal_truth": False,
        "coach_intention_truth": False,
        "empty_window_is_process_absence_truth": False,
        "creates_independent_support": False,
    }
