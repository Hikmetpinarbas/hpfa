from pathlib import Path

from hpfa.modules.core.analyst_report_block_composer_lite.src.match_story_report_projection import (
    compose_match_story_report,
)


def _story(entity="team_a", shared=None):
    shared = shared or []
    return {
        "entity_scope": entity,
        "story_state": "RECURRENT_PROCESS_SET_WITH_VISIBLE_COUNTEREVIDENCE",
        "source_narrative_ids": ["n1", "n2"],
        "process_narrative_count": 2,
        "recurrent_process_count": 2,
        "robust_recurrent_process_count": 1,
        "counterevidence_bearing_process_count": 1,
        "context_sensitive_process_count": 1,
        "null_evaluated_process_count": 1,
        "nominal_support_sum": 6,
        "unique_trace_ref_count": 5 if shared else 6,
        "unique_trace_refs": ["v1", "v2", "v3", "v4", "v5"] if shared else ["v1", "v2", "v3", "v4", "v5", "v6"],
        "shared_trace_refs_across_processes": shared,
        "nominal_support_is_independent_evidence_count": False,
        "cross_process_support_independence_proven": False,
        "story_tr": "Takımın görünür süreçleri birlikte değerlendirildi; tekrar eden örnekler ve karşı örnekler aynı sentezde tutuldu.",
        "safe_meaning_tr": "Admitted görünür süreçlerin tekrar, sonuç dengesi ve karşı örnek profili birlikte özetlenmiştir.",
        "forbidden_inference": ["coach intention", "causality", "dominance"],
        "withdrawal_condition": "Recompute if source narratives or exact trace cohorts change.",
        "chronological_story_claimed": False,
        "tactical_plan_truth_claimed": False,
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY",
    }


def _payload(stories, status="PASS"):
    return {
        "module_id": "match_story_synthesis_lite_v1",
        "status": status,
        "decision": "MATCH_LOCAL_PROCESS_STORY_SYNTHESIZED",
        "entity_stories": stories,
        "entity_story_count": len(stories),
        "hard_block_hits": [],
        "review_hits": [],
        "chronological_story_claimed": False,
        "tactical_plan_truth_claimed": False,
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY",
    }


def test_match_story_becomes_analyst_report_candidate_without_claim_strengthening():
    result = compose_match_story_report(_payload([_story()]))
    assert result["status"] == "SMOKE_PASS"
    block = result["report_blocks"][0]
    assert block["block_family"] == "match_story_analyst_reading_candidate"
    assert block["entity_scope"] == "team_a"
    assert block["source_narrative_ids"] == ["n1", "n2"]
    assert block["nominal_support_sum"] == 6
    assert block["unique_trace_ref_count"] == 6
    assert block["nominal_support_is_independent_evidence_count"] is False
    assert block["cross_process_support_independence_proven"] is False
    assert block["claim_output_allowed"] is False
    assert block["production_report_allowed"] is False
    assert block["final_report_allowed"] is False
    assert block["canonical_event_count"] == "UNKNOWN"
    assert block["true_action_count"] == "UNKNOWN"
    assert block["production_release"] is False


def test_shared_trace_refs_survive_as_review_not_independent_support():
    result = compose_match_story_report(_payload([_story(shared=["v3"])]))
    assert result["status"] == "REVIEW_REQUIRED"
    assert "shared_trace_refs_review:team_a" in result["review_hits"]
    block = result["report_blocks"][0]
    assert block["status"] == "REVIEW_REQUIRED"
    assert block["shared_trace_refs_across_processes"] == ["v3"]
    assert block["cross_process_support_independence_proven"] is False


def test_review_upstream_stays_review_required():
    result = compose_match_story_report(_payload([_story()], status="REVIEW_REQUIRED"))
    assert result["status"] == "REVIEW_REQUIRED"
    assert "source_review_required" in result["review_hits"]
    assert result["report_blocks"][0]["status"] == "REVIEW_REQUIRED"


def test_nominal_support_cannot_be_promoted_to_independent_evidence():
    story = _story()
    story["nominal_support_is_independent_evidence_count"] = True
    result = compose_match_story_report(_payload([story]))
    assert result["status"] == "FAIL_CLOSED"
    assert "story_nominal_support_independence_lock_breach:team_a" in result["hard_block_hits"]


def test_cross_process_independence_cannot_be_fabricated():
    story = _story()
    story["cross_process_support_independence_proven"] = True
    result = compose_match_story_report(_payload([story]))
    assert result["status"] == "FAIL_CLOSED"
    assert "story_cross_process_independence_lock_breach:team_a" in result["hard_block_hits"]


def test_unique_trace_count_mismatch_fails_closed():
    story = _story()
    story["unique_trace_ref_count"] = 99
    result = compose_match_story_report(_payload([story]))
    assert result["status"] == "FAIL_CLOSED"
    assert "unique_trace_count_mismatch:team_a" in result["hard_block_hits"]


def test_story_claim_lock_breach_fails_closed():
    story = _story()
    story["causality_claimed"] = True
    result = compose_match_story_report(_payload([story]))
    assert result["status"] == "FAIL_CLOSED"
    assert "story_causality_lock_breach:team_a" in result["hard_block_hits"]


def test_wrong_source_claim_ceiling_fails_closed():
    payload = _payload([_story()])
    payload["claim_ceiling"] = "TACTICAL_TRUTH"
    result = compose_match_story_report(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "source_claim_ceiling_mismatch" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/analyst_report_block_composer_lite/src/match_story_report_projection.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
