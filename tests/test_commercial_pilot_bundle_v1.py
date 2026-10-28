from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_controlled_commercial_pilot_bundle_v1",
    ROOT / "tools" / "build_controlled_commercial_pilot_bundle_v1.py",
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_bundle_contains_owned_product_and_excludes_forbidden_roots(tmp_path: Path) -> None:
    out = tmp_path / "pilot.zip"
    report = MOD.build_bundle(ROOT, out, exact_head_sha="abc123")
    assert report["bundle_status"] == "PASS"
    assert report["exact_head_sha"] == "abc123"
    assert report["raw_match_data_bundled"] is False
    assert report["raw_donor_bundled"] is False
    assert report["production_release"] is False
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
    for required in [
        "README.md",
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md",
        "pyproject.toml",
        "release/commercial_pilot_policy_v1.json",
        "release/HPFA_CONTROLLED_COMMERCIAL_PILOT_QUICKSTART_V1.md",
        "active_match_spine_runner.py",
    ]:
        assert required in names
    assert not any(name.startswith("runtime/") for name in names)
    assert not any(name.startswith("data/") for name in names)
    assert not any(name.startswith("vendor/") for name in names)
    assert not any("/tests/" in name or name.startswith("tests/") for name in names)
    assert not any("__pycache__" in name for name in names)


def test_bundle_is_deterministic_for_same_tree(tmp_path: Path) -> None:
    one = tmp_path / "one.zip"
    two = tmp_path / "two.zip"
    first = MOD.build_bundle(ROOT, one, exact_head_sha="abc123")
    second = MOD.build_bundle(ROOT, two, exact_head_sha="abc123")
    assert first["bundle_sha256"] == second["bundle_sha256"]
    assert one.read_bytes() == two.read_bytes()
