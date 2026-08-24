import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_alias_field_semantics_lite" / "src"
sys.path.insert(0, str(SRC))

from provider_time_semantic_admission import (
    ABSOLUTE_SECONDS,
    ADMITTED,
    REVIEW_REQUIRED,
    build_minimum_context_report,
    build_time_admission,
)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ID", "start", "end", "action", "half", "pos_x", "pos_y"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_xml(path: Path, rows: list[dict[str, str]]) -> None:
    root = ET.Element("file")
    all_instances = ET.SubElement(root, "ALL_INSTANCES")
    for index, row in enumerate(rows):
        instance = ET.SubElement(all_instances, "instance")
        ET.SubElement(instance, "ID").text = str(index + 1)
        ET.SubElement(instance, "start").text = row["start"]
        ET.SubElement(instance, "end").text = row["end"]
        ET.SubElement(instance, "code").text = row["action"]
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def _absolute_rows() -> list[dict[str, str]]:
    return [
        {"ID": "1", "start": "10.0", "end": "12.0", "action": "pass", "half": "1", "pos_x": "20", "pos_y": "30"},
        {"ID": "2", "start": "2700.0", "end": "2702.0", "action": "shot", "half": "1", "pos_x": "80", "pos_y": "30"},
        {"ID": "3", "start": "2760.0", "end": "2761.0", "action": "pass", "half": "2", "pos_x": "40", "pos_y": "30"},
        {"ID": "4", "start": "5400.0", "end": "5401.0", "action": "shot", "half": "2", "pos_x": "85", "pos_y": "30"},
    ]


def test_admits_cross_format_absolute_match_seconds(tmp_path: Path) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    result = build_time_admission(tmp_path)
    assert result["status"] == ADMITTED
    assert result["unit_candidate"] == "SECOND"
    assert result["time_basis_candidate"] == ABSOLUTE_SECONDS
    assert result["runtime_checks"]["absolute_continuation_across_halves"] is True
    assert result["source_row_order_is_temporal_truth"] is False


def test_rejects_half_local_reset(tmp_path: Path) -> None:
    rows = _absolute_rows()
    rows[2]["start"] = "20.0"
    rows[2]["end"] = "21.0"
    rows[3]["start"] = "2600.0"
    rows[3]["end"] = "2601.0"
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    result = build_time_admission(tmp_path)
    assert result["status"] == REVIEW_REQUIRED
    assert "absolute_match_time_basis_not_demonstrated" in result["review_reasons"]


def test_rejects_cross_format_time_mismatch(tmp_path: Path) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    xml_rows = [dict(row) for row in rows]
    xml_rows[-1]["start"] = "5410.0"
    _write_xml(tmp_path / "surface.xml", xml_rows)
    result = build_time_admission(tmp_path)
    assert result["status"] == REVIEW_REQUIRED
    assert "csv_xml_start_surface_mismatch" in result["review_reasons"]


def test_admitted_adapter_builds_time_context_without_source_order_truth(tmp_path: Path) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    report = build_minimum_context_report(tmp_path, ROOT)
    assert report["time_admission_status"] == "ADMITTED"
    assert report["context_candidate_count"] == 8
    assert report["context_summary"]["time_unit_status_counts"] == {"SECOND": 8}
    assert report["source_row_order_is_temporal_truth"] is False
    assert report["sequence_truth"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_no_sample_match_identity_leak() -> None:
    src = (SRC / "provider_time_semantic_admission.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "World Cup", "Fenerbahce", "Galatasaray", "25.06.2026"]:
        assert token not in src
