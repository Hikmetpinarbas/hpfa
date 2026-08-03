from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from event_label_structural_progression_evidence import (  # noqa: E402
    _line_break_evidence,
    _persistence,
    _structural_progression,
)


def test_backward_or_reset_zone_change_is_not_called_lateral_relocation():
    classification, evidence = _structural_progression(
        "LABEL_SUPPORTED",
        "AXIS_ELIGIBLE_CANDIDATE",
        {
            "zone_delta_class": "RESET_OR_BACKWARD_ZONE_CHANGE_CANDIDATE",
            "consequence_class_candidate": "NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE",
        },
        "SUPPORTED_CANDIDATE",
        "SUPPORTED_CANDIDATE",
    )
    assert classification == "PROGRESSION_CONTEXT_UNRESOLVED"
    assert "RESET_OR_BACKWARD_ZONE_CHANGE_CANDIDATE" in evidence


def test_line_break_fully_supported_requires_all_disclosed_support_components():
    axis = {"coordinate_support": "SUPPORTED_CANDIDATE"}
    partial = {
        "outcome_support": "UNAVAILABLE",
        "consequence_support": "SUPPORTED_CANDIDATE",
        "aggregate_support": "SUPPORT_ONLY",
    }
    full = {
        "outcome_support": "SUPPORTED_CANDIDATE",
        "consequence_support": "SUPPORTED_CANDIDATE",
        "aggregate_support": "SUPPORT_ONLY",
    }

    partial_result = _line_break_evidence("EXACT_REVIEWED_RULE", axis, partial)
    full_result = _line_break_evidence("EXACT_REVIEWED_RULE", axis, full)

    assert partial_result["result_class"] == "LABEL_GEOMETRY_SUPPORTED"
    assert full_result["result_class"] == "LABEL_FULLY_SUPPORTED"
    assert full_result["line_break_truth"] is False


def test_deep_and_box_classes_require_visible_outcome_support():
    for zone_delta in (
        "THIRD_BREAK_CANDIDATE",
        "BOX_ACCESS_CANDIDATE",
        "CENTRAL_DEEP_BOX_ENTRY_CANDIDATE",
    ):
        unsupported, _ = _structural_progression(
            "LABEL_SUPPORTED",
            "AXIS_ELIGIBLE_CANDIDATE",
            {
                "zone_delta_class": zone_delta,
                "consequence_class_candidate": "CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE",
            },
            "SUPPORTED_CANDIDATE",
            "UNAVAILABLE",
        )
        supported, _ = _structural_progression(
            "LABEL_SUPPORTED",
            "AXIS_ELIGIBLE_CANDIDATE",
            {
                "zone_delta_class": zone_delta,
                "consequence_class_candidate": "CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE",
            },
            "SUPPORTED_CANDIDATE",
            "SUPPORTED_CANDIDATE",
        )
        assert unsupported == "TERRITORIAL_ADVANCEMENT_CANDIDATE"
        assert supported in {
            "DEEP_ADVANCEMENT_CANDIDATE",
            "BOX_PENETRATION_CANDIDATE",
        }


def test_box_reaching_retained_gain_is_terminal_progression_candidate():
    assert _persistence(
        {
            "zone_delta_class": "BOX_ACCESS_CANDIDATE",
            "false_progression_candidate": "VISIBLE_ZONE_GAIN_RETAINED_CANDIDATE",
        }
    ) == "TERMINAL_PROGRESSION_CANDIDATE"
    assert _persistence(
        {
            "zone_delta_class": "ZONE_GAIN_CANDIDATE",
            "false_progression_candidate": "VISIBLE_ZONE_GAIN_RETAINED_CANDIDATE",
        }
    ) == "VISIBLE_PROGRESSION_RETAINED_CANDIDATE"
