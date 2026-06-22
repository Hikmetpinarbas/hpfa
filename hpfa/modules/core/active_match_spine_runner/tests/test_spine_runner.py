import json
import zipfile
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
sys.path.insert(0, str(SRC))

from spine_runner import run_spine_check, validate_output_root


def write_csv(path: Path):
    path.write_text("id,x,y\n1,10,20\n", encoding="utf-8")


def write_xml(path: Path):
    path.write_text("<root><instance/><instance/></root>", encoding="utf-8")


def write_xlsx(path: Path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/worksheets/sheet1.xml", "<worksheet><sheetData><row/><row/></sheetData></worksheet>")


def make_active_match(tmp_path: Path) -> Path:
    match = tmp_path / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    write_csv(match / "Players.csv")
    write_csv(match / "Teams.csv")
    write_csv(match / "Goalkeepers.csv")
    write_xml(match / "Players.xml")
    write_xml(match / "Teams.xml")
    write_xml(match / "Goalkeepers.xml")
    write_xlsx(match / "Players.xlsx")
    write_xlsx(match / "Goalkeepers.xlsx")
    return match


def make_registry(tmp_path: Path) -> Path:
    registry = tmp_path / "composite_registry.json"
    registry.write_text(json.dumps([
        {
            "composite_id": "COMP-SPINE-RUNNER",
            "dominant_capability": "canonical_ingest",
            "source_count": 4,
            "sources": ["TERMUX", "GITHUB"],
            "active_match_validation_required": True,
            "members": [
                {
                    "file_name": "canonical_ingest.py",
                    "normalized_name": "canonical_ingest",
                    "source_path": "/tmp/canonical_ingest.py",
                    "symbols": ["def:run"],
                    "dependency_flags": [],
                }
            ],
        }
    ]), encoding="utf-8")
    return registry


def test_spine_runner_writes_flat_json_and_txt_outputs(tmp_path):
    match = make_active_match(tmp_path)
    registry = make_registry(tmp_path)
    out = tmp_path / "HPFA"

    result = run_spine_check(match, out, composite_registry=registry, root=ROOT)

    assert result["status"] == "PASS"
    assert result["surface_manifest"]["status"] == "PASS"
    assert result["surface_manifest"]["surface_file_count"] == 8
    assert result["surface_manifest"]["report_language_allowed"] is False
    assert result["production_binding_allowed"] is False
    assert result["boundary_scores"]["score_count"] == 1

    assert (out / "active_match_surface_manifest_v1.json").exists()
    assert (out / "boundary_analysis_score_registry_v1.json").exists()
    assert (out / "active_match_spine_check_v1.json").exists()
    assert (out / "active_match_spine_check_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_spine_runner_can_skip_boundary_scores(tmp_path):
    match = make_active_match(tmp_path)
    out = tmp_path / "HPFA"

    result = run_spine_check(match, out, root=ROOT)

    assert result["status"] == "PASS"
    assert result["boundary_scores"] is None
    summary = (out / "active_match_spine_check_v1.txt").read_text(encoding="utf-8")
    assert "[boundary_scores]" in summary
    assert "status=SKIPPED" in summary


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root("/sdcard/Download/HPFA/spine-run")


def test_phone_output_root_is_allowed():
    assert str(validate_output_root("/sdcard/Download/HPFA")).endswith("/Download/HPFA")
