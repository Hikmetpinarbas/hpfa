from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "csv_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

from csv_surface_reader import inspect_csv_file, write_outputs


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(rows)


def event_rows() -> list[list[str]]:
    return [
        ["Team", "Type", "Period", "Start Time [s]", "End Time [s]", "Note"],
        ["Home", "PASS", "1", "1.0", "2.0", "visible evidence"],
    ]


def test_quoted_multiline_value_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows()
    rows[1][-1] = "first line\nsecond line"
    write_csv(path, rows)

    result = inspect_csv_file(path)
    note_profile = next(
        profile
        for profile in result["column_profiles"]
        if profile["raw_column"] == "Note"
    )

    assert note_profile["example_values"] == ["first line\nsecond line"]
    assert result["surface_row_count"] == 1
    assert result["profiled_row_count"] == 1


def test_physical_row_lineage_survives_blank_and_repeated_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "surface.csv"
    path.write_text(
        "Team,Type,Period,Start Time [s],End Time [s]\n"
        "Home,PASS,1,1,2\n"
        "\n"
        "Team,Type,Period,Start Time [s],End Time [s]\n"
        "Away,SHOT,1,3,2\n",
        encoding="utf-8",
    )

    result = inspect_csv_file(path)

    assert result["repeated_header_row_indices"] == [4]
    assert result["time_audit"]["negative_duration_rows"] == [5]


def test_active_match_evidence_is_false_when_hard_block_exists(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    surface = root / "surface.csv"
    write_csv(surface, event_rows() + [["Home", "PASS"]])

    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "file_id": "f1",
                        "relative_path": surface.name,
                        "extension": ".csv",
                        "source_role": "EVENT_ROW_OR_TABULAR_SURFACE_CANDIDATE",
                        "sha256": "candidate",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = write_outputs(root, inventory_path, tmp_path / "HPFA")

    assert payload["status"] == "REVIEW_REQUIRED"
    assert "row_width_mismatch" in payload["hard_block_hits"]
    assert payload["active_match_evidence_pass"] is False
