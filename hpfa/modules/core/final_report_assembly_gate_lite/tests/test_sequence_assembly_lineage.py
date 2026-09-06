import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "final_report_assembly_gate_lite" / "src"
sys.path.insert(0, str(SRC))

from final_report_assembly_gate import evaluate_assembly_item


def sequence_contract_item():
    lineage = {
        "trace_family_refs": ["TRACE_A"],
        "trace_variant_refs": ["TRACE_A", "TRACE_B"],
        "counterevidence_refs": ["TRACE_B"],
        "dependency_summary": {"independence_proven": False},
        "robustness_summary": {"robustness_state": "CONDITIONAL"},
        "uncertainty": {"ordering": "ORDER_INDETERMINATE"},
        "withdrawal_condition": "support cohort or dependency state changes",
        "observed_support": 2,
        "upstream_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY",
        "origin_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY",
    }
    return {
        "contract_item_id": "contract_sequence_GENERIC",
        "report_block_id": "sequence_narrative_report_GENERIC",
        "block_family": "sequence_narrative_analyst_reading_candidate",
        "inclusion_decision": "INCLUDE_BLOCK_CANDIDATE",
        "output_text_candidate_tr": "Görünür tekrar adayı exact kanıt zinciri ve geri çekme koşuluyla birlikte taşınır.",
        "claim_ceiling": "report_output_contract_candidate_only",
        "claim_output_allowed": False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "sequence_evidence_lineage": lineage,
    }


def test_sequence_lineage_survives_assembly_gate_exactly():
    item = sequence_contract_item()
    result = evaluate_assembly_item(item)
    assert result["status"] == "SMOKE_PASS"
    assert result["assembly_decision"] == "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE"
    assert result["sequence_evidence_lineage"] == item["sequence_evidence_lineage"]
    assert result["block_family"] == item["block_family"]


def test_sequence_lineage_missing_or_incomplete_fails_closed():
    item = sequence_contract_item()
    item.pop("sequence_evidence_lineage")
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "sequence_evidence_lineage_missing" in result["hard_block_hits"]

    cases = (
        ("trace_variant_refs", [], "assembly_sequence_trace_variant_refs_missing"),
        ("dependency_summary", None, "assembly_sequence_dependency_summary_missing"),
        ("robustness_summary", None, "assembly_sequence_robustness_summary_missing"),
        ("uncertainty", None, "assembly_sequence_uncertainty_missing"),
        ("withdrawal_condition", "", "assembly_sequence_withdrawal_condition_missing"),
        ("upstream_claim_ceiling", "", "assembly_sequence_upstream_claim_ceiling_missing"),
        ("origin_claim_ceiling", "", "assembly_sequence_origin_claim_ceiling_missing"),
    )
    for field, value, expected in cases:
        item = sequence_contract_item()
        item["sequence_evidence_lineage"][field] = value
        result = evaluate_assembly_item(item)
        assert result["status"] == "FAIL_CLOSED"
        assert expected in result["hard_block_hits"]
        assert result["assembly_item_candidate_tr"] == ""


def test_sequence_support_and_anchor_consistency_are_revalidated():
    item = sequence_contract_item()
    item["sequence_evidence_lineage"]["observed_support"] = 3
    result = evaluate_assembly_item(item)
    assert "assembly_sequence_trace_cohort_support_mismatch" in result["hard_block_hits"]

    item = sequence_contract_item()
    item["sequence_evidence_lineage"]["trace_family_refs"] = ["TRACE_C"]
    result = evaluate_assembly_item(item)
    assert "assembly_sequence_anchor_not_in_trace_cohort" in result["hard_block_hits"]


def test_sequence_claim_ceiling_vocabulary_and_hop_are_revalidated():
    item = sequence_contract_item()
    item["sequence_evidence_lineage"]["upstream_claim_ceiling"] = "TACTICAL_PATTERN_TRUTH"
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_sequence_upstream_claim_ceiling_mismatch" in result["hard_block_hits"]

    item = sequence_contract_item()
    item["sequence_evidence_lineage"]["origin_claim_ceiling"] = "CAUSAL_TRUTH"
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_sequence_origin_claim_ceiling_mismatch" in result["hard_block_hits"]

    item = sequence_contract_item()
    item["block_family"] = "sequence_safe_finding_analyst_reading_candidate"
    item["sequence_evidence_lineage"]["upstream_claim_ceiling"] = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_sequence_unexpected_origin_claim_ceiling" in result["hard_block_hits"]

    item = sequence_contract_item()
    item["block_family"] = "sequence_safe_finding_analyst_reading_candidate"
    item["sequence_evidence_lineage"]["upstream_claim_ceiling"] = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"
    item["sequence_evidence_lineage"]["origin_claim_ceiling"] = ""
    result = evaluate_assembly_item(item)
    assert result["status"] == "SMOKE_PASS"


def test_claim_locks_cannot_be_promoted_at_assembly_boundary():
    item = sequence_contract_item()
    item["true_action_count"] = 2
    result = evaluate_assembly_item(item)
    assert "true_action_count_claim_rejected" in result["hard_block_hits"]

    item = sequence_contract_item()
    item["production_release"] = True
    result = evaluate_assembly_item(item)
    assert "production_release_claim_rejected" in result["hard_block_hits"]

    result = evaluate_assembly_item(sequence_contract_item())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak_in_assembly_producer():
    src = (SRC / "final_report_assembly_gate.py").read_text(encoding="utf-8")
    for token in ["Genclerbirligi", "Fenerbahce", "15.08.2026", "Turkey", "Australia"]:
        assert token not in src
