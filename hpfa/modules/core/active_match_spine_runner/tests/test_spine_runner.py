import json
import sys
import types
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
sys.path.insert(0, str(SRC))

from spine_runner import (  # noqa: E402
    _boundary_scorer_module,
    _surface_manifest_module,
    run_spine_check,
    validate_active_match_authority,
    validate_output_root,
    validate_runtime_surface,
)


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
    assert result["active_match_authority_validated"] is True
    assert result["surface_manifest"]["status"] == "PASS"
    assert result["surface_manifest"]["surface_file_count"] == 8
    assert result["surface_manifest"]["report_language_allowed"] is False
    assert result["production_binding_allowed"] is False
    assert result["boundary_scores"]["score_count"] == 1
    assert result["runtime_surface_policy"]["executed_runtime_surfaces"] == [
        "hpfa/modules/core/canonical_ingest_surface_manifest",
        "hpfa/modules/core/composite_integration_office",
    ]
    assert result["runtime_surface_policy"]["unregistered_runtime_surface_allowed"] is False
    assert result["runtime_surface_policy"]["donor_runtime_binding_allowed"] is False

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
    assert result["runtime_surface_policy"]["executed_runtime_surfaces"] == [
        "hpfa/modules/core/canonical_ingest_surface_manifest"
    ]
    summary = (out / "active_match_spine_check_v1.txt").read_text(encoding="utf-8")
    assert "[runtime_surface_policy]" in summary
    assert "[boundary_scores]" in summary
    assert "status=SKIPPED" in summary


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root("/sdcard/Download/HPFA/spine-run")


def test_phone_output_root_is_allowed():
    assert str(validate_output_root("/sdcard/Download/HPFA")).endswith("/Download/HPFA")


def test_active_match_authority_is_path_discovered_but_suffix_contract_is_fixed(tmp_path):
    match = make_active_match(tmp_path)
    assert validate_active_match_authority(match) == match.resolve()

    wrong = tmp_path / "runtime" / "some_other_match" / "current"
    wrong.mkdir(parents=True)
    with pytest.raises(ValueError, match="runtime_authority_path_invalid"):
        validate_active_match_authority(wrong)


def test_case_variant_active_match_authority_suffix_is_rejected(tmp_path):
    case_variant = tmp_path / "RUNTIME" / "ACTIVE_SINGLE_MATCH" / "CURRENT"
    case_variant.mkdir(parents=True)
    with pytest.raises(ValueError, match="runtime_authority_path_invalid"):
        validate_active_match_authority(case_variant)


def test_only_registered_product_runtime_surfaces_are_executable():
    allowed = ROOT / "hpfa" / "modules" / "core" / "canonical_ingest_surface_manifest" / "src"
    assert validate_runtime_surface(ROOT, allowed) == allowed.resolve()

    with pytest.raises(ValueError, match="unregistered_runtime_surface"):
        validate_runtime_surface(ROOT, ROOT / "docs" / "contracts")


def test_archive_donor_reference_and_fixture_runtime_surfaces_fail_closed(tmp_path):
    for relative, error_code in [
        ("archive/legacy.py", "archive_surface_import_attempted"),
        ("donor/engine.py", "donor_surface_runtime_bound"),
        ("reference_only/note.py", "reference_only_surface_executed"),
        ("fixtures/sample.py", "fixture_surface_used_as_active_match"),
    ]:
        candidate = tmp_path / relative
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("pass\n", encoding="utf-8")
        with pytest.raises(ValueError, match=error_code):
            validate_runtime_surface(tmp_path, candidate)


def test_runtime_surface_outside_product_repo_is_rejected(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("pass\n", encoding="utf-8")
    with pytest.raises(ValueError, match="runtime_surface_outside_product_repo"):
        validate_runtime_surface(ROOT, outside)


def test_cached_surface_manifest_from_wrong_origin_fails_closed(monkeypatch, tmp_path):
    fake = types.SimpleNamespace(__file__=str(tmp_path / "surface_manifest.py"))
    monkeypatch.setitem(sys.modules, "surface_manifest", fake)
    with pytest.raises(ValueError, match="runtime_module_origin_mismatch:surface_manifest"):
        _surface_manifest_module(ROOT)


def test_cached_boundary_scorer_from_wrong_origin_fails_closed(monkeypatch, tmp_path):
    fake = types.SimpleNamespace(__file__=str(tmp_path / "boundary_analysis_scorer.py"))
    monkeypatch.setitem(sys.modules, "boundary_analysis_scorer", fake)
    with pytest.raises(ValueError, match="runtime_module_origin_mismatch:boundary_analysis_scorer"):
        _boundary_scorer_module(ROOT)
