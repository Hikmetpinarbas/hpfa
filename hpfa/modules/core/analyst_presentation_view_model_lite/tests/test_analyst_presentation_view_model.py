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
                        "claim_ceiling": "argument_candidate_only",
                    },
                    "fusion": {
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
                    "claim_ceiling": "ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY",
                }
            ],
        },
    )
    payload = build_view_model(tmp_path)
    assert payload["surfaces"]["analyst_report"]["state"] == "AVAILABLE"
    assert payload["surfaces"]["observed_replay"]["state"] == "DEGRADED"
    assert payload["surfaces"]["traceback_evidence_drawer"]["state"] == "AVAILABLE"
    assert payload["surfaces"]["match_story"]["state"] == "NOT_EVALUATED"
    assert payload["surfaces"]["six_phase_match_view"]["state"] == "DEGRADED"
    assert payload["surfaces"]["counterevidence_cards"]["state"] == "AVAILABLE"
    assert payload["surfaces"]["broadcast_summary"]["state"] == "DEGRADED"
    assert len(payload["surface_data"]["observed_replay_cards"]) == 1
    assert len(payload["surface_data"]["phase_activity_candidates"]) == 1
    assert len(payload["surface_data"]["counterevidence_cards"]) == 1
    assert payload["surface_data"]["broadcast_sentence_candidates"] == ["Görünür kanıt aday okumayı destekler."]
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
