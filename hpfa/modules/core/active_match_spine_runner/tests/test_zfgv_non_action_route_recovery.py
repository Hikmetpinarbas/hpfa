from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src.orphan_capability_sidecars import (
    _zfgv_non_action_route_projection,
)


def test_zfgv_non_action_routes_are_recovered_without_event_promotion(tmp_path: Path) -> None:
    payload = {
        "semantic_routes": [
            {
                "evidence_atom_id": "a1",
                "semantic_route": "PARTICIPATION_INTERVAL_ROUTE",
                "route_status": "PASS",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "semantic_role_candidate": "PARTICIPATION_INTERVAL",
                "team_identity_candidate_id": "team_1",
                "actor_identity_candidate_id": "actor_1",
                "claim_ceiling": "ACTION_BUNDLE_CANDIDATE_ONLY",
            },
            {
                "evidence_atom_id": "a2",
                "semantic_route": "CONTEXT_INTERVAL_ROUTE",
                "route_status": "PASS",
                "source_role": "TEAM_SURFACE_CANDIDATE",
                "semantic_role_candidate": "CONTEXT_INTERVAL",
                "team_identity_candidate_id": "team_1",
                "actor_identity_candidate_id": None,
                "claim_ceiling": "ACTION_BUNDLE_CANDIDATE_ONLY",
            },
            {
                "evidence_atom_id": "a3",
                "semantic_route": "TERMINAL_OUTCOME_ROUTE",
                "route_status": "PASS",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "semantic_role_candidate": "TERMINAL_OUTCOME_CANDIDATE",
                "team_identity_candidate_id": "team_1",
                "actor_identity_candidate_id": "actor_2",
                "claim_ceiling": "ACTION_BUNDLE_CANDIDATE_ONLY",
            },
            {
                "evidence_atom_id": "a4",
                "semantic_route": "PRIMARY_ACTION_ANCHOR_ROUTE",
                "route_status": "PASS",
            },
        ]
    }
    (tmp_path / "semantic_role_action_bundle_candidates_lite_v1.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    result = _zfgv_non_action_route_projection(tmp_path)

    assert result["status"] == "PASS"
    assert result["observation_route_record_count"] == 3
    assert result["capability_counts"]["PROCESS_PARTICIPATION"] == 1
    assert result["capability_counts"]["EXTERNAL_OR_MATCH_CONTEXT"] == 1
    assert result["capability_counts"]["OUTCOME_QUALIFIER"] == 1
    assert "PRIMARY_ACTION_ANCHOR_ROUTE" not in result["route_counts"]
    assert result["event_instance_created"] is False
    assert result["action_identity_created"] is False
    assert result["possession_truth"] is False
    assert result["tactical_truth"] is False
    assert result["causality_truth"] is False
    assert result["independent_evidence_vote_created"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_zfgv_non_action_route_projection_fails_soft_when_upstream_missing(tmp_path: Path) -> None:
    result = _zfgv_non_action_route_projection(tmp_path)
    assert result["status"] == "NOT_EVALUATED_PREREQUISITE_MISSING"
    assert result["observation_route_record_count"] == 0
    assert result["event_instance_created"] is False
    assert result["production_release"] is False
