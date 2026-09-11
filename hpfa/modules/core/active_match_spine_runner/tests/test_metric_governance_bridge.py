from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src.metric_governance_bridge import (
    _metric_capability_admission_rows,
    run_metric_governance_bridge,
)
from hpfa.modules.core.active_match_spine_runner.src.zfgv_runtime_capability_admission import (
    build_runtime_capability_admission,
)


def test_metric_governance_bridge_preserves_claim_locks_without_runtime_prerequisites(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    report = run_metric_governance_bridge(tmp_path, repo_root)

    assert report["module_id"] == "active_match_metric_governance_bridge_v1"
    assert report["status"] in {"REVIEW_REQUIRED", "FAIL_CLOSED"}
    assert report["observation_model"] == "MULTI_SURFACE_FOOTBALL_OBSERVATION_FABRIC"
    assert report["global_event_only_gate"] is False
    assert report["metric_admission_rule"] == "REQUIRED_CAPABILITIES_SUBSET_OF_ADMITTED_CAPABILITIES"
    assert report["zfgv_capability_contract_present"] is True
    assert report["runtime_capability_admission_evaluated"] is False
    assert report["zfgv_metric_capability_requirements"]
    assert all(
        isinstance(row.get("required_observation_capabilities"), list)
        for row in report["zfgv_metric_capability_requirements"]
    )
    assert report["metric_value_output_allowed"] is False
    assert report["construct_truth"] is False
    assert report["aggregate_equivalence_truth"] is False
    assert report["same_provider_multiformat_is_independent_support"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False
    assert any("prerequisite_missing" in hit for hit in report["review_hits"])
    assert (tmp_path / "active_match_metric_governance_bridge_v1.json").is_file()
    assert (tmp_path / "active_match_metric_governance_bridge_v1.txt").is_file()


def test_runtime_capability_admission_recovers_zfgv_surfaces_without_truth_promotion(tmp_path: Path) -> None:
    (tmp_path / "trackable_action_trace_candidates_lite_v1.json").write_text(json.dumps({
        "module_status": "PASS",
        "trackable_action_trace_candidates": [{
            "period_candidate": 1,
            "start_candidate": 12.0,
            "end_candidate": 13.0,
        }],
    }), encoding="utf-8")
    (tmp_path / "match_local_identity_candidates_lite_v1.json").write_text(json.dumps({
        "status": "PASS",
        "actor_identity_candidates": [{"actor_identity_candidate_id": "a1"}],
        "team_identity_candidates": [{"team_identity_candidate_id": "t1"}],
    }), encoding="utf-8")
    (tmp_path / "visible_geometry_lens_lite_v1.json").write_text(json.dumps({
        "status": "PASS",
        "overall_coordinate_surface": {"coordinate_point_count": 2},
        "direction_normalized": False,
    }), encoding="utf-8")
    (tmp_path / "xlsx_surface_audit_lite_v1.json").write_text(json.dumps({
        "status": "PASS",
        "analyst_evidence": {"visible_xlsx_surfaces": 2},
    }), encoding="utf-8")
    (tmp_path / "semantic_role_action_bundle_candidates_lite_v1.json").write_text(json.dumps({
        "module_status": "PASS",
        "semantic_routes": [
            {"semantic_route": "PARTICIPATION_INTERVAL_ROUTE", "route_status": "PASS"},
            {"semantic_route": "TERMINAL_OUTCOME_ROUTE", "route_status": "PASS"},
            {"semantic_route": "REFERENCE_ROUTE", "route_status": "PASS"},
            {"semantic_route": "DERIVED_CONSEQUENCE_ROUTE", "route_status": "PASS"},
        ],
    }), encoding="utf-8")

    report = build_runtime_capability_admission(tmp_path)
    admitted = set(report["admitted_observation_capabilities"])
    assert report["runtime_capability_admission_evaluated"] is True
    assert {
        "ACTION_EVENT", "TEMPORAL", "ENTITY_ACTOR", "SPATIAL",
        "AGGREGATE_TABULAR", "PROCESS_PARTICIPATION", "OUTCOME_QUALIFIER",
        "RELATIONAL", "HPFA_DERIVED_INTELLIGENCE",
    } <= admitted
    assert report["event_identity_created"] is False
    assert report["metric_value_output_allowed"] is False
    assert report["construct_truth_granted"] is False
    assert report["possession_truth"] is False
    assert report["tactical_truth"] is False
    assert report["causality_truth"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_metric_capability_subset_controls_eligibility_without_granting_metric_truth() -> None:
    requirements = [
        {"metric_id": "m_ready", "required_observation_capabilities": ["ACTION_EVENT", "TEMPORAL"]},
        {"metric_id": "m_blocked", "required_observation_capabilities": ["ACTION_EVENT", "TRACKING_VIDEO"]},
    ]
    runtime = {
        "runtime_capability_admission_evaluated": True,
        "admitted_observation_capabilities": ["ACTION_EVENT", "TEMPORAL", "SPATIAL"],
    }
    rows = _metric_capability_admission_rows(requirements, runtime)
    by_id = {row["metric_id"]: row for row in rows}

    assert by_id["m_ready"]["capability_eligibility_state"] == "ELIGIBLE_REQUIRED_CAPABILITIES_PRESENT"
    assert by_id["m_ready"]["missing_required_observation_capabilities"] == []
    assert by_id["m_blocked"]["capability_eligibility_state"] == "NOT_ELIGIBLE_MISSING_REQUIRED_CAPABILITIES"
    assert by_id["m_blocked"]["missing_required_observation_capabilities"] == ["TRACKING_VIDEO"]
    assert by_id["m_ready"]["metric_value_output_allowed_by_capability_match"] is False
    assert by_id["m_ready"]["construct_truth_granted_by_capability_match"] is False
