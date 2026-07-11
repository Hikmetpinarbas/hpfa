from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "core_pipeline_orchestrator_lite" / "src"
sys.path.insert(0, str(SRC))

from core_pipeline_orchestrator import (  # noqa: E402
    StageSpec,
    artifact_fingerprint,
    run_pipeline,
)


def initial_artifact() -> dict:
    return {
        "artifact_id": "surface_001",
        "artifact_type": "surface_candidate",
        "status": "SMOKE_PASS",
        "decision": "READY_FOR_NEXT_STAGE",
        "claim_ceiling": "surface_candidate_only",
        "hard_block_hits": [],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "nested": {"values": [1, 2]},
    }


def stage_output(artifact: dict, *, status: str, decision: str) -> dict:
    return {
        "artifact_id": "feature_001",
        "artifact_type": "feature_candidate",
        "status": status,
        "decision": decision,
        "claim_ceiling": "feature_candidate_only",
        "hard_block_hits": [],
        "review_hits": [],
        "upstream_artifact_id": artifact["artifact_id"],
        "canonical_event_count": "UNKNOWN",
    }


def test_status_only_fail_closed_rolls_up_as_pipeline_block():
    result = run_pipeline(
        run_id="regression_fail_status",
        initial_artifact=initial_artifact(),
        stages=[
            StageSpec(
                "stage_a",
                "surface_candidate",
                "feature_candidate",
                lambda artifact: stage_output(
                    artifact,
                    status="FAIL_CLOSED",
                    decision="NO_HARD_BLOCK_HIT_PRESENT",
                ),
            )
        ],
    )

    assert result["status"] == "FAIL_CLOSED"
    assert result["decision"] == "PIPELINE_BLOCKED"
    assert result["halt_reason"] == "blocking_stage_output"


def test_decision_only_block_rolls_up_as_pipeline_block():
    result = run_pipeline(
        run_id="regression_block_decision",
        initial_artifact=initial_artifact(),
        stages=[
            StageSpec(
                "stage_a",
                "surface_candidate",
                "feature_candidate",
                lambda artifact: stage_output(
                    artifact,
                    status="SMOKE_PASS",
                    decision="BLOCK_UNSAFE_OUTPUT",
                ),
            )
        ],
    )

    assert result["status"] == "FAIL_CLOSED"
    assert result["decision"] == "PIPELINE_BLOCKED"


def test_non_halting_review_status_cannot_roll_up_as_smoke_pass():
    result = run_pipeline(
        run_id="regression_review_status",
        initial_artifact=initial_artifact(),
        stages=[
            StageSpec(
                "stage_a",
                "surface_candidate",
                "feature_candidate",
                lambda artifact: stage_output(
                    artifact,
                    status="REVIEW_REQUIRED",
                    decision="READY_FOR_OPTIONAL_REVIEW",
                ),
                halt_on_review=False,
            )
        ],
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["decision"] == "PIPELINE_HALTED_FOR_REVIEW"
    assert result["pipeline_halted"] is False
    assert result["completed_all_stages"] is True


def test_nested_runner_mutation_does_not_change_recorded_input_fingerprint():
    artifact = initial_artifact()
    expected_fingerprint = artifact_fingerprint(artifact)

    def mutating_runner(stage_input: dict) -> dict:
        stage_input["nested"]["values"].append(99)
        return stage_output(
            stage_input,
            status="SMOKE_PASS",
            decision="READY_FOR_NEXT_STAGE",
        )

    result = run_pipeline(
        run_id="regression_nested_mutation",
        initial_artifact=artifact,
        stages=[
            StageSpec(
                "stage_a",
                "surface_candidate",
                "feature_candidate",
                mutating_runner,
            )
        ],
    )

    assert result["stage_ledger"][0]["input_fingerprint"] == expected_fingerprint
    assert artifact["nested"]["values"] == [1, 2]
