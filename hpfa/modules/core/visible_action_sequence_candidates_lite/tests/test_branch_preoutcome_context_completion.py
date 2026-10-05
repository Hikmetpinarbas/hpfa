from safe_finding_admission_current_v1 import _branch_preoutcome_context_enrichment


def test_unique_score_state_and_single_process_family_complete_branch_context():
    source = {
        "anchor_centered_sequence_branch_maps": [{
            "comparable_set_id": "set_1",
            "team_identity_candidate_id": "team_1",
            "period_candidate": "1",
            "anchor_time_candidate": 100.0,
            "anchor_action_family_counts": {"PASS": 1},
        }],
        "safe_finding_handoff_candidates": [{
            "safe_finding_handoff_candidate_id": "sfh_1",
            "source_comparable_set_id": "set_1",
        }],
    }
    admission = {
        "safe_finding_admission_decisions": [{
            "source_safe_finding_handoff_ref": "sfh_1",
        }]
    }
    rich = {
        "game_state_process_mix_context": {
            "profiles": [{
                "team_identity_candidate_id": "team_1",
                "segment_start_second_candidate": 90.0,
                "segment_end_second_candidate": 110.0,
                "score_state_candidate": {"team_1": 1, "team_2": 0},
            }]
        }
    }
    participation = {
        "process_participation_candidates": [{
            "semantic_role": "CONTEXT_INTERVAL",
            "team_identity_candidate_id": "team_1",
            "period_candidate": "1",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "start_candidate": 95.0,
            "end_candidate": 105.0,
        }]
    }

    out = _branch_preoutcome_context_enrichment(source, admission, rich, participation)
    profile = out["profiles_by_handoff_ref"]["sfh_1"]

    assert profile["state"] == "PRE_BRANCH_CONTEXT_ENRICHED_GAME_STATE_AND_PROCESS"
    assert profile["branch_comparison_context_complete"] is True