from __future__ import annotations

from typing import Any

import user_output_bundle as _bundle

REVIEW_SAFE_TRACE_CONTEXT_STATES = {
    "TRACE_CANDIDATE_COHORT_CONTEXT_ONLY",
    "TRACE_CANDIDATE_COHORT_CONTEXT_REVIEW_BOUND",
}


def _review_safe_trace_cohort_action_family_candidate_labels(row: dict[str, Any]) -> list[str]:
    """Expose cohort navigation labels without upgrading them to action truth.

    REVIEW_BOUND means the trace cohort remains usable for analyst navigation/context,
    not that it becomes individual-action support, physical-action truth, recurrence
    support, or an independent evidence vote.
    """
    state = str(row.get("aggregate_support_trace_context_state") or "")
    if state not in REVIEW_SAFE_TRACE_CONTEXT_STATES:
        return []
    if row.get("aggregate_support_trace_relation_is_cohort_context_only") is not True:
        return []
    if row.get("aggregate_support_trace_relation_is_individual_action_support") is not False:
        return []
    if row.get("aggregate_support_trace_relation_is_physical_action_truth") is not False:
        return []
    if row.get("aggregate_support_is_independent_vote") is True:
        return []

    labels: set[str] = set()
    for trace_ref in row.get("aggregate_support_trackable_trace_candidate_refs") or []:
        if not isinstance(trace_ref, dict):
            continue
        for label in trace_ref.get("action_family_candidates") or []:
            normalized = str(label or "").strip()
            if normalized:
                labels.add(normalized)
    return sorted(labels)


# Runtime rehabilitation only: keep the canonical bundle writer and report builder,
# but replace the overly narrow helper before the runner invokes them.
_bundle._trace_cohort_action_family_candidate_labels = _review_safe_trace_cohort_action_family_candidate_labels

snapshot_output_state = _bundle.snapshot_output_state
write_standard_user_outputs = _bundle.write_standard_user_outputs
build_analyst_report = _bundle.build_analyst_report

__all__ = [
    "snapshot_output_state",
    "write_standard_user_outputs",
    "build_analyst_report",
    "REVIEW_SAFE_TRACE_CONTEXT_STATES",
    "_review_safe_trace_cohort_action_family_candidate_labels",
]
