from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.match_story_synthesis import (
    synthesize_match_story,
)


def _narrative(
    narrative_id: str,
    *,
    entity: str = "team_a",
    priority: int = 1,
    state: str = "RECURRENT_VISIBLE_TRACE",
    refs: list[str] | None = None,
    success: int = 2,
    failure: int = 1,
    divergence: int = 0,
    no_followup: int = 0,
    counter: bool = True,
    context_effect: str | None = None,
    null_state: str | None = None,
):
    refs = refs or [f"{narrative_id}_v1", f"{narrative_id}_v2", f"{narrative_id}_v3"]
    variations = []
    if context_effect:
        variations = [{
            "context_dimension": "period_candidate",
            "effect_descriptor": context_effect,
        }]
    null_summary = {}
    if null_state:
        null_summary = {"state": null_state}
    return {
        "narrative_id": narrative_id,
        "priority_rank": priority,
        "entity_scope": entity,
        "trace_variant_refs": refs,
        "headline_tr": "Aynı görünür süreç maç içinde birden fazla kez tekrarlandı.",
        "support": len(refs),
        "success_support": success,
        "failure_support": failure,
        "divergence_support": divergence,
        "no_visible_followup_support": no_followup,
        "counterevidence_ref_count": 1 if counter else 0,
        "admission_state": state,
        "context_variations": variations,
        "null_contrast_summary": null_summary,
        "claim_output_allowed": False,
        "chronology_direction_claimed": False,
        "context_change_causality_claimed": False,
        "tactical_adaptation_claimed": False,
        "null_contrast_significance_claimed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _payload(rows, status="PASS"):
    return {
        "module_id": "sequence_analyst_narrative_lite_v1",
        "status": status,
        "narrative_blocks": rows,
        "narrative_block_count": len(rows),
        "hard_block_hits": [],
        "chronological_story_claimed": False,
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "tactical_plan_truth_claimed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_multiple_safe_narratives_become_one_entity_match_story():
    rows = [
        _narrative(
            "n1",
            state="ROBUST_RECURRENT_VISIBLE_TRACE",
            priority=1,
            context_effect="VISIBLE_OUTCOME_DISTRIBUTION_DIFFERENCE_CANDIDATE",
            null_state="OBSERVED_ABOVE_DEFINED_NULL_MEDIAN",
        ),
        _narrative(
            "n2",
            priority=2,
            failure=0,
            divergence=1,
            counter=True,
        ),
        _narrative(
            "n3",
            state="PROXY_CANDIDATE",
            priority=3,
            failure=0,
            divergence=0,
            counter=False,
        ),
    ]
    result = synthesize_match_story(_payload(rows))
    assert result["status"] == "PASS"
    story = result["entity_stories"][0]
    assert story["process_narrative_count"] == 3
    assert story["robust_recurrent_process_count"] == 1
    assert story["recurrent_process_count"] == 2
    assert story["proxy_process_count"] == 1
    assert story["counterevidence_bearing_process_count"] == 2
    assert story["context_sensitive_process_count"] == 1
    assert story["null_evaluated_process_count"] == 1
    assert story["null_above_median_process_count"] == 1
    assert story["story_state"] == "RECURRENT_PROCESS_SET_WITH_CONTEXT_VARIATION"
    assert "bağlama göre ayrışan" in story["story_tr"]
    assert "koşulsuz çalışan üstünlük" in story["story_tr"]
    assert "kronolojik maç hikâyesi" in story["story_tr"]


def test_story_keeps_nominal_support_separate_from_independent_evidence():
    result = synthesize_match_story(_payload([
        _narrative("n1", refs=["v1", "v2", "v3"]),
        _narrative("n2", refs=["v4", "v5", "v6"]),
    ]))
    story = result["entity_stories"][0]
    assert story["nominal_support_sum"] == 6
    assert story["unique_trace_ref_count"] == 6
    assert story["nominal_support_is_independent_evidence_count"] is False
    assert story["cross_process_support_independence_proven"] is False


def test_shared_trace_refs_trigger_review_instead_of_fake_independence():
    result = synthesize_match_story(_payload([
        _narrative("n1", refs=["v1", "v2", "v3"]),
        _narrative("n2", refs=["v3", "v4", "v5"]),
    ]))
    assert result["status"] == "REVIEW_REQUIRED"
    assert "trace_refs_shared_across_narrative_blocks_independence_not_proven" in result["review_hits"]
    story = result["entity_stories"][0]
    assert story["unique_trace_ref_count"] == 5
    assert story["shared_trace_refs_across_processes"] == ["v3"]


def test_no_visible_context_difference_does_not_become_stability_truth():
    row = _narrative(
        "n1",
        context_effect="NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION",
    )
    story = synthesize_match_story(_payload([row]))["entity_stories"][0]
    assert story["context_sensitive_process_count"] == 0
    assert story["no_visible_context_difference_process_count"] == 1
    assert story["story_state"] != "RECURRENT_PROCESS_SET_WITH_CONTEXT_VARIATION"


def test_multiple_entities_get_separate_stories():
    result = synthesize_match_story(_payload([
        _narrative("a1", entity="team_a"),
        _narrative("b1", entity="team_b"),
    ]))
    assert result["entity_story_count"] == 2
    assert {x["entity_scope"] for x in result["entity_stories"]} == {"team_a", "team_b"}


def test_duplicate_narrative_id_fails_closed():
    result = synthesize_match_story(_payload([
        _narrative("n1"),
        _narrative("n1", refs=["x1", "x2", "x3"]),
    ]))
    assert result["status"] == "FAIL_CLOSED"
    assert "duplicate_narrative_id:n1" in result["hard_block_hits"]


def test_support_trace_mismatch_fails_closed():
    row = _narrative("n1")
    row["support"] = 99
    result = synthesize_match_story(_payload([row]))
    assert result["status"] == "FAIL_CLOSED"
    assert "narrative_support_trace_mismatch:n1" in result["hard_block_hits"]


def test_upstream_chronology_or_tactical_lock_breach_fails_closed():
    payload = _payload([_narrative("n1")])
    payload["chronological_story_claimed"] = True
    result = synthesize_match_story(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_chronology_lock_missing" in result["hard_block_hits"]

    payload = _payload([_narrative("n1")])
    payload["tactical_plan_truth_claimed"] = True
    result = synthesize_match_story(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_tactical_plan_lock_missing" in result["hard_block_hits"]


def test_review_status_survives_synthesis():
    result = synthesize_match_story(_payload([_narrative("n1")], status="REVIEW_REQUIRED"))
    assert result["status"] == "REVIEW_REQUIRED"
    assert "narrative_upstream_review_required" in result["review_hits"]


def test_claim_locks_remain_closed():
    result = synthesize_match_story(_payload([_narrative("n1")]))
    story = result["entity_stories"][0]
    assert result["chronological_story_claimed"] is False
    assert result["tactical_plan_truth_claimed"] is False
    assert result["coach_intention_claimed"] is False
    assert result["causality_claimed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert story["chronological_story_claimed"] is False
    assert story["tactical_plan_truth_claimed"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/match_story_synthesis.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
