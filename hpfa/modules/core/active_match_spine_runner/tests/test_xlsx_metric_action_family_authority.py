from openpyxl import Workbook

from hpfa.modules.core.xlsx_entity_metric_row_projection_lite.src.xlsx_entity_metric_row_projection import (
    METRIC_ACTION_FAMILY_RELATION_STATE,
    _project_sheet,
)


def _book():
    wb = Workbook()
    ws = wb.active
    ws.title = "Players"
    ws.append(["Player", "Team", "Shots", "Progressive passes"])
    ws.append(["TRACE_A", "TEAM_A", 4, 12])
    return wb, ws


def test_metric_labels_do_not_create_action_family_authority():
    formula_book, formula_ws = _book()
    value_book, value_ws = _book()
    try:
        result = _project_sheet(
            formula_ws,
            value_ws,
            {
                "sheet_name": "Players",
                "sheet_state": "visible",
                "header_row_index": 1,
                "raw_columns": ["Player", "Team", "Shots", "Progressive passes"],
                "column_profiles": [
                    {"raw_column": "Player", "normalized_column": "player", "identity_role_candidate": "player"},
                    {"raw_column": "Team", "normalized_column": "team", "identity_role_candidate": "team"},
                    {"raw_column": "Shots", "normalized_column": "shots", "identity_role_candidate": None},
                    {"raw_column": "Progressive passes", "normalized_column": "progressive_passes", "identity_role_candidate": None},
                ],
            },
            {
                "file_id": "file_a",
                "relative_path": "player.xlsx",
                "source_sha256": "a" * 64,
                "source_role": "PLAYER_XLSX",
            },
            "binding_a",
        )
    finally:
        formula_book.close()
        value_book.close()

    assert result["status"] == "PASS"
    row = result["rows"][0]
    for key in ("shots", "progressive_passes"):
        metric = row["metric_values"][key]
        assert metric["value_status"] == "OBSERVED"
        assert metric["action_family_relation_state"] == METRIC_ACTION_FAMILY_RELATION_STATE
        assert metric["action_family_candidates"] == []
        assert metric["action_family_relation_basis"] == []
        assert metric["action_family_relation_is_inferred_from_metric_label"] is False
        assert metric["action_family_relation_is_validated"] is False
        assert metric["metric_is_action_trace_support"] is False
        assert metric["metric_is_physical_action_truth"] is False


def test_raw_action_like_metric_name_cannot_upgrade_relation():
    formula_book, formula_ws = _book()
    value_book, value_ws = _book()
    try:
        result = _project_sheet(
            formula_ws,
            value_ws,
            {
                "sheet_name": "Players",
                "sheet_state": "visible",
                "header_row_index": 1,
                "raw_columns": ["Player", "Team", "Shots", "Progressive passes"],
                "column_profiles": [
                    {"raw_column": "Player", "normalized_column": "player", "identity_role_candidate": "player"},
                    {"raw_column": "Team", "normalized_column": "team", "identity_role_candidate": "team"},
                    {"raw_column": "Shots", "normalized_column": "SHOT", "identity_role_candidate": None},
                    {"raw_column": "Progressive passes", "normalized_column": "PASS", "identity_role_candidate": None},
                ],
            },
            {
                "file_id": "file_b",
                "relative_path": "player.xlsx",
                "source_sha256": "b" * 64,
                "source_role": "PLAYER_XLSX",
            },
            "binding_b",
        )
    finally:
        formula_book.close()
        value_book.close()

    row = result["rows"][0]
    assert row["metric_values"]["SHOT"]["action_family_candidates"] == []
    assert row["metric_values"]["PASS"]["action_family_candidates"] == []
    assert row["metric_values"]["SHOT"]["action_family_relation_state"] == METRIC_ACTION_FAMILY_RELATION_STATE
    assert row["metric_values"]["PASS"]["action_family_relation_state"] == METRIC_ACTION_FAMILY_RELATION_STATE
