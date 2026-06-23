import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_family_registry_lite" / "src"
sys.path.insert(0, str(SRC))

from metric_family_registry import build_registry, write_outputs


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_registers_progression_family_while_primary_unresolved(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "primary_event_surface_gate_lite_v1.json", {"decision": "UNRESOLVED_REVIEW_REQUIRED", "primary_event_surface_candidate": "UNRESOLVED"})

    report = build_registry(out)

    assert report["status"] == "PASS"
    assert report["family_counts"]["PROGRESSION_FAMILY"] >= 1
    progression = [r for r in report["registry_records"] if r["metric_family"] == "PROGRESSION_FAMILY"]
    assert all(r["calculation_status"] == "WAIT_PRIMARY_SURFACE_REVIEW" for r in progression)
    assert report["metric_value_output_allowed"] is False


def test_registers_physical_cost_family_from_audit(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "physical_cost_surface_audit_v1.json", {
        "record_count": 3,
        "surface_counts": {"PHYSICAL_COST_SURFACE": 2, "REPORT_METRIC_SURFACE": 1},
        "metric_family_counts": {"DISTANCE_TOTAL": 2, "SPEED_MAX": 1},
    })

    report = build_registry(out)

    names = {r["metric_name"] for r in report["registry_records"] if r["metric_family"] == "PHYSICAL_COST_FAMILY"}
    assert {"DISTANCE_TOTAL", "SPEED_MAX"}.issubset(names)
    assert report["efficiency_calculation_allowed"] is False


def test_report_context_metrics_do_not_enter_physical_cost_family(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "physical_cost_surface_audit_v1.json", {
        "record_count": 4,
        "surface_counts": {"PHYSICAL_COST_SURFACE": 2, "REPORT_METRIC_SURFACE": 2},
        "metric_family_counts": {
            "DISTANCE_TOTAL": 2,
            "FIFA_TECHNICAL_CONTEXT": 1,
            "FORM_REPORT_CONTEXT": 1,
            "OFFICIAL_METRIC_CONTEXT": 1,
        },
    })

    report = build_registry(out)

    physical_names = {r["metric_name"] for r in report["registry_records"] if r["metric_family"] == "PHYSICAL_COST_FAMILY"}
    report_names = {r["metric_name"] for r in report["registry_records"] if r["metric_family"] == "REPORT_CONTEXT_FAMILY"}
    assert "DISTANCE_TOTAL" in physical_names
    assert "FIFA_TECHNICAL_CONTEXT" not in physical_names
    assert "FORM_REPORT_CONTEXT" not in physical_names
    assert "OFFICIAL_METRIC_CONTEXT" not in physical_names
    assert {"FIFA_TECHNICAL_CONTEXT", "FORM_REPORT_CONTEXT", "OFFICIAL_METRIC_CONTEXT"}.issubset(report_names)


def test_efficiency_family_waits_when_primary_unresolved(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "primary_event_surface_gate_lite_v1.json", {"decision": "UNRESOLVED_REVIEW_REQUIRED", "primary_event_surface_candidate": "UNRESOLVED"})
    write_json(out / "physical_cost_surface_audit_v1.json", {"metric_family_counts": {"DISTANCE_TOTAL": 1}})

    report = build_registry(out)

    efficiency = [r for r in report["registry_records"] if r["metric_family"] == "EFFICIENCY_FAMILY"]
    assert efficiency
    assert all(r["calculation_status"] == "WAIT_PRIMARY_SURFACE_REVIEW" for r in efficiency)
    assert report["efficiency_calculation_allowed"] is False


def test_progression_can_be_ready_only_when_primary_selected(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "primary_event_surface_gate_lite_v1.json", {"decision": "CANDIDATE_SELECTED", "primary_event_surface_candidate": "Players.csv"})

    report = build_registry(out)

    progression = [r for r in report["registry_records"] if r["metric_family"] == "PROGRESSION_FAMILY"]
    assert all(r["calculation_status"] == "READY_FOR_CANDIDATE_CALCULATION" for r in progression)
    fusion = [r for r in report["registry_records"] if r["metric_family"] == "FUSION_READINESS_FAMILY"]
    assert fusion[0]["calculation_status"] == "WAIT_TEMPORAL_BINDING"


def test_write_outputs_flat_files(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "primary_event_surface_gate_lite_v1.json", {"decision": "UNRESOLVED_REVIEW_REQUIRED", "primary_event_surface_candidate": "UNRESOLVED"})

    report = write_outputs(out, root=ROOT)

    assert report["status"] == "PASS"
    assert (out / "metric_family_registry_lite_v1.json").exists()
    assert (out / "metric_family_registry_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs("/sdcard/Download/HPFA/metric-family", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "metric_family_registry.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "13.06.2026", "77798", "6935"]
    for token in forbidden:
        assert token not in src
