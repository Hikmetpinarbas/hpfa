import json
from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.visible_episode_context_contrast import (
    attach_visible_episode_context_contrast,
)


ROOT = Path(__file__).resolve().parents[5]
CONTEXT_STANDARDIZATION_CONTRACT = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "professional_finding_candidate_lite"
    / "contract"
    / "context_standardized_process_profile_lite_v1.json"
)


def test_period_change_alone_does_not_create_visible_context_variation():
    finding = {
        "module_id": "professional_finding_candidate_lite_v1",
        "status": "REVIEW_REQUIRED",
        "professional_finding_candidates": [{
            "professional_finding_candidate_id": "p1",
            "support": {
                "visible_repeat_count_candidate": 2,
                "supporting_reciprocal_process_chain_candidate_ids": ["c1", "c2"],
            },
            "finding_challenge_packet": {
                "evaluated_falsifier_families": [],
                "pending_falsifier_families": ["CONTEXT_DEPENDENCE", "THRESHOLD_SENSITIVITY", "FAILED_TRACE_SUPPORT"],
            },
            "alternative_explanations": [],
            "uncertainty": {},
        }],
        "hard_block_hits": [],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    reciprocal = {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "reciprocal_process_chain_candidates": [
            {
                "reciprocal_process_chain_candidate_id": "c1",
                "anchor_episode_candidate_id": "a1",
                "anchor_team_identity_candidate_id": "ta",
                "response_episode_candidate_id": "r1",
                "response_team_identity_candidate_id": "tb",
                "counter_response_visible": False,
                "response_consequence_candidate_counts": {"CONTINUE": 1},
                "counter_response_consequence_candidate_counts": {},
                "supporting_trackable_action_trace_candidate_ids": ["t1"],
            },
            {
                "reciprocal_process_chain_candidate_id": "c2",
                "anchor_episode_candidate_id": "a2",
                "anchor_team_identity_candidate_id": "ta",
                "response_episode_candidate_id": "r2",
                "response_team_identity_candidate_id": "tb",
                "counter_response_visible": False,
                "response_consequence_candidate_counts": {"TURNOVER": 1},
                "counter_response_consequence_candidate_counts": {},
                "supporting_trackable_action_trace_candidate_ids": ["t2"],
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    def activity_row(episode, team, period):
        return {
            "episode_candidate_id": episode,
            "team_identity_candidate_id": team,
            "period_candidate": period,
            "visible_activity_signals_present": ["CIRCULATION_ACTIVITY_CANDIDATE"],
            "action_family_candidate_counts": {"PASS": 2},
            "zone_candidate_counts": {"MIDDLE_THIRD": 2},
            "channel_candidate_counts": {"CENTRAL": 2},
        }
    activity = {
        "module_id": "team_episode_activity_lens_lite_v1",
        "status": "PASS",
        "team_episode_activity_rows": [
            activity_row("a1", "ta", 1),
            activity_row("r1", "tb", 1),
            activity_row("a2", "ta", 2),
            activity_row("r2", "tb", 2),
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    result = attach_visible_episode_context_contrast(finding, reciprocal, activity)
    row = result["professional_finding_candidates"][0]
    contrast = row["finding_challenge_packet"]["visible_episode_context_contrast"]
    assert contrast["state_candidate"] == "NO_VISIBLE_EPISODE_CONTEXT_DIFFERENCE_AT_CURRENT_RESOLUTION"
    assert contrast["period_reported_but_not_used_as_activity_fingerprint"] is True
    assert row["uncertainty"]["period_alone_does_not_create_context_variation"] is True
    assert result["claim_output_allowed_count"] == 0


def test_cross_match_context_standardization_stays_contract_only_until_game_state_is_admitted():
    contract = json.loads(CONTEXT_STANDARDIZATION_CONTRACT.read_text(encoding="utf-8"))
    required = set(contract["required_context_fields_for_standardization"])
    policy = contract["field_admission_policy"]
    state = contract["current_execution_state"]

    assert {"minute_state", "score_state", "manpower_state", "venue_state", "eligible_exposure"} <= required
    assert policy["missing_required_context_is_zero"] is False
    assert policy["missing_required_context_is_neutral_state"] is False
    assert policy["provider_label_is_context_truth"] is False
    assert state["runtime_context_standardization_evaluated"] is False
    assert state["model_implementation_present"] is False
    assert state["model_execution_allowed"] is False
    assert state["standardized_rate_output_allowed"] is False
    assert state["cross_match_team_tendency_claim_allowed"] is False
    assert state["tactical_adaptation_claim_allowed"] is False
    assert state["coach_intention_claim_allowed"] is False
    assert state["causal_score_effect_claim_allowed"] is False
    assert contract["canonical_event_count"] == "UNKNOWN"
    assert contract["true_action_count"] == "UNKNOWN"
    assert contract["production_release"] is False
