from __future__ import annotations

from collections import Counter
from typing import Any

MICRO_ACTION_DECISION_CLASS = "REFINEMENT_CANDIDATE_SINGLE_ANCHOR_OSCILLATION"
MICRO_ACTION_ROLE = "MICRO_ACTION_PHASE_OVERLAY_CANDIDATE"
SOURCE_PHASE_ROLE = "SOURCE_PHASE_SEGMENT_CANDIDATE"
OVERLAY_VERSION = "1.0.0"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _number(value: Any) -> float | None:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return None


def _zero_span(segment: dict[str, Any]) -> bool:
    start = _number(segment.get("start_time_candidate"))
    end = _number(segment.get("end_time_candidate"))
    return start is not None and end is not None and abs(start - end) <= 1e-9


def _overlay_phase(
    decision: dict[str, Any],
    segment_by_id: dict[str, dict[str, Any]],
) -> tuple[str, str, bool, list[str], str | None]:
    source_id = _clean(decision.get("source_event_derived_phase_segment_id"))
    source = segment_by_id.get(source_id)
    source_phase = _clean((source or {}).get("phase_class_candidate"))
    if decision.get("decision_class") != MICRO_ACTION_DECISION_CLASS:
        return source_phase, SOURCE_PHASE_ROLE, True, ["source_phase_segment_preserved"], None

    previous_id = _clean(decision.get("previous_phase_segment_id"))
    following_id = _clean(decision.get("following_phase_segment_id"))
    previous = segment_by_id.get(previous_id)
    following = segment_by_id.get(following_id)
    previous_phase = _clean((previous or {}).get("phase_class_candidate"))
    following_phase = _clean((following or {}).get("phase_class_candidate"))
    source_anchors = (source or {}).get("visible_anchor_count")
    flank_anchors = [
        (previous or {}).get("visible_anchor_count"),
        (following or {}).get("visible_anchor_count"),
    ]
    valid = (
        bool(source)
        and bool(previous)
        and bool(following)
        and previous_phase
        and previous_phase == following_phase
        and source_phase
        and source_phase != previous_phase
        and source_anchors == 1
        and _zero_span(source)
        and all(isinstance(value, int) and value >= 2 for value in flank_anchors)
    )
    if not valid:
        return (
            source_phase,
            SOURCE_PHASE_ROLE,
            True,
            ["micro_action_overlay_reconciliation_failed"],
            f"micro_action_overlay_reconciliation_failed:{source_id or 'NONE'}",
        )
    return (
        previous_phase,
        MICRO_ACTION_ROLE,
        False,
        [
            "same_sequence_matching_flank_phase",
            "single_visible_anchor",
            "zero_span_source_interval",
            "flanking_phases_each_supported_by_multiple_visible_anchors",
            "source_phase_segment_preserved",
        ],
        None,
    )


def apply_micro_action_phase_overlay(
    phase_payload: dict[str, Any],
    refinement_payload: dict[str, Any],
) -> dict[str, Any]:
    """Add analyst-facing effective phase fields without deleting source segments."""
    segments = phase_payload.get("event_derived_phase_segments")
    decisions = refinement_payload.get("phase_refinement_decisions")
    if not isinstance(segments, list) or not isinstance(decisions, list):
        return refinement_payload

    segment_by_id = {
        _clean(segment.get("event_derived_phase_segment_id")): segment
        for segment in segments
        if isinstance(segment, dict)
        and _clean(segment.get("event_derived_phase_segment_id"))
    }
    overlay_count = 0
    effective_counts: Counter[str] = Counter()
    hard_blocks = list(refinement_payload.get("hard_block_hits") or [])

    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        source_phase = _clean(decision.get("phase_class_candidate"))
        effective, role, display_allowed, evidence, block = _overlay_phase(
            decision, segment_by_id
        )
        decision["source_phase_class_candidate"] = source_phase
        decision["effective_phase_class_candidate"] = effective or source_phase
        decision["phase_representation_role"] = role
        decision["separate_phase_display_allowed"] = display_allowed
        decision["micro_action_overlay_candidate"] = role == MICRO_ACTION_ROLE
        decision["phase_representation_evidence"] = evidence
        if role == MICRO_ACTION_ROLE:
            overlay_count += 1
        if decision["effective_phase_class_candidate"]:
            effective_counts[decision["effective_phase_class_candidate"]] += 1
        if block:
            hard_blocks.append(block)

    refinement_payload["phase_representation_overlay_version"] = OVERLAY_VERSION
    refinement_payload["micro_action_overlay_candidate_count"] = overlay_count
    refinement_payload["separate_phase_display_suppressed_count"] = overlay_count
    refinement_payload["effective_phase_class_candidate_counts"] = dict(
        sorted(effective_counts.items())
    )
    refinement_payload["source_phase_segments_preserved"] = True
    refinement_payload["hard_block_hits"] = sorted(set(hard_blocks))
    if hard_blocks:
        refinement_payload["status"] = "FAIL_CLOSED"
        refinement_payload["module_status"] = "FAIL_CLOSED"
    return refinement_payload


def apply_effective_phase_to_context_slices(
    refinement_payload: dict[str, Any],
    context_payload: dict[str, Any],
) -> dict[str, Any]:
    """Use effective phase for analyst-facing context while retaining source phase."""
    decisions = refinement_payload.get("phase_refinement_decisions")
    slices = context_payload.get("match_context_slices")
    if not isinstance(decisions, list) or not isinstance(slices, list):
        return context_payload

    decision_by_segment = {
        _clean(item.get("source_event_derived_phase_segment_id")): item
        for item in decisions
        if isinstance(item, dict)
        and _clean(item.get("source_event_derived_phase_segment_id"))
    }
    overlay_count = 0
    effective_counts: Counter[str] = Counter()
    hard_blocks = list(context_payload.get("hard_block_hits") or [])

    for item in slices:
        if not isinstance(item, dict):
            continue
        segment_id = _clean(item.get("source_event_derived_phase_segment_id"))
        decision = decision_by_segment.get(segment_id)
        if decision is None:
            hard_blocks.append(f"effective_phase_decision_missing:{segment_id or 'NONE'}")
            continue
        source_phase = _clean(item.get("phase_class_candidate"))
        effective_phase = _clean(decision.get("effective_phase_class_candidate")) or source_phase
        role = _clean(decision.get("phase_representation_role")) or SOURCE_PHASE_ROLE
        display_allowed = decision.get("separate_phase_display_allowed") is not False
        item["source_phase_class_candidate"] = source_phase
        item["phase_class_candidate"] = effective_phase
        item["effective_phase_class_candidate"] = effective_phase
        item["phase_representation_role"] = role
        item["separate_phase_display_allowed"] = display_allowed
        item["micro_action_source_phase_excursion_candidate"] = (
            source_phase if role == MICRO_ACTION_ROLE else None
        )
        if role == MICRO_ACTION_ROLE:
            overlay_count += 1
        if effective_phase:
            effective_counts[effective_phase] += 1

    context_payload["phase_representation_overlay_version"] = OVERLAY_VERSION
    context_payload["micro_action_overlay_context_slice_count"] = overlay_count
    context_payload["separate_phase_display_suppressed_count"] = overlay_count
    context_payload["effective_phase_class_candidate_counts"] = dict(
        sorted(effective_counts.items())
    )
    context_payload["source_phase_segments_preserved"] = True
    context_payload["hard_block_hits"] = sorted(set(hard_blocks))
    if hard_blocks:
        context_payload["status"] = "FAIL_CLOSED"
        context_payload["module_status"] = "FAIL_CLOSED"
        context_payload["match_context_slices"] = []
        context_payload["match_context_slice_count"] = 0
    return context_payload
