from pathlib import Path
import importlib.util
import json
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "active_match_phone_evidence_run.py"
SPEC = importlib.util.spec_from_file_location("active_match_phone_evidence_run", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_surface_files_accept_only_event_formats(tmp_path):
    for name in ("a.csv", "b.xml", "c.xlsx", "ignore.mp4", "ignore.txt"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert [path.name for path in MODULE._surface_files(tmp_path)] == ["a.csv", "b.xml", "c.xlsx"]


def test_declared_phone_roots_are_accepted():
    assert MODULE._validate_flat_phone_output(Path("/sdcard/Download/HPFA")) == Path("/sdcard/Download/HPFA")
    assert MODULE._validate_flat_phone_output(Path("/storage/emulated/0/Download/HPFA")) == Path("/storage/emulated/0/Download/HPFA")


def test_nested_phone_output_is_rejected():
    try:
        MODULE._validate_flat_phone_output(Path("/sdcard/Download/HPFA/nested"))
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested output path was not rejected")


def _write_expected_outputs(output_root: Path, overrides=None):
    overrides = overrides or {}
    exact_status = {
        "active_match_spine_check_v1.json": "PASS",
        "active_match_surface_manifest_v1.json": "PASS",
        "active_match_full_run_lite_v1.json": "REVIEW_REQUIRED",
        "active_match_analyst_report_lite_v1.json": "PASS",
    }
    for name in MODULE.EXPECTED_OUTPUTS:
        path = output_root / name
        if name.endswith(".json"):
            status = overrides.get(name, exact_status.get(name, "SMOKE_PASS"))
            path.write_text(json.dumps({"status": status, "module_id": name}), encoding="utf-8")
        else:
            path.write_text("evidence\n", encoding="utf-8")


def _passed_steps():
    return [{"command": ["python", "step.py"], "returncode": 0, "passed": True, "stdout": "", "stderr": ""}]


def test_clear_owned_artifacts_prevents_stale_evidence_reuse(tmp_path):
    stale = tmp_path / MODULE.EXPECTED_OUTPUTS[0]
    stale.write_text("stale", encoding="utf-8")
    unrelated = tmp_path / "user_file.txt"
    unrelated.write_text("keep", encoding="utf-8")
    cleared = MODULE._clear_owned_artifacts(tmp_path)
    assert MODULE.EXPECTED_OUTPUTS[0] in cleared
    assert not stale.exists()
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_manifest_fails_closed_on_semantic_status_even_when_steps_return_zero(tmp_path):
    surface = tmp_path / "input.csv"
    surface.write_text("event\npass\n", encoding="utf-8")
    _write_expected_outputs(tmp_path, {"active_match_spine_check_v1.json": "FAIL_CLOSED"})
    report = MODULE._write_manifest(tmp_path, tmp_path, [surface], _passed_steps(), [])
    assert report["status"] == "FAIL_CLOSED"
    assert report["engineering_evidence"]["all_steps_passed"] is True
    assert report["engineering_evidence"]["semantic_outputs_passed"] is False
    assert report["engineering_evidence"]["status_failures"][0]["name"] == "active_match_spine_check_v1.json"


def test_manifest_fails_closed_on_empty_or_malformed_output(tmp_path):
    surface = tmp_path / "input.csv"
    surface.write_text("event\npass\n", encoding="utf-8")
    _write_expected_outputs(tmp_path)
    (tmp_path / "active_match_spine_check_v1.txt").write_text("", encoding="utf-8")
    (tmp_path / "time_scale_router_lite_v1.json").write_text("{", encoding="utf-8")
    report = MODULE._write_manifest(tmp_path, tmp_path, [surface], _passed_steps(), [])
    assert report["status"] == "FAIL_CLOSED"
    assert "active_match_spine_check_v1.txt" in report["engineering_evidence"]["empty_outputs"]
    assert report["engineering_evidence"]["malformed_json_outputs"][0]["name"] == "time_scale_router_lite_v1.json"


def test_manifest_pass_requires_fresh_complete_semantic_evidence(tmp_path):
    surface = tmp_path / "input.csv"
    surface.write_text("event\npass\n", encoding="utf-8")
    _write_expected_outputs(tmp_path)
    report = MODULE._write_manifest(tmp_path, tmp_path, [surface], _passed_steps(), ["old.json"])
    assert report["status"] == "ACTIVE_MATCH_EVIDENCE_PASS"
    assert report["engineering_evidence"]["semantic_outputs_passed"] is True
    assert report["surface_inputs"][0]["name"] == "input.csv"
    assert len(report["surface_inputs"][0]["sha256"]) == 64
    assert report["evidence_zip"].endswith(MODULE.EVIDENCE_ZIP)


def test_zip_contains_self_consistent_manifest(tmp_path):
    surface = tmp_path / "input.csv"
    surface.write_text("event\npass\n", encoding="utf-8")
    _write_expected_outputs(tmp_path)
    report = MODULE._write_manifest(tmp_path, tmp_path, [surface], _passed_steps(), [])
    zip_path = MODULE._write_zip(tmp_path)
    with zipfile.ZipFile(zip_path) as archive:
        archived = json.loads(archive.read(MODULE.MANIFEST_JSON))
    assert archived["evidence_zip"] == report["evidence_zip"]
    assert archived["status"] == "ACTIVE_MATCH_EVIDENCE_PASS"

