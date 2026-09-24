from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPINE = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src" / "spine_runner.py"
ADAPTER = ROOT / "hpfa" / "platforms" / "termux_delivery_policy.py"


def test_core_spine_does_not_own_android_absolute_paths() -> None:
    text = SPINE.read_text(encoding="utf-8")
    assert "/sdcard/" not in text
    assert "/storage/emulated/" not in text
    assert "termux_delivery_policy" in text


def test_termux_delivery_adapter_owns_legacy_flat_download_policy() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "/sdcard/Download/HPFA" in text
    assert "/storage/emulated/0/Download/HPFA" in text
    assert 'POLICY_IS_FOOTBALL_TRUTH = False' in text
    assert 'POLICY_IS_RUNTIME_AUTHORITY = False' in text


def test_termux_delivery_adapter_is_packaged_under_hpfa_namespace() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'include = ["hpfa*", "canon*"]' in pyproject
    assert ADAPTER.is_file()
