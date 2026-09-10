from copy import deepcopy
from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_safe_finding_binding import build_sequence_safe_finding_blocks


def _payload(state="RECURRENT_VISIBLE_TRACE", independent="UNKNOWN", with_context=False):
    row = {
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
    }
    if with_context:
        row.update({
            "sequence_occurrence_object_context_state": "PATTERN_OCCURRENCE_CONTEXT_LINEAGE_ONLY",
            "sequence_occurrence_team_context_refs": ["team_ctx_2", "team_ctx_1", "team_ctx_1"],
            "sequence_occurrence_goalkeeper_context_refs": ["gk_ctx_1"],
            "sequence_occurrence_goalkeeper_context_bundle_refs": ["gk_bundle_1"],
            "sequence_occurrence_reflection_context_refs": ["reflection_1"],
            "sequence_occurrence_relation_type_candidates": ["TEAM_CONTEXT", "GOALKEEPER_CONTEXT"],
            "sequence_occurrence_context_is_pattern_support": False,
            "sequence_occurrence_context_is_independent_support": False,
            "goalkeeper_context_is_pattern_participant_truth": False,
            "reflection_context_is_pattern_equivalence_truth": False,
            "sequence_occurrence_context_ref_count_is_pattern_count": False,
            "sequence_occurrence_context_ref_count_is_recurrence_count": False,
            "sequence_occurrence_context_creates_event": False,
        })
    return {
        "module_id": "sequence_pattern_admission_lite_v1",
        "status": "PASS",
        "sequence_pattern_admissions": [row],
        "tactical_pattern_state_allowed": False,
        "coach_intention_state_allowed": False,
        "team_style_truth_state_allowed": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_recurrent_without_independence_is_downgraded_not_emitted():
    result = build_sequence_safe_finding_blocks(_payload())
    row = result["analyst_report_blocks"][0]
    assert row["finding_status"] == "DOWNGRADE"
    assert row["professional_finding_emitted"] is False
    assert row["claim_output_allowed"] is False
    assert "independent_support_not_admitted" in row["downgrade_reasons"]


def test_robust_independent_challenged_trace_emits_defeasible_finding():
    result = build_sequence_safe_finding_blocks(_payload("ROBUST_RECURRENT_VISIBLE_TRACE", 3))
    row = result["analyst_report_blocks"][0]
    assert row["finding_status"] == "EMIT"
    assert row["professional_finding_emitted"] is True
    assert row["claim_output_allowed"] is True
    assert result["professional_finding_emitted_count"] == 1
    assert result["finding_status_counts"] == {"EMIT": 1, "DOWNGRADE": 0, "ABSTAIN": 0}
    assert row["production_release"] is False
    assert "causality" in row["FORBIDDEN_INFERENCE"]


def test_review_required_envelope_preserves_row_level_emission_eligibility():
    payload = _payload("ROBUST_RECURRENT_VISIBLE_TRACE", 3)
    payload["status"] = "REVIEW_REQUIRED"
    result = build_sequence_safe_finding_blocks(payload)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["professional_finding_emitted_count"] == 1
    assert result["claim_output_allowed_count"] == 1
    assert result["analyst_report_block_count"] == 1
    assert result["finding_status_counts"] == {"EMIT": 1, "DOWNGRADE": 0, "ABSTAIN": 0}
    assert result["review_required_is_global_abstain"] is False
    assert result["row_scoped_review_preserves_other_row_eligibility"] is True
    assert "admission_upstream_review_required_row_scoped" in result["review_hits"]


def test_mixed_review_payload_routes_each_finding_without_cross_row_poisoning():
    payload = _payload("ROBUST_RECURRENT_VISIBLE_TRACE", 3)
    payload["status"] = "REVIEW_REQUIRED"
    emit_row = payload["sequence_pattern_admissions"][0]

    downgrade_row = deepcopy(emit_row)
    downgrade_row.update({
        "trace_family_ref": "down_a",
        "eligible_trace_refs": ["down_a", "down_b", "down_c", "down_d", "down_e"],
        "admission_state": "RECURRENT_VISIBLE_TRACE",
        "independent_support_count": "UNKNOWN",
        "counterevidence_refs": ["down_b"],
        "dependency_summary": {"independence_proven": False},
    })

    review_row = deepcopy(emit_row)
    review_row.update({
        "trace_family_ref": "review_a",
        "eligible_trace_refs": ["review_a", "review_b", "review_c", "review_d", "review_e"],
        "admission_state": "REVIEW_REQUIRED",
        "counterevidence_refs": ["review_b"],
    })

    payload["sequence_pattern_admissions"] = [emit_row, downgrade_row, review_row]
    result = build_sequence_safe_finding_blocks(payload)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["analyst_report_block_count"] == 2
    assert result["finding_status_counts"] == {"EMIT": 1, "DOWNGRADE": 1, "ABSTAIN": 1}
    assert result["professional_finding_emitted_count"] == 1
    assert result["claim_output_allowed_count"] == 1
    assert {row["finding_status"] for row in result["analyst_report_blocks"]} == {"EMIT", "DOWNGRADE"}
    assert "admission_row_review_required:review_a" in result["review_hits"]


def test_unrecognized_upstream_status_still_abstains_globally():
    payload = _payload("ROBUST_RECURRENT_VISIBLE_TRACE", 3)
    payload["status"] = "UNKNOWN"
    result = build_sequence_safe_finding_blocks(payload)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["analyst_report_block_count"] == 0
    assert result["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 1}
    assert result["review_required_is_global_abstain"] is True


def test_robust_trace_without_challenge_surface_downgrades():
    payload = _payload("ROBUST_RECURRENT_VISIBLE_TRACE", 3)
    payload["sequence_pattern_admissions"][0]["counterevidence_refs"] = []
    payload["sequence_pattern_admissions"][0]["alternative_explanations"] = []
    row = build_sequence_safe_finding_blocks(payload)["analyst_report_blocks"][0]
    assert row["finding_status"] == "DOWNGRADE"
    assert "challenge_surface_empty" in row["downgrade_reasons"]


def test_review_and_rejected_rows_abstain():
    review = build_sequence_safe_finding_blocks(_payload("REVIEW_REQUIRED"))
    rejected = build_sequence_safe_finding_blocks(_payload("REJECTED_INSUFFICIENT_EVIDENCE"))
    assert review["finding_status_counts"]["ABSTAIN"] == 1
    assert rejected["finding_status_counts"]["ABSTAIN"] == 1
    assert review["analyst_report_block_count"] == 0
    assert rejected["analyst_report_block_count"] == 0


def test_pattern_occurrence_context_survives_as_lineage_only_not_support():
    row = build_sequence_safe_finding_blocks(_payload(with_context=True))["analyst_report_blocks"][0]
    assert row["sequence_occurrence_object_context_state"] == "SAFE_FINDING_OCCURRENCE_CONTEXT_LINEAGE_ONLY"
    assert row["sequence_occurrence_context_is_finding_support"] is False
    assert row["sequence_occurrence_context_is_independent_support"] is False
    assert row["sequence_occurrence_context_creates_event"] is False


def test_unsafe_occurrence_context_abstains_under_review():
    payload = _payload(with_context=True)
    payload["sequence_pattern_admissions"][0]["sequence_occurrence_context_is_pattern_support"] = True
    result = build_sequence_safe_finding_blocks(payload)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["analyst_report_block_count"] == 0
    assert result["finding_status_counts"]["ABSTAIN"] == 1


def test_missing_or_mismatched_trace_cohort_fails_closed():
    missing = _payload(); missing["sequence_pattern_admissions"][0]["eligible_trace_refs"] = []
    mismatch = _payload(); mismatch["sequence_pattern_admissions"][0]["eligible_trace_refs"] = ["variant_a"]
    assert build_sequence_safe_finding_blocks(missing)["status"] == "FAIL_CLOSED"
    assert build_sequence_safe_finding_blocks(mismatch)["status"] == "FAIL_CLOSED"


def test_boolean_numeric_evidence_cannot_become_support_or_independence():
    observed = _payload("ROBUST_RECURRENT_VISIBLE_TRACE", 3)
    observed["sequence_pattern_admissions"][0]["observed_support"] = True
    result = build_sequence_safe_finding_blocks(observed)
    assert result["status"] == "FAIL_CLOSED"
    assert any("observed_support" in hit for hit in result["hard_block_hits"])

    independent = _payload("ROBUST_RECURRENT_VISIBLE_TRACE", True)
    result = build_sequence_safe_finding_blocks(independent)
    assert result["status"] == "FAIL_CLOSED"
    assert any("independent_support_count" in hit for hit in result["hard_block_hits"])
    assert result["professional_finding_emitted_count"] == 0


def test_negative_or_overallocated_outcome_accounting_fails_closed():
    negative = _payload()
    negative["sequence_pattern_admissions"][0]["divergence_count"] = -1
    assert build_sequence_safe_finding_blocks(negative)["status"] == "FAIL_CLOSED"

    over = _payload()
    row = over["sequence_pattern_admissions"][0]
    row["failure_variant_count"] = 3
    row["divergence_count"] = 2
    row["no_visible_followup_count"] = 1
    result = build_sequence_safe_finding_blocks(over)
    assert result["status"] == "FAIL_CLOSED"
    assert any("outcome_accounting_exceeds_observed_support" in hit for hit in result["hard_block_hits"])


def test_no_visible_followup_never_becomes_failure_or_counterevidence():
    row = build_sequence_safe_finding_blocks(_payload())["analyst_report_blocks"][0]
    assert row["no_visible_followup_support"] == 1
    assert "is not failure" in row["COUNTEREVIDENCE"]


def test_upstream_claim_lock_breach_fails_closed():
    payload = _payload(); payload["tactical_pattern_state_allowed"] = True
    result = build_sequence_safe_finding_blocks(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert result["claim_output_allowed_count"] == 0


def test_release_and_truth_locks_remain_closed_even_when_finding_emits():
    result = build_sequence_safe_finding_blocks(_payload("ROBUST_RECURRENT_VISIBLE_TRACE", 3))
    row = result["analyst_report_blocks"][0]
    assert row["canonical_event_count"] == "UNKNOWN"
    assert row["true_action_count"] == "UNKNOWN"
    assert row["production_release"] is False
    assert row["numeric_evidence_counts_are_strict_nonnegative_integers"] is True
    assert row["boolean_numeric_evidence_rejected"] is True
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/sequence_safe_finding_binding.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
