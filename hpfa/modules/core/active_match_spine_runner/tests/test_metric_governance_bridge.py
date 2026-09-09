from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src.metric_governance_bridge import run_metric_governance_bridge


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
