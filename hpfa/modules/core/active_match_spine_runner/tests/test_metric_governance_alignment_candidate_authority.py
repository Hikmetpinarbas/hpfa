from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.metric_governance_bridge import (
    _alignment_candidate_rows,
)


def _candidate(**overrides):
    row = {
        "alignment_decision": "DEFINITION_ALIGNMENT_CANDIDATE",
        "metric_value_output_allowed": False,
        "claim_allowed": False,
        "aggregate_equivalence_truth": False,
        "independent_confirmation_allowed": False,
        "measurement_invariance_truth": False,
    }
    row.update(overrides)
    return row


def test_safe_alignment_candidate_remains_candidate_only() -> None:
    rows, violations = _alignment_candidate_rows({"alignment_rows": [_candidate()]})

    assert len(rows) == 1
    assert violations == []
    assert rows[0]["alignment_decision"] == "DEFINITION_ALIGNMENT_CANDIDATE"
    assert rows[0]["metric_value_output_allowed"] is False
    assert rows[0]["claim_allowed"] is False


def test_non_candidate_rows_do_not_enter_alignment_candidate_count() -> None:
    rows, violations = _alignment_candidate_rows({
        "alignment_rows": [
            _candidate(alignment_decision="REVIEW_REQUIRED_DEFINITION_ALIGNMENT"),
            _candidate(alignment_decision="BLOCKED_INVALID_DEFINITION"),
        ]
    })

    assert rows == []
    assert violations == []


def test_candidate_metric_value_escalation_is_claim_lock_violation() -> None:
    rows, violations = _alignment_candidate_rows({
        "alignment_rows": [_candidate(metric_value_output_allowed=True)]
    })

    assert len(rows) == 1
    assert violations == ["alignment_candidate_claim_lock_invalid:0:metric_value_output_allowed"]


def test_candidate_construct_or_equivalence_escalation_is_claim_lock_violation() -> None:
    _, violations = _alignment_candidate_rows({
        "alignment_rows": [
            _candidate(claim_allowed=True),
            _candidate(aggregate_equivalence_truth=True),
            _candidate(independent_confirmation_allowed=True),
            _candidate(measurement_invariance_truth=True),
        ]
    })

    assert violations == [
        "alignment_candidate_claim_lock_invalid:0:claim_allowed",
        "alignment_candidate_claim_lock_invalid:1:aggregate_equivalence_truth",
        "alignment_candidate_claim_lock_invalid:2:independent_confirmation_allowed",
        "alignment_candidate_claim_lock_invalid:3:measurement_invariance_truth",
    ]
