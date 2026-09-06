import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "report_output_contract_lite" / "src"
sys.path.insert(0, str(SRC))

from report_output_contract import evaluate_report_block


def narrative_block():
    return {
        "report_block_id": "sequence_narrative_report_null_context",
        "block_family": "sequence_narrative_analyst_reading_candidate",
        "block_language": "tr",
        "report_block_candidate_tr": "Görünür tekrar, null ve context denetimleriyle birlikte koşullu bir analist okumasıdır.",
        "status": "SMOKE_PASS",
        "decision": "NARRATIVE_ANALYST_READING_CANDIDATE_COMPOSED",
        "claim_ceiling": "analyst_report_block_candidate_only",
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "trace_family_refs": ["TRACE_A"],
        "trace_variant_refs": ["TRACE_A", "TRACE_B", "TRACE_C"],
        "counterevidence_refs": ["TRACE_B"],
        "observed_support": 3,
        "dependency_summary": {"independence_proven": False, "dependency_groups": ["DEP_A"]},
        "robustness_summary": {"robustness_state": "CONDITIONAL"},
        "uncertainty": {"independence": "UNKNOWN"},
        "withdrawal_condition": "Downgrade if the exact evidence cohort or audit state changes.",
        "upstream_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY",
        "origin_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY",
        "null_contrast_summary": {
            "state": "EVALUATED",
            "observed_support": 3,
            "null_median_support": 1.5,
            "upper_tail_probability_uncorrected": 0.12,
            "claim_strengthened": False,
            "significance_claim_allowed": False,
            "tactical_pattern_truth_allowed": False,
            "multiple_testing_corrected": False,
        },
        "context_variations": [
            {
                "dimension": "period_candidate",
                "baseline_trace_refs": ["TRACE_A"],
                "comparison_trace_refs": ["TRACE_B", "TRACE_C"],
                "chronology_direction_claimed": False,
                "causality_claimed": False,
                "tactical_adaptation_claimed": False,
                "coach_intention_claimed": False,
            }
        ],
    }


def test_output_contract_preserves_audited_null_and_context_lineage_exactly():
    block = narrative_block()
    item = evaluate_report_block(block)
    assert item["status"] == "SMOKE_PASS"
    assert item["inclusion_decision"] == "INCLUDE_BLOCK_CANDIDATE"
    lineage = item["sequence_evidence_lineage"]
    assert lineage["null_contrast_summary"] == block["null_contrast_summary"]
    assert lineage["context_variations"] == block["context_variations"]
    assert item["canonical_event_count"] == "UNKNOWN"
    assert item["true_action_count"] == "UNKNOWN"
    assert item["production_release"] is False


def test_output_contract_rejects_null_claim_strengthening():
    block = narrative_block()
    block["null_contrast_summary"]["claim_strengthened"] = True
    item = evaluate_report_block(block)
    assert item["status"] == "FAIL_CLOSED"
    assert "sequence_lineage_null_contrast_claim_strengthened" in item["hard_block_hits"]


def test_output_contract_rejects_uncorrected_tail_promoted_to_significance():
    block = narrative_block()
    block["null_contrast_summary"]["significance_claim_allowed"] = True
    item = evaluate_report_block(block)
    assert item["status"] == "FAIL_CLOSED"
    assert "sequence_lineage_null_contrast_significance_lock_breach" in item["hard_block_hits"]


def test_output_contract_rejects_context_causal_or_adaptation_claims():
    for flag in ("causality_claimed", "tactical_adaptation_claimed", "coach_intention_claimed"):
        block = narrative_block()
        block["context_variations"][0][flag] = True
        item = evaluate_report_block(block)
        assert item["status"] == "FAIL_CLOSED"
        assert f"sequence_lineage_context_variation_claim_lock_breach:{flag}" in item["hard_block_hits"]


def test_output_contract_rejects_context_trace_outside_exact_support_cohort():
    block = narrative_block()
    block["context_variations"][0]["comparison_trace_refs"] = ["TRACE_OUTSIDE"]
    item = evaluate_report_block(block)
    assert item["status"] == "FAIL_CLOSED"
    assert "sequence_lineage_context_variation_trace_lineage_mismatch" in item["hard_block_hits"]


def test_output_contract_rejects_malformed_null_or_context_lineage():
    block = narrative_block()
    block["null_contrast_summary"] = "not-a-dict"
    item = evaluate_report_block(block)
    assert item["status"] == "FAIL_CLOSED"
    assert "sequence_lineage_null_contrast_summary_invalid" in item["hard_block_hits"]

    block = narrative_block()
    block["context_variations"] = {"not": "a-list"}
    item = evaluate_report_block(block)
    assert item["status"] == "FAIL_CLOSED"
    assert "sequence_lineage_context_variations_invalid" in item["hard_block_hits"]
