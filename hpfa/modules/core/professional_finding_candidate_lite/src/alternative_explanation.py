from __future__ import annotations

from typing import Any

FINDING_MODULE_ID = "professional_finding_candidate_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def _signal_state(state: Any, positive_tokens: tuple[str, ...]) -> bool:
    text = _status(state)
    return any(token in text for token in positive_tokens)


def attach_alternative_explanation_evaluation(finding_payload: dict[str, Any]) -> dict[str, Any]:
    """Turn existing challenge results into explicit alternative-explanation candidates.

    This is a dependent projection over already-produced event-only challenge evidence.
    It does not discover a causal mechanism and never treats absence of an alternative
    signal as confirmation of the primary explanation. Video/tracking alternatives and
    unresolved dependency/reflection questions remain outside the current scope.
    """
    result = dict(finding_payload)
    rows = [
        dict(row)
        for row in (finding_payload.get("professional_finding_candidates") or [])
        if isinstance(row, dict)
    ]
    result["professional_finding_candidates"] = rows

    blocks: list[str] = []
    if finding_payload.get("module_id") != FINDING_MODULE_ID:
        blocks.append("finding_module_id_mismatch")
    if finding_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("finding_canonical_event_count_claimed")
    if finding_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("finding_true_action_count_claimed")
    if finding_payload.get("production_release") is True:
        blocks.append("finding_production_release_claimed")
    if _status(finding_payload.get("status")) == "FAIL_CLOSED" or finding_payload.get("hard_block_hits"):
        blocks.append("finding_input_fail_closed")

    if blocks:
        result["status"] = "FAIL_CLOSED"
        result["alternative_explanation_status"] = "FAIL_CLOSED"
        result["hard_block_hits"] = sorted(set((finding_payload.get("hard_block_hits") or []) + blocks))
        result["claim_output_allowed_count"] = 0
        result["professional_finding_emitted_count"] = 0
        result["canonical_event_count"] = CANONICAL_EVENT_COUNT
        result["true_action_count"] = TRUE_ACTION_COUNT
        result["production_release"] = False
        return result

    complete_scope = 0
    partial_scope = 0
    signal_present = 0

    for row in rows:
        challenge = dict(row.get("finding_challenge_packet") or {})
        visible_alternatives: list[dict[str, Any]] = []
        unavailable_families: list[str] = []

        player = challenge.get("player_concentration")
        if isinstance(player, dict) and _clean(player.get("state")):
            if _signal_state(player.get("state"), ("RISK", "OUTLIER", "CONCENTRATION_PRESENT")):
                visible_alternatives.append({
                    "type": "PLAYER_CONCENTRATION",
                    "evidence_state_candidate": player.get("state"),
                    "safe_meaning": "The visible repeat may be concentrated around one anchor actor rather than representing a broad team process.",
                })
        else:
            unavailable_families.append("PLAYER_CONCENTRATION")

        segment = challenge.get("segment_only")
        if isinstance(segment, dict) and _clean(segment.get("state")):
            if _signal_state(segment.get("state"), ("RISK_PRESENT", "SEGMENT_ONLY")):
                visible_alternatives.append({
                    "type": "SEGMENT_CONCENTRATION",
                    "evidence_state_candidate": segment.get("state"),
                    "safe_meaning": "The repeat may be local to one admitted episode scope rather than distributed through the match.",
                })
        else:
            unavailable_families.append("SEGMENT_CONCENTRATION")

        opponent = challenge.get("opponent_symmetry")
        if isinstance(opponent, dict) and _clean(opponent.get("state")):
            if _signal_state(opponent.get("state"), ("SYMMETRY", "MIRROR", "PRESENT")) and not _signal_state(
                opponent.get("state"), ("NO_", "ABSENT", "NOT_PRESENT")
            ):
                visible_alternatives.append({
                    "type": "OPPONENT_SYMMETRY",
                    "evidence_state_candidate": opponent.get("state"),
                    "safe_meaning": "A similar visible process on the opponent side may weaken a one-team-specific explanation.",
                })
        else:
            unavailable_families.append("OPPONENT_SYMMETRY")

        trace_dependency = challenge.get("trace_dependency")
        if isinstance(trace_dependency, dict) and _clean(trace_dependency.get("state")):
            ratio = _number(trace_dependency.get("trace_membership_uniqueness_ratio_candidate"))
            if ratio is not None and ratio < 1.0:
                visible_alternatives.append({
                    "type": "TRACE_DEPENDENCY",
                    "trace_membership_uniqueness_ratio_candidate": ratio,
                    "safe_meaning": "Some nominal support reuses trace membership, so evidence volume may overstate distinct support.",
                })
        else:
            unavailable_families.append("TRACE_DEPENDENCY")

        context = challenge.get("visible_episode_context_contrast")
        if isinstance(context, dict) and _clean(context.get("state_candidate")):
            if context.get("state_candidate") == "VISIBLE_EPISODE_CONTEXT_VARIATION_ACROSS_OUTCOMES_CANDIDATE":
                visible_alternatives.append({
                    "type": "CONTEXT_DEPENDENCE",
                    "evidence_state_candidate": context.get("state_candidate"),
                    "safe_meaning": "Different visible episode contexts accompany different outcomes, so context dependence remains a plausible explanation.",
                })
        else:
            unavailable_families.append("CONTEXT_DEPENDENCE")

        threshold = challenge.get("threshold_sensitivity")
        if isinstance(threshold, dict) and _clean(threshold.get("state_candidate")):
            if threshold.get("state_candidate") in {
                "SENSITIVE_TO_STRICTER_REPEAT_THRESHOLD",
                "FAILS_TESTED_REPEAT_THRESHOLDS",
            }:
                visible_alternatives.append({
                    "type": "THRESHOLD_SENSITIVITY",
                    "evidence_state_candidate": threshold.get("state_candidate"),
                    "safe_meaning": "The apparent recurrence is sensitive to the descriptive repeat gate and should not be treated as a stable pattern.",
                })
        else:
            unavailable_families.append("THRESHOLD_SENSITIVITY")

        failed_trace = challenge.get("failed_trace_support")
        full_trace_scope = False
        if isinstance(failed_trace, dict) and _clean(failed_trace.get("state_candidate")):
            full_trace_scope = failed_trace.get("full_occurrence_binding_scope_evaluated") is True
            if failed_trace.get("state_candidate") in {
                "NO_SUPPORTING_TRACE_LINKAGE_REVIEW_REQUIRED",
                "INCOMPLETE_CHAIN_TRACE_LINKAGE_REVIEW_REQUIRED",
                "INCOMPLETE_OCCURRENCE_TRACE_EVIDENCE_REVIEW_REQUIRED",
            }:
                visible_alternatives.append({
                    "type": "TRACE_COVERAGE_LIMITATION",
                    "evidence_state_candidate": failed_trace.get("state_candidate"),
                    "safe_meaning": "Incomplete trace visibility may explain part of the apparent support structure; missing trace is not a failed football action.",
                })
        else:
            unavailable_families.append("FAILED_TRACE_SUPPORT")

        if challenge.get("different_visible_outcome_analogue_present") is True:
            visible_alternatives.append({
                "type": "DIFFERENT_VISIBLE_OUTCOME_ANALOGUE",
                "evidence_state_candidate": "VISIBLE",
                "safe_meaning": "The same admitted process-family signature has a different visible outcome analogue, so outcome is not determined by the signature alone.",
            })

        current_scope_complete = not unavailable_families and full_trace_scope
        if current_scope_complete:
            scope_state = (
                "VISIBLE_ALTERNATIVE_EXPLANATION_SIGNAL_PRESENT"
                if visible_alternatives
                else "NO_VISIBLE_ALTERNATIVE_SIGNAL_CURRENT_SCOPE"
            )
            complete_scope += 1
        else:
            scope_state = "PARTIAL_ALTERNATIVE_EXPLANATION_COVERAGE"
            partial_scope += 1
        if visible_alternatives:
            signal_present += 1

        labels = [item["type"] for item in visible_alternatives]
        if labels:
            summary = (
                "Current event-only evidence leaves alternative explanations visible: "
                + ", ".join(labels)
                + ". These are challenge candidates, not causal mechanisms."
            )
        else:
            summary = (
                "No alternative signal is visible in the evaluated event-only challenge families at the current resolution; "
                "this does not confirm the primary explanation."
            )

        evaluation = {
            "state_candidate": scope_state,
            "visible_alternative_explanation_candidates": visible_alternatives,
            "visible_alternative_explanation_candidate_count": len(visible_alternatives),
            "unavailable_or_incomplete_event_only_families": sorted(set(unavailable_families)),
            "full_occurrence_trace_scope_evaluated": full_trace_scope,
            "safe_alternative_explanation_summary_candidate": summary,
            "scope": "CURRENT_EVENT_ONLY_VISIBLE_CHALLENGE_FAMILIES",
            "alternative_explanation_is_causal_truth": False,
            "absence_of_visible_alternative_proves_primary_explanation": False,
            "video_tracking_alternative_remains_unresolved": True,
            "duplicate_reflection_risk_remains_separate_gate": True,
        }

        evaluated_families = list(challenge.get("evaluated_falsifier_families") or [])
        marker = (
            "ALTERNATIVE_EXPLANATION_CURRENT_EVENT_ONLY_SCOPE"
            if current_scope_complete
            else "ALTERNATIVE_EXPLANATION_PARTIAL_EVENT_ONLY_SCOPE"
        )
        if marker not in evaluated_families:
            evaluated_families.append(marker)
        challenge["evaluated_falsifier_families"] = evaluated_families
        if current_scope_complete:
            challenge["pending_falsifier_families"] = [
                value
                for value in (challenge.get("pending_falsifier_families") or [])
                if value != "ALTERNATIVE_EXPLANATION"
            ]
        challenge["alternative_explanation_evaluation"] = evaluation
        challenge["alternative_explanation_search_complete_for_current_event_only_visible_scope"] = current_scope_complete
        challenge["alternative_explanation_search_complete_for_final_finding"] = False
        challenge["counter_search_complete_for_final_finding"] = False
        challenge["challenge_packet_is_final_finding"] = False
        row["finding_challenge_packet"] = challenge

        existing = [dict(item) for item in (row.get("alternative_explanations") or []) if isinstance(item, dict)]
        row["alternative_explanations"] = existing + [
            {
                "type": "CURRENT_EVENT_ONLY_ALTERNATIVE_EXPLANATION_EVALUATION",
                "state": scope_state,
                "visible_candidate_types": labels,
                "safe_summary_candidate": summary,
                "causal_truth": False,
            }
        ]
        uncertainty = dict(row.get("uncertainty") or {})
        uncertainty["alternative_explanation_search_complete_for_current_event_only_visible_scope"] = current_scope_complete
        uncertainty["alternative_explanation_search_complete_for_final_finding"] = False
        uncertainty["video_tracking_alternative_remains_unresolved"] = True
        uncertainty["duplicate_reflection_risk_remains_unresolved"] = True
        row["uncertainty"] = uncertainty
        row["claim_output_allowed"] = False
        row["professional_finding_emitted"] = False

    result["alternative_explanation_status"] = "REVIEW_REQUIRED"
    result["alternative_explanation_evaluated_candidate_count"] = len(rows)
    result["alternative_explanation_current_scope_complete_candidate_count"] = complete_scope
    result["alternative_explanation_partial_scope_candidate_count"] = partial_scope
    result["findings_with_visible_alternative_explanation_signal_count"] = signal_present
    result["alternative_explanation_search_complete_for_final_finding"] = False
    result["status"] = "REVIEW_REQUIRED"
    result["claim_output_allowed_count"] = 0
    result["professional_finding_emitted_count"] = 0
    result["canonical_event_count"] = CANONICAL_EVENT_COUNT
    result["true_action_count"] = TRUE_ACTION_COUNT
    result["production_release"] = False
    return result
