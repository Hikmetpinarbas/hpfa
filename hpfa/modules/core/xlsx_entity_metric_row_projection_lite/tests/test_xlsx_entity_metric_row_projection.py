from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from hpfa.modules.core.xlsx_entity_metric_row_projection_lite.src.xlsx_entity_metric_row_projection import (
    build_projection,
)


def _write_book(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Players"
    ws.append(["Player", "Team", "Minutes", "Shots"])
    ws.append(["A Player", "Team A", 90, 3])
    wb.save(path)
    wb.close()


def _audit(file_id: str, relative_path: str, sha256: str) -> dict:
    return {
        "module_id": "xlsx_surface_reader_lite_v1",
        "status": "PASS",
        "files": [
            {
                "file_id": file_id,
                "relative_path": relative_path,
                "sha256": sha256,
                "sheets": [
                    {
                        "sheet_name": "Players",
                        "sheet_state": "visible",
                        "header_row_index": 1,
                        "raw_columns": ["Player", "Team", "Minutes", "Shots"],
                        "column_profiles": [
                            {
                                "raw_column": "Player",
                                "normalized_column": "player",
                                "identity_role_candidate": "player",
                            },
                            {
                                "raw_column": "Team",
                                "normalized_column": "team",
                                "identity_role_candidate": "team",
                            },
                            {
                                "raw_column": "Minutes",
                                "normalized_column": "minutes",
                                "identity_role_candidate": "minutes",
                            },
                            {
                                "raw_column": "Shots",
                                "normalized_column": "shots",
                                "identity_role_candidate": None,
                                "percent_header_candidate": False,
                            },
                        ],
                    }
                ],
            }
        ],
    }


def test_missing_input_root_fails_closed_and_preserves_truth_locks(tmp_path):
    missing = tmp_path / "missing"
    result = build_projection(
        missing,
        {"files": []},
        {"module_id": "xlsx_surface_reader_lite_v1", "status": "PASS", "files": []},
        match_surface_binding_id="surface_1",
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["hard_block_hits"] == ["input_root_missing"]
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["metric_truth"] is False
    assert result["production_release"] is False


def test_projection_keeps_xlsx_row_as_aggregate_entity_metric_surface(tmp_path):
    path = tmp_path / "players.xlsx"
    _write_book(path)
    import hashlib
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    inventory = {
        "files": [
            {
                "file_id": "file_1",
                "relative_path": path.name,
                "sha256": sha,
                "source_role": "XLSX_AGGREGATE_SURFACE",
            }
        ]
    }
    result = build_projection(
        tmp_path,
        inventory,
        _audit("file_1", path.name, sha),
        match_surface_binding_id="surface_1",
    )
    assert result["status"] == "PASS"
    assert result["row_projection_count"] == 1
    row = result["files"][0]["sheets"][0]["rows"][0]
    assert row["identity_candidates"]["player_raw_candidate"] == "A Player"
    assert row["identity_candidates"]["team_raw_candidate"] == "Team A"
    assert row["identity_candidates"]["minutes_raw_candidate"] == 90
    assert row["metric_values"]["shots"]["raw_value"] == 3
    assert row["match_surface_binding_id"] == "surface_1"
    assert row["row_projection_is_canonical_event"] is False
    assert row["validated_identity"] is False
    assert row["metric_values"]["shots"]["metric_truth"] is False
    assert row["claim_ceiling"] == "XLSX_ROW_ALIGNED_ENTITY_METRIC_SURFACE_ONLY"


def test_inventory_audit_binding_mismatch_fails_closed(tmp_path):
    path = tmp_path / "players.xlsx"
    _write_book(path)
    import hashlib
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    inventory = {
        "files": [
            {
                "file_id": "file_1",
                "relative_path": path.name,
                "sha256": sha,
                "source_role": "XLSX_AGGREGATE_SURFACE",
            }
        ]
    }
    bad = _audit("file_1", "different.xlsx", sha)
    result = build_projection(tmp_path, inventory, bad)
    assert result["status"] == "FAIL_CLOSED"
    assert result["row_projection_count"] == 0
    assert any(hit.startswith("inventory_audit_binding_mismatch:file_1") for hit in result["hard_block_hits"])
