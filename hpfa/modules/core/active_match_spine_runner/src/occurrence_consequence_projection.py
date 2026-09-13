from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "occurrence_consequence_projection_v1"
OUTPUT_JSON = "occurrence_consequence_projection_v1.json"
OUTPUT_TXT = "occurrence_consequence_projection_v1.txt"
HORIZON_BASIS = "FIXED_TIME_WITH_LAYER_CAP_VISIBLE_TRACE_SEARCH"
END_BOUNDARY_TYPES = {"HALFTIME", "FULL_TIME"}
NONBLOCKING_ADMIN_BOUNDARY_REVIEW_REASONS = {"visible_field_serialization_discrepancy"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _values(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sorted_text(values: Any) -> list[str]:
    return sorted({_text(value) for value in _values(values) if _text(value)})


def _union_text(records: list[dict[str, Any]], key: str) -> list[str]:
    values: set[str] = set()
    for record in records:
        values.update(_sorted_text(record.get(key)))
    return sorted(values)


def _candidate_id(occurrence_id: str) -> str:
    digest = hashlib.sha1(occurrence_id.encode("utf-8")).hexdigest()[:24]
    return f"ocp_{digest}"


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_number_list(value: Any) -> list[float]:
    result: set[float] = set()
    for item in _values(value):
        if isinstance(item, bool):
            continue
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            result.add(parsed)
    return sorted(result)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _horizon_contract(consequence_payload: dict[str, Any]) -> dict[str, Any]:
    windows = _positive_number_list(consequence_payload.get("window_seconds"))
    max_layers = _positive_int(consequence_payload.get("max_follow_up_time_layers"))
    declared = bool(windows and max_layers)
    return {
        "horizon_definition_state": "DECLARED_SOURCE_HORIZON" if declared else "HORIZON_UNSPECIFIED",
        "horizon_basis": HORIZON_BASIS if declared else None,
        "window_seconds": windows,
        "maximum_window_seconds": max(windows) if windows else None,
        "max_follow_up_time_layers": max_layers,
        "same_episode_terminal_horizon_assessed": False,
        "right_censoring_assessed": False,
        "horizon_is_construct_definition": True,
        "fixed_window_is_terminal_outcome_truth": False,
    }


def _boundary_review_reasons(members: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    reasons: set[str] = set()
    declared_count = 0
    for row in members:
        declared_count += int(row.get("review_debt_count") or 0)
        for ref in _values(row.get("review_debt_refs")):
            if not isinstance(ref, dict):
                continue
            reason = _text(ref.get("reason"))
            if reason:
                reasons.add(reason)
    if declared_count and not reasons:
        reasons.add("UNSPECIFIED_REVIEW_DEBT")
    blocking = sorted(reasons - NONBLOCKING_ADMIN_BOUNDARY_REVIEW_REASONS)
    return sorted(reasons), blocking


def _administrative_end_boundary_index(
    episode_payload: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], bool, list[str]]:
    """Index explicit observation-ending administrative boundaries by period.

    Only HALF/FULL-TIME navigation boundaries are consumed. They define an observation
    limit for fixed-horizon follow-up search; they never become football actions, phases,
    possession truth, sequence truth, or an ordering device for same-time actions.

    A visible-field serialization discrepancy may remain as review debt while the grouped
    administrative type/time still converges. That debt is not treated as independent
    corroboration and does not by itself invalidate the observation boundary.
    """
    if not isinstance(episode_payload, dict):
        return {}, False, []
    rows = episode_payload.get("administrative_boundary_candidates")
    if not isinstance(rows, list):
        return {}, False, ["administrative_boundary_candidates_missing_or_invalid"]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reviews: list[str] = []
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            reviews.append(f"administrative_boundary_record_invalid:{position}")
            continue
        boundary_type = _text(row.get("boundary_type"))
        if boundary_type not in END_BOUNDARY_TYPES:
            continue
        period = _text(row.get("period_candidate"))
        second = _number(row.get("second_candidate"))
        boundary_ref = _text(row.get("administrative_boundary_candidate_id"))
        if not period or second is None or not boundary_ref:
            reviews.append(f"administrative_end_boundary_semantics_incomplete:{position}")
            continue
        grouped[period].append(row)

    if not grouped:
        return {}, False, sorted(set(reviews + ["administrative_end_boundary_not_visible"]))

    index: dict[str, dict[str, Any]] = {}
    for period, members in sorted(grouped.items()):
        seconds = sorted({_number(row.get("second_candidate")) for row in members})
        seconds = [value for value in seconds if value is not None]
        if len(seconds) != 1:
            reviews.append(f"administrative_end_boundary_time_conflict:{period}")
            continue
        boundary_types = sorted({_text(row.get("boundary_type")) for row in members if _text(row.get("boundary_type"))})
        boundary_refs = sorted({_text(row.get("administrative_boundary_candidate_id")) for row in members if _text(row.get("administrative_boundary_candidate_id"))})
        review_debt_count = sum(int(row.get("review_debt_count") or 0) for row in members)
        review_reasons, blocking_review_reasons = _boundary_review_reasons(members)
        index[period] = {
            "boundary_second": seconds[0],
            "boundary_types": boundary_types,
            "boundary_refs": boundary_refs,
            "review_debt_count": review_debt_count,
            "review_debt_reasons": review_reasons,
            "blocking_review_debt_reasons": blocking_review_reasons,
            "serialization_review_only": bool(review_reasons) and not blocking_review_reasons,
            "same_time_visible_layer_collision": any(
                row.get("same_time_visible_layer_collision") is True for row in members
            ),
            "boundary_can_split_same_time_visible_layer": False,
            "boundary_is_football_action_truth": False,
            "boundary_is_phase_truth": False,
            "reflection_rows_are_independent_evidence_votes": False,
        }
        if blocking_review_reasons:
            reviews.append(f"administrative_end_boundary_blocking_review_debt:{period}")

    return index, bool(index), sorted(set(reviews))


def _right_censoring_profile(
    consequences: list[dict[str, Any]],
    trace_by_id: dict[str, dict[str, Any]],
    maximum_window_seconds: float | None,
    boundary_by_period: dict[str, dict[str, Any]],
    boundary_surface_present: bool,
) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "right_censoring_status": "CENSORING_NOT_ASSESSED",
        "right_censoring_assessed": False,
        "right_censored": False,
        "declared_horizon_fully_observable": False,
        "seconds_to_observation_boundary_min": None,
        "seconds_to_observation_boundary_max": None,
        "observation_boundary_refs": [],
        "observation_boundary_types": [],
        "observation_boundary_review_reasons": [],
        "administrative_boundary_is_football_action_truth": False,
        "administrative_boundary_is_phase_truth": False,
        "administrative_boundary_orders_same_time_action": False,
        "administrative_boundary_reflections_are_independent_evidence_votes": False,
    }
    if not consequences:
        profile["right_censoring_status"] = "CENSORING_UNRESOLVED_SOURCE_COVERAGE"
        return profile
    if maximum_window_seconds is None:
        profile["right_censoring_status"] = "CENSORING_UNRESOLVED_HORIZON_UNSPECIFIED"
        return profile
    if not boundary_surface_present:
        return profile

    admitted_after = _union_text(consequences, "admitted_after_follow_up_trace_ids")
    visible_followup = _union_text(consequences, "visible_follow_up_trace_ids")
    if admitted_after:
        profile["right_censoring_status"] = "NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"
        profile["right_censoring_assessed"] = True
        return profile
    if visible_followup:
        profile["right_censoring_status"] = "CENSORING_NOT_CAUSE_VISIBLE_FOLLOWUP_ORDER_UNRESOLVED"
        profile["right_censoring_assessed"] = True
        return profile
    if any(
        row.get("terminal_outcome_support_visible") is True
        or row.get("derived_consequence_support_visible") is True
        for row in consequences
    ):
        profile["right_censoring_status"] = "CENSORING_NOT_CAUSE_ANCHOR_SUPPORT_VISIBLE"
        profile["right_censoring_assessed"] = True
        return profile

    anchors: list[tuple[str, float]] = []
    for consequence in consequences:
        anchor_id = _text(consequence.get("anchor_trackable_action_trace_candidate_id"))
        anchor = trace_by_id.get(anchor_id)
        period = _text((anchor or {}).get("period_candidate"))
        start = _number((anchor or {}).get("start_candidate"))
        if not anchor_id or anchor is None or not period or start is None:
            profile["right_censoring_status"] = "CENSORING_UNRESOLVED_ANCHOR_TIME_OR_PERIOD"
            return profile
        anchors.append((period, start))
    if not anchors:
        profile["right_censoring_status"] = "CENSORING_UNRESOLVED_ANCHOR_MISSING"
        return profile

    remaining: list[float] = []
    boundary_refs: set[str] = set()
    boundary_types: set[str] = set()
    review_reasons: set[str] = set()
    for period, start in anchors:
        boundary = boundary_by_period.get(period)
        if not boundary:
            profile["right_censoring_status"] = "CENSORING_UNRESOLVED_END_BOUNDARY_MISSING"
            return profile
        blocking_review_reasons = _sorted_text(boundary.get("blocking_review_debt_reasons"))
        if blocking_review_reasons:
            profile["right_censoring_status"] = "CENSORING_UNRESOLVED_END_BOUNDARY_REVIEW_DEBT"
            profile["observation_boundary_review_reasons"] = blocking_review_reasons
            return profile
        review_reasons.update(_sorted_text(boundary.get("review_debt_reasons")))
        boundary_second = _number(boundary.get("boundary_second"))
        if boundary_second is None:
            profile["right_censoring_status"] = "CENSORING_UNRESOLVED_END_BOUNDARY_TIME"
            return profile
        delta = boundary_second - start
        if delta < 0:
            profile["right_censoring_status"] = "CENSORING_UNRESOLVED_BOUNDARY_BEFORE_ANCHOR"
            return profile
        if abs(delta) <= 1e-9:
            profile["right_censoring_status"] = "CENSORING_UNRESOLVED_SAME_TIME_ADMIN_BOUNDARY"
            return profile
        remaining.append(delta)
        boundary_refs.update(_sorted_text(boundary.get("boundary_refs")))
        boundary_types.update(_sorted_text(boundary.get("boundary_types")))

    profile["seconds_to_observation_boundary_min"] = round(min(remaining), 6)
    profile["seconds_to_observation_boundary_max"] = round(max(remaining), 6)
    profile["observation_boundary_refs"] = sorted(boundary_refs)
    profile["observation_boundary_types"] = sorted(boundary_types)
    profile["observation_boundary_review_reasons"] = sorted(review_reasons)

    complete_flags = [value >= maximum_window_seconds for value in remaining]
    if all(complete_flags):
        profile["right_censoring_status"] = "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP"
        profile["right_censoring_assessed"] = True
        profile["declared_horizon_fully_observable"] = True
    elif not any(complete_flags):
        profile["right_censoring_status"] = "RIGHT_CENSORED_BY_ADMIN_BOUNDARY"
        profile["right_censoring_assessed"] = True
        profile["right_censored"] = True
    else:
        profile["right_censoring_status"] = "CENSORING_UNRESOLVED_MIXED_PARTICIPANT_HORIZON_COVERAGE"
    return profile


def _admitted_followup_horizon_profile(
    consequences: list[dict[str, Any]],
    trace_by_id: dict[str, dict[str, Any]],
    windows: list[float],
) -> tuple[list[dict[str, Any]], str, bool]:
    """Test visible admitted-after follow-up availability across declared time horizons.

    Only follow-up traces already admitted as AFTER_CONFIRMED are eligible. Numeric time is
    used to place those admitted relations inside the declared fixed-time windows; it never
    upgrades row order, same-time order, possession, terminal outcome, or causality.
    """
    if not consequences or len(windows) < 2:
        return [], "HORIZON_SENSITIVITY_UNRESOLVED", False

    unresolved = False
    admitted_delta_by_trace_id: dict[str, float] = {}
    for consequence in consequences:
        admitted_ids = _sorted_text(consequence.get("admitted_after_follow_up_trace_ids"))
        if not admitted_ids:
            continue
        anchor_id = _text(consequence.get("anchor_trackable_action_trace_candidate_id"))
        anchor = trace_by_id.get(anchor_id)
        anchor_start = _number((anchor or {}).get("start_candidate"))
        anchor_period = _text((anchor or {}).get("period_candidate"))
        if not anchor_id or anchor is None or anchor_start is None or not anchor_period:
            unresolved = True
            continue
        for follow_id in admitted_ids:
            follow = trace_by_id.get(follow_id)
            follow_start = _number((follow or {}).get("start_candidate"))
            follow_period = _text((follow or {}).get("period_candidate"))
            if follow is None or follow_start is None or follow_period != anchor_period:
                unresolved = True
                continue
            delta = follow_start - anchor_start
            if delta <= 0:
                unresolved = True
                continue
            prior = admitted_delta_by_trace_id.get(follow_id)
            if prior is not None and abs(prior - delta) > 1e-9:
                unresolved = True
                continue
            admitted_delta_by_trace_id[follow_id] = delta

    profile = [
        {
            "window_seconds": seconds,
            "admitted_after_followup_trace_count": sum(
                delta <= seconds for delta in admitted_delta_by_trace_id.values()
            ),
            "admitted_after_followup_present": any(
                delta <= seconds for delta in admitted_delta_by_trace_id.values()
            ),
        }
        for seconds in windows
    ]
    if unresolved:
        return profile, "HORIZON_SENSITIVITY_UNRESOLVED", False
    presence = {row["admitted_after_followup_present"] for row in profile}
    state = (
        "STABLE_ACROSS_DECLARED_WINDOWS"
        if len(presence) <= 1
        else "SENSITIVE_ACROSS_DECLARED_WINDOWS"
    )
    return profile, state, True


def _followup_observation_state(
    *,
    consequence_ids: list[str],
    visible_follow_up_ids: list[str],
    admitted_after_ids: list[str],
    terminal_support: bool,
    derived_support: bool,
    censoring_status: str,
) -> tuple[str, str]:
    if not consequence_ids:
        return "FOLLOWUP_UNRESOLVED", "SOURCE_COVERAGE_INSUFFICIENT"
    if admitted_after_ids:
        return "VISIBLE_FOLLOWUP", "ORDER_ADMITTED_WITHIN_DECLARED_SOURCE_HORIZON"
    if visible_follow_up_ids:
        return "FOLLOWUP_UNRESOLVED", "ORDER_INDETERMINATE"
    if terminal_support or derived_support:
        return "FOLLOWUP_UNRESOLVED", "SUPPORT_VISIBLE_FOLLOWUP_ACTION_NOT_ESTABLISHED"
    if censoring_status == "RIGHT_CENSORED_BY_ADMIN_BOUNDARY":
        return "FOLLOWUP_CENSORED", "RIGHT_CENSORED"
    if censoring_status == "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP":
        return "NO_VISIBLE_FOLLOWUP", "COMPLETE_TO_HORIZON"
    if censoring_status == "CENSORING_NOT_ASSESSED":
        return "FOLLOWUP_UNRESOLVED", "CENSORING_NOT_ASSESSED"
    return "FOLLOWUP_UNRESOLVED", "CENSORING_UNRESOLVED"


def _terminal_state(terminal_support: bool) -> tuple[str, str]:
    if terminal_support:
        return "TERMINAL_SUPPORT_VISIBLE_TYPE_UNRESOLVED", "UNKNOWN"
    return "TERMINAL_STATE_UNRESOLVED", "UNKNOWN"


def _process_state(primary_candidates: list[str]) -> str:
    if any(
        candidate in {
            "SAME_TEAM_CONTINUATION_CANDIDATE",
            "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE",
        }
        for candidate in primary_candidates
    ):
        return "PROCESS_CONTINUES_VISIBLE_CANDIDATE"
    return "PROCESS_STATE_UNRESOLVED"


def build_occurrence_consequence_projection(
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
    episode_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    primary_trace_surface_present = "primary_occurrence_trace_candidates" in trace_payload
    trace_source = (
        trace_payload.get("primary_occurrence_trace_candidates")
        if primary_trace_surface_present
        else trace_payload.get("trackable_action_trace_candidates")
    )
    trace_records = [row for row in _values(trace_source) if isinstance(row, dict)]
    all_trace_records = [
        row
        for row in _values(trace_payload.get("trackable_action_trace_candidates"))
        if isinstance(row, dict)
    ]
    if not all_trace_records:
        all_trace_records = list(trace_records)
    trace_member_surface = (
        "PRIMARY_OCCURRENCE_TRACE"
        if primary_trace_surface_present
        else "LEGACY_COMPATIBILITY_FALLBACK"
    )
    consequence_records = [
        row
        for row in _values(consequence_payload.get("trackable_action_consequence_candidates"))
        if isinstance(row, dict)
    ]
    binding_surface_present = "occurrence_trace_binding_records" in trace_payload
    binding_records = [
        row
        for row in _values(trace_payload.get("occurrence_trace_binding_records"))
        if isinstance(row, dict)
    ]
    horizon = _horizon_contract(consequence_payload)
    boundary_by_period, boundary_surface_present, boundary_reviews = _administrative_end_boundary_index(
        episode_payload
    )

    binding_by_occurrence = {
        _text(row.get("action_occurrence_candidate_id")): row
        for row in binding_records
        if _text(row.get("action_occurrence_candidate_id"))
    }
    traces_by_occurrence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trace in trace_records:
        for occurrence_id in _sorted_text(trace.get("supporting_action_occurrence_candidate_ids")):
            traces_by_occurrence[occurrence_id].append(trace)

    trace_by_id: dict[str, dict[str, Any]] = {}
    duplicate_trace_ids: set[str] = set()
    for trace in all_trace_records:
        trace_id = _text(trace.get("trackable_action_trace_candidate_id"))
        if not trace_id:
            continue
        if trace_id in trace_by_id:
            duplicate_trace_ids.add(trace_id)
        else:
            trace_by_id[trace_id] = trace

    consequences_by_occurrence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    consequence_by_anchor_trace: dict[str, dict[str, Any]] = {}
    duplicate_consequence_anchor_trace_ids: set[str] = set()
    for consequence in consequence_records:
        for occurrence_id in _sorted_text(consequence.get("supporting_action_occurrence_candidate_ids")):
            consequences_by_occurrence[occurrence_id].append(consequence)
        anchor_trace_id = _text(consequence.get("anchor_trackable_action_trace_candidate_id"))
        if anchor_trace_id:
            if anchor_trace_id in consequence_by_anchor_trace:
                duplicate_consequence_anchor_trace_ids.add(anchor_trace_id)
            else:
                consequence_by_anchor_trace[anchor_trace_id] = consequence

    if binding_surface_present:
        occurrence_ids = sorted(binding_by_occurrence)
    else:
        occurrence_ids = sorted(
            set(binding_by_occurrence) | set(traces_by_occurrence) | set(consequences_by_occurrence)
        )
    authoritative_occurrence_ids = set(occurrence_ids)
    legacy_unbound_consequence_count = sum(
        1
        for consequence in consequence_records
        if not (
            set(_sorted_text(consequence.get("supporting_action_occurrence_candidate_ids")))
            & authoritative_occurrence_ids
        )
    )

    records: list[dict[str, Any]] = []
    visible_count = 0
    review_count = 0
    no_consequence_record_count = 0
    terminal_support_count = 0
    ensuing_terminal_support_count = 0
    ensuing_derived_support_count = 0
    horizon_sensitivity_tested_count = 0
    horizon_sensitive_count = 0
    horizon_sensitivity_unresolved_count = 0
    censoring_eligible_count = 0
    censoring_assessed_count = 0
    right_censored_count = 0
    complete_horizon_no_followup_count = 0
    censoring_unresolved_count = 0

    for occurrence_id in occurrence_ids:
        binding = binding_by_occurrence.get(occurrence_id, {})
        traces = traces_by_occurrence.get(occurrence_id, [])
        consequences = consequences_by_occurrence.get(occurrence_id, [])

        trace_ids = sorted(
            {
                _text(row.get("trackable_action_trace_candidate_id"))
                for row in traces
                if _text(row.get("trackable_action_trace_candidate_id"))
            }
        )
        consequence_ids = sorted(
            {
                _text(row.get("trackable_action_consequence_candidate_id"))
                for row in consequences
                if _text(row.get("trackable_action_consequence_candidate_id"))
            }
        )
        visible_follow_up_ids = _union_text(consequences, "visible_follow_up_trace_ids")
        admitted_after_ids = _union_text(consequences, "admitted_after_follow_up_trace_ids")
        consequence_signals = _union_text(consequences, "consequence_signal_candidates")
        primary_candidates = sorted(
            {
                _text(row.get("primary_consequence_candidate"))
                for row in consequences
                if _text(row.get("primary_consequence_candidate"))
            }
        )
        ensuing_terminal_support_trace_ids = sorted(
            trace_id
            for trace_id in admitted_after_ids
            if consequence_by_anchor_trace.get(trace_id, {}).get("terminal_outcome_support_visible") is True
        )
        ensuing_derived_support_trace_ids = sorted(
            trace_id
            for trace_id in admitted_after_ids
            if consequence_by_anchor_trace.get(trace_id, {}).get("derived_consequence_support_visible") is True
        )
        ensuing_terminal_support_visible = bool(ensuing_terminal_support_trace_ids)
        ensuing_derived_support_visible = bool(ensuing_derived_support_trace_ids)
        censoring = _right_censoring_profile(
            consequences,
            trace_by_id,
            horizon.get("maximum_window_seconds"),
            boundary_by_period,
            boundary_surface_present,
        )
        horizon_profile, horizon_sensitivity_state, horizon_sensitivity_tested = (
            _admitted_followup_horizon_profile(
                consequences,
                trace_by_id,
                horizon.get("window_seconds") or [],
            )
        )
        no_future_observation = not (
            admitted_after_ids
            or visible_follow_up_ids
            or any(row.get("terminal_outcome_support_visible") is True for row in consequences)
            or any(row.get("derived_consequence_support_visible") is True for row in consequences)
        )
        if no_future_observation:
            if censoring.get("right_censoring_status") == "RIGHT_CENSORED_BY_ADMIN_BOUNDARY":
                horizon_sensitivity_state = "HORIZON_SENSITIVITY_CENSORED"
                horizon_sensitivity_tested = False
            elif censoring.get("right_censoring_status") != "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP":
                horizon_sensitivity_state = "HORIZON_SENSITIVITY_UNRESOLVED_BY_CENSORING"
                horizon_sensitivity_tested = False
        horizon_sensitive = horizon_sensitivity_state == "SENSITIVE_ACROSS_DECLARED_WINDOWS"

        action_families: set[str] = set()
        actor_ids: set[str] = set()
        team_ids: set[str] = set()
        periods: set[str] = set()
        starts: set[str] = set()
        ends: set[str] = set()
        source_roles: set[str] = set()
        for trace in traces:
            action_families.update(_sorted_text(trace.get("action_family_candidates")))
            if _text(trace.get("actor_identity_candidate_id")):
                actor_ids.add(_text(trace.get("actor_identity_candidate_id")))
            if _text(trace.get("team_identity_candidate_id")):
                team_ids.add(_text(trace.get("team_identity_candidate_id")))
            if _text(trace.get("period_candidate")):
                periods.add(_text(trace.get("period_candidate")))
            if _text(trace.get("start_candidate")):
                starts.add(_text(trace.get("start_candidate")))
            if _text(trace.get("end_candidate")):
                ends.add(_text(trace.get("end_candidate")))
            if _text(trace.get("source_role")):
                source_roles.add(_text(trace.get("source_role")))

        terminal_support = any(row.get("terminal_outcome_support_visible") is True for row in consequences)
        derived_support = any(row.get("derived_consequence_support_visible") is True for row in consequences)
        visible = bool(visible_follow_up_ids or terminal_support or derived_support)
        any_review = any(_text(row.get("record_status")).upper() == "REVIEW_REQUIRED" for row in consequences)
        missing_trace = not trace_ids
        missing_consequence = not consequence_ids
        record_status = "REVIEW_REQUIRED" if (any_review or missing_trace or missing_consequence) else "PASS"
        followup_status, observation_status = _followup_observation_state(
            consequence_ids=consequence_ids,
            visible_follow_up_ids=visible_follow_up_ids,
            admitted_after_ids=admitted_after_ids,
            terminal_support=terminal_support,
            derived_support=derived_support,
            censoring_status=_text(censoring.get("right_censoring_status")),
        )
        terminal_status, terminal_type = _terminal_state(terminal_support)
        process_status = _process_state(primary_candidates)

        if visible:
            visible_count += 1
        if record_status == "REVIEW_REQUIRED":
            review_count += 1
        if missing_consequence:
            no_consequence_record_count += 1
        else:
            censoring_eligible_count += 1
            if censoring.get("right_censoring_assessed") is True:
                censoring_assessed_count += 1
            else:
                censoring_unresolved_count += 1
        if terminal_support:
            terminal_support_count += 1
        if ensuing_terminal_support_visible:
            ensuing_terminal_support_count += 1
        if ensuing_derived_support_visible:
            ensuing_derived_support_count += 1
        if horizon_sensitivity_tested:
            horizon_sensitivity_tested_count += 1
        else:
            horizon_sensitivity_unresolved_count += 1
        if horizon_sensitive:
            horizon_sensitive_count += 1
        if censoring.get("right_censored") is True:
            right_censored_count += 1
        if censoring.get("right_censoring_status") == "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP":
            complete_horizon_no_followup_count += 1

        records.append(
            {
                "occurrence_consequence_projection_id": _candidate_id(occurrence_id),
                "action_occurrence_candidate_id": occurrence_id,
                "occurrence_topology": _text(binding.get("occurrence_topology")) or "UNRESOLVED",
                "required_participant_scope": _text(binding.get("required_participant_scope")) or "UNRESOLVED",
                "binding_state": _text(binding.get("binding_state")) or "UNRESOLVED",
                "supporting_trackable_action_trace_candidate_ids": trace_ids,
                "supporting_consequence_candidate_ids": consequence_ids,
                "supporting_trace_candidate_count": len(trace_ids),
                "supporting_consequence_candidate_count": len(consequence_ids),
                "actor_identity_candidate_ids": sorted(actor_ids),
                "team_identity_candidate_ids": sorted(team_ids),
                "source_roles": sorted(source_roles),
                "action_family_candidates": sorted(action_families),
                "period_candidates": sorted(periods),
                "start_candidates": sorted(starts),
                "end_candidates": sorted(ends),
                "visible_follow_up_trace_ids": visible_follow_up_ids,
                "admitted_after_follow_up_trace_ids": admitted_after_ids,
                "admitted_followup_horizon_profile": horizon_profile,
                "admitted_followup_horizon_sensitivity_state": horizon_sensitivity_state,
                "admitted_followup_horizon_sensitivity_tested": horizon_sensitivity_tested,
                "admitted_followup_horizon_sensitive": horizon_sensitive,
                "ensuing_terminal_support_trace_ids": ensuing_terminal_support_trace_ids,
                "ensuing_derived_consequence_support_trace_ids": ensuing_derived_support_trace_ids,
                "ensuing_terminal_support_visible": ensuing_terminal_support_visible,
                "ensuing_derived_consequence_support_visible": ensuing_derived_support_visible,
                "ensuing_support_relation_basis": "ADMITTED_AFTER_FOLLOW_UP_TRACE_ONLY",
                "followup_observation_status": followup_status,
                "process_continuation_status": process_status,
                "terminal_status": terminal_status,
                "terminal_type": terminal_type,
                "observation_status": observation_status,
                "right_censoring_status": censoring.get("right_censoring_status"),
                "right_censoring_assessed": censoring.get("right_censoring_assessed") is True,
                "right_censored": censoring.get("right_censored") is True,
                "declared_horizon_fully_observable": censoring.get("declared_horizon_fully_observable") is True,
                "seconds_to_observation_boundary_min": censoring.get("seconds_to_observation_boundary_min"),
                "seconds_to_observation_boundary_max": censoring.get("seconds_to_observation_boundary_max"),
                "observation_boundary_refs": censoring.get("observation_boundary_refs") or [],
                "observation_boundary_types": censoring.get("observation_boundary_types") or [],
                "observation_boundary_review_reasons": censoring.get("observation_boundary_review_reasons") or [],
                "horizon_definition_state": horizon["horizon_definition_state"],
                "horizon_basis": horizon["horizon_basis"],
                "maximum_window_seconds": horizon["maximum_window_seconds"],
                "max_follow_up_time_layers": horizon["max_follow_up_time_layers"],
                "consequence_signal_candidates": consequence_signals,
                "primary_consequence_candidates": primary_candidates,
                "terminal_outcome_support_visible": terminal_support,
                "derived_consequence_support_visible": derived_support,
                "visible_consequence_support": visible,
                "record_status": record_status,
                "no_visible_followup_is_failure": False,
                "followup_is_terminal_outcome_truth": False,
                "terminal_support_is_terminal_type_truth": False,
                "admitted_followup_horizon_profile_is_terminal_outcome_truth": False,
                "admitted_followup_horizon_profile_is_causal_truth": False,
                "ensuing_terminal_support_is_causal_truth": False,
                "ensuing_terminal_support_is_anchor_terminal_state_truth": False,
                "observation_status_is_outcome_polarity_truth": False,
                "administrative_boundary_is_football_action_truth": False,
                "administrative_boundary_is_phase_truth": False,
                "administrative_boundary_orders_same_time_action": False,
                "administrative_boundary_reflections_are_independent_evidence_votes": False,
                "competing_terminal_outcomes_assessed": False,
                "projection_is_action_identity_truth": False,
                "projection_is_sequence_truth": False,
                "projection_is_possession_truth": False,
                "projection_is_causal_truth": False,
                "same_timestamp_is_total_order": False,
                "source_row_order_is_temporal_truth": False,
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            }
        )

    expected_occurrence_count = int(trace_payload.get("current_occurrence_candidate_count") or 0)
    projection_count = len(records)
    hard_blocks: list[str] = []
    review_hits: list[str] = list(boundary_reviews)
    if expected_occurrence_count and projection_count != expected_occurrence_count:
        hard_blocks.append("occurrence_projection_count_mismatch")
    if duplicate_trace_ids:
        hard_blocks.append("duplicate_trace_id_in_horizon_index")
    if duplicate_consequence_anchor_trace_ids:
        hard_blocks.append("duplicate_consequence_anchor_trace_id")
    if episode_payload is not None:
        if episode_payload.get("canonical_event_count") not in {None, "UNKNOWN"}:
            hard_blocks.append("episode_boundary_surface_canonical_event_count_claimed")
        if episode_payload.get("true_action_count") not in {None, "UNKNOWN"}:
            hard_blocks.append("episode_boundary_surface_true_action_count_claimed")
        if episode_payload.get("production_release") is True:
            hard_blocks.append("episode_boundary_surface_production_release_claimed")
    if review_count:
        review_hits.append("occurrence_consequence_projection_review_required")
    if no_consequence_record_count:
        review_hits.append("occurrence_without_consequence_record_present")
    if horizon["horizon_definition_state"] == "HORIZON_UNSPECIFIED":
        review_hits.append("consequence_horizon_unspecified")
    if horizon_sensitive_count:
        review_hits.append("admitted_followup_horizon_sensitive_occurrence_present")
    if horizon_sensitivity_unresolved_count:
        review_hits.append("admitted_followup_horizon_sensitivity_unresolved")
    if boundary_surface_present and censoring_unresolved_count:
        review_hits.append("right_censoring_unresolved_occurrence_present")
    if episode_payload is not None and not boundary_surface_present:
        review_hits.append("administrative_end_boundary_surface_not_admitted")

    followup_counts = Counter(row.get("followup_observation_status") for row in records)
    process_counts = Counter(row.get("process_continuation_status") for row in records)
    terminal_counts = Counter(row.get("terminal_status") for row in records)
    observation_counts = Counter(row.get("observation_status") for row in records)
    horizon_sensitivity_counts = Counter(
        row.get("admitted_followup_horizon_sensitivity_state") for row in records
    )
    censoring_counts = Counter(row.get("right_censoring_status") for row in records)

    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "PASS")
    if hard_blocks:
        records = []
        projection_count = 0
        visible_count = 0
        review_count = 0
        no_consequence_record_count = 0
        terminal_support_count = 0
        ensuing_terminal_support_count = 0
        ensuing_derived_support_count = 0
        horizon_sensitivity_tested_count = 0
        horizon_sensitive_count = 0
        horizon_sensitivity_unresolved_count = 0
        censoring_eligible_count = 0
        censoring_assessed_count = 0
        right_censored_count = 0
        complete_horizon_no_followup_count = 0
        censoring_unresolved_count = 0
        followup_counts = Counter()
        process_counts = Counter()
        terminal_counts = Counter()
        observation_counts = Counter()
        horizon_sensitivity_counts = Counter()
        censoring_counts = Counter()

    all_occurrences_horizon_tested = bool(projection_count) and (
        horizon_sensitivity_tested_count == projection_count
    )
    right_censoring_assessed = bool(censoring_eligible_count) and (
        censoring_assessed_count == censoring_eligible_count
    )
    horizon["right_censoring_assessed"] = right_censoring_assessed

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "source_trace_status": trace_payload.get("status"),
        "source_consequence_status": consequence_payload.get("status"),
        "source_episode_boundary_status": episode_payload.get("status") if isinstance(episode_payload, dict) else None,
        "source_trace_member_surface": trace_member_surface,
        "source_primary_occurrence_trace_candidate_count": len(trace_records),
        "source_legacy_trace_candidate_count": trace_payload.get("trackable_action_trace_candidate_count", 0),
        "source_legacy_consequence_candidate_count": consequence_payload.get("trackable_action_consequence_candidate_count", 0),
        "source_action_occurrence_candidate_count": expected_occurrence_count,
        "occurrence_consequence_projection_count": projection_count,
        "occurrence_with_visible_consequence_support_count": visible_count,
        "review_required_occurrence_projection_count": review_count,
        "occurrence_without_consequence_record_count": no_consequence_record_count,
        "occurrence_with_terminal_outcome_support_count": terminal_support_count,
        "occurrence_with_ensuing_terminal_support_count": ensuing_terminal_support_count,
        "occurrence_with_ensuing_derived_consequence_support_count": ensuing_derived_support_count,
        "admitted_followup_horizon_sensitivity_tested_occurrence_count": horizon_sensitivity_tested_count,
        "admitted_followup_horizon_sensitive_occurrence_count": horizon_sensitive_count,
        "admitted_followup_horizon_sensitivity_unresolved_occurrence_count": horizon_sensitivity_unresolved_count,
        "admitted_followup_horizon_sensitivity_state_counts": dict(sorted(horizon_sensitivity_counts.items())),
        "admitted_followup_horizon_sensitivity_tested": all_occurrences_horizon_tested,
        "right_censoring_eligible_occurrence_count": censoring_eligible_count,
        "right_censoring_assessed_occurrence_count": censoring_assessed_count,
        "right_censored_occurrence_count": right_censored_count,
        "complete_to_declared_horizon_no_admitted_followup_count": complete_horizon_no_followup_count,
        "right_censoring_unresolved_occurrence_count": censoring_unresolved_count,
        "right_censoring_status_counts": dict(sorted(censoring_counts.items())),
        "administrative_end_boundary_surface_present": boundary_surface_present,
        "administrative_end_boundary_period_count": len(boundary_by_period),
        "administrative_end_boundary_reviews": boundary_reviews,
        "legacy_unbound_consequence_candidate_count": legacy_unbound_consequence_count,
        "followup_observation_status_counts": dict(sorted(followup_counts.items())),
        "process_continuation_status_counts": dict(sorted(process_counts.items())),
        "terminal_status_counts": dict(sorted(terminal_counts.items())),
        "observation_status_counts": dict(sorted(observation_counts.items())),
        "source_consequence_horizon": horizon,
        "occurrence_consequence_projections": records,
        "occurrence_binding_records_are_primary_member_authority": binding_surface_present,
        "legacy_trace_records_are_support_evidence_not_action_universe": True,
        "legacy_consequence_records_cannot_create_occurrence_members": binding_surface_present,
        "occurrence_projection_is_primary_action_member_candidate_surface": True,
        "ensuing_support_uses_admitted_after_only": True,
        "admitted_followup_horizon_profile_uses_after_confirmed_only": True,
        "admitted_followup_horizon_sensitivity_is_terminal_outcome_truth": False,
        "no_visible_followup_is_failure": False,
        "followup_is_terminal_outcome_truth": False,
        "terminal_support_is_terminal_type_truth": False,
        "ensuing_terminal_support_is_causal_truth": False,
        "ensuing_terminal_support_is_anchor_terminal_state_truth": False,
        "right_censoring_assessed": right_censoring_assessed,
        "administrative_boundary_is_football_action_truth": False,
        "administrative_boundary_is_phase_truth": False,
        "administrative_boundary_orders_same_time_action": False,
        "administrative_boundary_reflections_are_independent_evidence_votes": False,
        "competing_terminal_outcomes_assessed": False,
        "outcome_polarity_emitted": False,
        "projection_is_action_identity_truth": False,
        "projection_is_sequence_truth": False,
        "projection_is_possession_truth": False,
        "projection_is_causal_truth": False,
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(
        "\n".join(
            [
                "HPFA OCCURRENCE CONSEQUENCE PROJECTION V1",
                f"status={payload.get('status')}",
                f"source_action_occurrence_candidate_count={payload.get('source_action_occurrence_candidate_count', 0)}",
                f"occurrence_consequence_projection_count={payload.get('occurrence_consequence_projection_count', 0)}",
                f"occurrence_with_visible_consequence_support_count={payload.get('occurrence_with_visible_consequence_support_count', 0)}",
                f"occurrence_with_ensuing_terminal_support_count={payload.get('occurrence_with_ensuing_terminal_support_count', 0)}",
                f"occurrence_with_ensuing_derived_consequence_support_count={payload.get('occurrence_with_ensuing_derived_consequence_support_count', 0)}",
                f"admitted_followup_horizon_sensitivity_tested_occurrence_count={payload.get('admitted_followup_horizon_sensitivity_tested_occurrence_count', 0)}",
                f"admitted_followup_horizon_sensitive_occurrence_count={payload.get('admitted_followup_horizon_sensitive_occurrence_count', 0)}",
                f"admitted_followup_horizon_sensitivity_unresolved_occurrence_count={payload.get('admitted_followup_horizon_sensitivity_unresolved_occurrence_count', 0)}",
                f"admitted_followup_horizon_sensitivity_state_counts={payload.get('admitted_followup_horizon_sensitivity_state_counts', {})}",
                f"right_censoring_assessed={payload.get('right_censoring_assessed')}",
                f"right_censoring_eligible_occurrence_count={payload.get('right_censoring_eligible_occurrence_count', 0)}",
                f"right_censoring_assessed_occurrence_count={payload.get('right_censoring_assessed_occurrence_count', 0)}",
                f"right_censored_occurrence_count={payload.get('right_censored_occurrence_count', 0)}",
                f"complete_to_declared_horizon_no_admitted_followup_count={payload.get('complete_to_declared_horizon_no_admitted_followup_count', 0)}",
                f"right_censoring_unresolved_occurrence_count={payload.get('right_censoring_unresolved_occurrence_count', 0)}",
                f"right_censoring_status_counts={payload.get('right_censoring_status_counts', {})}",
                f"review_required_occurrence_projection_count={payload.get('review_required_occurrence_projection_count', 0)}",
                f"followup_observation_status_counts={payload.get('followup_observation_status_counts', {})}",
                f"process_continuation_status_counts={payload.get('process_continuation_status_counts', {})}",
                f"terminal_status_counts={payload.get('terminal_status_counts', {})}",
                f"observation_status_counts={payload.get('observation_status_counts', {})}",
                f"source_consequence_horizon={payload.get('source_consequence_horizon', {})}",
                f"source_trace_member_surface={payload.get('source_trace_member_surface')}",
                f"source_primary_occurrence_trace_candidate_count={payload.get('source_primary_occurrence_trace_candidate_count', 0)}",
                f"source_legacy_trace_candidate_count={payload.get('source_legacy_trace_candidate_count', 0)}",
                f"source_legacy_consequence_candidate_count={payload.get('source_legacy_consequence_candidate_count', 0)}",
                f"legacy_unbound_consequence_candidate_count={payload.get('legacy_unbound_consequence_candidate_count', 0)}",
                "legacy_trace_records_are_support_evidence_not_action_universe=true",
                "ensuing_support_uses_admitted_after_only=true",
                "admitted_followup_horizon_profile_uses_after_confirmed_only=true",
                "admitted_followup_horizon_sensitivity_is_terminal_outcome_truth=false",
                "no_visible_followup_is_failure=false",
                "followup_is_terminal_outcome_truth=false",
                "ensuing_terminal_support_is_causal_truth=false",
                "administrative_boundary_is_football_action_truth=false",
                "administrative_boundary_is_phase_truth=false",
                "administrative_boundary_orders_same_time_action=false",
                "administrative_boundary_reflections_are_independent_evidence_votes=false",
                "competing_terminal_outcomes_assessed=false",
                "projection_is_causal_truth=false",
                "canonical_event_count=UNKNOWN",
                "true_action_count=UNKNOWN",
                "production_release=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"json": json_path, "txt": txt_path}
