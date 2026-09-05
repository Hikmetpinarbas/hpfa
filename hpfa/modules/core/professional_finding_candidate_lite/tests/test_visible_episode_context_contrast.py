from hpfa.modules.core.professional_finding_candidate_lite.src.visible_episode_context_contrast import (
    attach_visible_episode_context_contrast,
)


def _finding():
    return {
        "module_id": "professional_finding_candidate_lite_v1",
        "status": "REVIEW_REQUIRED",
        "professional_finding_candidates": [{
            "professional_finding_candidate_id": "pfc1",
            "support": {"supporting_reciprocal_process_chain_candidate_ids": ["c1", "c2"]},
            "finding_challenge_packet": {
                "evaluated_falsifier_families": ["DIRECT_VISIBLE_OUTCOME_CONTRAST"],
                "pending_falsifier_families": ["CONTEXT_DEPENDENCE", "ALTERNATIVE_EXPLANATION"],
            },
            "alternative_explanations": [{"type": "CONTEXT_DEPENDENCE", "state": "NOT_EVALUATED_V1"}],
            "uncertainty": {},
            "claim_output_allowed": False,
            "professional_finding_emitted": False,
        }],
        "hard_block_hits": [],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _reciprocal():
    return {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "reciprocal_process_chain_candidates": [
            {
                "reciprocal_process_chain_candidate_id": "c1",
                "anchor_episode_candidate_id": "e1",
                "anchor_team_identity_candidate_id": "ta",
                "response_episode_candidate_id": "e2",
                "response_team_identity_candidate_id": "tb",
                "counter_response_visible": False,
                "response_consequence_candidate_counts": {"CONTINUE": 1},
                "counter_response_consequence_candidate_counts": {},
            },
            {
                "reciprocal_process_chain_candidate_id": "c2",
                "anchor_episode_candidate_id": "e3",
                "anchor_team_identity_candidate_id": "ta",
                "response_episode_candidate_id": "e4",
                "response_team_identity_candidate_id": "tb",
                "counter_response_visible": False,
                "response_consequence_candidate_counts": {"TURNOVER": 1},
                "counter_response_consequence_candidate_counts": {},
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _activity(*, same_context=False, missing=False):
    rows = [
        {
            "episode_candidate_id": "e1",
            "team_identity_candidate_id": "ta",
            "period_candidate": 1,
            "visible_activity_signals_present": ["CIRCULATION_ACTIVITY_CANDIDATE"],
            "action_family_candidate_counts": {"PASS": 3},
            "zone_candidate_counts": {"MIDDLE_THIRD": 3},
            "channel_candidate_counts": {"CENTRAL": 3},
        },
        {
            "episode_candidate_id": "e2",
            "team_identity_candidate_id": "tb",
            "period_candidate": 1,
            "visible_activity_signals_present": ["DUEL_TACKLE_ACTIVITY_CANDIDATE"],
            "action_family_candidate_counts": {"DUEL": 2},
            "zone_candidate_counts": {"MIDDLE_THIRD": 2},
            "channel_candidate_counts": {"CENTRAL": 2},
        },
        {
            "episode_candidate_id": "e3",
            "team_identity_candidate_id": "ta",
            "period_candidate": 1,
            "visible_activity_signals_present": ["CIRCULATION_ACTIVITY_CANDIDATE"],
            "action_family_candidate_counts": {"PASS": 2},
            "zone_candidate_counts": {"MIDDLE_THIRD": 2},
            "channel_candidate_counts": {"CENTRAL": 2},
        },
        {
            "episode_candidate_id": "e4",
            "team_identity_candidate_id": "tb",
            "period_candidate": 1,
            "visible_activity_signals_present": ["DUEL_TACKLE_ACTIVITY_CANDIDATE" if same_context else "RECOVERY_INTERCEPTION_ACTIVITY_CANDIDATE"],
            "action_family_candidate_counts": {"DUEL" if same_context else "RECOVERY": 2},
            "zone_candidate_counts": {"MIDDLE_THIRD": 2},
            "channel_candidate_counts": {"CENTRAL": 2},
        },
    ]
    if missing:
        rows = rows[:-1]
    return {
        "module_id": "team_episode_activity_lens_lite_v1",
        "status": "PASS",
        "team_episode_activity_rows": rows,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_different_outcomes_can_surface_visible_episode_context_variation_without_causality():
    result = attach_visible_episode_context_contrast(_finding(), _reciprocal(), _activity())
    row = result["professional_finding_candidates"][0]
    contrast = row["finding_challenge_packet"]["visible_episode_context_contrast"]
    assert contrast["state_candidate"] == "VISIBLE_EPISODE_CONTEXT_VARIATION_ACROSS_OUTCOMES_CANDIDATE"
    assert contrast["context_difference_is_causal_explanation"] is False
    assert contrast["context_difference_is_tactical_truth"] is False
    assert result["findings_with_visible_context_variation_candidate_count"] == 1
    assert row["claim_output_allowed"] is False
    assert row["professional_finding_emitted"] is False


def test_same_visible_episode_context_does_not_become_proof_of_context_independence():
    result = attach_visible_episode_context_contrast(_finding(), _reciprocal(), _activity(same_context=True))
    contrast = result["professional_finding_candidates"][0]["finding_challenge_packet"]["visible_episode_context_contrast"]
    assert contrast["state_candidate"] == "NO_VISIBLE_EPISODE_CONTEXT_DIFFERENCE_AT_CURRENT_RESOLUTION"
    assert contrast["absence_of_visible_context_difference_disproves_context_dependence"] is False
    assert result["context_dependence_search_complete_for_final_finding"] is False


def test_missing_episode_activity_keeps_context_contrast_review_required():
    result = attach_visible_episode_context_contrast(_finding(), _reciprocal(), _activity(missing=True))
    contrast = result["professional_finding_candidates"][0]["finding_challenge_packet"]["visible_episode_context_contrast"]
    assert contrast["state_candidate"] == "PARTIAL_CONTEXT_COVERAGE_REVIEW_REQUIRED"
    assert result["context_contrast_partial_coverage_candidate_count"] == 1
    assert result["claim_output_allowed_count"] == 0


def test_claim_locks_remain_closed_after_context_contrast():
    result = attach_visible_episode_context_contrast(_finding(), _reciprocal(), _activity())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["claim_output_allowed_count"] == 0
    assert result["professional_finding_emitted_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
