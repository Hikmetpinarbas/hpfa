from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "csv_surface_reader_lite" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import csv_surface_reader as reader
from content_role_bridge import install_content_team_binding


def _write_rows(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerows(rows)


def test_content_embedded_team_candidate_does_not_require_filename_role(tmp_path: Path) -> None:
    install_content_team_binding(reader)
    path = tmp_path / "opaque.csv"
    _write_rows(
        path,
        [
            ["ID", "start", "end", "code", "action", "half", "pos_x", "pos_y"],
            ["1", "1.0", "1.5", "Alpha (101) - PASS", "PASS", "1", "10", "20"],
            ["2", "2.0", "2.5", "Beta (202) - SHOT", "SHOT", "1", "30", "40"],
        ],
    )

    result = reader.inspect_csv_file(path, "MATCH_SUMMARY_SURFACE_CANDIDATE")

    assert result["team_binding"]["binding_status"] == "EMBEDDED_CODE_TEAM_CANDIDATE"
    assert result["team_binding"]["resolved_source_role_candidate"] == "TEAM_SURFACE_CANDIDATE"
    assert result["team_binding"]["binding_evidence"]["filename_support_used_for_admission"] is False
    assert result["team_binding"]["validated_team_identity"] is False
    assert "team_field_unusable" not in result["hard_block_hits"]
    assert result["canonical_event_count"] == "UNKNOWN"


def test_unresolved_content_is_not_promoted_to_team(tmp_path: Path) -> None:
    install_content_team_binding(reader)
    path = tmp_path / "opaque.csv"
    _write_rows(
        path,
        [
            ["ID", "start", "end", "code", "action", "half", "pos_x", "pos_y"],
            ["1", "1.0", "1.5", "unstructured-code", "PASS", "1", "10", "20"],
        ],
    )

    result = reader.inspect_csv_file(path, "MATCH_SUMMARY_SURFACE_CANDIDATE")

    assert result["team_binding"]["binding_status"] == "UNRESOLVED"
    assert "team_field_unusable" in result["hard_block_hits"]
    assert result["canonical_event_count"] == "UNKNOWN"
