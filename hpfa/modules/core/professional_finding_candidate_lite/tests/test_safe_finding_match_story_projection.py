from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.safe_finding_match_story_projection import (
    build_safe_finding_match_story_candidates,
)


def _emit_row():
    return {
        "analyst_report_block_id": "sfb_generic_1",
        "entity_scope": "TEAM_IDENTITY_CANDIDATE_GENERIC",
        "context_scope": ["PERIOD_1"],
        "SAFE_MEANING": "A robust recurrent visible process candidate is supported in the observed match-local scope.",
        "WHERE_WHEN": "The statement is restricted to the admitted match-local evidence scope.",
        "SUPPORT": "Observed support=5; independent support=2.",
        "COUNTEREVIDENCE": "Visible failure variants=1; divergence variants=1; counterevidence refs=2. No-visible-followup is not failure.",
        "ALTERNATIVE_EXPLANATIONS": "Visible alternatives/challenges: CONTEXT_DEPENDENCE",
        "alternative_explanations": [{"type": "CONTEXT_DEPENDENCE", "causal_truth": False}],
        "ANALYST_ACTION": "Review recurrent examples and adverse twins before using the finding.",
        "withdrawal_condition": "Withdraw if recurrence, independence, counterevidence or context evidence changes materially.",
        "FORBIDDEN_INFERENCE": [
            "causality",
            "coach intention",
            "dominance",
            "team shape",
            "true pressure geometry",
        ],
        "finding_status": "EMIT",
        "professional_finding_emitted": True,
        "claim_output_allowed": True,
    }


def _payload(rows=None):
    return {
        "module_id": "sequence_safe_finding_binding_lite_v1",
        "status": "PASS",
        "analyst_report_blocks": rows if rows is not None else [_emit_row()],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_emit_finding_projects_to_claim_safe_match_story_candidate():
    result = build_safe_finding_match_story_candidates(_payload())
    row = result["match_story_candidates"][0]
    assert result["status"] == "PASS"
    assert result["match_story_candidate_count"] == 1
    assert row["source_professional_finding_ref"] == "sfb_generic_1"
    assert "No-visible-followup is not failure" in row["match_story_candidate_text"]
    assert "CONTEXT_DEPENDENCE" in row["match_story_candidate_text"]
    assert row["story_alternative_explanations"] == "Visible alternatives/challenges: CONTEXT_DEPENDENCE"
    assert row["story_alternative_explanation_objects"] == [{"type": "CONTEXT_DEPENDENCE", "causal_truth": False}]
    assert row["story_order_is_football_chronology_truth"] is False
    assert row["story_is_tactical_phase_truth"] is False
    assert row["story_is_formation_or_shape_truth"] is False
    assert row["story_is_true_pressure_truth"] is False
    assert row["story_is_coach_intention_truth"] is False
    assert row["story_is_dominance_truth"] is False
    assert row["story_is_causality_truth"] is False
    assert row["canonical_event_count"] == "UNKNOWN"
    assert row["true_action_count"] == "UNKNOWN"
    assert row["production_release"] is False


def test_upstream_review_required_never_projects_story_even_with_emit_row():
    payload = _payload()
    payload["status"] = "REVIEW_REQUIRED"
    result = build_safe_finding_match_story_candidates(payload)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["match_story_candidate_count"] == 0
    assert result["non_emitting_finding_rows_skipped"] == 1
    assert "upstream_review_required" in result["review_hits"]


def test_alternative_only_challenge_is_retained_in_story_surface():
    row = _emit_row()
    row["COUNTEREVIDENCE"] = "Visible failure variants=0; divergence variants=0; counterevidence refs=0. No-visible-followup=0 is reported separately and is not failure."
    result = build_safe_finding_match_story_candidates(_payload([row]))
    story = result["match_story_candidates"][0]
    assert result["status"] == "PASS"
    assert "CONTEXT_DEPENDENCE" in story["story_alternative_explanations"]
    assert "CONTEXT_DEPENDENCE" in story["match_story_candidate_text"]


def test_downgrade_and_abstain_never_enter_match_story():
    downgraded = _emit_row()
    downgraded["finding_status"] = "DOWNGRADE"
    downgraded["professional_finding_emitted"] = False
    downgraded["claim_output_allowed"] = False
    abstain = _emit_row()
    abstain["analyst_report_block_id"] = "sfb_generic_2"
    abstain["finding_status"] = "ABSTAIN"
    abstain["professional_finding_emitted"] = False
    abstain["claim_output_allowed"] = False
    result = build_safe_finding_match_story_candidates(_payload([downgraded, abstain]))
    assert result["match_story_candidate_count"] == 0
    assert result["non_emitting_finding_rows_skipped"] == 2


def test_emit_label_without_upstream_claim_gate_is_review_required_not_story():
    row = _emit_row()
    row["claim_output_allowed"] = False
    result = build_safe_finding_match_story_candidates(_payload([row]))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["match_story_candidate_count"] == 0
    assert "emit_row_without_claim_gate:sfb_generic_1" in result["review_hits"]


def test_missing_counterevidence_alternative_or_withdrawal_surface_blocks_story_projection():
    row = _emit_row()
    row["COUNTEREVIDENCE"] = ""
    result = build_safe_finding_match_story_candidates(_payload([row]))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["match_story_candidate_count"] == 0


def test_forbidden_inference_surface_must_remain_explicit():
    row = _emit_row()
    row["FORBIDDEN_INFERENCE"] = ["causality"]
    result = build_safe_finding_match_story_candidates(_payload([row]))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["match_story_candidate_count"] == 0
    assert "emit_row_forbidden_inference_surface_incomplete:sfb_generic_1" in result["review_hits"]


def test_upstream_truth_or_release_lock_breach_fails_closed():
    payload = _payload()
    payload["production_release"] = True
    result = build_safe_finding_match_story_candidates(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert result["match_story_candidate_count"] == 0
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path(__file__).resolve().parents[1] / "src" / "safe_finding_match_story_projection.py"
    text = source.read_text(encoding="utf-8")
    forbidden = ["Genclerbirligi", "Fenerbahce", "15.08.2026"]
    assert not any(token in text for token in forbidden)
