from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_analyst_narrative import (
    compose_sequence_analyst_narrative,
)


def _payload(*, simulation_count=99, resolution=0.01, finite_only=True):
    row = {
        "analyst_report_block_id": "block_a",
        "entity_scope": "team_scope",
        "context_scope": [],
        "trace_family_refs": ["TRACE_A"],
        "trace_variant_refs": ["TRACE_A", "TRACE_B", "TRACE_C"],
        "recurrence_summary": {
            "observed_support": 3,
            "eligible_trace_count": 3,
            "independent_support_count": 3,
            "admission_state": "RECURRENT_VISIBLE_TRACE",
        },
        "robustness_summary": {"robustness_state": "CONDITIONAL"},
        "success_support": 2,
        "failure_support": 1,
        "divergence_support": 0,
        "no_visible_followup_support": 0,
        "counterevidence": {"refs": ["TRACE_B"]},
        "SAFE_MEANING": "A recurrent visible process candidate exists in the observed scope.",
        "FORBIDDEN_INFERENCE": ["causality", "tactical truth"],
        "dependency_summary": {"independence_proven": False, "dependency_group_refs": []},
        "uncertainty": {"independence": "AUDITED_ONLY"},
        "withdrawal_condition": "Downgrade if admitted evidence changes.",
        "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY",
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "null_contrast_summary": {
            "state": "OBSERVED_ABOVE_DEFINED_NULL_MEDIAN",
            "observed_independent_recurrence": 3,
            "simulation_count": simulation_count,
            "null_mean": 1.4,
            "null_median": 1.0,
            "null_q95": 3.0,
            "empirical_upper_tail_probability_uncorrected": 0.02,
            "empirical_upper_tail_resolution": resolution,
            "finite_simulation_resolution_only": finite_only,
            "observed_percentile_in_null_draws": 0.98,
            "null_model_id": "defined_recurrence_null",
            "null_model_version": "v1",
            "null_mechanism": "constraint_preserving_resample",
            "preserved_constraints": ["eligible_trace_count"],
            "exchangeability_assumption": "AUDITED_ASSUMPTION_ONLY",
            "multiple_testing_corrected": False,
            "significance_claim_allowed": False,
            "tactical_pattern_truth_allowed": False,
            "causality_allowed": False,
            "claim_strengthened": False,
            "withdrawal_condition": "Withdraw null comparison if the audited null specification changes.",
            "claim_ceiling": "UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY",
        },
    }
    return {
        "module_id": "sequence_safe_finding_binding_lite_v1",
        "status": "PASS",
        "analyst_report_blocks": [row],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_narrative_preserves_exact_finite_null_tail_resolution():
    result = compose_sequence_analyst_narrative(_payload())
    assert result["status"] == "PASS"
    block = result["narrative_blocks"][0]
    summary = block["null_contrast_summary"]
    assert summary["simulation_count"] == 99
    assert summary["empirical_upper_tail_resolution"] == 0.01
    assert summary["finite_simulation_resolution_only"] is True
    assert "simülasyon=99" in block["null_contrast_tr"]
    assert "finite-simulation kuyruk çözünürlüğü=0.01" in block["null_contrast_tr"]
    assert block["null_contrast_significance_claimed"] is False
    assert block["null_contrast_causality_claimed"] is False


def test_narrative_rejects_mismatched_null_tail_resolution():
    result = compose_sequence_analyst_narrative(_payload(resolution=0.02))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_null_contrast_tail_resolution_mismatch" in result["hard_block_hits"]


def test_narrative_rejects_missing_finite_resolution_lock():
    result = compose_sequence_analyst_narrative(_payload(finite_only=False))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_null_contrast_finite_resolution_lock_breach" in result["hard_block_hits"]


def test_narrative_rejects_invalid_simulation_count():
    result = compose_sequence_analyst_narrative(_payload(simulation_count=0, resolution=1.0))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_null_contrast_simulation_count_invalid" in result["hard_block_hits"]
