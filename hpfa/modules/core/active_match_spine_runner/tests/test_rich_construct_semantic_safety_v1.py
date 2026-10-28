from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.rich_construct_metric_governance_guard import (
    assess_rich_construct_candidate,
)


def _governance(*labels: str) -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "aggregate_definition_alignment": {
            "alignment_rows": [
                {
                    "aggregate_label": label,
                    "alignment_decision": "DEFINITION_ALIGNMENT_CANDIDATE",
                    "metric_definition_bound": True,
                    "aggregate_label_observed": True,
                    "rate_calculation_admitted": True,
                }
                for label in labels
            ]
        },
    }


def _metric(label: str) -> dict:
    return {
        "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
        "raw_metric_label": label,
    }


def test_progression_construct_rejects_goalkeeper_terminal_metric() -> None:
    candidate = {
        "packet_family": "progression",
        "input_metrics": [
            _metric("Progressive open passes"),
            _metric("Shots faced"),
        ],
    }
    result = assess_rich_construct_candidate(
        candidate,
        _governance("Progressive open passes", "Shots faced"),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["admitted"] is False
    assert result["reason"] == "construct_semantic_family_mismatch"
    assert result["semantic_safety_hits"] == [
        "defensive_or_goalkeeper_terminal_metric:Shots faced"
    ]
    assert result["construct_truth"] is False
    assert result["production_release"] is False


def test_progression_construct_can_pass_semantic_safety_with_offensive_metrics() -> None:
    candidate = {
        "packet_family": "progression",
        "input_metrics": [
            _metric("Progressive open passes"),
            _metric("Shots"),
        ],
    }
    result = assess_rich_construct_candidate(
        candidate,
        _governance("Progressive open passes", "Shots"),
    )
    assert result["status"] == "PASS"
    assert result["admitted"] is True
    assert result["semantic_safety_hits"] == []
    assert result["construct_truth"] is False


def test_non_progression_packet_is_not_subject_to_progression_semantic_guard() -> None:
    candidate = {
        "packet_family": "other",
        "input_metrics": [_metric("Shots faced")],
    }
    result = assess_rich_construct_candidate(
        candidate,
        _governance("Shots faced"),
    )
    assert result["status"] == "PASS"
    assert result["admitted"] is True
    assert result["semantic_safety_hits"] == []
