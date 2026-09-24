from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hpfa_release_readiness_audit_v1",
    ROOT / "tools" / "hpfa_release_readiness_audit_v1.py",
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def _wheel(path: Path, forbidden: bool = False) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("hpfa/modules/core/example.py", "x=1\n")
        z.writestr("hpfa/modules/core/example/registry/items.json", "{}")
        z.writestr("hpfa-0.1.0.dist-info/LICENSE", "private")
        z.writestr("hpfa-0.1.0.dist-info/NOTICE", "notice")
        if forbidden:
            z.writestr("vendor/raw.py", "x=1\n")
    return path


def test_clean_bundle_passes_integrity_but_release_remains_review_required(tmp_path: Path) -> None:
    report = MOD.audit(ROOT, _wheel(tmp_path / "hpfa.whl"))
    assert report["bundle_integrity_status"] == "PASS"
    assert report["release_decision"] == "REVIEW_REQUIRED"
    assert report["production_release"] is False
    assert report["exact_dependency_lock_present"] is False
    assert report["forbidden_bundle_entries"] == []


def test_forbidden_raw_surface_fails_bundle_integrity(tmp_path: Path) -> None:
    report = MOD.audit(ROOT, _wheel(tmp_path / "hpfa.whl", forbidden=True))
    assert report["bundle_integrity_status"] == "FAIL"
    assert report["release_decision"] == "REVIEW_REQUIRED"
    assert report["forbidden_bundle_entries"] == ["vendor/raw.py"]


def test_every_optional_dependency_has_release_license_policy(tmp_path: Path) -> None:
    report = MOD.audit(ROOT, _wheel(tmp_path / "hpfa.whl"))
    assert report["missing_license_policy_entries"] == []
    assert report["orphan_license_policy_entries"] == []
