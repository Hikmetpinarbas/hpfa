from __future__ import annotations

import copy
from typing import Any

SEGMENT_FAMILY = "SEGMENT_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _signature_from_finding(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    raw = row.get("process_family_signature_candidate") or {}
    anchor = tuple(sorted(_clean(v) for v in (raw.get("anchor_action_families") or []) if _clean(v)))
    response = tuple(sorted(_clean(v) for v in (raw.get("response_action_families") or []) if _clean(v)))
    return anchor, response


def _signature_from_profile(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return _signature_from_finding(row)


def _add_once(values: list[str], value: str) -> list[str]:
    return sorted(set([*values, value]))


def _without(values: list[str], value: str) -> list[str]:
    return sorted({item for item in values if item != value})


def evaluate_segment_only_falsifier(
    finding_payload: dict[str, Any],
    profile_payload: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate the existing SEGMENT_ONLY falsifier using admitted episode spread.

    The result is a safety-envelope refinement over existing finding inputs. It does
    not create new occurrences, episodes, independent evidence, recurrence truth or
    stable-team-tendency truth.
    """
    output = copy.deepcopy(finding_payload)
    rows = output.get("defeasible_process_finding_inputs") or []
    profiles = profile_payload.get("process_variant_profiles") or []
    if not isinstance(rows, list) or not isinstance(profiles, list):
        output["segment_only_falsifier_status"] = "FAIL_CLOSED"
        output["segment_only_falsifier_evaluated_count"] = 0
        output["segment_only_risk_candidate_count"] = 0
        output["segment_only_multi_episode_not_observed_count"] = 0
        output["segment_only_pending_count"] = 0
        output["canonical_event_count"] = CANONICAL_EVENT_COUNT
        output["true_action_count"] = TRUE_ACTION_COUNT
        output["production_release"] = False
        return output

    index: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        signature = _signature_from_profile(profile)
        if any(signature):
            index[signature] = profile

    evaluated = 0
    risks = 0
    multi_episode_not_observed = 0
    pending = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        profile = index.get(_signature_from_finding(row))
        state = "SEGMENT_SCOPE_NOT_EVALUATED_NO_PROFILE"
        risk = False
        episode_count = None
        repeat_count = None
        incomplete = None
        can_evaluate = False

        if profile is not None:
            episode_count = int(profile.get("unique_episode_scope_count_candidate") or 0)
            repeat_count = int(profile.get("visible_repeat_count_candidate") or 0)
            incomplete = int(profile.get("incomplete_episode_binding_count") or 0)
            if repeat_count <= 1:
                state = "SEGMENT_SCOPE_NOT_EVALUATED_NO_REPEAT_ANALOGUE"
            elif incomplete > 0:
                state = "SEGMENT_SCOPE_NOT_EVALUATED_INCOMPLETE_EPISODE_BINDING"
            elif episode_count <= 1:
                state = "SINGLE_EPISODE_SCOPE_ONLY_CANDIDATE"
                risk = True
                can_evaluate = True
            else:
                state = "MULTI_EPISODE_SCOPE_VISIBLE_CANDIDATE"
                can_evaluate = True

        evaluated_families = list(row.get("counter_search_evaluated_families") or [])
        pending_families = list(row.get("counter_search_pending_families") or [])
        falsifier_evaluated = list(row.get("falsifier_families_evaluated") or [])
        falsifier_pending = list(row.get("falsifier_families_pending") or [])

        if can_evaluate:
            evaluated += 1
            evaluated_families = _add_once(evaluated_families, SEGMENT_FAMILY)
            pending_families = _without(pending_families, SEGMENT_FAMILY)
            falsifier_evaluated = _add_once(falsifier_evaluated, SEGMENT_FAMILY)
            falsifier_pending = _without(falsifier_pending, SEGMENT_FAMILY)
            if risk:
                risks += 1
            else:
                multi_episode_not_observed += 1
        else:
            pending += 1
            if SEGMENT_FAMILY not in pending_families:
                pending_families = _add_once(pending_families, SEGMENT_FAMILY)
            if SEGMENT_FAMILY not in falsifier_pending:
                falsifier_pending = _add_once(falsifier_pending, SEGMENT_FAMILY)

        row["counter_search_evaluated_families"] = evaluated_families
        row["counter_search_pending_families"] = pending_families
        row["falsifier_families_evaluated"] = falsifier_evaluated
        row["falsifier_families_pending"] = falsifier_pending
        row["segment_only_evaluation_state"] = state
        row["segment_only_falsifier_evaluated"] = can_evaluate
        row["segment_only_risk_candidate"] = risk
        row["segment_only_unique_episode_scope_count_candidate"] = episode_count
        row["segment_only_visible_repeat_count_candidate"] = repeat_count
        row["segment_only_incomplete_episode_binding_count"] = incomplete
        row["segment_only_absence_confirms_recurrence"] = False
        row["segment_only_multi_episode_spread_is_stable_tendency_truth"] = False
        row["segment_only_is_tactical_truth"] = False
        row["counter_search_complete_for_final_finding"] = False
        row["falsifier_coverage_state"] = "PARTIAL"
        row["finding_emitted"] = False

    output["segment_only_falsifier_status"] = "PASS_PARTIAL_FALSIFIER_COVERAGE" if rows else "NO_FINDING_INPUTS"
    output["segment_only_falsifier_evaluated_count"] = evaluated
    output["segment_only_risk_candidate_count"] = risks
    output["segment_only_multi_episode_not_observed_count"] = multi_episode_not_observed
    output["segment_only_pending_count"] = pending
    output["counter_search_complete_for_final_finding"] = False
    output["falsifier_coverage_state"] = "PARTIAL"
    output["segment_only_evaluation_is_recurrence_truth"] = False
    output["segment_only_evaluation_is_stable_tendency_truth"] = False
    output["canonical_event_count"] = CANONICAL_EVENT_COUNT
    output["true_action_count"] = TRUE_ACTION_COUNT
    output["production_release"] = False
    return output
