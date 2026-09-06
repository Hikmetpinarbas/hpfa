from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.recurrence_null_contrast import (
    evaluate_recurrence_null_contrast,
)


def _admission(independent=3):
    return {
        "module_id": "sequence_pattern_admission_lite_v1",
        "status": "PASS",
        "sequence_pattern_admissions": [{
            "trace_family_ref": "TRACE_A",
            "eligible_trace_refs": ["TRACE_A", "TRACE_B", "TRACE_C"],
            "observed_support": 3,
            "independent_support_count": independent,
            "admission_state": "ROBUST_RECURRENT_VISIBLE_TRACE" if isinstance(independent, int) else "RECURRENT_VISIBLE_TRACE",
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _null(draws=None):
    draws = draws or [0, 1, 1, 2, 1, 0, 2, 1, 1, 0]
    return {
        "module_id": "recurrence_null_contrast_v1",
        "method": {
            "null_model_id": "within_match_independent_recurrence_shuffle",
            "null_model_version": "synthetic_v1",
            "null_mechanism": "shuffle admissible trace-family labels while preserving declared match-local constraints",
            "preserved_constraints": ["eligible_trace_count", "independence_group_cardinality"],
            "exchangeability_assumption": "trace-family labels are exchangeable under the declared null mechanism",
            "observed_labels_reused_as_null_truth": False,
        },
        "null_rows": [{
            "trace_family_ref": "TRACE_A",
            "eligible_trace_refs": ["TRACE_A", "TRACE_B", "TRACE_C"],
            "simulation_count": len(draws),
            "null_independent_recurrence_counts": draws,
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_observed_independent_recurrence_is_compared_to_explicit_null_distribution():
    result = evaluate_recurrence_null_contrast(_admission(), _null())
    row = result["rows"][0]
    assert result["status"] == "PASS"
    assert row["observed_independent_recurrence"] == 3
    assert row["state"] == "OBSERVED_ABOVE_NULL_MEDIAN"
    assert row["empirical_upper_tail_probability_uncorrected"] > 0
    assert row["observed_percentile_in_null_draws"] == 1.0


def test_null_contrast_does_not_emit_significance_or_tactical_truth():
    result = evaluate_recurrence_null_contrast(_admission(), _null())
    row = result["rows"][0]
    assert result["multiple_testing_corrected"] is False
    assert result["significance_claim_allowed"] is False
    assert result["tactical_pattern_truth_allowed"] is False
    assert row["significance_claim_allowed"] is False
    assert row["tactical_pattern_truth_allowed"] is False
    assert row["causality_allowed"] is False


def test_exact_admitted_trace_cohort_is_required():
    payload = _null()
    payload["null_rows"][0]["eligible_trace_refs"] = ["TRACE_A", "TRACE_B"]
    result = evaluate_recurrence_null_contrast(_admission(), payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "null_trace_cohort_mismatch:TRACE_A" in result["hard_block_hits"]


def test_unknown_independent_support_is_not_converted_into_null_evidence():
    result = evaluate_recurrence_null_contrast(_admission(independent="UNKNOWN"), _null())
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["rows"][0]
    assert row["state"] == "NOT_EVALUATED_INDEPENDENT_SUPPORT_UNKNOWN"
    assert row["observed_independent_recurrence"] == "UNKNOWN"


def test_null_draws_cannot_exceed_current_eligible_cohort():
    result = evaluate_recurrence_null_contrast(_admission(), _null(draws=[0, 1, 4]))
    assert result["status"] == "FAIL_CLOSED"
    assert "null_draw_exceeds_eligible_cohort:TRACE_A" in result["hard_block_hits"]


def test_null_method_must_declare_constraints_and_exchangeability():
    payload = _null()
    payload["method"]["preserved_constraints"] = []
    payload["method"]["exchangeability_assumption"] = ""
    result = evaluate_recurrence_null_contrast(_admission(), payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "null_method_preserved_constraints_missing" in result["hard_block_hits"]
    assert "null_method_missing:exchangeability_assumption" in result["hard_block_hits"]


def test_claim_locks_remain_closed():
    result = evaluate_recurrence_null_contrast(_admission(), _null())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/recurrence_null_contrast.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
