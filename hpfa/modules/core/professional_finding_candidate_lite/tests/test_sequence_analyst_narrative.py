from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_analyst_narrative import (
    compose_sequence_analyst_narrative,
)


def _row(state="RECURRENT_VISIBLE_TRACE", support=5, success=2, failure=1, divergence=1, no_followup=1):
    refs = [f"v{i}" for i in range(1, support + 1)]
    return {
        "analyst_report_block_id": "sfb_a",
        "entity_scope": "team_a",
        "context_scope": [{"period_candidate": "1"}],
        "trace_family_refs": ["v1"],
        "trace_variant_refs": refs,
        "recurrence_summary": {"observed_support": support, "eligible_trace_count": support, "independent_support_count": "UNKNOWN", "admission_state": state},
        "robustness_summary": {"robustness_state": "CONDITIONAL"},
        "success_support": success,
        "failure_support": failure,
        "divergence_support": divergence,
        "no_visible_followup_support": no_followup,
        "counterevidence": {"refs": ["v2"] if failure or divergence else []},
        "SAFE_MEANING": "A recurrent visible process candidate exists in the observed scope.",
        "FORBIDDEN_INFERENCE": ["coach intention", "causality"],
        "dependency_summary": {"independence_proven": False, "dependency_group_refs": ["dep_a"]},
        "uncertainty": {"independence": "UNKNOWN"},
        "withdrawal_condition": "Downgrade if evidence changes.",
        "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY",
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _payload(rows):
    return {
        "module_id": "sequence_safe_finding_binding_lite_v1",
        "status": "PASS",
        "analyst_report_blocks": rows,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _deviation(*, effect="VISIBLE_OUTCOME_DISTRIBUTION_DIFFERENCE_CANDIDATE", baseline=None, comparison=None):
    baseline = baseline or ["v1", "v2"]
    comparison = comparison or ["v3", "v4", "v5"]
    return {
        "module_id": "context_conditioned_trace_deviation_lite_v1",
        "status": "PASS",
        "context_conditioned_trace_deviations": [{
            "context_conditioned_trace_deviation_id": "ctd_a",
            "trace_family_ref": "ctf_a",
            "entity_scope": {"team_identity_candidate_id": "team_a"},
            "context_dimension": "period_candidate",
            "baseline_cohort_ref": "period_candidate:1",
            "comparison_cohort_ref": "period_candidate:2",
            "baseline_trace_refs": baseline,
            "comparison_trace_refs": comparison,
            "effect_descriptor": effect,
            "outcome_difference": effect != "NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION",
            "sequence_difference": False,
            "support_difference": len(comparison) - len(baseline),
            "dependency_summary": {"shared_dependency_group_refs": [], "independence_proven": False},
            "uncertainty": {"cohort_counts_are_independence_truth": False},
            "alternative_explanations": ["SAMPLE_COMPOSITION", "DEPENDENT_EVIDENCE"],
            "sample_warning": None,
            "context_difference_is_causality_truth": False,
            "context_difference_is_tactical_adaptation_truth": False,
            "context_difference_is_coach_intention_truth": False,
        }],
        "hard_block_hits": [],
        "context_difference_is_causality_truth": False,
        "context_difference_is_tactical_adaptation_truth": False,
        "context_difference_is_coach_intention_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_narrative_explains_repeat_success_failure_divergence_in_plain_turkish():
    result = compose_sequence_analyst_narrative(_payload([_row()]))
    story = result["narrative_blocks"][0]["story_tr"]
    assert "birden fazla kez tekrarlandı" in story
    assert "2 benzer ilerleme" in story
    assert "1 başarısız sonlanma" in story
    assert "1 farklılaşan devam" in story
    assert "başarısızlık sayılmadı" in story


def test_context_conditioned_variation_becomes_match_story_without_causal_escalation():
    result = compose_sequence_analyst_narrative(_payload([_row()]), _deviation())
    block = result["narrative_blocks"][0]
    assert "period_candidate:1" in block["change_tr"]
    assert "period_candidate:2" in block["change_tr"]
    assert "farklı görünür sonuç/sequence dağılımı" in block["change_tr"]
    assert "adaptasyonu veya taktik değişim kanıtı değildir" in block["change_tr"]
    assert block["context_variations"][0]["baseline_trace_refs"] == ["v1", "v2"]
    assert block["context_variations"][0]["comparison_trace_refs"] == ["v3", "v4", "v5"]
    assert block["chronology_direction_claimed"] is False
    assert block["context_change_causality_claimed"] is False
    assert block["tactical_adaptation_claimed"] is False


def test_no_visible_context_difference_is_not_converted_to_no_change_truth():
    result = compose_sequence_analyst_narrative(
        _payload([_row()]),
        _deviation(effect="NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION"),
    )
    text = result["narrative_blocks"][0]["change_tr"]
    assert "görünür dağılım farkı saptanmadı" in text
    assert "değişmediğini" in text
    assert "kanıtlamaz" in text


def test_context_variation_requires_exact_same_trace_cohort_before_binding():
    result = compose_sequence_analyst_narrative(
        _payload([_row()]),
        _deviation(baseline=["v1"], comparison=["v2", "v3"]),
    )
    block = result["narrative_blocks"][0]
    assert block["context_variations"] == []
    assert block["change_tr"] == ""


def test_overlapping_context_cohorts_fail_closed_when_exact_cohort_otherwise_matches():
    result = compose_sequence_analyst_narrative(
        _payload([_row()]),
        _deviation(baseline=["v1", "v2", "v3"], comparison=["v3", "v4", "v5"]),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "context_deviation_overlapping_cohorts" in result["hard_block_hits"]


def test_context_deviation_claim_lock_breach_fails_closed():
    deviation = _deviation()
    deviation["context_difference_is_causality_truth"] = True
    result = compose_sequence_analyst_narrative(_payload([_row()]), deviation)
    assert result["status"] == "FAIL_CLOSED"
    assert "context_deviation_causality_lock_missing" in result["hard_block_hits"]


def test_counterexample_prevents_unconditional_superiority_language():
    story = compose_sequence_analyst_narrative(_payload([_row()]))["narrative_blocks"][0]["counterweight_tr"]
    assert "koşulsuz çalışan bir üstünlük" in story
    assert "okunmamalı" in story


def test_no_counterexample_does_not_become_confirmation():
    row = _row(success=5, failure=0, divergence=0, no_followup=0)
    text = compose_sequence_analyst_narrative(_payload([row]))["narrative_blocks"][0]["counterweight_tr"]
    assert "kanıtlamaz" in text


def test_story_priority_uses_evidence_strength_not_fake_chronology():
    weak = _row("DISCOVERY_ONLY", support=10)
    weak["analyst_report_block_id"] = "weak"
    robust = _row("ROBUST_RECURRENT_VISIBLE_TRACE", support=3)
    robust["analyst_report_block_id"] = "robust"
    result = compose_sequence_analyst_narrative(_payload([weak, robust]))
    assert result["narrative_blocks"][0]["source_report_block_id"] == "robust"
    assert result["story_order_basis"].endswith("NOT_FOOTBALL_CHRONOLOGY")
    assert result["chronological_story_claimed"] is False


def test_review_upstream_survives_as_review_not_fake_pass():
    payload = _payload([_row()])
    payload["status"] = "REVIEW_REQUIRED"
    result = compose_sequence_analyst_narrative(payload)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "binding_upstream_review_required" in result["review_hits"]


def test_claim_lock_breach_fails_closed():
    row = _row()
    row["claim_output_allowed"] = True
    result = compose_sequence_analyst_narrative(_payload([row]))
    assert result["status"] == "FAIL_CLOSED"
    assert result["narrative_block_count"] == 0


def test_narrative_preserves_exact_evidence_lineage():
    row = _row()
    block = compose_sequence_analyst_narrative(_payload([row]))["narrative_blocks"][0]
    assert block["trace_family_refs"] == row["trace_family_refs"]
    assert block["trace_variant_refs"] == row["trace_variant_refs"]
    assert block["counterevidence_refs"] == row["counterevidence"]["refs"]
    assert block["counterevidence_ref_count"] == len(row["counterevidence"]["refs"])
    assert block["dependency_summary"] == row["dependency_summary"]
    assert block["robustness_summary"] == row["robustness_summary"]
    assert block["uncertainty"] == row["uncertainty"]
    assert block["withdrawal_condition"] == row["withdrawal_condition"]
    assert block["upstream_claim_ceiling"] == row["claim_ceiling"]
    assert block["canonical_event_count"] == "UNKNOWN"
    assert block["true_action_count"] == "UNKNOWN"
    assert block["production_release"] is False


def test_missing_exact_trace_cohort_fails_closed():
    row = _row()
    row["trace_variant_refs"] = []
    result = compose_sequence_analyst_narrative(_payload([row]))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_trace_variant_refs_missing" in result["hard_block_hits"]


def test_trace_cohort_support_mismatch_fails_closed():
    row = _row()
    row["trace_variant_refs"] = row["trace_variant_refs"][:-1]
    result = compose_sequence_analyst_narrative(_payload([row]))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_trace_cohort_support_mismatch" in result["hard_block_hits"]


def test_missing_epistemic_lineage_fails_closed():
    cases = (
        ("dependency_summary", "upstream_dependency_summary_missing"),
        ("robustness_summary", "upstream_robustness_summary_missing"),
        ("uncertainty", "upstream_uncertainty_missing"),
        ("withdrawal_condition", "upstream_withdrawal_condition_missing"),
        ("claim_ceiling", "upstream_claim_ceiling_missing"),
    )
    for field, expected in cases:
        row = _row()
        row.pop(field)
        result = compose_sequence_analyst_narrative(_payload([row]))
        assert result["status"] == "FAIL_CLOSED"
        assert expected in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/sequence_analyst_narrative.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
