from pathlib import Path

from hpfa.modules.core.report_output_contract_lite.src.report_output_contract import evaluate_report_block


def _block(shared=None):
    shared = shared or []
    refs = ["v1", "v2", "v3", "v4", "v5"] if shared else ["v1", "v2", "v3", "v4", "v5", "v6"]
    return {
        "report_block_id": "match_story_report_a",
        "block_family": "match_story_analyst_reading_candidate",
        "block_language": "tr",
        "report_block_candidate_tr": "Takımın admitted görünür süreçleri tekrar, bozulma ve bağlamsal varyasyon bakımından birlikte değerlendirildi.",
        "source_narrative_ids": ["n1", "n2"],
        "story_state": "RECURRENT_PROCESS_SET_WITH_VISIBLE_COUNTEREVIDENCE",
        "entity_scope": "team_a",
        "nominal_support_sum": 6,
        "unique_trace_ref_count": len(refs),
        "unique_trace_refs": refs,
        "shared_trace_refs_across_processes": shared,
        "nominal_support_is_independent_evidence_count": False,
        "cross_process_support_independence_proven": False,
        "withdrawal_condition": "Recompute if source narratives or exact trace cohorts change.",
        "upstream_claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY",
        "status": "SMOKE_PASS",
        "decision": "MATCH_STORY_ANALYST_READING_CANDIDATE_COMPOSED",
        "claim_ceiling": "analyst_report_block_candidate_only",
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_match_story_block_is_admitted_with_exact_story_lineage():
    result = evaluate_report_block(_block())
    assert result["status"] == "SMOKE_PASS"
    assert result["inclusion_decision"] == "INCLUDE_BLOCK_CANDIDATE"
    lineage = result["match_story_evidence_lineage"]
    assert lineage["source_narrative_ids"] == ["n1", "n2"]
    assert lineage["unique_trace_ref_count"] == 6
    assert lineage["unique_trace_refs"] == ["v1", "v2", "v3", "v4", "v5", "v6"]
    assert lineage["nominal_support_sum"] == 6
    assert lineage["nominal_support_is_independent_evidence_count"] is False
    assert lineage["cross_process_support_independence_proven"] is False
    assert lineage["upstream_claim_ceiling"] == "DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY"
    assert result["sequence_evidence_lineage"] == {}


def test_nominal_support_independence_escalation_fails_closed():
    block = _block()
    block["nominal_support_is_independent_evidence_count"] = True
    result = evaluate_report_block(block)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_story_lineage_nominal_support_independence_lock_breach" in result["hard_block_hits"]


def test_unique_trace_count_mismatch_fails_closed():
    block = _block()
    block["unique_trace_ref_count"] = 99
    result = evaluate_report_block(block)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_story_lineage_unique_trace_ref_count_mismatch" in result["hard_block_hits"]


def test_wrong_story_claim_ceiling_fails_closed():
    block = _block()
    block["upstream_claim_ceiling"] = "TACTICAL_TRUTH"
    result = evaluate_report_block(block)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_story_lineage_upstream_claim_ceiling_mismatch" in result["hard_block_hits"]


def test_shared_trace_refs_must_belong_to_unique_trace_set():
    block = _block(shared=["v3"])
    block["shared_trace_refs_across_processes"] = ["not_in_cohort"]
    result = evaluate_report_block(block)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_story_lineage_shared_trace_refs_not_subset" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/report_output_contract_lite/src/report_output_contract.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
