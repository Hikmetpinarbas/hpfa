from hpfa.modules.core.xlsx_entity_metric_row_projection_lite.src.xlsx_entity_metric_row_projection import (
    METRIC_ACTION_FAMILY_RELATION_STATE,
    _project_sheet,
)


class _Cell:
    def __init__(self, value):
        self.value = value
        self.data_type = "n" if isinstance(value, (int, float)) else "s"
        self.number_format = ""


class _Sheet:
    def __init__(self, rows):
        self._rows = rows
        self.max_row = len(rows)

    def cell(self, row, column):
        try:
            value = self._rows[row - 1][column - 1]
        except IndexError:
            value = None
        return _Cell(value)


def _sheets():
    rows = [
        ["Player", "Team", "Shots", "Progressive passes"],
        ["TRACE_A", "TEAM_A", 4, 12],
    ]
    return _Sheet(rows), _Sheet(rows)


def _audit(metric_keys=("shots", "progressive_passes")):
    return {
        "sheet_name": "Players",
        "sheet_state": "visible",
        "header_row_index": 1,
        "raw_columns": ["Player", "Team", "Shots", "Progressive passes"],
        "column_profiles": [
            {"raw_column": "Player", "normalized_column": "player", "identity_role_candidate": "player"},
            {"raw_column": "Team", "normalized_column": "team", "identity_role_candidate": "team"},
            {"raw_column": "Shots", "normalized_column": metric_keys[0], "identity_role_candidate": None},
            {"raw_column": "Progressive passes", "normalized_column": metric_keys[1], "identity_role_candidate": None},
        ],
    }


def _project(metric_keys=("shots", "progressive_passes")):
    formula_ws, value_ws = _sheets()
    return _project_sheet(
        formula_ws,
        value_ws,
        _audit(metric_keys),
        {
            "file_id": "file_a",
            "relative_path": "player.xlsx",
            "source_sha256": "a" * 64,
            "source_role": "PLAYER_XLSX",
        },
        "binding_a",
    )


def test_metric_labels_do_not_create_action_family_authority():
    result = _project()
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
    result = _project(("SHOT", "PASS"))
    row = result["rows"][0]
    assert row["metric_values"]["SHOT"]["action_family_candidates"] == []
    assert row["metric_values"]["PASS"]["action_family_candidates"] == []
    assert row["metric_values"]["SHOT"]["action_family_relation_state"] == METRIC_ACTION_FAMILY_RELATION_STATE
    assert row["metric_values"]["PASS"]["action_family_relation_state"] == METRIC_ACTION_FAMILY_RELATION_STATE
