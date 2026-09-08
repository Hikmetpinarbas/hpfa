import json

from hpfa.modules.core.active_match_spine_runner.src.phase_dynamics_intelligence_lane import (
    INPUTS,
    run_phase_dynamics_intelligence_lane,
)


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_missing_inputs_fail_closed(tmp_path):
    payload = run_phase_dynamics_intelligence_lane(tmp_path)
    assert payload["status"] == "FAIL_CLOSED"
    assert payload["production_release"] is False
    assert payload["canonical_event_count"] == "UNKNOWN"


def test_lane_writes_all_three_outputs(monkeypatch, tmp_path):
    import hpfa.modules.core.active_match_spine_runner.src.phase_dynamics_intelligence_lane as lane

    for filename in INPUTS.values():
        _write(tmp_path / filename, {"placeholder": True})

    interaction = {
        "module_id": "phase_conditioned_interaction_projection_v1",
        "status": "PASS",
        "interaction_episode_candidate_count": 1,
        "interaction_episode_candidates": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    dynamics = {
        "module_id": "observed_match_dynamics_projection_v1",
        "status": "PASS",
        "observed_match_dynamics_candidate_count": 1,
        "observed_match_dynamics_candidates": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    bridge = {
        "module_id": "phase_dynamics_interaction_bridge_v1",
        "status": "PASS",
        "phase_dynamics_interaction_candidate_count": 1,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }

    monkeypatch.setattr(lane, "build_phase_conditioned_interactions", lambda *args: interaction)
    monkeypatch.setattr(lane, "build_observed_match_dynamics", lambda *args: dynamics)
    monkeypatch.setattr(lane, "build_phase_dynamics_interaction_bridge", lambda *args: bridge)

    result = run_phase_dynamics_intelligence_lane(tmp_path)
    assert result["status"] == "SMOKE_PASS"
    assert result["phase_dynamics_interaction_candidate_count"] == 1
    for path in result["outputs"].values():
        assert __import__("pathlib").Path(path).is_file()
    assert result["tempo_truth"] is False
    assert result["momentum_truth"] is False
    assert result["causal_truth"] is False


def test_no_sample_match_identity_leak(tmp_path):
    payload = run_phase_dynamics_intelligence_lane(tmp_path)
    rendered = str(payload)
    assert "Genclerbirligi" not in rendered
    assert "Fenerbahce" not in rendered
    assert "Galatasaray" not in rendered
