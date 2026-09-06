from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_safe_finding_binding import (
    build_sequence_safe_finding_blocks,
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
            "failure_variant_count": 0,
            "divergence_count": 0,
            "no_visible_followup_count": 0,
            "robustness_state": "ROBUST_WITHIN_TESTED_RANGE",
            "counterevidence_refs": [],
            "alternative_explanations": [],
            "dependency_summary": {"independence_proven": isinstance(independent, int)},
            "uncertainty": {"recurrence_is_tactical_intention_truth": False},
            "withdrawal_condition": "Downgrade if admitted evidence changes.",
            "admission_state": "ROBUST_RECURRENT_VISIBLE_TRACE" if isinstance(independent, int) else "RECURRENT_VISIBLE_TRACE",
            "source_anchor_context": {"team_identity_candidate_id": "TEAM_A"},
            "forbidden_inference": ["TACTICAL_PATTERN_TRUTH", "CAUSALITY"],
        }],
        "hard_block_hits": [],
        "tactical_pattern_state_allowed": False,
        "coach_intention_state_allowed": False,
        "team_style_truth_state_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _null(independent=3):
    return {
        "contrast_id": "recurrence_null_contrast_v1",
        "status": "PASS",
        "rows": [{
            "trace_family_ref": "TRACE_A",
            "eligible_trace_refs": ["TRACE_A", "TRACE_B", "TRACE_C"],
            "state": "OBSERVED_ABOVE_NULL_MEDIAN",
            "observed_independent_recurrence": independent,
            "simulation_count": 1000,
            "null_mean": 1.2,
            "null_median": 1.0,
            "null_q95": 2.0,
            "empirical_upper_tail_probability_uncorrected": 0.01,
            "observed_percentile_in_null_draws": 0.99,
            "null_model_id": "DECLARED_NULL_A",
            "null_model_version": "V1",
            "null_mechanism": "declared synthetic shuffle",
            "preserved_constraints": ["eligible_trace_count", "independence_group_cardinality"],
            "exchangeability_assumption": "declared exchangeability",
            "multiple_testing_corrected": False,
            "significance_claim_allowed": False,
            "tactical_pattern_truth_allowed": False,
            "withdrawal_condition": "Recompute if null assumptions change.",
            "claim_ceiling": "UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY",
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_defined_null_contrast_reaches_safe_finding_without_upgrading_claim():
    result = build_sequence_safe_finding_blocks(_admission(), _null())
    row = result["analyst_report_blocks"][0]
    assert result["status"] == "PASS"
    assert result["null_contrast_consumed"] is True
    assert row["null_contrast_summary"]["state"] == "OBSERVED_ABOVE_NULL_MEDIAN"
    assert row["null_contrast_summary"]["empirical_upper_tail_probability_uncorrected"] == 0.01
    assert row["null_contrast_summary"]["claim_strengthened"] is False
    assert row["claim_output_allowed"] is False
    assert row["production_release"] is False
    assert "uncorrected upper-tail probability" in row["SUPPORT"]
    assert "without treating the uncorrected tail probability as significance" in row["SAFE_MEANING"]


def test_null_contrast_cannot_change_admission_state():
    result = build_sequence_safe_finding_blocks(_admission(), _null())
    row = result["analyst_report_blocks"][0]
    assert row["recurrence_summary"]["admission_state"] == "ROBUST_RECURRENT_VISIBLE_TRACE"
    assert row["null_contrast_summary"]["claim_strengthened"] is False


def test_null_contrast_must_match_exact_trace_cohort():
    null = _null()
    null["rows"][0]["eligible_trace_refs"] = ["TRACE_A", "TRACE_B"]
    result = build_sequence_safe_finding_blocks(_admission(), null)
    assert result["status"] == "FAIL_CLOSED"
    assert "null_contrast_trace_cohort_mismatch:TRACE_A" in result["hard_block_hits"]


def test_null_contrast_cannot_fabricate_independence():
    null = _null(independent=3)
    result = build_sequence_safe_finding_blocks(_admission(independent="UNKNOWN"), null)
    assert result["status"] == "FAIL_CLOSED"
    assert "null_contrast_unknown_independence_escalated:TRACE_A" in result["hard_block_hits"]


def test_null_significance_or_tactical_truth_lock_breach_fails_closed():
    null = _null()
    null["rows"][0]["significance_claim_allowed"] = True
    result = build_sequence_safe_finding_blocks(_admission(), null)
    assert result["status"] == "FAIL_CLOSED"
    assert "null_contrast_significance_lock_breach:TRACE_A" in result["hard_block_hits"]

    null = _null()
    null["rows"][0]["tactical_pattern_truth_allowed"] = True
    result = build_sequence_safe_finding_blocks(_admission(), null)
    assert result["status"] == "FAIL_CLOSED"
    assert "null_contrast_tactical_truth_lock_breach:TRACE_A" in result["hard_block_hits"]


def test_claim_locks_and_sample_identity_remain_safe():
    result = build_sequence_safe_finding_blocks(_admission(), _null())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/sequence_safe_finding_binding.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
