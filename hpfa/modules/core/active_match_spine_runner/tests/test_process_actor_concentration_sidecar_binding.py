from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from hpfa.modules.core.active_match_spine_runner.src import orphan_capability_sidecars as sidecars


def _process_participation_payload() -> dict:
    common = {
        "team_identity_candidate_id": "team_a",
        "process_family_candidate": "POSITIONAL_ATTACK",
        "period_candidate": "1",
        "start_candidate": "10.0",
        "end_candidate": "20.0",
    }
    rows = [
        {
            **common,
            "process_participation_candidate_id": "ctx_1",
            "semantic_role": "CONTEXT_INTERVAL",
        },
        {
            **common,
            "process_participation_candidate_id": "p_1",
            "semantic_role": "PARTICIPATION_INTERVAL",
            "actor_identity_candidate_id": "player_1",
            "reflection_dependency_state": "UNIQUE",
        },
        {
            **common,
            "process_participation_candidate_id": "p_2",
            "semantic_role": "PARTICIPATION_INTERVAL",
            "actor_identity_candidate_id": "player_2",
            "reflection_dependency_state": "UNIQUE",
        },
    ]
    return {
        "module_id": "analyst_episode_process_participation_projection_v1",
        "status": "PASS",
        "process_participation_candidates": rows,
        "process_participation_candidate_count": len(rows),
        "annotation_count_is_action_count": False,
        "annotation_count_is_independent_support_count": False,
        "reflection_adds_independent_vote": False,
        "absence_is_counterevidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_sidecar_materializes_process_actor_concentration_without_role_truth(tmp_path: Path):
    for name in (sidecars.EVIDENCE_OUTPUT, sidecars.IDENTITY_OUTPUT, sidecars.EPISODE_OUTPUT):
        (tmp_path / name).write_text("{}", encoding="utf-8")

    process_payload = _process_participation_payload()
    with patch.object(
        sidecars.report_lite,
        "write_report",
        return_value={"status": "PASS", "engineering_evidence": {}},
    ), patch.object(
        sidecars.process_participation,
        "build_process_participation_projection",
        return_value=process_payload,
    ), patch.object(
        sidecars.process_participation,
        "write_outputs",
        return_value={},
    ), patch.object(
        sidecars,
        "run_metric_governance_bridge",
        return_value={"status": "SMOKE_PASS", "current_invocation_artifacts": []},
    ):
        report = sidecars.run_sidecars(tmp_path, tmp_path, tmp_path)

    target = tmp_path / sidecars.PROCESS_ACTOR_CONCENTRATION_OUTPUT
    assert target.is_file()
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert report["process_actor_concentration_status"] == "PASS"
    assert report["process_actor_concentration_prerequisite_present"] is True
    assert payload["process_actor_concentration_profile_count"] == 1
    profile = payload["process_actor_concentration_profiles"][0]
    assert profile["unique_actor_count"] == 2
    assert profile["actor_observation_coverage_rate"] == 1.0
    assert payload["high_actor_concentration_is_player_indispensability_truth"] is False
    assert payload["dyad_coparticipation_is_pass_relation_truth"] is False
    assert payload["projection_creates_new_evidence"] is False
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["true_action_count"] == "UNKNOWN"
    assert payload["production_release"] is False

    names = {Path(value).name for value in report["current_invocation_artifacts"]}
    assert sidecars.PROCESS_ACTOR_CONCENTRATION_OUTPUT in names
