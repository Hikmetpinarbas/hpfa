import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_presentation_view_model_lite" / "src"
sys.path.insert(0, str(SRC))

from analyst_presentation_view_model import build_view_model, write_view_model

def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")

def test_fail_closed_when_full_spine_missing(tmp_path):
    payload = build_view_model(tmp_path)
    assert payload["status"] == "FAIL_CLOSED"
    assert payload["decision"] == "UPSTREAM_FULL_SPINE_MISSING"
    assert payload["surfaces"]["observed_replay"]["state"] == "MISSING"
    assert payload["production_release"] is False

def test_surface_states_preserve_claim_ceiling(tmp_path):
    _write_json(
        tmp_path / "active_match_full_spine_v1.json",
        {
            "status": "REVIEW_REQUIRED",
            "current_invocation_artifacts": [
                str(tmp_path / "analyst_episode_locator_lite_v1.json"),
                str(tmp_path / "match_local_identity_candidates_lite_v1.json"),
                str(tmp_path / "trackable_action_trace_candidates_lite_v1.json"),
                str(tmp_path / "trackable_action_consequence_candidates_lite_v1.json"),
            ],
            "rich_multiformat_analysis_lattice": {
                "phase_state_candidates": [
                    {
                        "phase_state_candidate_id": "psc_1",
                        "labels": ["LOSS_TRANSITION_ACTIVITY_CANDIDATE"],
                        "phase_truth": False,
                    }
                ]
            },
            "intelligence_chains": [
                {
                    "argument": {
                        "argument_id": "arg_1",
                        "argument_family": "progression_without_terminal_value",
                        "status": "ARGUMENT_SUPPORTED",
                        "counter_scenarios": ["sample_window_may_understate_terminal_output"],
                        "withdrawal_conditions": ["terminal_action_value_becomes_high_in_same_window"],
                        "context_refs": ["context_1"],
                        "supporting_refs": ["support_1"],
                        "contradicting_refs": [],
                        "claim_ceiling": "argument_candidate_only",
                    },
                    "fusion": {
                        "packet_id": "packet_1",
                        "contradicting_refs": [],
                        "independence_state": "INDEPENDENCE_NOT_ADMITTED",
                    },
                    "safe_sentence": {
                        "safe_sentence_candidate_tr": "Görünür kanıt aday okumayı destekler."
                    },
                }
            ],
        },
    )
    (tmp_path / "HPFA_ANALYST_REPORT.txt").write_text("candidate", encoding="utf-8")
    _write_json(
        tmp_path / "analyst_episode_locator_lite_v1.json",
        {
            "status": "REVIEW_REQUIRED",
            "episode_candidates": [
                {
                    "episode_candidate_id": "ep_1",
                    "start_second_candidate": 10,
                    "end_second_candidate": 20,
                    "action_family_distribution": {"PASS": 2},
                    "context_refs": ["ctx_1"],
                    "row_nucleus_refs": ["row_1"],
                    "action_occurrence_eligible_context_refs": ["ctx_1"],
                    "support_only_context_refs": [],
                    "review_debt_refs": [],
                    "claim_ceiling": "ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY",
                }
            ],
        },
    )
    _write_json(
        tmp_path / "match_local_identity_candidates_lite_v1.json",
        {"actor_identity_candidates": [{
            "actor_identity_candidate_id": "actor_1",
            "actor_aliases_raw": ["9. Player One (1)"],
            "team_identity_candidate_id": "team_1",
            "team_normalized_key": "team_one",
            "identity_scope": "MATCH_LOCAL_CANDIDATE_ONLY",
            "validated_player_identity": False,
        }]},
    )
    _write_json(
        tmp_path / "trackable_action_trace_candidates_lite_v1.json",
        {"trackable_action_trace_candidates": [{
            "trackable_action_trace_candidate_id": "trace_1",
            "actor_identity_candidate_id": "actor_1",
            "team_identity_candidate_id": "team_1",
            "action_family_candidates": ["PASS"],
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "period_candidate": "1",
            "supporting_evidence_atom_ids": ["atom_1"],
        }]},
    )
    _write_json(
        tmp_path / "trackable_action_consequence_candidates_lite_v1.json",
        {"trackable_action_consequence_candidates": [{
            "trackable_action_consequence_candidate_id": "consequence_1",
            "anchor_trackable_action_trace_candidate_id": "trace_1",
            "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
            "visible_follow_up_trace_ids": ["trace_2"],
        }]},
    )
    payload = build_view_model(tmp_path)
    assert payload["surfaces"]["analyst_report"]["state"] == "AVAILABLE"
    assert payload["surfaces"]["observed_replay"]["state"] == "DEGRADED"
    assert payload["surfaces"]["traceback_evidence_drawer"]["state"] == "AVAILABLE"
    assert payload["surfaces"]["match_story"]["state"] == "DEGRADED"
    assert payload["surfaces"]["mechanism_cards"]["state"] == "AVAILABLE"
    assert payload["surfaces"]["six_phase_match_view"]["state"] == "DEGRADED"
    assert payload["surfaces"]["counterevidence_cards"]["state"] == "AVAILABLE"
    assert payload["surfaces"]["player_process_cards"]["state"] == "DEGRADED"
    assert payload["surfaces"]["broadcast_summary"]["state"] == "DEGRADED"
    assert len(payload["surface_data"]["observed_replay_cards"]) == 1
    assert len(payload["surface_data"]["phase_activity_candidates"]) == 1
    assert len(payload["surface_data"]["counterevidence_cards"]) == 1
    assert len(payload["surface_data"]["mechanism_cards"]) == 1
    assert len(payload["surface_data"]["player_process_cards"]) == 1
    player = payload["surface_data"]["player_process_cards"][0]
    assert player["actor_identity_candidate_id"] == "actor_1"
    assert player["trace_candidate_count"] == 1
    assert player["action_family_candidate_counts"] == {"PASS": 1}
    assert player["trace_candidate_count_is_physical_action_count"] is False
    assert player["process_participation_is_off_ball_tactical_role"] is False
    mechanism = payload["surface_data"]["mechanism_cards"][0]
    assert mechanism["process_family"] == "progression_without_terminal_value"
    assert mechanism["nominal_chain_count"] == 1
    assert mechanism["nominal_counts_are_independent_support"] is False
    assert payload["surface_data"]["match_story"]["emitted_mechanism_count"] == 1
    assert payload["surface_data"]["match_story"]["forced_minimum_disabled"] is True
    assert payload["surface_data"]["broadcast_sentence_candidates"] == ["Görünür kanıt aday okumayı destekler."]
    traceback = payload["surface_data"]["traceback_index"]
    assert traceback["scope"] == "REFERENCE_ID_GRAPH_ONLY_NOT_RAW_ROW_RENDER"
    assert traceback["episodes"]["ep_1"]["row_nucleus_refs"] == ["row_1"]
    mechanism_trace = traceback["mechanisms"]["mechanism:progression_without_terminal_value:UNKNOWN_RELATION_SCOPE:UNKNOWN_ANALYSIS_ROUTE"]
    assert mechanism_trace["argument_ids"] == ["arg_1"]
    assert mechanism_trace["packet_ids"] == ["packet_1"]
    assert mechanism_trace["context_refs"] == ["context_1"]
    assert traceback["players"]["actor_1"]["trace_candidate_ids"] == ["trace_1"]
    assert traceback["players"]["actor_1"]["consequence_candidate_ids_by_trace"]["trace_1"] == ["consequence_1"]
    assert traceback["players"]["actor_1"]["supporting_evidence_atom_ids"] == ["atom_1"]
    assert payload["interaction_provenance_may_affect_evidence"] is False
    assert payload["client_may_create_new_football_semantics"] is False
    assert payload["closed_claims"]["canonical_event_count"] == "UNKNOWN"

def test_write_view_model_is_deterministic_for_same_inputs(tmp_path):
    _write_json(tmp_path / "active_match_full_spine_v1.json", {"status": "REVIEW_REQUIRED"})
    first = write_view_model(tmp_path)
    first_bytes = (tmp_path / "analyst_presentation_view_model_lite_v1.json").read_bytes()
    second = write_view_model(tmp_path)
    second_bytes = (tmp_path / "analyst_presentation_view_model_lite_v1.json").read_bytes()
    assert first == second
    assert first_bytes == second_bytes

def test_stale_optional_artifacts_are_not_promoted(tmp_path):
    _write_json(
        tmp_path / "active_match_full_spine_v1.json",
        {"status": "REVIEW_REQUIRED", "current_invocation_artifacts": []},
    )
    _write_json(tmp_path / "analyst_episode_locator_lite_v1.json", {"status": "SMOKE_PASS"})
    payload = build_view_model(tmp_path)
    states = {item["name"]: item["state"] for item in payload["artifact_provenance"]}
    assert states["analyst_episode_locator_lite_v1.json"] == "STALE_NOT_CURRENT_INVOCATION"
    assert payload["surfaces"]["observed_replay"]["state"] == "MISSING"
    assert payload["surfaces"]["counterevidence_cards"]["state"] == "NOT_EVALUATED"
