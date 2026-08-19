from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

from hpfa.modules.core.xlsx_surface_reader_lite.tests.ooxml_fixture import write_xlsx

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "xlsx_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

import xlsx_runtime_guard as guard


def make_workbook(path: Path) -> None:
    write_xlsx(
        path,
        sheets=[
            {
                "name": "Main statistics",
                "rows": [
                    ["Player", "Team", "Minutes"],
                    ["Alpha", "Side A", 90],
                ],
            }
        ],
    )


def inventory(path: Path, relative_path: str | None = None) -> dict:
    return {
        "files": [
            {
                "file_id": "xlsx_a",
                "relative_path": relative_path or path.name,
                "extension": ".xlsx",
                "sha256": "candidate_sha",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
            }
        ]
    }


def write_inventory(path: Path, payload: dict) -> Path:
    target = path / "inventory.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def test_valid_xlsx_archive_passes(tmp_path: Path) -> None:
    workbook = tmp_path / "players.xlsx"
    make_workbook(workbook)
    result = guard.guard_runtime_inputs(
        tmp_path,
        write_inventory(tmp_path, inventory(workbook)),
    )
    assert result["status"] == "PASS"
    assert result["xlsx_file_count"] == 1
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_inventory_path_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.xlsx"
    make_workbook(outside)
    payload = inventory(outside, "../outside.xlsx")
    with pytest.raises(
        guard.XlsxRuntimeGuardError,
        match="inventory_relative_path_outside_input_root",
    ):
        guard.guard_runtime_inputs(
            tmp_path,
            write_inventory(tmp_path, payload),
        )


def test_required_xlsx_members_are_enforced(tmp_path: Path) -> None:
    fake = tmp_path / "fake.xlsx"
    with zipfile.ZipFile(fake, "w") as archive:
        archive.writestr("placeholder.txt", "not a workbook")
    with pytest.raises(
        guard.XlsxRuntimeGuardError,
        match="xlsx_required_members_missing",
    ):
        guard.inspect_xlsx_archive(fake)


def test_uncompressed_archive_budget_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = tmp_path / "large.xlsx"
    with zipfile.ZipFile(fake, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("[Content_Types].xml", "x" * 40)
        archive.writestr("xl/workbook.xml", "y" * 40)
    monkeypatch.setattr(guard, "MAX_XLSX_ARCHIVE_UNCOMPRESSED_BYTES", 32)
    with pytest.raises(
        guard.XlsxRuntimeGuardError,
        match="xlsx_archive_uncompressed_budget_exceeded",
    ):
        guard.inspect_xlsx_archive(fake)


def test_malformed_inventory_fails_closed(tmp_path: Path) -> None:
    inventory_file = tmp_path / "inventory.json"
    inventory_file.write_text("{not-json", encoding="utf-8")
    with pytest.raises(
        guard.XlsxRuntimeGuardError,
        match="inventory_json_malformed",
    ):
        guard.guard_runtime_inputs(tmp_path, inventory_file)


def test_no_sample_match_identity_leak() -> None:
    text = (SRC / "xlsx_runtime_guard.py").read_text(encoding="utf-8").casefold()
    forbidden = [
        "australia",
        "turkey",
        "galatasaray",
        "fenerbahce",
        "13.06.2026",
    ]
    assert not any(token in text for token in forbidden)
