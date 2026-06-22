import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "support" / "reference_document_ingest_lite" / "src"
sys.path.insert(0, str(SRC))

from reference_document_ingest import build_manifest_and_pages, sha256_file, write_outputs


def write_minimal_pdf(path: Path):
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )


def test_reference_document_ingest_indexes_pdf_and_sha(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    pdf = incoming / "team_load_report.pdf"
    write_minimal_pdf(pdf)

    manifest, pages, audit = build_manifest_and_pages(incoming, active_match_mode=True)

    assert audit["pdf_count"] == 1
    assert audit["runtime_event_truth"] is False
    assert manifest[0]["sha256"] == sha256_file(pdf)
    assert manifest[0]["source_role"] == "ACTIVE_MATCH_ADJACENT_SUPPORT_DOCUMENT"
    assert manifest[0]["support_signal_type"] == "LOAD_FITNESS_SUPPORT_PDF"
    assert isinstance(pages, list)


def test_reference_document_ingest_writes_flat_outputs(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    write_minimal_pdf(incoming / "gps_report.pdf")
    out = tmp_path / "HPFA"

    audit = write_outputs(incoming, out, active_match_mode=True, root=ROOT)

    assert audit["pdf_count"] == 1
    assert (out / "reference_document_manifest_v1.json").exists()
    assert (out / "reference_document_pages_v1.jsonl").exists()
    assert (out / "reference_document_extraction_audit_v1.json").exists()
    assert (out / "reference_document_extraction_audit_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(incoming, "/sdcard/Download/HPFA/reference-docs", root=ROOT)
