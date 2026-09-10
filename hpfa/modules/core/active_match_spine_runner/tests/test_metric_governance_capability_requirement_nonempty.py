from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.metric_governance_bridge import (
    _metric_capability_admission_rows,
)


def test_empty_required_capabilities_are_not_vacuously_eligible() -> None:
    rows = _metric_capability_admission_rows(
        [{"metric_id": "m_undeclared", "required_observation_capabilities": []}],
        {
            "runtime_capability_admission_evaluated": True,
            "admitted_observation_capabilities": [
                "ACTION_EVENT",
                "TEMPORAL",
                "ENTITY_ACTOR",
                "AGGREGATE_TABULAR",
            ],
        },
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["metric_id"] == "m_undeclared"
    assert row["required_observation_capabilities"] == []
    assert row["required_observation_capabilities_declared"] is False
    assert row["capability_eligibility_state"] == "NOT_ELIGIBLE_REQUIRED_CAPABILITIES_UNDECLARED"
    assert row["missing_required_observation_capabilities"] == []
    assert row["metric_value_output_allowed_by_capability_match"] is False
    assert row["construct_truth_granted_by_capability_match"] is False


def test_nonempty_required_capabilities_keep_existing_subset_semantics() -> None:
    rows = _metric_capability_admission_rows(
        [
            {"metric_id": "m_ready", "required_observation_capabilities": ["ACTION_EVENT", "TEMPORAL"]},
            {"metric_id": "m_missing", "required_observation_capabilities": ["ACTION_EVENT", "TRACKING_VIDEO"]},
        ],
        {
            "runtime_capability_admission_evaluated": True,
            "admitted_observation_capabilities": ["ACTION_EVENT", "TEMPORAL"],
        },
    )
    by_id = {row["metric_id"]: row for row in rows}

    assert by_id["m_ready"]["required_observation_capabilities_declared"] is True
    assert by_id["m_ready"]["capability_eligibility_state"] == "ELIGIBLE_REQUIRED_CAPABILITIES_PRESENT"
    assert by_id["m_missing"]["required_observation_capabilities_declared"] is True
    assert by_id["m_missing"]["capability_eligibility_state"] == "NOT_ELIGIBLE_MISSING_REQUIRED_CAPABILITIES"
    assert by_id["m_missing"]["missing_required_observation_capabilities"] == ["TRACKING_VIDEO"]
