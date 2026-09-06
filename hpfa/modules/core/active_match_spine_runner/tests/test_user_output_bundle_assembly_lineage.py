from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from user_output_bundle import build_analyst_report


def _base_spine(chain):
    return {
        "status": "SMOKE_PASS",
        "decision": "FULL_SPINE_EXECUTION_COMPLETED",
        "episode_candidate_count": None,
        "episode_feature_vector_count": None,
        "temporal_episode_signature_count": None,
        "intelligence_chain_count": 1,
        "hard_block_hits": [],
        "review_hits": [],
        "engineering_evidence": {
            "current_context_episode_feature_lane_completed": False,
            "current_c4_producers_reused": True,
            "rich_multiformat_lane_executed": False,
        },
        "intelligence_chains": [chain],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _lineage():
    return {
        "trace_family_refs": ["TRACE_A"],
        "trace_variant_refs": ["TRACE_A", "TRACE_B"],
        "observed_support": 2,
        "dependency_summary": {"independent_support_count": "UNKNOWN"},
        "robustness_summary": {"state": "ROBUST_WITHIN_TESTED_RANGE"},
        "uncertainty": {"ordering": "ORDER_INDETERMINATE"},
        "withdrawal_condition": "withdraw_if_trace_cohort_or_dependency_changes",
        "upstream_claim_ceiling": "report_output_contract_candidate_only",
        "origin_claim_ceiling": "VISIBLE_RECURRENT_TRACE_CANDIDATE_ONLY",
    }


def test_user_report_never_bypasses_blocked_final_assembly(tmp_path):
    chain = {
        "safe_sentence": {"safe_sentence_candidate_tr": "EARLY_SAFE_SENTENCE_MUST_NOT_SHIP"},
        "assembly": {
            "status": "FAIL_CLOSED",
            "assembly_decision": "BLOCK_ASSEMBLY_ITEM",
            "assembly_item_candidate_tr": "",
            "draft_report_candidate_allowed": False,
            "block_family": "generic_analyst_reading_candidate",
            "sequence_evidence_lineage": {},
        },
    }
    text = build_analyst_report(tmp_path, _base_spine(chain))
    assert "EARLY_SAFE_SENTENCE_MUST_NOT_SHIP" not in text
    assert "final assembly gate tarafindan admitted analyst-text candidate gorunmedi" in text


def test_sequence_assembly_candidate_preserves_exact_lineage_in_user_report(tmp_path):
    lineage = _lineage()
    chain = {
        "safe_sentence": {"safe_sentence_candidate_tr": "EARLY_SENTENCE_NOT_AUTHORITY"},
        "assembly": {
            "status": "SMOKE_PASS",
            "assembly_decision": "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE",
            "assembly_item_candidate_tr": "ASSEMBLY_ADMITTED_VISIBLE_SEQUENCE_CANDIDATE",
            "draft_report_candidate_allowed": True,
            "block_family": "sequence_narrative_analyst_reading_candidate",
            "sequence_evidence_lineage": lineage,
            "claim_ceiling": "final_report_assembly_candidate_only",
        },
    }
    text = build_analyst_report(tmp_path, _base_spine(chain))
    assert "ASSEMBLY_ADMITTED_VISIBLE_SEQUENCE_CANDIDATE" in text
    assert "EARLY_SENTENCE_NOT_AUTHORITY" not in text
    assert 'trace_variant_refs=["TRACE_A", "TRACE_B"]' in text
    assert "observed_support=2" in text
    assert "independent_support_count" in text
    assert "ORDER_INDETERMINATE" in text
    assert "withdraw_if_trace_cohort_or_dependency_changes" in text
    assert "VISIBLE_RECURRENT_TRACE_CANDIDATE_ONLY" in text
    assert "assembly_claim_ceiling=final_report_assembly_candidate_only" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "true_action_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_sequence_candidate_with_cohort_support_mismatch_is_suppressed(tmp_path):
    lineage = _lineage()
    lineage["observed_support"] = 3
    chain = {
        "assembly": {
            "status": "SMOKE_PASS",
            "assembly_decision": "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE",
            "assembly_item_candidate_tr": "MALFORMED_SEQUENCE_CANDIDATE_MUST_NOT_SHIP",
            "draft_report_candidate_allowed": True,
            "block_family": "sequence_narrative_analyst_reading_candidate",
            "sequence_evidence_lineage": lineage,
            "claim_ceiling": "final_report_assembly_candidate_only",
        }
    }
    text = build_analyst_report(tmp_path, _base_spine(chain))
    assert "MALFORMED_SEQUENCE_CANDIDATE_MUST_NOT_SHIP" not in text


def test_sequence_candidate_missing_withdrawal_condition_is_suppressed(tmp_path):
    lineage = _lineage()
    lineage.pop("withdrawal_condition")
    chain = {
        "assembly": {
            "status": "SMOKE_PASS",
            "assembly_decision": "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE",
            "assembly_item_candidate_tr": "LINEAGE_INCOMPLETE_CANDIDATE_MUST_NOT_SHIP",
            "draft_report_candidate_allowed": True,
            "block_family": "sequence_safe_finding_analyst_reading_candidate",
            "sequence_evidence_lineage": lineage,
            "claim_ceiling": "final_report_assembly_candidate_only",
        }
    }
    text = build_analyst_report(tmp_path, _base_spine(chain))
    assert "LINEAGE_INCOMPLETE_CANDIDATE_MUST_NOT_SHIP" not in text
