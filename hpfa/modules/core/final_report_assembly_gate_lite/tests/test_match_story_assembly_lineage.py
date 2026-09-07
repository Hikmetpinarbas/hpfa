from pathlib import Path

from hpfa.modules.core.final_report_assembly_gate_lite.src.final_report_assembly_gate import evaluate_assembly_item


def _item():
    return {
        "module_id": "report_output_contract_lite_v1",
        "contract_item_id": "contract_match_story_report_a",
        "report_block_id": "match_story_report_a",
        "block_family": "match_story_analyst_reading_candidate",
        "block_language": "tr",
        "inclusion_decision": "INCLUDE_BLOCK_CANDIDATE",
        "output_text_candidate_tr": "Takımın admitted görünür süreçleri tekrar, bozulma ve bağlamsal varyasyon bakımından birlikte değerlendirildi.",
        "claim_ceiling": "report_output_contract_candidate_only",
        "upstream_claim_ceiling": "analyst_report_block_candidate_only",
        "status": "SMOKE_PASS",
        "hard_block_hits": [],
        "review_hits": [],
        "match_story_evidence_lineage": {
            "source_narrative_ids": ["n1", "n2"],
            "unique_trace_refs": ["v1", "v2", "v3", "v4", "v5", "v6"],
            "unique_trace_ref_count": 6,
            "shared_trace_refs_across_processes": [],
            "nominal_support_sum": 6,
            "process_narrative_count": 2,
            "recurrent_process_count": 1,
            "robust_recurrent_process_count": 1,
            "counterevidence_bearing_process_count": 1,
            "context_sensitive_process_count": 1,
            "null_evaluated_process_count": 1,
            "nominal_support_is_independent_evidence_count": False,
            "cross_process_support_independence_proven": False,
            "story_state": "RECURRENT_PROCESS_SET_WITH_VISIBLE_COUNTEREVIDENCE",
            "entity_scope": "team_a",
            "withdrawal_condition": "Recompute if source narratives or exact trace cohorts change.",
            "upstream_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY",
        },
        "claim_output_allowed": False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_match_story_lineage_reaches_ready_assembly_candidate():
    result = evaluate_assembly_item(_item())
    assert result["status"] == "SMOKE_PASS"
    assert result["assembly_decision"] == "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE"
    assert result["match_story_evidence_lineage"]["source_narrative_ids"] == ["n1", "n2"]
    assert result["match_story_evidence_lineage"]["unique_trace_ref_count"] == 6
    assert result["match_story_evidence_lineage"]["process_narrative_count"] == 2
    assert result["match_story_evidence_lineage"]["robust_recurrent_process_count"] == 1
    assert result["match_story_evidence_lineage"]["nominal_support_is_independent_evidence_count"] is False
    assert result["sequence_evidence_lineage"] == {}
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_missing_match_story_lineage_fails_closed():
    item = _item()
    item["match_story_evidence_lineage"] = {}
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_story_evidence_lineage_missing" in result["hard_block_hits"]


def test_match_story_nominal_support_independence_escalation_fails_closed():
    item = _item()
    item["match_story_evidence_lineage"]["nominal_support_is_independent_evidence_count"] = True
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_match_story_nominal_support_independence_lock_breach" in result["hard_block_hits"]


def test_match_story_claim_ceiling_mismatch_fails_closed():
    item = _item()
    item["match_story_evidence_lineage"]["upstream_claim_ceiling"] = "TACTICAL_TRUTH"
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_match_story_upstream_claim_ceiling_mismatch" in result["hard_block_hits"]


def test_shared_refs_must_be_subset_of_unique_trace_refs():
    item = _item()
    item["match_story_evidence_lineage"]["shared_trace_refs_across_processes"] = ["outside"]
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_match_story_shared_trace_refs_not_subset" in result["hard_block_hits"]


def test_process_narrative_count_must_equal_exact_source_cohort():
    item = _item()
    item["match_story_evidence_lineage"]["process_narrative_count"] = 3
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_match_story_process_narrative_count_mismatch" in result["hard_block_hits"]


def test_boolean_process_accounting_is_not_integer_evidence():
    item = _item()
    item["match_story_evidence_lineage"]["null_evaluated_process_count"] = True
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_match_story_null_evaluated_process_count_invalid" in result["hard_block_hits"]


def test_subprocess_count_cannot_exceed_process_cohort():
    item = _item()
    item["match_story_evidence_lineage"]["context_sensitive_process_count"] = 3
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_match_story_context_sensitive_process_count_exceeds_process_count" in result["hard_block_hits"]


def test_robust_recurrent_count_cannot_exceed_recurrent_count():
    item = _item()
    item["match_story_evidence_lineage"]["recurrent_process_count"] = 0
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "assembly_match_story_robust_recurrent_exceeds_recurrent" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/final_report_assembly_gate_lite/src/final_report_assembly_gate.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
