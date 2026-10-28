from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hpfa_reproducible_wheel_probe_v1",
    ROOT / "tools" / "hpfa_reproducible_wheel_probe_v1.py",
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def _zip(path: Path, payload: bytes) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("hpfa/a.py", payload)
    return path


def test_compare_wheels_accepts_byte_identical_archives(tmp_path: Path) -> None:
    a = _zip(tmp_path / "a.whl", b"x")
    b = tmp_path / "b.whl"
    b.write_bytes(a.read_bytes())
    report = MOD.compare_wheels(a, b)
    assert report["byte_identical"] is True
    assert report["entry_name_sets_equal"] is True
    assert report["content_diff_entries"] == []


def test_compare_wheels_separates_content_drift(tmp_path: Path) -> None:
    a = _zip(tmp_path / "a.whl", b"x")
    b = _zip(tmp_path / "b.whl", b"y")
    report = MOD.compare_wheels(a, b)
    assert report["byte_identical"] is False
    assert report["content_diff_entries"] == ["hpfa/a.py"]
