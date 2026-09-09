from hpfa.modules.core.active_match_spine_runner.src.user_output_bundle import _assembly_report_entries, build_analyst_report


def _lineage(**updates):
    value = {
        "source_narrative_ids": ["NARRATIVE_A", "NARRATIVE_B"],
        "process_narrative_count": 2,
        "recurrent_process_count": 1,
        "robust_recurrent_process_count": 1,
        "counterevidence_bearing_process_count": 1,
        "context_sensitive_process_count": 1,
        "null_evaluated_process_count": 0,
        "alternative_explanation_bearing_process_count": 1,
        "alternative_explanations": [
            {
                "source_narrative_id": "NARRATIVE_A",
                "alternative_explanation": {"type": "CONTEXT_DEPENDENCE", "detail": "visible context may account for recurrence"},
            }
        ],
        "nominal_support_is_independent_evidence_count": False,
        "cross_process_support_independence_proven": False,
        "alternative_explanation_is_independent_counterevidence_vote": False,
        "alternative_explanation_count_is_support_count": False,
    }
    value.update(updates)
    return value


def _full_spine(lineage):
    return {
        "status": "SMOKE_PASS",
        "decision": "FULL_SPINE_COMPLETED",
        "intelligence_chain_count": 1,
        "hard_block_hits": [],
        "review_hits": [],
        "engineering_evidence": {"current_c4_producers_reused": True},
        "intelligence_chains": [
            {
                "assembly": {
                    "status": "SMOKE_PASS",
                    "assembly_decision": "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE",
                    "draft_report_candidate_allowed": True,
                    "block_family": "match_story_analyst_reading_candidate",
                    "assembly_item_candidate_tr": "ASSEMBLY_ADMITTED_MATCH_STORY",
                    "claim_ceiling": "final_report_assembly_candidate_only",
                    "match_story_evidence_lineage": lineage,
                }
            }
        ],
    }


def test_match_story_alternative_lineage_reaches_analyst_report(tmp_path):
    spine = _full_spine(_lineage())
    entries = _assembly_report_entries(spine)
    assert len(entries) == 1
    text = build_analyst_report(tmp_path, spine)
    assert "ASSEMBLY_ADMITTED_MATCH_STORY" in text
    assert "alternative_explanation_bearing_process_count=1" in text
    assert '"source_narrative_id": "NARRATIVE_A"' in text
    assert "alternative_explanation_is_independent_counterevidence_vote=false" in text
    assert "alternative_explanation_count_is_support_count=false" in text


def test_cross_cohort_alternative_source_suppresses_match_story_entry():
    bad = _lineage(
        alternative_explanations=[
            {"source_narrative_id": "NARRATIVE_X", "alternative_explanation": {"type": "CONTEXT_DEPENDENCE"}}
        ]
    )
    assert _assembly_report_entries(_full_spine(bad)) == []


def test_alternative_explanation_escalation_suppresses_match_story_entry():
    assert _assembly_report_entries(
        _full_spine(_lineage(alternative_explanation_is_independent_counterevidence_vote=True))
    ) == []
    assert _assembly_report_entries(
        _full_spine(_lineage(alternative_explanation_count_is_support_count=True))
    ) == []


def test_claim_locks_remain_non_release(tmp_path):
    text = build_analyst_report(tmp_path, _full_spine(_lineage()))
    assert "canonical_event_count=UNKNOWN" in text
    assert "true_action_count=UNKNOWN" in text
    assert "production_release=false" in text
