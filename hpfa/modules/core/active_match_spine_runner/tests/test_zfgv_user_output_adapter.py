from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from zfgv_user_output_adapter import _review_safe_trace_cohort_action_family_candidate_labels


def _row(state: str) -> dict:
    return {
        "aggregate_support_trace_context_state": state,
        "aggregate_support_trace_relation_is_cohort_context_only": True,
        "aggregate_support_trace_relation_is_individual_action_support": False,
        "aggregate_support_trace_relation_is_physical_action_truth": False,
        "aggregate_support_is_independent_vote": False,
        "aggregate_support_trackable_trace_candidate_refs": [
            {"trackable_action_trace_candidate_id": "tat_generic_1", "action_family_candidates": ["PASS"]},
            {"trackable_action_trace_candidate_id": "tat_generic_2", "action_family_candidates": ["CARRY", "PASS"]},
        ],
    }


def test_review_bound_trace_cohort_remains_visible_for_navigation_only() -> None:
    labels = _review_safe_trace_cohort_action_family_candidate_labels(
        _row("TRACE_CANDIDATE_COHORT_CONTEXT_REVIEW_BOUND")
    )
    assert labels == ["CARRY", "PASS"]


def test_non_admitted_trace_state_does_not_surface_navigation_labels() -> None:
    labels = _review_safe_trace_cohort_action_family_candidate_labels(
        _row("TRACE_CANDIDATE_CONTEXT_UNAVAILABLE")
    )
    assert labels == []


def test_review_bound_trace_context_cannot_upgrade_truth_or_independence() -> None:
    row = _row("TRACE_CANDIDATE_COHORT_CONTEXT_REVIEW_BOUND")
    row["aggregate_support_trace_relation_is_individual_action_support"] = True
    assert _review_safe_trace_cohort_action_family_candidate_labels(row) == []

    row = _row("TRACE_CANDIDATE_COHORT_CONTEXT_REVIEW_BOUND")
    row["aggregate_support_trace_relation_is_physical_action_truth"] = True
    assert _review_safe_trace_cohort_action_family_candidate_labels(row) == []

    row = _row("TRACE_CANDIDATE_COHORT_CONTEXT_REVIEW_BOUND")
    row["aggregate_support_is_independent_vote"] = True
    assert _review_safe_trace_cohort_action_family_candidate_labels(row) == []
