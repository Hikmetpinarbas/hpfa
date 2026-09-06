import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "report_output_contract_lite" / "src"
sys.path.insert(0, str(SRC))

from report_output_contract import evaluate_report_block


def _narrative_block():
    return {
        "report_block_id": "sequence_narrative_report_GENERIC",
        "block_family": "sequence_narrative_analyst_reading_candidate",
        "block_language": "tr",
        "report_block_candidate_tr": "Görünür süreç tekrarı exact evidence lineage ile taşınır.",
        "status": "SMOKE_PASS",
        "decision": "NARRATIVE_ANALYST_READING_CANDIDATE_COMPOSED",
        "claim_ceiling": "analyst_report_block_candidate_only",
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "trace_family_refs": ["TRACE_GENERIC_A"],
        "trace_variant_refs": ["TRACE_GENERIC_A", "TRACE_GENERIC_B"],
        "counterevidence_refs": ["TRACE_GENERIC_B"],
        "observed_support": 2,
        "dependency_summary": {"independence_proven": False},
        "robustness_summary": {"robustness_state": "CONDITIONAL"},
        "uncertainty": {"ordering": "ORDER_INDETERMINATE"},
        "withdrawal_condition": "withdraw_if_evidence_lineage_changes",
        "upstream_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY",
        "origin_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY",
    }


def _safe_finding_block():
    block = _narrative_block()
    block["report_block_id"] = "sequence_safe_finding_report_GENERIC"
    block["block_family"] = "sequence_safe_finding_analyst_reading_candidate"
    block["decision"] = "ANALYST_READING_CANDIDATE_COMPOSED"
    block["upstream_claim_ceiling"] = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"
    block.pop("origin_claim_ceiling")
    return block


def test_narrative_claim_ceiling_lineage_accepts_only_authoritative_vocabulary():
    item = evaluate_report_block(_narrative_block())
    assert item["status"] == "SMOKE_PASS"
    assert item["sequence_evidence_lineage"]["upstream_claim_ceiling"] == "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY"
    assert item["sequence_evidence_lineage"]["origin_claim_ceiling"] == "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"


def test_narrative_upstream_claim_ceiling_escalation_fails_closed():
    block = _narrative_block()
    block["upstream_claim_ceiling"] = "TACTICAL_PATTERN_TRUTH"
    item = evaluate_report_block(block)
    assert item["status"] == "FAIL_CLOSED"
    assert "sequence_lineage_upstream_claim_ceiling_mismatch" in item["hard_block_hits"]
    assert item["output_text_candidate_tr"] == ""


def test_narrative_origin_claim_ceiling_escalation_fails_closed():
    block = _narrative_block()
    block["origin_claim_ceiling"] = "CAUSAL_SEQUENCE_TRUTH"
    item = evaluate_report_block(block)
    assert item["status"] == "FAIL_CLOSED"
    assert "sequence_lineage_origin_claim_ceiling_mismatch" in item["hard_block_hits"]


def test_safe_finding_claim_ceiling_lineage_is_exact_and_has_no_origin_hop():
    item = evaluate_report_block(_safe_finding_block())
    assert item["status"] == "SMOKE_PASS"

    block = _safe_finding_block()
    block["upstream_claim_ceiling"] = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY"
    item = evaluate_report_block(block)
    assert "sequence_lineage_upstream_claim_ceiling_mismatch" in item["hard_block_hits"]

    block = _safe_finding_block()
    block["origin_claim_ceiling"] = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"
    item = evaluate_report_block(block)
    assert "sequence_lineage_unexpected_origin_claim_ceiling" in item["hard_block_hits"]


def test_claim_locks_remain_unchanged():
    item = evaluate_report_block(_narrative_block())
    assert item["canonical_event_count"] == "UNKNOWN"
    assert item["true_action_count"] == "UNKNOWN"
    assert item["production_release"] is False


def test_no_sample_identity_hardcode_in_producer():
    source = (SRC / "report_output_contract.py").read_text(encoding="utf-8")
    for token in ["Genclerbirligi", "Fenerbahce", "15.08.2026"]:
        assert token not in source
