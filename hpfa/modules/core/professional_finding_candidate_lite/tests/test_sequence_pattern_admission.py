from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_pattern_admission import (
    build_sequence_pattern_admissions,
)


def _variant(variant_id: str, *, order="LAYER_ORDER_CONFIRMED_INTERNAL_SINGLETONS", chronology="EXPLICIT_POSITIVE_TIME_LAYER_ORDER", period="1"):
    return {
        "trace_variant_id": variant_id,
        "ordering_completeness": order,
        "chronology_confidence": chronology,
        "context_signature": {"team_identity_candidate_id": "team_a", "period_candidate": period},
    }


def _payloads(*, robustness="ROBUST_WITHIN_TESTED_RANGE", independent="UNKNOWN", independence_groups=None, packet_state="CONTRAST_AVAILABLE", eligible=None):
    eligible = eligible or ["v1", "v2"]
    variants = [_variant("v1"), _variant("v2")]
    variant_payload = {
        "module_id": "partial_order_trace_variant_lite_v1",
        "status": "PASS",
        "partial_order_trace_variants": variants,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    contrast_payload = {
        "module_id": "trace_contrast_packet_lite_v1",
        "status": "PASS",
        "trace_contrast_packets": [{
            "anchor_trace_family": "v1",
            "eligible_trace_refs": eligible,
            "failure_count": 1,
            "divergence_count": 0,
            "no_visible_followup_count": 0,
            "counterevidence_refs": ["v2"],
            "dependency_groups": ["occurrence:a", "occurrence:b"],
            "independence_groups": independence_groups or [],
            "independent_support_count": independent,
            "packet_state": packet_state,
        }],
        "no_visible_followup_is_failure": False,
        "absence_of_evidence_is_counterevidence": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    robustness_payload = {
        "module_id": "recurrence_robustness_envelope_lite_v1",
        "status": "PASS",
        "recurrence_robustness_envelopes": [{
            "pattern_family_ref": "v1",
            "nominal_recurrence": len(eligible),
            "robustness_state": robustness,
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return variant_payload, contrast_payload, robustness_payload


def test_robust_nominal_recurrence_without_independence_stops_at_recurrent_visible_trace():
    result = build_sequence_pattern_admissions(*_payloads())
    row = result["sequence_pattern_admissions"][0]
    assert row["admission_state"] == "RECURRENT_VISIBLE_TRACE"
    assert row["independent_support_count"] == "UNKNOWN"
    assert row["dependency_summary"]["independence_proven"] is False
    assert result["status"] == "REVIEW_REQUIRED"


def test_robust_recurrent_state_requires_explicit_independence_admission():
    result = build_sequence_pattern_admissions(*_payloads(independent=2, independence_groups=["i1", "i2"]))
    row = result["sequence_pattern_admissions"][0]
    assert row["admission_state"] == "ROBUST_RECURRENT_VISIBLE_TRACE"
    assert row["independent_support_count"] == 2
    assert row["dependency_summary"]["independence_proven"] is True


def test_threshold_sensitive_candidate_is_not_robust_pattern():
    result = build_sequence_pattern_admissions(*_payloads(robustness="THRESHOLD_SENSITIVE"))
    row = result["sequence_pattern_admissions"][0]
    assert row["admission_state"] == "PROXY_CANDIDATE"
    assert {item["type"] for item in row["alternative_explanations"]} >= {"THRESHOLD_SELECTION_SENSITIVITY"}
    assert "TACTICAL_PATTERN_TRUTH" in row["forbidden_inference"]


def test_single_visible_trace_is_rejected_insufficient_evidence():
    variant, contrast, robustness = _payloads(eligible=["v1"])
    result = build_sequence_pattern_admissions(variant, contrast, robustness)
    row = result["sequence_pattern_admissions"][0]
    assert row["admission_state"] == "REJECTED_INSUFFICIENT_EVIDENCE"


def test_no_visible_followup_cannot_be_reclassified_as_failure_by_gate():
    variant, contrast, robustness = _payloads()
    contrast["no_visible_followup_is_failure"] = True
    result = build_sequence_pattern_admissions(variant, contrast, robustness)
    assert result["status"] == "FAIL_CLOSED"
    assert "contrast_no_visible_followup_failure_policy_breached" in result["hard_block_hits"]


def test_row_order_or_same_time_policy_breach_fails_closed():
    variant, contrast, robustness = _payloads()
    variant["source_row_order_is_temporal_truth"] = True
    result = build_sequence_pattern_admissions(variant, contrast, robustness)
    assert result["status"] == "FAIL_CLOSED"
    assert "variant_source_row_order_policy_breached" in result["hard_block_hits"]


def test_dependent_object_views_never_infer_independent_support_from_nominal_count():
    result = build_sequence_pattern_admissions(*_payloads())
    row = result["sequence_pattern_admissions"][0]
    assert row["observed_support"] == 2
    assert row["independent_support_count"] == "UNKNOWN"
    assert row["dependency_summary"]["object_views_or_reflections_may_not_create_independent_support"] is True
    assert result["independent_support_inferred_from_nominal_count"] is False


def test_counterevidence_is_preserved_and_not_treated_as_disproof_or_causality():
    result = build_sequence_pattern_admissions(*_payloads())
    row = result["sequence_pattern_admissions"][0]
    assert row["counterevidence_state"] == "VISIBLE"
    assert row["counterevidence_refs"] == ["v2"]
    assert "CAUSALITY" in row["forbidden_inference"]


def test_claim_and_release_locks_remain_closed():
    result = build_sequence_pattern_admissions(*_payloads())
    assert result["tactical_pattern_state_allowed"] is False
    assert result["coach_intention_state_allowed"] is False
    assert result["team_style_truth_state_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/sequence_pattern_admission.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
