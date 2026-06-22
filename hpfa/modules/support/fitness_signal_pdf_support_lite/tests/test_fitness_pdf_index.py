import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "support" / "fitness_signal_pdf_support_lite" / "src"
sys.path.insert(0, str(SRC))

from fitness_pdf_index import build_index, write_outputs


def test_pdf_index_finds_pdfs_and_preserves_claim_boundary(tmp_path):
    match = tmp_path / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    (match / "team_load_report.pdf").write_bytes(b"%PDF-1.4\n%stub\n")

    result = build_index(match)

    assert result["status"] == "PDF_INDEX_PASS"
    assert result["pdf_count"] == 1
    assert result["runtime_event_truth"] is False
    assert result["pdfs"][0]["extraction_status"] == "PDF_PRESENT_EXTRACTION_PENDING"


def test_pdf_index_writes_flat_outputs(tmp_path):
    match = tmp_path / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    (match / "gps_report.pdf").write_bytes(b"%PDF-1.4\n%stub\n")
    out = tmp_path / "HPFA"

    result = write_outputs(match, out, root=ROOT)

    assert result["status"] == "PDF_INDEX_PASS"
    assert (out / "fitness_signal_pdf_index_v1.json").exists()
    assert (out / "fitness_signal_pdf_index_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected(tmp_path):
    match = tmp_path / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(match, "/sdcard/Download/HPFA/pdf-index", root=ROOT)
