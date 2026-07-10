from pathlib import Path
import importlib.util


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
