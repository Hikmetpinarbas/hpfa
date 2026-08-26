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


def stage_output(
    artifact: dict,
    *,
    status: str,
    decision: str,
    artifact_id: str = "feature_001",
    artifact_type: str = "feature_candidate",
    hard_block_hits: list[str] | None = None,
) -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "status": status,
        "decision": decision,
        "claim_ceiling": "feature_candidate_only",
        "hard_block_hits": hard_block_hits or [],
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
    assert result["first_failed_node"] == "stage_a"
    assert result["first_failed_reason_code"] == "status:FAIL_CLOSED"


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
    assert result["first_failed_node"] == "stage_a"
    assert result["first_failed_reason_code"] == "decision:BLOCK_UNSAFE_OUTPUT"


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
    assert result["first_failed_node"] is None
    assert result["first_failed_reason_code"] is None


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


def test_first_failed_node_is_preserved_and_later_outputs_are_disclosed_as_blocked():
    second_stage_called = False

    def fail_stage(artifact: dict) -> dict:
        return stage_output(
            artifact,
            status="FAIL_CLOSED",
            decision="BLOCK_PIPELINE",
            hard_block_hits=["semantic_contract_failed"],
        )

    def should_not_run(artifact: dict) -> dict:
        nonlocal second_stage_called
        second_stage_called = True
        return stage_output(
            artifact,
            status="SMOKE_PASS",
            decision="READY_FOR_NEXT_STAGE",
            artifact_id="report_001",
            artifact_type="report_candidate",
        )

    result = run_pipeline(
        run_id="first_failure_disclosure",
        initial_artifact=initial_artifact(),
        stages=[
            StageSpec("semantic_gate", "surface_candidate", "feature_candidate", fail_stage),
            StageSpec("report_builder", "feature_candidate", "report_candidate", should_not_run),
        ],
    )

    assert second_stage_called is False
    assert result["first_failed_node"] == "semantic_gate"
    assert result["first_failed_reason_code"] == "semantic_contract_failed"
    assert result["first_failed_stage_index"] == 0
    assert result["first_failed_artifact_id"] == "feature_001"
    assert result["blocked_outputs"] == ["report_candidate"]
    assert result["upstream_status"] == "SMOKE_PASS"


def test_initial_upstream_failure_blocks_all_downstream_execution_and_preserves_root_cause():
    artifact = initial_artifact()
    artifact["status"] = "FAIL_CLOSED"
    artifact["decision"] = "BLOCK_INPUT"
    artifact["hard_block_hits"] = ["source_authority_failed"]
    downstream_called = False

    def should_not_run(stage_input: dict) -> dict:
        nonlocal downstream_called
        downstream_called = True
        return stage_output(
            stage_input,
            status="SMOKE_PASS",
            decision="READY_FOR_NEXT_STAGE",
        )

    result = run_pipeline(
        run_id="initial_failure_disclosure",
        initial_artifact=artifact,
        stages=[
            StageSpec(
                "semantic_gate",
                "surface_candidate",
                "feature_candidate",
                should_not_run,
            ),
            StageSpec(
                "report_builder",
                "feature_candidate",
                "report_candidate",
                should_not_run,
            ),
        ],
    )

    assert downstream_called is False
    assert result["status"] == "FAIL_CLOSED"
    assert result["decision"] == "PIPELINE_BLOCKED"
    assert result["pipeline_halted"] is True
    assert result["halt_reason"] == "blocking_initial_artifact"
    assert result["first_failed_node"] == "INITIAL_ARTIFACT"
    assert result["first_failed_reason_code"] == "source_authority_failed"
    assert result["first_failed_stage_index"] == -1
    assert result["first_failed_artifact_id"] == "surface_001"
    assert result["stage_count_executed"] == 0
    assert result["blocked_outputs"] == ["feature_candidate", "report_candidate"]


def test_blocking_initial_artifact_with_no_stages_stays_fail_closed():
    artifact = initial_artifact()
    artifact["status"] = "FAIL_CLOSED"
    artifact["decision"] = "BLOCK_INPUT"
    artifact["hard_block_hits"] = ["source_authority_failed"]

    result = run_pipeline(
        run_id="initial_failure_no_stages",
        initial_artifact=artifact,
        stages=[],
    )

    assert result["status"] == "FAIL_CLOSED"
    assert result["decision"] == "PIPELINE_BLOCKED"
    assert result["completed_all_stages"] is False
    assert result["first_failed_node"] == "INITIAL_ARTIFACT"
    assert result["first_failed_reason_code"] == "source_authority_failed"
    assert result["first_failed_stage_index"] == -1
    assert result["stage_count_executed"] == 0


def test_successful_pipeline_has_no_first_failure_or_blocked_outputs():
    result = run_pipeline(
        run_id="no_failure_disclosure",
        initial_artifact=initial_artifact(),
        stages=[
            StageSpec(
                "stage_a",
                "surface_candidate",
                "feature_candidate",
                lambda artifact: stage_output(
                    artifact,
                    status="SMOKE_PASS",
                    decision="READY_FOR_NEXT_STAGE",
                ),
            )
        ],
    )

    assert result["status"] == "SMOKE_PASS"
    assert result["first_failed_node"] is None
    assert result["first_failed_reason_code"] is None
    assert result["first_failed_artifact_id"] is None
    assert result["first_failed_stage_index"] is None
    assert result["blocked_outputs"] == []
