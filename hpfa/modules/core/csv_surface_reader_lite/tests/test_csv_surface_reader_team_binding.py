from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "csv_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

from csv_surface_reader import inspect_csv_file


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, delimiter=";").writerows(rows)


def team_surface_rows() -> list[list[str]]:
    return [
        ["ID", "start", "end", "code", "action", "half", "pos_x", "pos_y"],
        ["1", "5.21", "5.21", "Start of the 1st half", "Start of the 1st half", "1", "", ""],
        ["2", "6.21", "11.21", "Alpha (10) - Passes accurate", "Passes accurate", "1", "52.5", "34"],
        ["3", "12.21", "18.21", "Beta (20) - Shots", "Shots", "1", "105", "68"],
    ]


def test_team_surface_embedded_code_team_binding_candidate(tmp_path: Path) -> None:
    path = tmp_path / "teams.csv"
    write_csv(path, team_surface_rows())
    result = inspect_csv_file(path, source_role="TEAM_SURFACE_CANDIDATE")

    assert result["status"] == "PASS"
    assert "team_field_unusable" not in result["hard_block_hits"]
    assert result["team_binding"]["binding_status"] == "EMBEDDED_CODE_TEAM_CANDIDATE"
    assert result["team_binding"]["raw_team_values"] == ["Alpha (10)", "Beta (20)"]
    assert result["team_binding"]["provider_team_id_candidates"] == ["10", "20"]


def test_embedded_team_candidate_not_final_identity(tmp_path: Path) -> None:
    path = tmp_path / "teams.csv"
    write_csv(path, team_surface_rows())
    binding = inspect_csv_file(path, source_role="TEAM_SURFACE_CANDIDATE")["team_binding"]

    assert binding["home_away_used_as_final_identity"] is False
    assert binding["binding_evidence"]["candidate_only"] is True
    assert binding["binding_evidence"]["method"] == "CODE_PREFIX_BEFORE_EXACT_ACTION_SUFFIX"


def test_player_code_prefix_not_promoted_to_team_candidate(tmp_path: Path) -> None:
    path = tmp_path / "players.csv"
    write_csv(path, team_surface_rows())
    result = inspect_csv_file(path, source_role="PLAYER_SURFACE_CANDIDATE")

    assert result["team_binding"]["binding_status"] == "UNRESOLVED"
    assert "team_field_unusable" in result["hard_block_hits"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_team_surface_without_embedded_candidate_stays_review_required(tmp_path: Path) -> None:
    rows = team_surface_rows()
    rows[2][3] = "Passes accurate"
    rows[3][3] = "Shots"
    path = tmp_path / "teams.csv"
    write_csv(path, rows)
    result = inspect_csv_file(path, source_role="TEAM_SURFACE_CANDIDATE")

    assert result["team_binding"]["binding_status"] == "UNRESOLVED"
    assert "team_field_unusable" in result["hard_block_hits"]
