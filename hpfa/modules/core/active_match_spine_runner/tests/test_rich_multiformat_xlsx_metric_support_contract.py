from pathlib import Path
import math
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rich_multiformat_analysis_lane import _construct_c01, _metric_refs


def _features(shot_count=0):
    return {
        "episode_feature_vectors": [
            {
                "shot_candidate_count": shot_count,
                "turnover_candidate_count": 0,
                "recovery_candidate_count": 0,
                "eligible_action_zone_counts": {},
                "action_family_counts": {},
            }
        ]
    }


def _row(progressive_value, shots_value, *, progressive_kind="number", shots_kind="number", progressive_label="Progressive passes", shots_label="Shots"):
    return {
        "row_projection_id": "xrp_support_contract",
        "source_sha256": "sha_support_contract",
        "identity_candidates": {"team_raw_candidate": "Team Generic"},
        "metric_values": {
            "progressive_passes": {
                "value_status": "OBSERVED",
                "value_kind": progressive_kind,
                "raw_metric_label": progressive_label,
                "raw_value": progressive_value,
                "metric_truth": False,
                "action_family_relation_state": "UNRESOLVED_NO_ADMITTED_SEMANTIC_AUTHORITY",
                "action_family_relation_is_inferred_from_metric_label": False,
                "action_family_relation_is_validated": False,
            },
            "shots": {
                "value_status": "OBSERVED",
                "value_kind": shots_kind,
                "raw_metric_label": shots_label,
                "raw_value": shots_value,
                "metric_truth": False,
                "action_family_relation_state": "UNRESOLVED_NO_ADMITTED_SEMANTIC_AUTHORITY",
                "action_family_relation_is_inferred_from_metric_label": False,
                "action_family_relation_is_validated": False,
            },
        },
    }


def test_positive_numeric_label_match_is_navigation_only_not_construct_support():
    rows = [_row(4, 2)]
    progression = _metric_refs(rows, ("progressive",))
    terminal = _metric_refs(rows, ("shot",))
    assert len(progression) == 1
    assert len(terminal) == 1
    assert progression[0]["raw_value"] == 4
    assert progression[0]["positive_numeric_observation"] is True
    assert progression[0]["label_navigation_only"] is True
    assert progression[0]["construct_support_allowed"] is False
    assert progression[0]["metric_label_match_is_construct_semantic_authority"] is False
    assert progression[0]["metric_truth"] is False
    assert progression[0]["independent_support_vote"] is False


def test_zero_cells_do_not_become_navigation_or_create_c01_packet():
    rows = [_row(0, 0)]
    result = _construct_c01(rows, _features(shot_count=0))
    assert result["progression_aggregate_ref_count"] == 0
    assert result["terminal_aggregate_ref_count"] == 0
    assert result["progression_label_navigation_ref_count"] == 0
    assert result["terminal_label_navigation_ref_count"] == 0
    assert result["packet_candidate"] is None
    assert result["xlsx_zero_metric_value_is_production_support"] is False
    assert result["construct_truth"] is False


def test_nonnumeric_boolean_and_string_cells_cannot_create_navigation_or_support_refs():
    cases = [
        _row(True, 2, progressive_kind="boolean"),
        _row("4", 2, progressive_kind="string"),
        _row(4, "2", shots_kind="string"),
    ]
    first = _construct_c01([cases[0]], _features())
    second = _construct_c01([cases[1]], _features())
    third = _construct_c01([cases[2]], _features())
    assert first["progression_label_navigation_ref_count"] == 0
    assert second["progression_label_navigation_ref_count"] == 0
    assert third["terminal_label_navigation_ref_count"] == 0
    assert first["packet_candidate"] is None
    assert second["packet_candidate"] is None
    assert third["packet_candidate"] is None


def test_nonfinite_raw_values_cannot_be_admitted_even_as_navigation():
    for invalid in (float("nan"), float("inf"), float("-inf")):
        rows = [_row(invalid, 2)]
        refs = _metric_refs(rows, ("progressive",))
        assert refs == []


def test_label_only_progression_plus_occurrence_terminal_never_creates_c01_packet():
    rows = [_row(4, 0)]
    result = _construct_c01(rows, _features(shot_count=1))
    assert result["progression_label_navigation_ref_count"] == 1
    assert result["progression_aggregate_ref_count"] == 0
    assert result["terminal_aggregate_ref_count"] == 0
    assert result["visible_shot_candidate_count"] == 1
    assert result["packet_candidate"] is None
    assert result["construct_semantic_authority_admitted"] is False
    assert result["xlsx_metric_label_match_is_construct_semantic_authority"] is False
    assert result["xlsx_label_navigation_is_construct_support"] is False
    assert result["aggregate_support_is_independent_vote"] is False
    assert result["construct_truth"] is False


def test_substring_traps_are_navigation_only_and_cannot_launder_semantics():
    rows = [{
        "row_projection_id": "xrp_substring_trap",
        "source_sha256": "sha_substring_trap",
        "identity_candidates": {"team_raw_candidate": "Team Generic"},
        "metric_values": {
            "goalkeeper_actions": {
                "value_status": "OBSERVED",
                "value_kind": "number",
                "raw_metric_label": "Goalkeeper actions",
                "raw_value": 8,
                "metric_truth": False,
                "action_family_relation_state": "UNRESOLVED_NO_ADMITTED_SEMANTIC_AUTHORITY",
                "action_family_relation_is_inferred_from_metric_label": False,
                "action_family_relation_is_validated": False,
            },
            "box_touches": {
                "value_status": "OBSERVED",
                "value_kind": "number",
                "raw_metric_label": "Box touches",
                "raw_value": 10,
                "metric_truth": False,
                "action_family_relation_state": "UNRESOLVED_NO_ADMITTED_SEMANTIC_AUTHORITY",
                "action_family_relation_is_inferred_from_metric_label": False,
                "action_family_relation_is_validated": False,
            },
        },
    }]
    result = _construct_c01(rows, _features(shot_count=2))
    assert result["progression_label_navigation_ref_count"] == 1
    assert result["terminal_label_navigation_ref_count"] == 1
    assert result["progression_aggregate_ref_count"] == 0
    assert result["terminal_aggregate_ref_count"] == 0
    assert result["packet_candidate"] is None
    assert result["review_reason"] == "xlsx_metric_label_navigation_present_but_construct_semantic_authority_not_admitted"
