import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "support" / "event_physical_cost_surface_lite" / "src"
sys.path.insert(0, str(SRC))
from event_physical_cost_surface import build_manifest, write_outputs


def write_page(out: Path, source_file: str, text: str):
    (out / "reference_document_pages_v1.jsonl").write_text(json.dumps({"source_file": source_file, "page_number": 1, "text": text}) + "\n", encoding="utf-8")


def test_classifies_physical_cost_surface_from_page_text(tmp_path):
    out = tmp_path / "HPFA"; out.mkdir()
    write_page(out, "fitness report.pdf", "Total distance 10450 m and sprint distance 330 m")
    report = build_manifest(out)
    assert report["status"] == "PASS"
    assert report["runtime_event_truth"] is False
    assert report["surface_counts"].get("PHYSICAL_COST_SURFACE", 0) >= 1
    assert "DISTANCE_TOTAL" in report["metric_family_counts"]


def test_binds_extracted_values_to_each_metric_family(tmp_path):
    out = tmp_path / "HPFA"; out.mkdir()
    write_page(out, "fitness players.pdf", "Total distance 10450 m and sprint distance 330 m")
    report = build_manifest(out); by_family = {row["metric_family"]: row for row in report["records"]}
    assert by_family["DISTANCE_TOTAL"]["metric_value_raw"] == "10450"
    assert by_family["DISTANCE_SPRINT"]["metric_value_raw"] == "330"


def test_minutes_played_is_produced_as_exposure_not_physical_cost(tmp_path):
    out = tmp_path / "HPFA"; out.mkdir()
    write_page(out, "fitness players.pdf", "Total distance 10450 m. Minutes played 90 minutes.")
    report = build_manifest(out)
    minutes = [r for r in report["records"] if r["metric_family"] == "MINUTES_PLAYED"]
    assert len(minutes) == 1
    assert minutes[0]["source_role"] == "EXPOSURE_NORMALIZATION_SURFACE"
    assert minutes[0]["claim_safety"] == "EXPOSURE_CANDIDATE_ONLY"
    assert minutes[0]["exposure_authority_status"] == "UNKNOWN"
    assert "MINUTES_PLAYED" not in report["metric_family_counts"]
    assert report["exposure_family_counts"]["MINUTES_PLAYED"] == 1
    assert report["surface_counts"]["EXPOSURE_NORMALIZATION_SURFACE"] == 1
    assert report["exposure_authority_truth"] is False
    assert not any(r["metric_family"] == "MINUTES_PLAYED" and r["source_role"] == "PHYSICAL_COST_SURFACE" for r in report["records"])


def test_classifies_fifa_report_as_report_metric_surface(tmp_path):
    out = tmp_path / "HPFA"; out.mkdir()
    write_page(out, "FIFA technical report.pdf", "FIFA technical report match summary and official statistics")
    report = build_manifest(out)
    assert report["surface_counts"].get("REPORT_METRIC_SURFACE", 0) >= 1
    assert "FIFA_TECHNICAL_CONTEXT" in report["metric_family_counts"]


def test_report_name_precedence_over_physical_words(tmp_path):
    out = tmp_path / "HPFA"; out.mkdir()
    write_page(out, "FIFA technical report.pdf", "The report mentions distance, speed, acceleration and sprint values in a technical context.")
    report = build_manifest(out)
    assert report["surface_counts"].get("PHYSICAL_COST_SURFACE", 0) in (None, 0)
    assert all(row["claim_safety"] == "REPORT_CONTEXT_ONLY" for row in report["records"])


def test_audit_fallback_when_pages_missing(tmp_path):
    out = tmp_path / "HPFA"; out.mkdir()
    (out / "reference_document_extraction_audit_v1.json").write_text(json.dumps({"pdf_count": 5, "page_count": 141, "texty_pages": 134, "chars_total": 284238}), encoding="utf-8")
    report = build_manifest(out)
    assert report["status"] == "PASS"
    assert report["record_count"] == 1


def test_write_outputs_flat_files(tmp_path):
    out = tmp_path / "HPFA"; out.mkdir()
    write_page(out, "fitness players.pdf", "maximum speed 31 km/h acceleration deceleration")
    report = write_outputs(out, root=ROOT)
    assert report["status"] == "PASS"
    for name in ["physical_cost_surface_manifest_v1.json", "physical_cost_metric_extract_v1.tsv", "physical_cost_surface_audit_v1.json", "physical_cost_surface_audit_v1.txt"]:
        assert (out / name).exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs("/sdcard/Download/HPFA/physical-cost", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "event_physical_cost_surface.py").read_text(encoding="utf-8")
    for token in ["Australia", "Turkey", "World Cup", "13.06.2026", "77798", "6935"]:
        assert token not in src
