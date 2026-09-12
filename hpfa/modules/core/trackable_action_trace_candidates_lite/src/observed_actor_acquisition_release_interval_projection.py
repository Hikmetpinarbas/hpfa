from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING = "OBSERVED_ACTOR_ACQUISITION_TO_RELEASE_START_INTERVAL_CANDIDATE_ONLY"
AFTER_CONFIRMED = "AFTER_CONFIRMED"
ACQUISITION_FAMILIES = {"RECOVERY", "INTERCEPTION"}
RELEASE_FAMILY = "PASS"
SAME_ACTOR_RETENTION_FAMILIES = {"CARRY", "DRIBBLE"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number(value: Any) -> float | None:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return None


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _families(row: dict[str, Any]) -> set[str]:
    return {_clean(v) for v in (row.get("action_family_candidates") or []) if _clean(v)}


def _primary_trace_map(trace_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = trace_payload.get("primary_occurrence_trace_candidates")
    if not isinstance(rows, list):
        return {}
    return {
        _clean(row.get("trackable_action_trace_candidate_id")): row
        for row in rows
        if isinstance(row, dict) and _clean(row.get("trackable_action_trace_candidate_id"))
    }


def _relation_records(trace_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in (trace_payload.get("temporal_relation_admission_records") or [])
        if isinstance(row, dict)
    ]


def _intervening_break(
    *,
    anchor: dict[str, Any],
    release: dict[str, Any],
    ordered_rows: list[dict[str, Any]],
) -> tuple[bool, list[str], list[str]]:
    anchor_start = _number(anchor.get("start_candidate"))
    release_start = _number(release.get("start_candidate"))
    if anchor_start is None or release_start is None:
        return True, [], []

    actor = _clean(anchor.get("actor_identity_candidate_id"))
    team = _clean(anchor.get("team_identity_candidate_id"))
    period = _clean(anchor.get("period_candidate"))
    retained: list[str] = []
    breakers: list[str] = []

    for row in ordered_rows:
        row_start = _number(row.get("start_candidate"))
        if row_start is None or not (anchor_start < row_start < release_start):
            continue
        if _clean(row.get("period_candidate")) != period:
            continue
        row_id = _clean(row.get("trackable_action_trace_candidate_id"))
        row_actor = _clean(row.get("actor_identity_candidate_id"))
        row_team = _clean(row.get("team_identity_candidate_id"))
        row_families = _families(row)

        if (
            row_actor == actor
            and row_team == team
            and row_families
            and row_families <= SAME_ACTOR_RETENTION_FAMILIES
        ):
            retained.append(row_id)
            continue
        breakers.append(row_id)

    return bool(breakers), sorted(set(retained)), sorted(set(breakers))


def build_observed_actor_acquisition_release_interval_projection(
    trace_payload: dict[str, Any],
) -> dict[str, Any]:
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    if trace_payload.get("canonical_event_count") != "UNKNOWN":
        hard_blocks.append("canonical_event_count_claimed")
    if trace_payload.get("true_action_count") != "UNKNOWN":
        hard_blocks.append("true_action_count_claimed")
    if trace_payload.get("production_release") is True:
        hard_blocks.append("production_release_claimed")
    if trace_payload.get("provider_time_contract_admission_status") != "ADMITTED":
        hard_blocks.append("provider_time_contract_not_admitted")
    if trace_payload.get("temporal_relation_uses_start_timestamp_only") is not True:
        hard_blocks.append("start_timestamp_only_temporal_contract_missing")
    if trace_payload.get("trace_end_candidate_used_for_ordering") is not False:
        hard_blocks.append("trace_end_used_for_ordering")
    if trace_payload.get("same_timestamp_is_total_order") is not False:
        hard_blocks.append("same_timestamp_total_order_breached")
    if trace_payload.get("source_row_order_is_temporal_truth") is not False:
        hard_blocks.append("source_row_order_temporal_truth_breached")
    if trace_payload.get("legacy_trace_records_are_primary_action_member_surface") is not False:
        hard_blocks.append("legacy_trace_primary_surface_breached")

    trace_by_id = _primary_trace_map(trace_payload)
    if not trace_by_id:
        hard_blocks.append("primary_occurrence_trace_surface_missing")

    relation_rows = _relation_records(trace_payload)
    relation_window = _number(trace_payload.get("temporal_relation_max_window_seconds"))
    if relation_window is None or relation_window <= 0:
        review_hits.append("temporal_relation_window_unknown")

    if hard_blocks:
        return {
            "status": "FAIL_CLOSED",
            "observed_actor_acquisition_release_interval_candidates": [],
            "observed_actor_acquisition_release_interval_candidate_count": 0,
            "eligible_acquisition_trace_count": 0,
            "acquisition_family_counts": {},
            "rejection_reason_counts": {},
            "hard_block_hits": sorted(set(hard_blocks)),
            "review_hits": sorted(set(review_hits)),
            "projection_creates_new_evidence": False,
            "projection_reconstructs_sequences": False,
            "start_timestamp_point_is_physical_control_time_truth": False,
            "release_start_timestamp_is_physical_ball_release_time_truth": False,
            "interval_is_physical_control_to_pass_time_truth": False,
            "interval_is_decision_speed_truth": False,
            "interval_is_cognitive_speed_truth": False,
            "interval_is_press_resistance_truth": False,
            "temporal_relation_window_is_observation_horizon_truth": False,
            "interval_candidates_are_right_censored": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    ordered_rows = sorted(
        trace_by_id.values(),
        key=lambda row: (
            _clean(row.get("period_candidate")),
            _number(row.get("start_candidate"))
            if _number(row.get("start_candidate")) is not None
            else float("inf"),
            _clean(row.get("trackable_action_trace_candidate_id")),
        ),
    )

    after_by_anchor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rel in relation_rows:
        if _clean(rel.get("relation_state")) != AFTER_CONFIRMED:
            continue
        anchor_id = _clean(rel.get("anchor_trackable_action_trace_candidate_id"))
        candidate_id = _clean(rel.get("candidate_trackable_action_trace_candidate_id"))
        if anchor_id in trace_by_id and candidate_id in trace_by_id:
            after_by_anchor[anchor_id].append(rel)

    anchors = [
        row
        for row in trace_by_id.values()
        if _families(row) & ACQUISITION_FAMILIES
        and _clean(row.get("actor_identity_candidate_id"))
        and _clean(row.get("team_identity_candidate_id"))
        and _clean(row.get("period_candidate"))
        and _number(row.get("start_candidate")) is not None
        and row.get("primary_occurrence_member_candidate") is True
        and row.get("occurrence_backed_trace_candidate") is True
    ]
    anchors.sort(
        key=lambda row: (
            _clean(row.get("period_candidate")),
            _number(row.get("start_candidate")) or 0.0,
            _clean(row.get("trackable_action_trace_candidate_id")),
        )
    )

    rejection = Counter()
    candidates: list[dict[str, Any]] = []
    used_release_ids: set[str] = set()

    for anchor in anchors:
        anchor_id = _clean(anchor.get("trackable_action_trace_candidate_id"))
        actor = _clean(anchor.get("actor_identity_candidate_id"))
        team = _clean(anchor.get("team_identity_candidate_id"))
        period = _clean(anchor.get("period_candidate"))
        anchor_start = _number(anchor.get("start_candidate"))
        anchor_families = sorted(_families(anchor) & ACQUISITION_FAMILIES)
        if anchor_start is None or not anchor_families:
            rejection["anchor_contract_incomplete"] += 1
            continue

        possible: list[
            tuple[float, dict[str, Any], dict[str, Any], list[str], list[str]]
        ] = []
        for rel in after_by_anchor.get(anchor_id, []):
            release_id = _clean(rel.get("candidate_trackable_action_trace_candidate_id"))
            release = trace_by_id.get(release_id)
            if release is None:
                continue
            release_start = _number(release.get("start_candidate"))
            if release_start is None or release_start <= anchor_start:
                continue
            if RELEASE_FAMILY not in _families(release):
                continue
            if _clean(release.get("actor_identity_candidate_id")) != actor:
                continue
            if _clean(release.get("team_identity_candidate_id")) != team:
                continue
            if _clean(release.get("period_candidate")) != period:
                continue
            if (
                release.get("primary_occurrence_member_candidate") is not True
                or release.get("occurrence_backed_trace_candidate") is not True
            ):
                continue

            has_break, retained, breakers = _intervening_break(
                anchor=anchor,
                release=release,
                ordered_rows=ordered_rows,
            )
            if has_break:
                rejection["intervening_action_break"] += 1
                continue
            possible.append((release_start, release, rel, retained, breakers))

        if not possible:
            rejection["no_admitted_same_actor_pass_release"] += 1
            continue

        possible.sort(
            key=lambda item: (
                item[0],
                _clean(item[1].get("trackable_action_trace_candidate_id")),
            )
        )
        release_start, release, rel, retained, _ = possible[0]
        release_id = _clean(release.get("trackable_action_trace_candidate_id"))
        if release_id in used_release_ids:
            rejection["release_already_bound"] += 1
            continue
        used_release_ids.add(release_id)

        interval = round(release_start - anchor_start, 6)
        if interval <= 0:
            rejection["non_positive_interval"] += 1
            continue

        acquisition_occurrences = sorted(
            {
                _clean(v)
                for v in (anchor.get("supporting_action_occurrence_candidate_ids") or [])
                if _clean(v)
            }
        )
        release_occurrences = sorted(
            {
                _clean(v)
                for v in (release.get("supporting_action_occurrence_candidate_ids") or [])
                if _clean(v)
            }
        )

        candidates.append(
            {
                "observed_actor_acquisition_release_interval_candidate_id": "aaric_"
                + _digest(
                    anchor_id,
                    release_id,
                    actor,
                    team,
                    period,
                    anchor_start,
                    release_start,
                )[:24],
                "actor_identity_candidate_id": actor,
                "team_identity_candidate_id": team,
                "period_candidate": period,
                "acquisition_trackable_action_trace_candidate_id": anchor_id,
                "release_trackable_action_trace_candidate_id": release_id,
                "acquisition_action_family_candidates": anchor_families,
                "release_action_family_candidate": RELEASE_FAMILY,
                "acquisition_start_timestamp_candidate": anchor_start,
                "release_start_timestamp_candidate": release_start,
                "acquisition_to_release_start_interval_seconds": interval,
                "temporal_relation_state": AFTER_CONFIRMED,
                "temporal_basis": rel.get("temporal_basis"),
                "ordering_basis": rel.get("ordering_basis"),
                "provider_time_contract_rule_id": rel.get("provider_time_contract_rule_id"),
                "intervening_same_actor_retention_trace_ids": retained,
                "supporting_action_occurrence_candidate_ids": sorted(
                    set(acquisition_occurrences + release_occurrences)
                ),
                "start_timestamp_point_is_physical_control_time_truth": False,
                "release_start_timestamp_is_physical_ball_release_time_truth": False,
                "interval_is_physical_control_to_pass_time_truth": False,
                "interval_is_decision_speed_truth": False,
                "interval_is_cognitive_speed_truth": False,
                "interval_is_press_resistance_truth": False,
                "interval_is_tactical_intention_truth": False,
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    if trace_payload.get("status") == "REVIEW_REQUIRED":
        review_hits.append("upstream_trace_review_required")
    if candidates:
        review_hits.append("interval_distribution_not_yet_calibrated")
    if relation_window is not None:
        review_hits.append("interval_candidate_visibility_window_limited")

    status = "REVIEW_REQUIRED" if review_hits else "PASS"
    return {
        "status": status,
        "observed_actor_acquisition_release_interval_candidates": candidates,
        "observed_actor_acquisition_release_interval_candidate_count": len(candidates),
        "eligible_acquisition_trace_count": len(anchors),
        "acquisition_family_counts": dict(
            sorted(
                Counter(
                    family
                    for row in anchors
                    for family in (_families(row) & ACQUISITION_FAMILIES)
                ).items()
            )
        ),
        "rejection_reason_counts": dict(sorted(rejection.items())),
        "temporal_relation_window_seconds": relation_window,
        "interval_candidate_visibility_is_window_limited": relation_window is not None,
        "temporal_relation_window_is_observation_horizon_truth": False,
        "interval_candidates_are_right_censored": False,
        "projection_creates_new_evidence": False,
        "projection_reconstructs_sequences": False,
        "projection_uses_primary_occurrence_trace_surface_only": True,
        "start_timestamp_point_is_physical_control_time_truth": False,
        "release_start_timestamp_is_physical_ball_release_time_truth": False,
        "interval_is_physical_control_to_pass_time_truth": False,
        "interval_is_decision_speed_truth": False,
        "interval_is_cognitive_speed_truth": False,
        "interval_is_press_resistance_truth": False,
        "hard_block_hits": [],
        "review_hits": sorted(set(review_hits)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
