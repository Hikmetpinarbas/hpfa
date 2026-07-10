import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_governance_lite" / "src"
FEATURE_SRC = ROOT / "hpfa" / "modules" / "core" / "feature_primitive_builder_lite" / "src"
sys.path.insert(0, str(FEATURE_SRC))
sys.path.insert(0, str(SRC))

from metric_candidate_governance_validator import (  # noqa: E402
    INITIAL_METRIC_CANDIDATES,
    build_metric_candidate_governance,
    write_metric_candidate_governance,
)


def _feature_registry(feature_ids=None, status="SMOKE_PASS", registry_gaps=None):
    ids = feature_ids or [
        "action_family_count",
        "zone_entry_count",
        "final_third_entry",
        "box_entry",
        "sequence_length",
        "sequence_duration",
        "loss_severity",
        "turnover_exposure",
        "event_density_window",
        "restart_surface_count",
        "terminal_action_count",
    ]
    return {
        "module_id": "feature_primitive_registry_loader_lite_v1",
        "claim_safety": "FEATURE_PRIMITIVE_REGISTRY_ONLY",
        "status": status,
        "registry_records": [{"feature_id": feature_id} for feature_id in ids],
        "registry_gaps": registry_gaps or [],
        "feature_value_output_allowed": False,
        "metric_value_output_allowed": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_initial_metric_candidates_load():
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry())
    assert report["module_id"] == "metric_candidate_governance_validator_lite_v1"
    assert report["metric_candidate_count"] == 11
    assert report["status"] == "SMOKE_PASS"
    assert report["readiness_counts"] == {"READY_FOR_METRIC_BUILDER_CONTRACT": 11}


def test_metric_candidates_reference_existing_feature_primitives():
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry())
    feature_ids = {item["feature_id"] for item in _feature_registry()["registry_records"]}
    for candidate in report["metric_candidates"]:
        assert candidate["requires_feature_primitives"]
        assert set(candidate["requires_feature_primitives"]).issubset(feature_ids)


def test_missing_feature_primitive_blocks_candidate():
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry(feature_ids=["action_family_count"]))
    assert report["status"] == "REVIEW_REQUIRED"
    assert any(gap["gap_type"] == "required_feature_primitive_missing" for gap in report["governance_gaps"])


def test_missing_required_feature_primitive_dependency_blocks_candidate():
    bad = [dict(INITIAL_METRIC_CANDIDATES[0])]
    bad[0].pop("requires_feature_primitives")
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry(), records=bad)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["metric_candidates"][0]["readiness"] == "BLOCKED"
    assert any(gap["gap_type"] == "required_feature_primitive_missing" for gap in report["governance_gaps"])


def test_failed_upstream_registry_fail_closes_governance():
    upstream = _feature_registry(
        status="FAIL_CLOSED",
        registry_gaps=[{"feature_id": "action_family_count", "gap_type": "DUPLICATE_FEATURE_ID", "severity": "FAIL_CLOSED"}],
    )
    report = build_metric_candidate_governance(feature_registry_report=upstream)
    assert report["status"] == "FAIL_CLOSED"
    assert report["readiness_counts"] == {"BLOCKED_UPSTREAM_FEATURE_REGISTRY": 11}
    assert any(gap["gap_type"] == "upstream_feature_registry_fail_closed" for gap in report["governance_gaps"])
    assert any(gap["gap_type"] == "upstream_feature_registry_gap" for gap in report["governance_gaps"])


def test_review_required_upstream_registry_blocks_governance():
    upstream = _feature_registry(
        status="REVIEW_REQUIRED",
        registry_gaps=[{"feature_id": "action_family_count", "gap_type": "MISSING_REQUIRED_REGISTRY_FIELDS", "severity": "BLOCKED"}],
    )
    report = build_metric_candidate_governance(feature_registry_report=upstream)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["readiness_counts"] == {"BLOCKED_UPSTREAM_FEATURE_REGISTRY": 11}
    assert any(gap["gap_type"] == "upstream_feature_registry_review_required" for gap in report["governance_gaps"])


def test_duplicate_metric_id_fail_closed():
    dup = [dict(INITIAL_METRIC_CANDIDATES[0]), dict(INITIAL_METRIC_CANDIDATES[0])]
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry(), records=dup)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "duplicate_metric_id" for gap in report["governance_gaps"])


def test_missing_claim_ceiling_blocks_candidate():
    bad = [dict(INITIAL_METRIC_CANDIDATES[0])]
    bad[0].pop("claim_ceiling")
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry(), records=bad)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["governance_gaps"][0]["gap_type"] == "claim_ceiling_missing"


def test_no_metric_value_output_allowed():
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry())
    assert report["metric_value_output_allowed"] is False
    assert all(candidate["metric_value_output_allowed"] is False for candidate in report["metric_candidates"])


def test_no_claim_output_allowed():
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry())
    assert report["claim_output_allowed"] is False
    assert all(candidate["claim_output_allowed"] is False for candidate in report["metric_candidates"])


def test_metric_candidate_dependency_graph_written():
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry())
    graph = report["dependency_graph"]
    assert graph["contract_id"] == "HPFA_METRIC_CANDIDATE_DEPENDENCY_GRAPH_V1"
    assert "action_family_volume_candidate" in graph["nodes"]
    assert {"type": "requires_feature_primitive", "from": "action_family_volume_candidate", "to": "action_family_count"} in graph["edges"]


def test_canonical_event_count_unknown():
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry())
    assert report["canonical_event_count"] == "UNKNOWN"
    assert all(candidate["canonical_event_count"] == "UNKNOWN" for candidate in report["metric_candidates"])


def test_no_sample_match_identity_leak():
    src = (SRC / "metric_candidate_governance_validator.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src


def test_metric_candidate_does_not_promote_feature_value_permission():
    report = build_metric_candidate_governance(feature_registry_report=_feature_registry())
    assert report["feature_value_output_allowed"] is False
    assert all(candidate["feature_value_output_allowed"] is False for candidate in report["metric_candidates"])


def test_write_metric_candidate_governance_outputs_json(tmp_path):
    report = write_metric_candidate_governance(tmp_path, feature_registry_report=_feature_registry())
    out = tmp_path / "metric_candidate_governance_lite_v1.json"
    assert out.exists()
    assert report["outputs"]["json"] == str(out)


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_metric_candidate_governance(
            "/sdcard/Download/HPFA/metric_governance_lite",
            feature_registry_report=_feature_registry(),
        )
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")
