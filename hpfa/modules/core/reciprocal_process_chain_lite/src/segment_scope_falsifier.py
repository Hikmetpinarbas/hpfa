from __future__ import annotations

from typing import Any

CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _signature_from_finding(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    raw = row.get("process_family_signature_candidate") or {}
    anchor = tuple(sorted(_clean(v) for v in (raw.get("anchor_action_families") or []) if _clean(v)))
    response = tuple(sorted(_clean(v) for v in (raw.get("response_action_families") or []) if _clean(v)))
    return anchor, response


def evaluate_segment_only_falsifier(
    finding_payload: dict[str, Any],
    profile_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build a read-only SEGMENT_ONLY evaluation surface from admitted episode spread.

    This first slice does not mutate #330 claim-safety lists. Propagation into the
    strict C4 safety envelope must be changed atomically with the validator in a
    follow-up slice. The surface therefore reports whether SEGMENT_ONLY could be
    evaluated from current episode evidence without pretending the pending family
    is already closed downstream.
    """
    rows = finding_payload.get("defeasible_process_finding_inputs") or []
    profiles = profile_payload.get("process_variant_profiles") or []
    if not isinstance(rows, list) or not isinstance(profiles, list):
        return {
            "segment_only_evaluations": [],
            "segment_only_falsifier_status": "FAIL_CLOSED",
            "segment_only_falsifier_evaluated_count": 0,
            "segment_only_risk_candidate_count": 0,
            "segment_only_multi_episode_not_observed_count": 0,
            "segment_only_pending_count": 0,
            "segment_only_safety_envelope_propagated": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        }

    index: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        signature = _signature_from_finding(profile)
        if any(signature):
            index[signature] = profile

    evaluations: list[dict[str, Any]] = []
    evaluated = 0
    risks = 0
    multi_episode_not_observed = 0
    pending = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        finding_id = _clean(row.get("defeasible_process_finding_input_id"))
        signature = _signature_from_finding(row)
        profile = index.get(signature)
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

        if can_evaluate:
            evaluated += 1
            if risk:
                risks += 1
            else:
                multi_episode_not_observed += 1
        else:
            pending += 1

        evaluations.append({
            "defeasible_process_finding_input_id": finding_id,
            "process_family_signature_candidate": row.get("process_family_signature_candidate") or {},
            "segment_only_evaluation_state": state,
            "segment_only_falsifier_evaluable_from_current_episode_scope": can_evaluate,
            "segment_only_risk_candidate": risk,
            "unique_episode_scope_count_candidate": episode_count,
            "visible_repeat_count_candidate": repeat_count,
            "incomplete_episode_binding_count": incomplete,
            "segment_only_absence_confirms_recurrence": False,
            "multi_episode_spread_is_stable_tendency_truth": False,
            "segment_only_is_tactical_truth": False,
            "safety_envelope_mutated": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        })

    return {
        "segment_only_evaluations": evaluations,
        "segment_only_falsifier_status": "EVALUATION_SURFACE_READY_REVIEW_REQUIRED" if evaluations else "NO_FINDING_INPUTS",
        "segment_only_falsifier_evaluated_count": evaluated,
        "segment_only_risk_candidate_count": risks,
        "segment_only_multi_episode_not_observed_count": multi_episode_not_observed,
        "segment_only_pending_count": pending,
        "segment_only_safety_envelope_propagated": False,
        "counter_search_complete_for_final_finding": False,
        "falsifier_coverage_state": "PARTIAL",
        "segment_only_evaluation_is_recurrence_truth": False,
        "segment_only_evaluation_is_stable_tendency_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }
