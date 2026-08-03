from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from event_label_structural_progression_evidence import (  # noqa: E402
    _line_break_evidence,
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
