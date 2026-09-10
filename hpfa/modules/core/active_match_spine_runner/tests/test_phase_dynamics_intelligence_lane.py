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
    assert payload["recovery_yield_truth"] is False
    assert payload["possession_gain_truth"] is False
    assert payload["penetration_truth"] is False
    assert payload["box_access_truth"] is False
    assert payload["progression_safe_finding_engineering_envelope_complete"] is False
    assert payload["ball_security_safe_finding_engineering_envelope_complete"] is False
    assert payload["recovery_safe_finding_engineering_envelope_complete"] is False
    assert payload["penetration_safe_finding_engineering_envelope_complete"] is False
    assert payload["physical_active_match_evidence_present"] is False
    assert payload["professional_finding_emitted"] is False


def test_lane_writes_all_outputs(monkeypatch, tmp_path):
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
    interaction = {**base, "module_id": "phase_conditioned_interaction_projection_v1", "interaction_episode_candidate_count": 1, "interaction_episode_candidates": []}
    dynamics = {**base, "module_id": "observed_match_dynamics_projection_v1", "observed_match_dynamics_candidate_count": 1, "observed_match_dynamics_candidates": []}
    episode_consequence = {**base, "module_id": "episode_consequence_projection_v1", "episode_consequence_candidate_count": 2, "bound_episode_consequence_candidate_count": 2, "episode_consequence_candidates": []}
    bridge = {**base, "module_id": "phase_dynamics_interaction_bridge_v1", "phase_dynamics_interaction_candidate_count": 1}
    progression = {**base, "module_id": "progression_effectiveness_construct_v1", "status": "PASS_CANDIDATE", "construct_candidate_count": 1, "construct_candidate": {"effectiveness_score_emitted": False}, "professional_finding_emitted": False, "claim_output_allowed": False}
    progression_finding = {**base, "module_id": "progression_safe_finding_projection_v1", "status": "PASS_CANDIDATE", "finding_candidate_count": 1, "finding_candidate": {"finding_state": "ENGINEERING_ENVELOPE_READY_PHYSICAL_ACTIVE_MATCH_REQUIRED"}, "engineering_envelope_complete": True, "physical_active_match_evidence_present": False, "professional_finding_emitted": False, "claim_output_allowed": False}
    ball_security = {**base, "module_id": "ball_security_construct_v1", "status": "PASS_CANDIDATE", "construct_candidate_count": 1, "construct_candidate": {"ball_security_score_emitted": False}, "ball_security_truth": False, "loss_exposure_truth": False, "professional_finding_emitted": False, "claim_output_allowed": False}
    ball_security_finding = {**base, "module_id": "ball_security_safe_finding_projection_v1", "status": "PASS_CANDIDATE", "finding_candidate_count": 1, "finding_candidate": {"finding_state": "ENGINEERING_ENVELOPE_READY_PHYSICAL_ACTIVE_MATCH_REQUIRED"}, "engineering_envelope_complete": True, "physical_active_match_evidence_present": False, "professional_finding_emitted": False, "claim_output_allowed": False}
    recovery_yield = {**base, "module_id": "recovery_yield_construct_v1", "status": "PASS_CANDIDATE", "construct_candidate_count": 1, "construct_candidate": {"recovery_yield_score_emitted": False}, "recovery_yield_truth": False, "possession_gain_truth": False, "professional_finding_emitted": False, "claim_output_allowed": False}
    recovery_finding = {**base, "module_id": "recovery_safe_finding_projection_v1", "status": "PASS_CANDIDATE", "finding_candidate_count": 1, "finding_candidate": {"finding_state": "ENGINEERING_ENVELOPE_READY_PHYSICAL_ACTIVE_MATCH_REQUIRED"}, "engineering_envelope_complete": True, "physical_active_match_evidence_present": False, "professional_finding_emitted": False, "claim_output_allowed": False}
    penetration = {**base, "module_id": "penetration_construct_v1", "status": "PASS_CANDIDATE", "construct_candidate_count": 1, "construct_candidate": {"visible_terminal_penetration_support_candidate_count": 1, "box_access_surface_available": False}, "penetration_truth": False, "box_access_truth": False, "professional_finding_emitted": False, "claim_output_allowed": False}
    penetration_finding = {**base, "module_id": "penetration_safe_finding_projection_v1", "status": "PASS_CANDIDATE", "finding_candidate_count": 1, "finding_candidate": {"finding_state": "ENGINEERING_ENVELOPE_READY_PHYSICAL_ACTIVE_MATCH_REQUIRED"}, "engineering_envelope_complete": True, "physical_active_match_evidence_present": False, "professional_finding_emitted": False, "claim_output_allowed": False}

    monkeypatch.setattr(lane, "build_phase_conditioned_interactions", lambda *args: interaction)
    monkeypatch.setattr(lane, "build_observed_match_dynamics", lambda *args: dynamics)
    monkeypatch.setattr(lane, "build_episode_consequence_projection", lambda *args: episode_consequence)
    monkeypatch.setattr(lane, "build_phase_dynamics_interaction_bridge", lambda *args: bridge)
    monkeypatch.setattr(lane, "load_guard", lambda *args: {"module_id": "construct_context_guard_v1"})
    monkeypatch.setattr(lane, "build_progression_effectiveness_construct", lambda *args, **kwargs: progression)
    monkeypatch.setattr(lane, "build_progression_safe_finding_projection", lambda *args: progression_finding)
    monkeypatch.setattr(lane, "build_ball_security_construct", lambda *args, **kwargs: ball_security)
    monkeypatch.setattr(lane, "build_ball_security_safe_finding_projection", lambda *args: ball_security_finding)
    monkeypatch.setattr(lane, "build_recovery_yield_construct", lambda *args, **kwargs: recovery_yield)
    monkeypatch.setattr(lane, "build_recovery_safe_finding_projection", lambda *args: recovery_finding)
    monkeypatch.setattr(lane, "build_penetration_construct", lambda *args, **kwargs: penetration)
    monkeypatch.setattr(lane, "build_penetration_safe_finding_projection", lambda *args: penetration_finding)

    result = run_phase_dynamics_intelligence_lane(tmp_path)
    assert result["status"] == "SMOKE_PASS"
    assert result["phase_dynamics_interaction_candidate_count"] == 1
    assert result["episode_consequence_candidate_count"] == 2
    assert result["bound_episode_consequence_candidate_count"] == 2
    assert result["progression_effectiveness_construct_candidate_count"] == 1
    assert result["progression_safe_finding_candidate_count"] == 1
    assert result["progression_safe_finding_engineering_envelope_complete"] is True
    assert result["ball_security_construct_candidate_count"] == 1
    assert result["ball_security_safe_finding_candidate_count"] == 1
    assert result["ball_security_safe_finding_engineering_envelope_complete"] is True
    assert result["recovery_yield_construct_candidate_count"] == 1
    assert result["recovery_safe_finding_candidate_count"] == 1
    assert result["recovery_safe_finding_engineering_envelope_complete"] is True
    assert result["penetration_construct_candidate_count"] == 1
    assert result["visible_terminal_penetration_support_candidate_count"] == 1
    assert result["box_access_surface_available"] is False
    assert result["penetration_safe_finding_candidate_count"] == 1
    assert result["penetration_safe_finding_engineering_envelope_complete"] is True
    for path in result["outputs"].values():
        assert __import__("pathlib").Path(path).is_file()
    assert result["tempo_truth"] is False
    assert result["momentum_truth"] is False
    assert result["causal_truth"] is False
    assert result["consequence_candidate_is_causal_truth"] is False
    assert result["progression_effectiveness_truth"] is False
    assert result["ball_security_truth"] is False
    assert result["loss_exposure_truth"] is False
    assert result["recovery_yield_truth"] is False
    assert result["possession_gain_truth"] is False
    assert result["penetration_truth"] is False
    assert result["box_access_truth"] is False
    assert result["territorial_control_truth"] is False
    assert result["physical_active_match_evidence_present"] is False
    assert result["professional_finding_emitted"] is False
    assert result["claim_output_allowed"] is False
    assert result["event_only_is_product_ceiling"] is False


def _patch_common_lane(monkeypatch, lane, base):
    monkeypatch.setattr(lane, "build_phase_conditioned_interactions", lambda *args: {**base, "module_id": "phase_conditioned_interaction_projection_v1", "interaction_episode_candidates": []})
    monkeypatch.setattr(lane, "build_observed_match_dynamics", lambda *args: {**base, "module_id": "observed_match_dynamics_projection_v1", "observed_match_dynamics_candidates": []})
    monkeypatch.setattr(lane, "build_episode_consequence_projection", lambda *args: {**base, "module_id": "episode_consequence_projection_v1", "episode_consequence_candidates": []})
    monkeypatch.setattr(lane, "build_phase_dynamics_interaction_bridge", lambda *args: {**base, "module_id": "phase_dynamics_interaction_bridge_v1"})
    monkeypatch.setattr(lane, "load_guard", lambda *args: {"module_id": "construct_context_guard_v1"})
    monkeypatch.setattr(lane, "build_ball_security_safe_finding_projection", lambda *args: {**base, "module_id": "ball_security_safe_finding_projection_v1", "finding_candidate_count": 0, "engineering_envelope_complete": False})
    monkeypatch.setattr(lane, "build_recovery_safe_finding_projection", lambda *args: {**base, "module_id": "recovery_safe_finding_projection_v1", "finding_candidate_count": 0, "engineering_envelope_complete": False})
    monkeypatch.setattr(lane, "build_penetration_construct", lambda *args, **kwargs: {**base, "module_id": "penetration_construct_v1", "construct_candidate_count": 1, "construct_candidate": {"box_access_surface_available": False}})
    monkeypatch.setattr(lane, "build_penetration_safe_finding_projection", lambda *args: {**base, "module_id": "penetration_safe_finding_projection_v1", "finding_candidate_count": 0, "engineering_envelope_complete": False})


def test_progression_construct_failure_closes_lane(monkeypatch, tmp_path):
    import hpfa.modules.core.active_match_spine_runner.src.phase_dynamics_intelligence_lane as lane
    for filename in INPUTS.values():
        _write(tmp_path / filename, {"placeholder": True})
    base = {"status": "PASS", "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": []}
    _patch_common_lane(monkeypatch, lane, base)
    monkeypatch.setattr(lane, "build_progression_effectiveness_construct", lambda *args, **kwargs: {**base, "module_id": "progression_effectiveness_construct_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["guard_failure"], "construct_candidate_count": 0})
    monkeypatch.setattr(lane, "build_progression_safe_finding_projection", lambda *args: {**base, "module_id": "progression_safe_finding_projection_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["upstream_progression_failure"], "finding_candidate_count": 0, "engineering_envelope_complete": False})
    monkeypatch.setattr(lane, "build_ball_security_construct", lambda *args, **kwargs: {**base, "module_id": "ball_security_construct_v1", "construct_candidate_count": 1})
    monkeypatch.setattr(lane, "build_recovery_yield_construct", lambda *args, **kwargs: {**base, "module_id": "recovery_yield_construct_v1", "construct_candidate_count": 1})
    result = run_phase_dynamics_intelligence_lane(tmp_path)
    assert result["status"] == "FAIL_CLOSED"
    assert "progression_effectiveness_fail_closed" in result["hard_block_hits"]
    assert "progression_safe_finding_fail_closed" in result["hard_block_hits"]


def test_ball_security_failure_closes_lane(monkeypatch, tmp_path):
    import hpfa.modules.core.active_match_spine_runner.src.phase_dynamics_intelligence_lane as lane
    for filename in INPUTS.values():
        _write(tmp_path / filename, {"placeholder": True})
    base = {"status": "PASS", "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": []}
    _patch_common_lane(monkeypatch, lane, base)
    monkeypatch.setattr(lane, "build_progression_effectiveness_construct", lambda *args, **kwargs: {**base, "module_id": "progression_effectiveness_construct_v1", "construct_candidate_count": 1})
    monkeypatch.setattr(lane, "build_progression_safe_finding_projection", lambda *args: {**base, "module_id": "progression_safe_finding_projection_v1", "finding_candidate_count": 1, "engineering_envelope_complete": False})
    monkeypatch.setattr(lane, "build_ball_security_construct", lambda *args, **kwargs: {**base, "module_id": "ball_security_construct_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["guard_failure"], "construct_candidate_count": 0})
    monkeypatch.setattr(lane, "build_ball_security_safe_finding_projection", lambda *args: {**base, "module_id": "ball_security_safe_finding_projection_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["upstream_ball_security_failure"], "finding_candidate_count": 0, "engineering_envelope_complete": False})
    monkeypatch.setattr(lane, "build_recovery_yield_construct", lambda *args, **kwargs: {**base, "module_id": "recovery_yield_construct_v1", "construct_candidate_count": 1})
    result = run_phase_dynamics_intelligence_lane(tmp_path)
    assert result["status"] == "FAIL_CLOSED"
    assert "ball_security_fail_closed" in result["hard_block_hits"]
    assert "ball_security_safe_finding_fail_closed" in result["hard_block_hits"]


def test_recovery_yield_failure_closes_lane(monkeypatch, tmp_path):
    import hpfa.modules.core.active_match_spine_runner.src.phase_dynamics_intelligence_lane as lane
    for filename in INPUTS.values():
        _write(tmp_path / filename, {"placeholder": True})
    base = {"status": "PASS", "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": []}
    _patch_common_lane(monkeypatch, lane, base)
    monkeypatch.setattr(lane, "build_progression_effectiveness_construct", lambda *args, **kwargs: {**base, "module_id": "progression_effectiveness_construct_v1", "construct_candidate_count": 1})
    monkeypatch.setattr(lane, "build_progression_safe_finding_projection", lambda *args: {**base, "module_id": "progression_safe_finding_projection_v1", "finding_candidate_count": 1, "engineering_envelope_complete": False})
    monkeypatch.setattr(lane, "build_ball_security_construct", lambda *args, **kwargs: {**base, "module_id": "ball_security_construct_v1", "construct_candidate_count": 1})
    monkeypatch.setattr(lane, "build_recovery_yield_construct", lambda *args, **kwargs: {**base, "module_id": "recovery_yield_construct_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["guard_failure"], "construct_candidate_count": 0})
    monkeypatch.setattr(lane, "build_recovery_safe_finding_projection", lambda *args: {**base, "module_id": "recovery_safe_finding_projection_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["upstream_recovery_failure"], "finding_candidate_count": 0, "engineering_envelope_complete": False})
    result = run_phase_dynamics_intelligence_lane(tmp_path)
    assert result["status"] == "FAIL_CLOSED"
    assert "recovery_yield_fail_closed" in result["hard_block_hits"]
    assert "recovery_safe_finding_fail_closed" in result["hard_block_hits"]


def test_no_sample_match_identity_leak(tmp_path):
    payload = run_phase_dynamics_intelligence_lane(tmp_path)
    rendered = str(payload)
    forbidden = ["Gencler" + "birligi", "Fener" + "bahce", "Gala" + "tasaray", "Ro" + "ma", "Ata" + "lanta"]
    assert all(token not in rendered for token in forbidden)
