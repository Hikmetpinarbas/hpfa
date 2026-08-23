from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "csv_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

from csv_surface_reader import build_csv_surface_audit, inspect_csv_file, write_outputs


def write_csv(path: Path, rows: list[list[str]], delimiter: str = ",", encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerows(rows)


def event_rows() -> list[list[str]]:
    return [
        ["Team", "Type", "Subtype", "Period", "Start Time [s]", "End Time [s]", "Start X", "Start Y", "End X", "End Y"],
        ["Home", "PASS", "", "1", "1.00", "1.50", "0.10", "0.20", "0.30", "0.40"],
        ["Away", "SHOT", "", "1", "2.00", "2.00", "0.90", "0.50", "", ""],
    ]


def inventory_for(path: Path, role: str = "EVENT_ROW_OR_TABULAR_SURFACE_CANDIDATE") -> dict:
    return {"files": [{"file_id": "f1", "relative_path": path.name, "extension": ".csv", "source_role": role, "sha256": "abc"}]}


def test_csv_delimiter_detection(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    write_csv(path, event_rows(), delimiter=";")
    result = inspect_csv_file(path)
    assert result["delimiter_candidate"] == ";"
    assert result["status"] == "PASS"


def test_csv_encoding_detection(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    path.write_bytes("Team;Type;Start Time [s]\nHôme;PASS;1,25\n".encode("cp1252"))
    result = inspect_csv_file(path)
    assert result["encoding_candidate"] == "cp1252"
    assert result["decimal_style_candidate"] == "COMMA"


def test_repeated_header_detection(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows() + [event_rows()[0], ["Home", "PASS", "", "1", "3", "3", "0.1", "0.2", "0.3", "0.4"]]
    write_csv(path, rows)
    result = inspect_csv_file(path)
    assert len(result["repeated_header_row_indices"]) == 1
    assert result["profiled_row_count"] == 3


def test_csv_row_width_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    write_csv(path, event_rows() + [["Home", "PASS"]])
    result = inspect_csv_file(path)
    assert "row_width_mismatch" in result["hard_block_hits"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_raw_columns_preserved_and_unknown_not_guessed(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows()
    rows[0].append("Provider Mystery")
    rows[1].append("x")
    rows[2].append("")
    write_csv(path, rows)
    result = inspect_csv_file(path)
    assert result["raw_columns"][-1] == "Provider Mystery"
    profile = result["column_profiles"][-1]
    assert profile["semantic_family_candidate"] == "unknown"
    assert profile["canonical_key_candidate"] is None


def test_type_subtype_preserved(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows()
    rows.append(["Home", "SET PIECE", "GOAL KICK", "1", "4", "4", "0.1", "0.2", "", ""])
    write_csv(path, rows)
    result = inspect_csv_file(path)
    mapped = [row for row in result["action_taxonomy"] if row["raw_type"] == "SET PIECE"]
    assert mapped[0]["raw_subtype"] == "GOAL KICK"
    assert mapped[0]["canonical_action_family_candidate"] == "goal_kick"


def test_home_away_not_final_team_identity(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    write_csv(path, event_rows())
    result = inspect_csv_file(path)
    assert result["team_binding"]["binding_status"] == "HOME_AWAY_LABEL_NOT_FINAL_IDENTITY"
    assert result["team_binding"]["home_away_used_as_final_identity"] is False


def test_time_base_not_assumed_zero_and_period_monotonic(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows()
    rows[1][4] = "12.50"
    rows[2][4] = "13.00"
    write_csv(path, rows)
    result = inspect_csv_file(path)
    assert result["time_audit"]["time_base_assumed_zero"] is False
    assert result["time_audit"]["period_time_monotonic"] is True


def test_extra_time_detected(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows()
    rows[2][3] = "3"
    write_csv(path, rows)
    assert inspect_csv_file(path)["time_audit"]["extra_time_candidate"] is True


def test_negative_duration_review_required(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows()
    rows[1][4], rows[1][5] = "2.0", "1.9"
    write_csv(path, rows)
    result = inspect_csv_file(path)
    assert result["time_audit"]["negative_duration_count"] == 1
    assert "negative_duration_unreviewed" in result["hard_block_hits"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_zero_duration_not_automatically_invalid(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    write_csv(path, event_rows())
    result = inspect_csv_file(path)
    assert result["time_audit"]["zero_duration_count"] == 1
    assert result["time_audit"]["zero_duration_automatically_invalid"] is False


def test_coordinate_scale_and_raw_preservation(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    write_csv(path, event_rows())
    audit = inspect_csv_file(path)["coordinate_audit"]
    assert audit["coordinate_scale_candidate"] == "0_TO_1_CANDIDATE"
    assert audit["raw_coordinates_preserved"] is True
    assert audit["clamp_applied"] is False


def test_out_of_range_coordinates_flagged(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows()
    rows[1][6] = "-0.01"
    rows[2][6] = "1.02"
    write_csv(path, rows)
    audit = inspect_csv_file(path)["coordinate_audit"]
    assert audit["coordinate_scale_candidate"] == "0_TO_1_CANDIDATE"
    assert audit["out_of_range_count"] == 2


def test_missing_coordinates_action_family_aware(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    write_csv(path, event_rows())
    audit = inspect_csv_file(path)["coordinate_audit"]
    assert audit["missing_coordinates_action_family_aware"] is True
    assert audit["missing_coordinate_counts"]["end_x"] == 1


def test_multi_event_timestamp_not_automatic_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    rows = event_rows()
    rows[2][4] = rows[1][4]
    write_csv(path, rows)
    audit = inspect_csv_file(path)["time_audit"]
    assert audit["duplicate_timestamp_group_count"] == 1
    assert audit["multi_event_timestamp_automatic_duplicate"] is False


def test_exact_duplicate_rows_are_reported_not_canonicalized(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    write_csv(path, event_rows() + [event_rows()[1]])
    result = inspect_csv_file(path)
    assert result["exact_duplicate_row_count"] == 1
    assert result["duplicate_primary_surface_key"] == "NOT_EVALUATED_IDENTITY_REQUIRED"
    assert result["canonical_event_count"] == "UNKNOWN"


def test_manifest_is_not_event_surface(tmp_path: Path) -> None:
    path = tmp_path / "manifest.tsv"
    write_csv(path, [["path", "role"], ["a.csv", "event"]], delimiter="\t")
    result = inspect_csv_file(path, source_role="MANIFEST_SURFACE_CANDIDATE")
    assert "team_field_unusable" not in result["hard_block_hits"]
    assert "action_field_unusable" not in result["hard_block_hits"]


def test_build_uses_unique_inventory_representative(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    write_csv(root / "surface.csv", event_rows())
    write_csv(root / "raw_surface.csv", event_rows())
    inventory = {
        "files": [
            {"file_id": "one", "relative_path": "surface.csv", "extension": ".csv", "source_role": "EVENT_ROW_OR_TABULAR_SURFACE_CANDIDATE", "sha256": "same"},
            {"file_id": "two", "relative_path": "raw_surface.csv", "extension": ".csv", "source_role": "EVENT_ROW_OR_TABULAR_SURFACE_CANDIDATE", "sha256": "same"}
        ],
        "inventory_representatives": [{"representative_file_id": "one"}]
    }
    assert build_csv_surface_audit(root, inventory)["csv_file_count"] == 1


def test_canonical_event_count_unknown_and_no_tactical_truth(tmp_path: Path) -> None:
    path = tmp_path / "surface.csv"
    write_csv(path, event_rows())
    result = inspect_csv_file(path)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert "tactical_truth" in result["does_not_measure"]
    assert result["production_release"] is False


def test_active_match_flag_requires_runtime_authority(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    path = root / "surface.csv"
    write_csv(path, event_rows())
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(inventory_for(path)), encoding="utf-8")
    result = write_outputs(root, inventory_path, tmp_path / "HPFA")
    assert result["active_match_evidence_pass"] is True


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    path = root / "surface.csv"
    write_csv(path, event_rows())
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(inventory_for(path)), encoding="utf-8")
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(root, inventory_path, tmp_path / "HPFA" / "nested")


def test_no_sample_match_identity_leak() -> None:
    source = (SRC / "csv_surface_reader.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798", "1745", "1935"]
    assert not any(token in source for token in forbidden)
