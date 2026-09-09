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
    assert payload["progression_effectiveness_truth"] is False
    assert payload["ball_security_truth"] is False
    assert payload["loss_exposure_truth"] is False
    assert payload["progression_safe_finding_engineering_envelope_complete"] is False
    assert payload["physical_active_match_evidence_present"] is False
    assert payload["professional_finding_emitted"] is False


def test_lane_writes_all_outputs(monkeypatch, tmp_path):
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
    episode_consequence = {
        "module_id": "episode_consequence_projection_v1",
        "status": "PASS",
        "episode_consequence_candidate_count": 2,
        "bound_episode_consequence_candidate_count": 2,
        "episode_consequence_candidates": [],
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
    progression = {
        "module_id": "progression_effectiveness_construct_v1",
        "status": "PASS_CANDIDATE",
        "construct_candidate_count": 1,
        "construct_candidate": {"effectiveness_score_emitted": False},
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
    }
    progression_finding = {
        "module_id": "progression_safe_finding_projection_v1",
        "status": "PASS_CANDIDATE",
        "finding_candidate_count": 1,
        "finding_candidate": {"finding_state": "ENGINEERING_ENVELOPE_READY_PHYSICAL_ACTIVE_MATCH_REQUIRED"},
        "engineering_envelope_complete": True,
        "physical_active_match_evidence_present": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
    }
    ball_security = {
        "module_id": "ball_security_construct_v1",
        "status": "PASS_CANDIDATE",
        "construct_candidate_count": 1,
        "construct_candidate": {"ball_security_score_emitted": False},
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "ball_security_truth": False,
        "loss_exposure_truth": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
    }

    monkeypatch.setattr(lane, "build_phase_conditioned_interactions", lambda *args: interaction)
    monkeypatch.setattr(lane, "build_observed_match_dynamics", lambda *args: dynamics)
    monkeypatch.setattr(lane, "build_episode_consequence_projection", lambda *args: episode_consequence)
    monkeypatch.setattr(lane, "build_phase_dynamics_interaction_bridge", lambda *args: bridge)
    monkeypatch.setattr(lane, "load_guard", lambda *args: {"module_id": "construct_context_guard_v1"})
    monkeypatch.setattr(lane, "build_progression_effectiveness_construct", lambda *args, **kwargs: progression)
    monkeypatch.setattr(lane, "build_progression_safe_finding_projection", lambda *args: progression_finding)
    monkeypatch.setattr(lane, "build_ball_security_construct", lambda *args, **kwargs: ball_security)

    result = run_phase_dynamics_intelligence_lane(tmp_path)
    assert result["status"] == "SMOKE_PASS"
    assert result["phase_dynamics_interaction_candidate_count"] == 1
    assert result["episode_consequence_candidate_count"] == 2
    assert result["bound_episode_consequence_candidate_count"] == 2
    assert result["progression_effectiveness_construct_candidate_count"] == 1
    assert result["progression_safe_finding_candidate_count"] == 1
    assert result["progression_safe_finding_engineering_envelope_complete"] is True
    assert result["ball_security_construct_candidate_count"] == 1
    for path in result["outputs"].values():
        assert __import__("pathlib").Path(path).is_file()
    assert result["tempo_truth"] is False
    assert result["momentum_truth"] is False
    assert result["causal_truth"] is False
    assert result["consequence_candidate_is_causal_truth"] is False
    assert result["progression_effectiveness_truth"] is False
    assert result["ball_security_truth"] is False
    assert result["loss_exposure_truth"] is False
    assert result["physical_active_match_evidence_present"] is False
    assert result["professional_finding_emitted"] is False
    assert result["claim_output_allowed"] is False
    assert result["event_only_is_product_ceiling"] is False


def test_progression_construct_failure_closes_lane(monkeypatch, tmp_path):
    import hpfa.modules.core.active_match_spine_runner.src.phase_dynamics_intelligence_lane as lane

    for filename in INPUTS.values():
        _write(tmp_path / filename, {"placeholder": True})
    base = {
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    monkeypatch.setattr(lane, "build_phase_conditioned_interactions", lambda *args: {**base, "module_id": "phase_conditioned_interaction_projection_v1", "interaction_episode_candidates": []})
    monkeypatch.setattr(lane, "build_observed_match_dynamics", lambda *args: {**base, "module_id": "observed_match_dynamics_projection_v1", "observed_match_dynamics_candidates": []})
    monkeypatch.setattr(lane, "build_episode_consequence_projection", lambda *args: {**base, "module_id": "episode_consequence_projection_v1", "episode_consequence_candidates": []})
    monkeypatch.setattr(lane, "build_phase_dynamics_interaction_bridge", lambda *args: {**base, "module_id": "phase_dynamics_interaction_bridge_v1"})
    monkeypatch.setattr(lane, "load_guard", lambda *args: {"module_id": "construct_context_guard_v1"})
    monkeypatch.setattr(lane, "build_progression_effectiveness_construct", lambda *args, **kwargs: {**base, "module_id": "progression_effectiveness_construct_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["guard_failure"], "construct_candidate_count": 0})
    monkeypatch.setattr(lane, "build_ball_security_construct", lambda *args, **kwargs: {**base, "module_id": "ball_security_construct_v1", "construct_candidate_count": 1})

    result = run_phase_dynamics_intelligence_lane(tmp_path)
    assert result["status"] == "FAIL_CLOSED"
    assert "progression_effectiveness_fail_closed" in result["hard_block_hits"]
    assert "progression_safe_finding_fail_closed" in result["hard_block_hits"]


def test_ball_security_failure_closes_lane(monkeypatch, tmp_path):
    import hpfa.modules.core.active_match_spine_runner.src.phase_dynamics_intelligence_lane as lane

    for filename in INPUTS.values():
        _write(tmp_path / filename, {"placeholder": True})
    base = {"status": "PASS", "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": []}
    monkeypatch.setattr(lane, "build_phase_conditioned_interactions", lambda *args: {**base, "module_id": "phase_conditioned_interaction_projection_v1", "interaction_episode_candidates": []})
    monkeypatch.setattr(lane, "build_observed_match_dynamics", lambda *args: {**base, "module_id": "observed_match_dynamics_projection_v1", "observed_match_dynamics_candidates": []})
    monkeypatch.setattr(lane, "build_episode_consequence_projection", lambda *args: {**base, "module_id": "episode_consequence_projection_v1", "episode_consequence_candidates": []})
    monkeypatch.setattr(lane, "build_phase_dynamics_interaction_bridge", lambda *args: {**base, "module_id": "phase_dynamics_interaction_bridge_v1"})
    monkeypatch.setattr(lane, "load_guard", lambda *args: {"module_id": "construct_context_guard_v1"})
    monkeypatch.setattr(lane, "build_progression_effectiveness_construct", lambda *args, **kwargs: {**base, "module_id": "progression_effectiveness_construct_v1", "construct_candidate_count": 1})
    monkeypatch.setattr(lane, "build_progression_safe_finding_projection", lambda *args: {**base, "module_id": "progression_safe_finding_projection_v1", "finding_candidate_count": 1, "engineering_envelope_complete": False})
    monkeypatch.setattr(lane, "build_ball_security_construct", lambda *args, **kwargs: {**base, "module_id": "ball_security_construct_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["guard_failure"], "construct_candidate_count": 0})

    result = run_phase_dynamics_intelligence_lane(tmp_path)
    assert result["status"] == "FAIL_CLOSED"
    assert "ball_security_fail_closed" in result["hard_block_hits"]


def test_no_sample_match_identity_leak(tmp_path):
    payload = run_phase_dynamics_intelligence_lane(tmp_path)
    rendered = str(payload)
    assert "Genclerbirligi" not in rendered
    assert "Fenerbahce" not in rendered
    assert "Galatasaray" not in rendered
    assert "Roma" not in rendered
    assert "Atalanta" not in rendered
