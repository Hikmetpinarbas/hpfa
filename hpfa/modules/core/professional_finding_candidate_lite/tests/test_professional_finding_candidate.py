from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.professional_finding_candidate import (
    build_professional_finding_candidates,
    write_outputs,
)


def _inputs(*, repeat=3, scopes=3, outcomes=2, incomplete=0, segment_state="NOT_SINGLE_EPISODE_ONLY_VISIBLE"):
    chain_ids = [f"c{i}" for i in range(repeat)]
    episode_scopes = [
        {
            "anchor_episode_candidate_id": f"a{i if scopes > 1 else 0}",
            "response_episode_candidate_id": f"r{i if scopes > 1 else 0}",
            "counter_response_episode_candidate_id": None,
        }
        for i in range(repeat)
    ]
    reciprocal = {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "process_variant_profiles": [{
            "process_variant_profile_candidate_id": "pv1",
            "process_family_signature_candidate": {"anchor_action_families": ["PASS"], "response_action_families": ["PASS", "TURNOVER"]},
            "reciprocal_process_chain_candidate_ids": chain_ids,
            "visible_repeat_count_candidate": repeat,
            "unique_episode_scope_count_candidate": scopes,
            "distinct_visible_outcome_signature_count_candidate": outcomes,
            "incomplete_episode_binding_count": incomplete,
            "episode_scope_candidates": episode_scopes,
        }],
        "defeasible_process_finding_inputs": [
            {
                "reciprocal_process_chain_candidate_id": chain_id,
                "counterevidence_chain_ids": [chain_ids[(idx + 1) % repeat]] if outcomes > 1 and repeat > 1 else [],
                "dependent_support_chain_ids": [chain_ids[(idx + 1) % repeat]] if outcomes == 1 and repeat > 1 else [],
            }
            for idx, chain_id in enumerate(chain_ids)
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    robustness = {
        "module_id": "process_robustness_lens_lite_v1",
        "status": "PASS",
        "process_robustness_rows": [{
            "process_variant_profile_candidate_id": "pv1",
            "segment_only_falsifier_state_candidate": segment_state,
            "segment_concentration_share_candidate": 1.0 if scopes == 1 else 0.5,
            "opponent_symmetry_falsifier_state_candidate": "VISIBLE_BOTH_ANCHOR_SIDES",
            "max_anchor_actor_chain_presence_share_candidate": 0.5,
            "trace_membership_uniqueness_ratio_candidate": 0.8,
            "visible_outcome_normalized_entropy_candidate": 0.9 if outcomes > 1 else 0.0,
            "leave_one_episode_scope_out_repeat_survives_candidate": scopes > 2,
            "leave_top_anchor_actor_out_repeat_survives_candidate": True,
            "player_outlier_search_state_candidate": "EVALUATED_VISIBLE_ACTOR_CONCENTRATION",
        }],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    metric = {
        "module_id": "process_metric_profile_lite_v1",
        "status": "PASS",
        "process_metric_rows": [{
            "process_variant_profile_candidate_id": "pv1",
            "M_PROCESS_REPEAT_POPULATION_SHARE_CANDIDATE": 0.1,
            "M_PROCESS_EPISODE_DISPERSION_CANDIDATE": 0.75,
            "M_PROCESS_VISIBLE_OUTCOME_ENTROPY_CANDIDATE": 0.9 if outcomes > 1 else 0.0,
            "M_PROCESS_RECURRENCE_SURFACE_ROBUSTNESS_COMPOSITE_CANDIDATE": 0.7,
        }],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    reconciliation = {
        "module_id": "match_reconciliation_ledger_lite_v2",
        "status": "PASS",
        "reciprocal_consistency_edges": [
            {
                "reciprocal_process_chain_candidate_id": chain_id,
                "roles": {
                    "anchor": {"actor_identity_candidate_ids": [f"pa{idx}"]},
                    "response": {"actor_identity_candidate_ids": [f"pb{idx}"]},
                },
            }
            for idx, chain_id in enumerate(chain_ids)
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    return reciprocal, robustness, metric, reconciliation


def test_multi_episode_outcome_variation_builds_qualified_but_unreleased_argument():
    result = build_professional_finding_candidates(*_inputs())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["professional_finding_candidate_count"] == 1
    row = result["professional_finding_candidates"][0]
    assert row["finding_state_candidate"] == "QUALIFIED_MULTI_EPISODE_REPEAT_WITH_OUTCOME_VARIATION"
    assert "appeared 3 times across 3 admitted episode scopes" in row["safe_analyst_sentence_candidate"]
    assert row["claim_output_allowed"] is False
    assert row["professional_finding_emitted"] is False
    assert row["counterevidence"]["direct_visible_outcome_counterevidence_chain_ids"]
    assert row["withdrawal_condition"]


def test_finding_challenge_packet_rehabilitates_analogue_and_robustness_surfaces():
    result = build_professional_finding_candidates(*_inputs())
    row = result["professional_finding_candidates"][0]
    challenge = row["finding_challenge_packet"]
    assert challenge["challenge_state_candidate"] == "PARTIAL_MATCH_LOCAL_CHALLENGE_EVALUATED"
    assert challenge["different_visible_outcome_analogue_present"] is True
    assert challenge["different_visible_outcome_analogue_chain_ids"]
    assert "DIRECT_VISIBLE_OUTCOME_CONTRAST" in challenge["evaluated_falsifier_families"]
    assert "SEGMENT_ONLY" in challenge["evaluated_falsifier_families"]
    assert "PLAYER_OUTLIER" in challenge["evaluated_falsifier_families"]
    assert "OPPONENT_SYMMETRY" in challenge["evaluated_falsifier_families"]
    assert "CONTEXT_DEPENDENCE" in challenge["pending_falsifier_families"]
    assert challenge["leave_one_episode_scope_out"]["repeat_survives_candidate"] is True
    assert challenge["player_concentration"]["leave_top_anchor_actor_out_repeat_survives_candidate"] is True
    assert challenge["counter_search_complete_for_final_finding"] is False
    assert challenge["alternative_explanation_search_complete"] is False
    assert challenge["challenge_packet_is_final_finding"] is False
    assert result["finding_challenge_packet_count"] == 1
    assert result["findings_with_direct_outcome_counterevidence_count"] == 1
    assert result["finding_challenge_complete_for_final_finding_count"] == 0


def test_no_visible_different_outcome_analogue_is_not_confirmation():
    result = build_professional_finding_candidates(*_inputs(outcomes=1))
    challenge = result["professional_finding_candidates"][0]["finding_challenge_packet"]
    assert challenge["different_visible_outcome_analogue_present"] is False
    assert challenge["no_visible_counterexample_is_confirmation"] is False
    assert challenge["counter_search_complete_for_final_finding"] is False


def test_single_episode_repeat_is_fragile_local_repeat():
    result = build_professional_finding_candidates(*_inputs(scopes=1, outcomes=1, segment_state="SEGMENT_ONLY_RISK_PRESENT"))
    row = result["professional_finding_candidates"][0]
    assert row["finding_state_candidate"] == "FRAGILE_LOCAL_REPEAT_ONLY"
    assert "local repeat" in row["safe_analyst_sentence_candidate"]
    assert row["finding_challenge_packet"]["segment_only"]["state"] == "SEGMENT_ONLY_RISK_PRESENT"


def test_incomplete_episode_binding_blocks_generalization():
    result = build_professional_finding_candidates(*_inputs(incomplete=1))
    row = result["professional_finding_candidates"][0]
    assert row["finding_state_candidate"] == "BLOCKED_INCOMPLETE_EPISODE_BINDING"
    assert "lacks complete admitted episode binding" in row["safe_analyst_sentence_candidate"]


def test_support_is_traceable_to_players_episodes_and_metrics():
    result = build_professional_finding_candidates(*_inputs())
    row = result["professional_finding_candidates"][0]
    support = row["support"]
    assert len(support["supporting_reciprocal_process_chain_candidate_ids"]) == 3
    assert support["supporting_episode_candidate_ids"]
    assert support["supporting_actor_identity_candidate_ids"]
    assert support["anchor_actor_identity_candidate_ids"]
    assert support["response_actor_identity_candidate_ids"]
    assert support["metric_candidate_values"]["M_PROCESS_RECURRENCE_SURFACE_ROBUSTNESS_COMPOSITE_CANDIDATE"] == 0.7
    assert row["alternative_explanations"]
    assert row["uncertainty"]["alternative_explanation_search_complete"] is False


def test_upstream_review_never_opens_claim_output():
    reciprocal, robustness, metric, reconciliation = _inputs()
    reciprocal["status"] = "REVIEW_REQUIRED"
    result = build_professional_finding_candidates(reciprocal, robustness, metric, reconciliation)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["claim_output_allowed_count"] == 0
    assert result["professional_finding_emitted_count"] == 0


def test_output_locks(tmp_path: Path):
    result = build_professional_finding_candidates(*_inputs())
    paths = write_outputs(result, tmp_path)
    text = paths["summary"].read_text(encoding="utf-8")
    assert "finding_challenge_packet_count=1" in text
    assert "finding_challenge_complete_for_final_finding_count=0" in text
    assert "claim_output_allowed_count=0" in text
    assert "professional_finding_emitted_count=0" in text
    assert "production_release=false" in text


def test_no_sample_match_identity_leak():
    root = Path(__file__).resolve().parents[1] / "src"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py")).casefold()
    forbidden = ("genclerbirligi", "fenerbahce", "15.08.2026", "samsunspor", "galatasaray", "besiktas")
    assert not any(token in text for token in forbidden)
