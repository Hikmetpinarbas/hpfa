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


def _row(progressive_value, shots_value, *, progressive_kind="number", shots_kind="number"):
    return {
        "row_projection_id": "xrp_support_contract",
        "source_sha256": "sha_support_contract",
        "identity_candidates": {"team_raw_candidate": "Team Generic"},
        "metric_values": {
            "progressive_passes": {
                "value_status": "OBSERVED",
                "value_kind": progressive_kind,
                "raw_metric_label": "Progressive passes",
                "raw_value": progressive_value,
            },
            "shots": {
                "value_status": "OBSERVED",
                "value_kind": shots_kind,
                "raw_metric_label": "Shots",
                "raw_value": shots_value,
            },
        },
    }


def test_positive_numeric_observation_is_the_only_admitted_metric_ref_shape():
    rows = [_row(4, 2)]
    progression = _metric_refs(rows, ("progressive",))
    terminal = _metric_refs(rows, ("shot",))
    assert len(progression) == 1
    assert len(terminal) == 1
    assert progression[0]["raw_value"] == 4
    assert progression[0]["positive_numeric_support_only"] is True
    assert progression[0]["metric_truth"] is False
    assert progression[0]["independent_support_vote"] is False


def test_zero_cells_do_not_become_production_support_or_create_c01_packet():
    rows = [_row(0, 0)]
    result = _construct_c01(rows, _features(shot_count=0))
    assert result["progression_aggregate_ref_count"] == 0
    assert result["terminal_aggregate_ref_count"] == 0
    assert result["packet_candidate"] is None
    assert result["review_reason"] == "positive_numeric_aggregate_progression_surface_not_observed"
    assert result["xlsx_zero_metric_value_is_production_support"] is False
    assert result["construct_truth"] is False


def test_nonnumeric_boolean_and_string_cells_cannot_create_support_refs():
    cases = [
        _row(True, 2, progressive_kind="boolean"),
        _row("4", 2, progressive_kind="string"),
        _row(4, "2", shots_kind="string"),
    ]
    first = _construct_c01([cases[0]], _features())
    second = _construct_c01([cases[1]], _features())
    third = _construct_c01([cases[2]], _features())
    assert first["progression_aggregate_ref_count"] == 0
    assert second["progression_aggregate_ref_count"] == 0
    assert third["terminal_aggregate_ref_count"] == 0
    assert first["packet_candidate"] is None
    assert second["packet_candidate"] is None
    assert third["packet_candidate"] is None


def test_nonfinite_raw_values_cannot_be_admitted_even_when_value_kind_says_number():
    for invalid in (float("nan"), float("inf"), float("-inf")):
        rows = [_row(invalid, 2)]
        refs = _metric_refs(rows, ("progressive",))
        assert refs == []


def test_positive_progression_plus_occurrence_terminal_surface_preserves_candidate_semantics():
    rows = [_row(4, 0)]
    result = _construct_c01(rows, _features(shot_count=1))
    assert result["progression_aggregate_ref_count"] == 1
    assert result["terminal_aggregate_ref_count"] == 0
    assert result["visible_shot_candidate_count"] == 1
    assert result["packet_candidate"] is not None
    assert result["xlsx_metric_support_requires_observed_positive_numeric_value"] is True
    assert result["aggregate_support_is_independent_vote"] is False
    assert result["construct_truth"] is False
