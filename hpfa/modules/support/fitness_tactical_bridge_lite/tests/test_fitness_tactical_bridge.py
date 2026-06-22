import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "support" / "fitness_tactical_bridge_lite" / "src"
sys.path.insert(0, str(SRC))

from fitness_tactical_bridge import build_bridge, write_outputs


def write_inputs(out: Path):
    out.mkdir(parents=True)
    (out / "canonical_event_lite_audit_v1.json").write_text(json.dumps({
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "primary_event_surface_candidate": "UNRESOLVED",
        "event_count_claim_allowed": False,
        "surface_row_inventory_total": 10,
        "canonical_lite_row_count_deprecated": 10,
        "surface_role_row_counts": {"players": 4, "teams": 4, "goalkeepers": 2},
        "coverage": {"coordinate_rows": 8, "surface_row_inventory_total": 10},
        "event_family_volume": {"PASS": 5, "SHOT": 2},
        "zone_distribution": {"FINAL_THIRD": {"visible_rows": 4, "pct": 40.0}},
        "channel_distribution": {"RIGHT_CHANNEL": {"visible_rows": 3, "pct": 30.0}},
        "team_row_volume": {"Alpha": 6, "Beta": 4},
    }), encoding="utf-8")
    (out / "fitness_signal_pdf_index_v1.json").write_text(json.dumps({
        "status": "PDF_INDEX_PASS",
        "pdf_count": 2,
        "runtime_event_truth": False,
        "pdfs": [
            {"support_signal_type": "LOAD_FITNESS_SUPPORT_PDF", "extraction_status": "PDF_PRESENT_EXTRACTION_PENDING"}
        ],
    }), encoding="utf-8")
    (out / "reference_document_extraction_audit_v1.json").write_text(json.dumps({
        "status": "REFERENCE_DOCUMENT_INGEST_PASS",
        "pdf_count": 2,
        "page_count": 10,
        "chars_total": 1000,
        "texty_pages": 8,
        "err_pages": 0,
        "runtime_event_truth": False,
    }), encoding="utf-8")


def test_bridge_builds_cross_surface_candidates(tmp_path):
    out = tmp_path / "HPFA"
    write_inputs(out)

    report = build_bridge(out)

    assert report["status"] == "PASS"
    event_summary = report["event_evidence_summary"]
    assert event_summary["canonical_event_count"] == "UNKNOWN"
    assert event_summary["deduplicated_event_count"] == "UNKNOWN"
    assert event_summary["primary_event_surface_candidate"] == "UNRESOLVED"
    assert event_summary["event_count_claim_allowed"] is False
    assert event_summary["surface_row_inventory_total"] == 10
    assert report["fitness_pdf_support_summary"]["runtime_event_truth"] is False
    assert len(report["cross_surface_review_candidates"]) == 2
    rendered = json.dumps(report, ensure_ascii=False).lower()
    assert "fatigue caused" not in rendered
    assert "load explains" not in rendered


def test_bridge_writes_flat_outputs(tmp_path):
    out = tmp_path / "HPFA"
    write_inputs(out)

    report = write_outputs(out, root=ROOT)

    assert report["status"] == "PASS"
    assert (out / "fitness_tactical_bridge_lite_v1.json").exists()
    assert (out / "fitness_tactical_bridge_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs("/sdcard/Download/HPFA/bridge", root=ROOT)
