from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_safe_finding_binding import (
    build_sequence_safe_finding_blocks,
)


def _payload(state="RECURRENT_VISIBLE_TRACE", independent="UNKNOWN"):
    return {
        "module_id": "sequence_pattern_admission_lite_v1",
        "status": "PASS",
        "sequence_pattern_admissions": [{
            "trace_family_ref": "variant_a",
            "eligible_trace_refs": ["variant_a", "variant_b", "variant_c", "variant_d", "variant_e"],
            "eligible_trace_count": 5,
            "admission_state": state,
            "observed_support": 5,
            "independent_support_count": independent,
            "failure_variant_count": 1,
            "divergence_count": 1,
            "no_visible_followup_count": 1,
            "robustness_state": "ROBUST_WITHIN_TESTED_RANGE",
            "counterevidence_refs": ["variant_b", "variant_c"],
            "alternative_explanations": [{"type": "CONTEXT_DEPENDENCE", "causal_truth": False}],
            "dependency_summary": {"independence_proven": independent != "UNKNOWN"},
            "uncertainty": {"recurrence_is_tactical_intention_truth": False},
            "context_scope": [{"period_candidate": "1"}],
            "source_anchor_context": {"team_identity_candidate_id": "team_a"},
            "forbidden_inference": ["TACTICAL_PATTERN_TRUTH", "CAUSALITY"],
            "withdrawal_condition": "Downgrade if evidence changes.",
        }],
        "tactical_pattern_state_allowed": False,
        "coach_intention_state_allowed": False,
        "team_style_truth_state_allowed": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_recurrent_trace_becomes_readable_analyst_block_not_tactical_truth():
    result = build_sequence_safe_finding_blocks(_payload())
    row = result["analyst_report_blocks"][0]
    assert row["WHAT_VISIBLE"].startswith("A comparable admitted visible trace family")
    assert "independence is not sufficiently established" in row["SAFE_MEANING"]
    assert "TACTICAL_PATTERN_TRUTH" in row["FORBIDDEN_INFERENCE"]
    assert row["professional_finding_emitted"] is False
    assert row["claim_output_allowed"] is False


def test_exact_supporting_trace_cohort_survives_safe_binding():
    row = build_sequence_safe_finding_blocks(_payload())["analyst_report_blocks"][0]
    assert row["trace_variant_refs"] == ["variant_a", "variant_b", "variant_c", "variant_d", "variant_e"]
    assert row["recurrence_summary"]["eligible_trace_count"] == row["recurrence_summary"]["observed_support"] == 5


def test_missing_or_mismatched_trace_cohort_fails_closed_before_prose():
    missing = _payload()
    missing["sequence_pattern_admissions"][0]["eligible_trace_refs"] = []
    result = build_sequence_safe_finding_blocks(missing)
    assert result["status"] == "FAIL_CLOSED"
    assert result["analyst_report_block_count"] == 0
    assert "admission_missing_eligible_trace_refs:variant_a" in result["hard_block_hits"]

    mismatch = _payload()
    mismatch["sequence_pattern_admissions"][0]["eligible_trace_refs"] = ["variant_a"]
    result = build_sequence_safe_finding_blocks(mismatch)
    assert result["status"] == "FAIL_CLOSED"
    assert "admission_trace_cohort_support_mismatch:variant_a" in result["hard_block_hits"]


def test_success_failure_divergence_and_no_followup_are_exposed_together():
    row = build_sequence_safe_finding_blocks(_payload())["analyst_report_blocks"][0]
    assert row["success_support"] == 2
    assert row["failure_support"] == 1
    assert row["divergence_support"] == 1
    assert row["no_visible_followup_support"] == 1
    assert "is not failure" in row["COUNTEREVIDENCE"]


def test_robust_admission_can_strengthen_language_without_causality():
    row = build_sequence_safe_finding_blocks(_payload("ROBUST_RECURRENT_VISIBLE_TRACE", 3))["analyst_report_blocks"][0]
    assert "explicitly admitted independent support" in row["SAFE_MEANING"]
    assert "causality" in row["FORBIDDEN_INFERENCE"]
    assert row["production_release"] is False


def test_counterevidence_alternative_and_withdrawal_condition_survive_binding():
    row = build_sequence_safe_finding_blocks(_payload())["analyst_report_blocks"][0]
    assert row["counterevidence"]["refs"] == ["variant_b", "variant_c"]
    assert row["alternative_explanations"][0]["type"] == "CONTEXT_DEPENDENCE"
    assert row["withdrawal_condition"] == "Downgrade if evidence changes."


def test_rejected_or_review_admission_does_not_become_analyst_claim():
    rejected = build_sequence_safe_finding_blocks(_payload("REJECTED_INSUFFICIENT_EVIDENCE"))
    review = build_sequence_safe_finding_blocks(_payload("REVIEW_REQUIRED"))
    assert rejected["analyst_report_block_count"] == 0
    assert review["analyst_report_block_count"] == 0
    assert review["status"] == "REVIEW_REQUIRED"
    assert "admission_row_review_required:variant_a" in review["review_hits"]


def test_unknown_or_forbidden_admission_state_fails_closed_before_prose():
    for state in ("TACTICAL_PATTERN", "UNKNOWN_FUTURE_STATE", ""):
        result = build_sequence_safe_finding_blocks(_payload(state))
        assert result["status"] == "FAIL_CLOSED"
        assert result["analyst_report_block_count"] == 0
        assert any(hit.startswith("unsupported_admission_state:") for hit in result["hard_block_hits"])


def test_upstream_claim_lock_breach_fails_closed():
    payload = _payload()
    payload["tactical_pattern_state_allowed"] = True
    result = build_sequence_safe_finding_blocks(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "tactical_pattern_lock_missing" in result["hard_block_hits"]


def test_claim_and_release_locks_remain_closed():
    result = build_sequence_safe_finding_blocks(_payload())
    assert result["professional_finding_emitted_count"] == 0
    assert result["claim_output_allowed_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/sequence_safe_finding_binding.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
