from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src.metric_governance_bridge import run_metric_governance_bridge


def test_metric_governance_bridge_preserves_claim_locks_without_runtime_prerequisites(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    report = run_metric_governance_bridge(tmp_path, repo_root)

    assert report["module_id"] == "active_match_metric_governance_bridge_v1"
    assert report["status"] in {"REVIEW_REQUIRED", "FAIL_CLOSED"}
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
