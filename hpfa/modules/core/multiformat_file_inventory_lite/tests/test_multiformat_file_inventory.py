from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "multiformat_file_inventory_lite" / "src"
sys.path.insert(0, str(SRC))

from multiformat_file_inventory import build_inventory, write_outputs


def write_csv(path: Path, delimiter: str = ",", encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = delimiter.join(["Team", "Type", "Start Time [s]"]) + "\n"
    text += delimiter.join(["Home", "PASS", "1.25"]) + "\n"
    path.write_bytes(text.encode(encoding))


def write_xlsx(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    visible = workbook.active
    visible.title = "Players"
    visible.append(["Player", "Passes"])
    visible.append(["One", 10])
    hidden = workbook.create_sheet("Metadata")
    hidden.sheet_state = "hidden"
    hidden.append(["Provider", "Candidate"])
    workbook.save(path)


def write_xml(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:s="urn:test">
  <s:event id="1"><s:team>Home</s:team></s:event>
</root>
""",
        encoding="utf-8",
    )


def test_recursive_file_inventory(tmp_path: Path) -> None:
    write_csv(tmp_path / "nested" / "surface.csv")
    write_xml(tmp_path / "deeper" / "surface.xml")
    result = build_inventory(tmp_path)
    assert result["file_count"] == 2
    assert {item["relative_path"] for item in result["files"]} == {
        "nested/surface.csv",
        "deeper/surface.xml",
    }


def test_file_hash_manifest(tmp_path: Path) -> None:
    write_csv(tmp_path / "surface.csv")
    result = build_inventory(tmp_path)
    item = result["files"][0]
    assert len(item["sha256"]) == 64
    assert item["file_id"].startswith("file_")
    assert item["schema_fingerprint"]
    assert item["signature_status"] == "TEXT_TABULAR_PARSED"


def test_csv_delimiter_detection(tmp_path: Path) -> None:
    write_csv(tmp_path / "surface.csv", delimiter=";")
    result = build_inventory(tmp_path)
    item = result["files"][0]
    assert item["delimiter_candidate"] == ";"
    assert item["visible_column_count"] == 3
    assert item["surface_row_count"] == 1


def test_csv_encoding_detection(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    path.write_bytes("Team,Type\nHôme,PASS\n".encode("cp1252"))
    result = build_inventory(tmp_path)
    assert result["files"][0]["encoding_candidate"] == "cp1252"


def test_xlsx_sheet_inventory(tmp_path: Path) -> None:
    write_xlsx(tmp_path / "surface.xlsx")
    result = build_inventory(tmp_path)
    item = result["files"][0]
    assert item["sheet_names"] == ["Players", "Metadata"]
    assert item["surface_row_count"] == 3
    assert item["visible_column_count"] == 2
    assert item["signature_status"] == "ZIP_XLSX_CONFIRMED"


def test_xlsx_hidden_sheet_report(tmp_path: Path) -> None:
    write_xlsx(tmp_path / "surface.xlsx")
    result = build_inventory(tmp_path)
    assert result["files"][0]["sheet_states"]["Metadata"] == "hidden"


def test_xml_namespace_handling(tmp_path: Path) -> None:
    write_xml(tmp_path / "surface.xml")
    result = build_inventory(tmp_path)
    item = result["files"][0]
    assert item["xml_root_tag"] == "root"
    assert item["xml_namespace_map"]["s"] == "urn:test"
    assert item["surface_row_count"] == 1


def test_xml_external_entities_disabled(tmp_path: Path) -> None:
    path = tmp_path / "surface.xml"
    path.write_text(
        """<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root><event>&xxe;</event></root>
""",
        encoding="utf-8",
    )
    result = build_inventory(tmp_path)
    item = result["files"][0]
    assert item["parse_status"] == "FAIL_CLOSED"
    assert "external_entity_resolution_attempted" in item["hard_block_hits"]
    assert result["status"] == "FAIL_CLOSED"


def test_exact_duplicate_detection(tmp_path: Path) -> None:
    write_csv(tmp_path / "one.csv")
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "one.csv").write_bytes((tmp_path / "one.csv").read_bytes())
    result = build_inventory(tmp_path)
    report = result["duplicate_report"]
    assert report["exact_duplicate_group_count"] == 1
    assert report["exact_duplicate_reflection_count"] == 1
    assert report["unique_content_file_count"] == 1
    assert result["unique_content_file_count"] == 1
    group = report["exact_duplicate_groups"][0]
    assert group["status"] == "EXACT_DUPLICATE_REFLECTION"
    assert group["representative_relative_path"] == "one.csv"
    assert "not_source_truth" in group["representative_selection_rule"]
    assert report["duplicate_file_conflict_count"] == 0


def test_duplicate_file_conflict(tmp_path: Path) -> None:
    write_csv(tmp_path / "one" / "surface.csv")
    write_csv(tmp_path / "two" / "surface.csv", delimiter=";")
    result = build_inventory(tmp_path)
    assert result["duplicate_report"]["duplicate_file_conflict_count"] == 1
    assert "duplicate_file_conflict" in result["hard_block_hits"]
    assert result["status"] == "FAIL_CLOSED"


def test_empty_file_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "empty.csv").write_bytes(b"")
    result = build_inventory(tmp_path)
    assert result["status"] == "FAIL_CLOSED"
    assert "empty_file" in result["files"][0]["hard_block_hits"]


def test_input_root_missing_fails_closed(tmp_path: Path) -> None:
    result = build_inventory(tmp_path / "missing")
    assert result["status"] == "FAIL_CLOSED"
    assert result["hard_block_hits"] == ["input_root_missing"]


def test_unknown_unsupported_file_requires_review(tmp_path: Path) -> None:
    write_csv(tmp_path / "surface.csv")
    (tmp_path / "video.mp4").write_bytes(b"not-a-video")
    result = build_inventory(tmp_path)
    assert result["unsupported_file_count"] == 1
    assert result["unresolved_unsupported_file_count"] == 1
    assert result["status"] == "REVIEW_REQUIRED"


def test_reference_pdf_does_not_degrade_status(tmp_path: Path) -> None:
    write_csv(tmp_path / "surface.csv")
    report = tmp_path / "reference_reports" / "report.pdf"
    report.parent.mkdir()
    report.write_bytes(b"%PDF-1.4 reference")
    result = build_inventory(tmp_path)
    assert result["unsupported_file_count"] == 1
    assert result["reference_only_unsupported_file_count"] == 1
    assert result["unresolved_unsupported_file_count"] == 0
    assert result["status"] == "PASS"
    item = result["unsupported_files"][0]
    assert item["source_role"] == "REFERENCE_REPORT_SURFACE"
    assert item["review_required"] is False


def test_governance_markdown_does_not_degrade_status(tmp_path: Path) -> None:
    write_csv(tmp_path / "surface.csv")
    path = tmp_path / "manifest" / "ACTIVE_MATCH_AUTHORITY.md"
    path.parent.mkdir()
    path.write_text("authority", encoding="utf-8")
    result = build_inventory(tmp_path)
    assert result["status"] == "PASS"
    item = result["unsupported_files"][0]
    assert item["source_role"] == "GOVERNANCE_MANIFEST_SURFACE"
    assert item["review_required"] is False


def test_manifest_tsv_is_not_event_surface(tmp_path: Path) -> None:
    path = tmp_path / "manifest" / "import_manifest.tsv"
    path.parent.mkdir()
    path.write_text("source\tstatus\n", encoding="utf-8")
    result = build_inventory(tmp_path)
    item = result["files"][0]
    assert item["surface_row_count"] == 0
    assert item["source_role"] == "MANIFEST_SURFACE_CANDIDATE"
    assert result["status"] == "PASS"


def test_canonical_event_count_unknown(tmp_path: Path) -> None:
    write_csv(tmp_path / "surface.csv")
    result = build_inventory(tmp_path)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert all(item["canonical_event_count"] == "UNKNOWN" for item in result["files"])
    assert result["active_match_evidence_pass"] is False
    assert result["production_release"] is False


def test_active_match_execution_is_bound_to_runtime_authority(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime" / "active_single_match" / "current"
    runtime.mkdir(parents=True)
    write_csv(runtime / "surface.csv")
    output_root = tmp_path / "HPFA"
    result = write_outputs(
        runtime,
        output_root,
        root=ROOT,
        runtime_authority=runtime,
        active_match_execution=True,
    )
    assert result["active_match_evidence_pass"] is True
    assert result["runtime_execution"]["input_matches_runtime_authority"] is True
    assert result["status"] == "PASS"
    decision = (output_root / "multiformat_ingest_decision_v1.txt").read_text(encoding="utf-8")
    assert "active_match_evidence_pass=true" in decision


def test_active_match_execution_fails_closed_on_wrong_authority(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime" / "active_single_match" / "current"
    other = tmp_path / "other"
    runtime.mkdir(parents=True)
    other.mkdir()
    write_csv(runtime / "surface.csv")
    result = write_outputs(
        runtime,
        tmp_path / "HPFA",
        root=ROOT,
        runtime_authority=other,
        active_match_execution=True,
    )
    assert result["active_match_evidence_pass"] is False
    assert result["status"] == "FAIL_CLOSED"
    assert "runtime_authority_mismatch" in result["hard_block_hits"]
    assert "runtime_authority_path_invalid" in result["hard_block_hits"]


def test_outputs_are_flat_and_complete(tmp_path: Path) -> None:
    write_csv(tmp_path / "input" / "surface.csv")
    output_root = tmp_path / "HPFA"
    result = write_outputs(tmp_path / "input", output_root, root=ROOT)
    assert result["status"] == "PASS"
    expected = {
        "multiformat_file_inventory_lite_v1.json",
        "input_file_inventory.json",
        "input_file_inventory.tsv",
        "unsupported_file_report.json",
        "duplicate_file_fingerprint_report.json",
        "multiformat_ingest_decision_v1.txt",
    }
    assert {path.name for path in output_root.iterdir()} == expected


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    write_csv(tmp_path / "input" / "surface.csv")
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(tmp_path / "input", tmp_path / "HPFA" / "nested", root=ROOT)


def test_no_sample_match_identity_leak() -> None:
    source = (SRC / "multiformat_file_inventory.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798"]
    assert not any(token in source for token in forbidden)
