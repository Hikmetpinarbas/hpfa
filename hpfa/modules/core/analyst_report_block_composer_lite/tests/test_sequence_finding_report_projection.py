from pathlib import Path

from hpfa.modules.core.analyst_report_block_composer_lite.src.sequence_finding_report_projection import (
    compose_sequence_finding_report,
    compose_sequence_narrative_report,
)


def _payload(*, state="RECURRENT_VISIBLE_TRACE", independent="UNKNOWN", source_status="PASS"):
    return {
        "module_id": "sequence_safe_finding_binding_lite_v1",
        "status": source_status,
        "analyst_report_blocks": [{
            "trace_family_refs": ["family_a"],
            "trace_variant_refs": ["family_a", "trace_b", "trace_c", "trace_d", "trace_e"],
            "entity_scope": "team_a",
            "context_scope": [{"period_candidate": "1"}],
            "success_support": 2,
            "failure_support": 1,
            "divergence_support": 1,
            "no_visible_followup_support": 1,
            "recurrence_summary": {
                "observed_support": 5,
                "eligible_trace_count": 5,
                "independent_support_count": independent,
                "admission_state": state,
            },
            "robustness_summary": {"robustness_state": "ROBUST_WITHIN_TESTED_RANGE"},
            "counterevidence": {"refs": ["family_b"]},
            "dependency_summary": {"independence_proven": independent != "UNKNOWN"},
            "uncertainty": {"recurrence_is_tactical_intention_truth": False},
            "FORBIDDEN_INFERENCE": ["TACTICAL_PATTERN_TRUTH", "CAUSALITY"],
            "ANALYST_ACTION": "Review the twins.",
            "withdrawal_condition": "Downgrade if evidence changes.",
            "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY",
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _narrative_payload(source_status="PASS"):
    return {
        "module_id": "sequence_analyst_narrative_lite_v1",
        "status": source_status,
        "narrative_blocks": [{
            "narrative_id": "sequence_story_001",
            "entity_scope": "team_a",
            "context_scope": [{"period_candidate": "1"}],
            "trace_family_refs": ["trace_a"],
            "trace_variant_refs": ["trace_a", "trace_b", "trace_c"],
            "headline_tr": "Aynı görünür süreç tekrarlandı.",
            "evidence_tr": "Görünür destek 3 örnek.",
            "counterweight_tr": "Karşı örnek mevcut.",
            "safe_meaning_tr": "Maç içi görünür tekrar adayıdır.",
            "analyst_action_tr": "Örnekleri birlikte incele.",
            "story_tr": "Aynı görünür süreç tekrarlandı. Görünür destek 3 örnek. Karşı örnek mevcut.",
            "support": 3,
            "success_support": 1,
            "failure_support": 1,
            "divergence_support": 1,
            "no_visible_followup_support": 0,
            "counterevidence_refs": ["trace_b"],
            "counterevidence_ref_count": 1,
            "admission_state": "RECURRENT_VISIBLE_TRACE",
            "dependency_summary": {"independence_proven": False, "dependency_groups": ["dep_a"]},
            "robustness_summary": {"robustness_state": "CONDITIONAL"},
            "uncertainty": {"independence": "UNKNOWN"},
            "withdrawal_condition": "Downgrade if evidence changes.",
            "upstream_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY",
            "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY",
            "forbidden_inference": ["causality"],
            "claim_output_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _add_null_and_context(payload):
    row = payload["narrative_blocks"][0]
    row["null_contrast_tr"] = "Null karşılaştırması descriptivedir."
    row["null_contrast_summary"] = {
        "state": "AUDITED_NULL_AVAILABLE",
        "observed_independent_recurrence": 2,
        "null_median": 1.0,
        "empirical_upper_tail_probability_uncorrected": 0.2,
        "claim_strengthened": False,
        "significance_claim_allowed": False,
        "tactical_pattern_truth_allowed": False,
    }
    row["change_tr"] = "Bağlama göre görünür dağılım farkı var."
    row["context_variations"] = [{
        "context_conditioned_trace_deviation_id": "ctx_001",
        "context_dimension": "period_candidate",
        "baseline_cohort_ref": "1",
        "comparison_cohort_ref": "2",
        "baseline_trace_refs": ["trace_a"],
        "comparison_trace_refs": ["trace_b"],
        "effect_descriptor": "VISIBLE_DISTRIBUTION_DIFFERENCE",
        "dependency_summary": {"independence_proven": False},
        "uncertainty": {"small_sample": True},
        "chronology_direction_claimed": False,
        "causality_claimed": False,
        "tactical_adaptation_claimed": False,
        "coach_intention_claimed": False,
    }]
    return payload


def test_projection_makes_sequence_evidence_readable_in_turkish():
    result = compose_sequence_finding_report(_payload())
    row = result["report_blocks"][0]
    assert "5 kez gözlendi" in row["report_block_candidate_tr"]
    assert "1 tanesi görünür başarısızlıkla" in row["report_block_candidate_tr"]
    assert "başarısızlık olarak sayılmadı" in row["report_block_candidate_tr"]
    assert "bağımsız destek henüz yeterince kanıtlanmadığı" in row["report_block_candidate_tr"]


def test_exact_trace_cohort_and_epistemic_payload_survive_projection():
    row = compose_sequence_finding_report(_payload())["report_blocks"][0]
    assert row["trace_variant_refs"] == ["family_a", "trace_b", "trace_c", "trace_d", "trace_e"]
    assert row["dependency_summary"]["independence_proven"] is False
    assert row["uncertainty"]["recurrence_is_tactical_intention_truth"] is False
    assert row["robustness_summary"]["robustness_state"] == "ROBUST_WITHIN_TESTED_RANGE"
    assert row["withdrawal_condition"] == "Downgrade if evidence changes."
    assert row["upstream_claim_ceiling"] == "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"


def test_missing_or_mismatched_trace_cohort_fails_closed_in_projection():
    missing = _payload()
    missing["analyst_report_blocks"][0]["trace_variant_refs"] = []
    result = compose_sequence_finding_report(missing)
    assert result["status"] == "FAIL_CLOSED"
    assert "sequence_finding_missing_trace_variant_refs:family_a" in result["hard_block_hits"]

    mismatch = _payload()
    mismatch["analyst_report_blocks"][0]["trace_variant_refs"] = ["family_a"]
    result = compose_sequence_finding_report(mismatch)
    assert result["status"] == "FAIL_CLOSED"
    assert "sequence_finding_trace_cohort_support_mismatch:family_a" in result["hard_block_hits"]


def test_missing_epistemic_lineage_fails_closed_in_projection():
    cases = (
        ("dependency_summary", "sequence_finding_missing_dependency_summary:family_a"),
        ("robustness_summary", "sequence_finding_missing_robustness_summary:family_a"),
        ("uncertainty", "sequence_finding_missing_uncertainty:family_a"),
        ("withdrawal_condition", "sequence_finding_missing_withdrawal_condition:family_a"),
        ("claim_ceiling", "sequence_finding_missing_claim_ceiling:family_a"),
    )
    for field, expected_hit in cases:
        payload = _payload()
        payload["analyst_report_blocks"][0][field] = {} if field not in {"withdrawal_condition", "claim_ceiling"} else ""
        result = compose_sequence_finding_report(payload)
        assert result["status"] == "FAIL_CLOSED"
        assert result["report_block_count"] == 0
        assert expected_hit in result["hard_block_hits"]


def test_counterevidence_changes_public_interpretation_not_support_count():
    row = compose_sequence_finding_report(_payload())["report_blocks"][0]
    assert row["observed_support"] == 5
    assert row["counterevidence_refs"] == ["family_b"]
    assert "sürekli çalışan bir üstünlük olarak değil" in row["safe_interpretation_tr"]


def test_robust_state_strengthens_only_descriptive_language():
    row = compose_sequence_finding_report(_payload(state="ROBUST_RECURRENT_VISIBLE_TRACE", independent=3))["report_blocks"][0]
    text = row["report_block_candidate_tr"]
    assert "bağımsız destek açık biçimde kabul edilmiş" in text
    assert "taktik plan veya nedensellik kanıtı değildir" in text
    assert row["final_report_allowed"] is False


def test_no_visible_followup_never_becomes_failure():
    row = compose_sequence_finding_report(_payload())["report_blocks"][0]
    assert row["failure_support"] == 1
    assert row["no_visible_followup_support"] == 1
    assert "başarısızlık olarak sayılmadı" in row["report_block_candidate_tr"]


def test_source_review_status_survives_projection():
    result = compose_sequence_finding_report(_payload(source_status="REVIEW_REQUIRED"))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["report_blocks"][0]["status"] == "REVIEW_REQUIRED"


def test_outcome_partition_cannot_exceed_observed_support():
    payload = _payload()
    payload["analyst_report_blocks"][0]["success_support"] = 99
    result = compose_sequence_finding_report(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert result["report_block_count"] == 0


def test_narrative_report_preserves_full_evidence_lineage():
    row = compose_sequence_narrative_report(_narrative_payload())["report_blocks"][0]
    assert row["trace_variant_refs"] == ["trace_a", "trace_b", "trace_c"]
    assert row["counterevidence_refs"] == ["trace_b"]
    assert row["dependency_summary"]["dependency_groups"] == ["dep_a"]
    assert row["robustness_summary"]["robustness_state"] == "CONDITIONAL"
    assert row["uncertainty"]["independence"] == "UNKNOWN"
    assert row["withdrawal_condition"] == "Downgrade if evidence changes."
    assert row["upstream_claim_ceiling"] == "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY"
    assert row["origin_claim_ceiling"] == "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"


def test_narrative_report_preserves_null_and_context_lineage():
    result = compose_sequence_narrative_report(_add_null_and_context(_narrative_payload()))
    row = result["report_blocks"][0]
    assert result["null_contrast_lineage_preserved"] is True
    assert result["context_variation_lineage_preserved"] is True
    assert row["null_contrast_summary"]["empirical_upper_tail_probability_uncorrected"] == 0.2
    assert row["null_contrast_summary"]["significance_claim_allowed"] is False
    assert row["context_variations"][0]["baseline_trace_refs"] == ["trace_a"]
    assert row["context_variations"][0]["causality_claimed"] is False
    assert row["change_tr"] == "Bağlama göre görünür dağılım farkı var."


def test_narrative_report_rejects_null_claim_strengthening():
    payload = _add_null_and_context(_narrative_payload())
    payload["narrative_blocks"][0]["null_contrast_summary"]["claim_strengthened"] = True
    result = compose_sequence_narrative_report(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "narrative_null_contrast_claim_strengthened:sequence_story_001" in result["hard_block_hits"]


def test_narrative_report_rejects_context_claim_escalation():
    payload = _add_null_and_context(_narrative_payload())
    payload["narrative_blocks"][0]["context_variations"][0]["causality_claimed"] = True
    result = compose_sequence_narrative_report(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "narrative_context_variation_claim_lock_breach:sequence_story_001:causality_claimed" in result["hard_block_hits"]


def test_narrative_report_rejects_context_trace_lineage_escape():
    payload = _add_null_and_context(_narrative_payload())
    payload["narrative_blocks"][0]["context_variations"][0]["comparison_trace_refs"] = ["trace_outside_cohort"]
    result = compose_sequence_narrative_report(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "narrative_context_variation_trace_lineage_mismatch:sequence_story_001" in result["hard_block_hits"]


def test_narrative_report_fails_closed_when_counterevidence_lineage_is_lost():
    payload = _narrative_payload()
    payload["narrative_blocks"][0]["counterevidence_refs"] = []
    result = compose_sequence_narrative_report(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "narrative_counterevidence_lineage_mismatch:sequence_story_001" in result["hard_block_hits"]


def test_narrative_report_fails_closed_when_claim_ceiling_lineage_is_missing():
    payload = _narrative_payload()
    payload["narrative_blocks"][0]["upstream_claim_ceiling"] = ""
    result = compose_sequence_narrative_report(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "narrative_missing_claim_ceiling_lineage:sequence_story_001" in result["hard_block_hits"]


def test_narrative_review_state_cannot_silently_become_pass():
    result = compose_sequence_narrative_report(_narrative_payload("REVIEW_REQUIRED"))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["report_blocks"][0]["status"] == "REVIEW_REQUIRED"


def test_claim_locks_remain_closed():
    result = compose_sequence_narrative_report(_narrative_payload())
    row = result["report_blocks"][0]
    assert row["claim_output_allowed"] is False
    assert row["production_report_allowed"] is False
    assert row["final_report_allowed"] is False
    assert row["canonical_event_count"] == "UNKNOWN"
    assert row["true_action_count"] == "UNKNOWN"
    assert row["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/analyst_report_block_composer_lite/src/sequence_finding_report_projection.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
