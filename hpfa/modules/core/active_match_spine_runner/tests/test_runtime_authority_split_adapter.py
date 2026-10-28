from pathlib import Path

import pytest

from hpfa.modules.core.active_match_spine_runner.src.runtime_authority_split_adapter import (
    validate_split_active_match_authority,
)


def test_split_runtime_authority_accepts_explicit_runtime_root(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime_authority"
    active = runtime_root / "runtime" / "active_single_match" / "current"
    active.mkdir(parents=True)

    resolved = validate_split_active_match_authority(active, runtime_root)

    assert resolved == active.resolve()


def test_split_runtime_authority_rejects_wrong_root(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime_authority"
    wrong_root = tmp_path / "product_checkout"
    active = runtime_root / "runtime" / "active_single_match" / "current"
    active.mkdir(parents=True)
    wrong_root.mkdir()

    with pytest.raises(ValueError, match="runtime_authority_root_binding_mismatch"):
        validate_split_active_match_authority(active, wrong_root)


def test_split_runtime_authority_rejects_forbidden_ancestry(tmp_path: Path) -> None:
    runtime_root = tmp_path / "archive" / "runtime_authority"
    active = runtime_root / "runtime" / "active_single_match" / "current"
    active.mkdir(parents=True)

    with pytest.raises(ValueError, match="runtime_authority_forbidden_ancestry"):
        validate_split_active_match_authority(active, runtime_root)
