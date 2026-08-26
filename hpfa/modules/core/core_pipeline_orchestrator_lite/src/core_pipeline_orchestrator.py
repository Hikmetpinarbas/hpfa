from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence


MODULE_ID = "core_pipeline_orchestrator_lite_v1"
CANDIDATE_ONLY = "pipeline_orchestration_candidate_only"
BLOCKING_STATUSES = {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED", "ERROR"}
REVIEW_STATUSES = {"REVIEW_REQUIRED", "WAITING_OPERATOR_SELECTION"}


class OrchestrationContractError(ValueError):
    """Raised when a stage or artifact violates the orchestration contract."""


StageRunner = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    input_artifact_type: str
    output_artifact_type: str
    runner: StageRunner
    halt_on_review: bool = True


REQUIRED_STAGE_OUTPUT_FIELDS = {
    "artifact_id",
    "artifact_type",
    "status",
    "decision",
    "claim_ceiling",
    "hard_block_hits",
    "review_hits",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def artifact_fingerprint(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _as_list(value: Any) -> list[Any]:
    if value in (None, "", False):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _meaningful_list(value: Any) -> list[Any]:
    return [item for item in _as_list(value) if item not in (None, "", False, [], {})]


def _normalized_status(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _normalized_decision(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def artifact_is_blocking(artifact: Mapping[str, Any]) -> bool:
    if _meaningful_list(artifact.get("hard_block_hits")):
        return True
    if _normalized_status(artifact.get("status")) in BLOCKING_STATUSES:
        return True
    return _normalized_decision(artifact.get("decision")).startswith("BLOCK")


def artifact_requires_review(artifact: Mapping[str, Any]) -> bool:
    if _meaningful_list(artifact.get("review_hits")):
        return True
    if _normalized_status(artifact.get("status")) in REVIEW_STATUSES:
        return True
    return "REVIEW" in _normalized_decision(artifact.get("decision"))


def _blocking_reason(artifact: Mapping[str, Any]) -> str:
    hard_blocks = _meaningful_list(artifact.get("hard_block_hits"))
    if hard_blocks:
        return str(hard_blocks[0])
    status = _normalized_status(artifact.get("status"))
    if status in BLOCKING_STATUSES:
        return f"status:{status}"
    decision = _normalized_decision(artifact.get("decision"))
    if decision.startswith("BLOCK"):
        return f"decision:{decision}"
    return ""


def _validate_stage_spec(stage: StageSpec) -> None:
    if not stage.stage_id.strip():
        raise OrchestrationContractError("stage_id_required")
    if not stage.input_artifact_type.strip():
        raise OrchestrationContractError(f"{stage.stage_id}:input_artifact_type_required")
    if not stage.output_artifact_type.strip():
        raise OrchestrationContractError(f"{stage.stage_id}:output_artifact_type_required")
    if not callable(stage.runner):
        raise OrchestrationContractError(f"{stage.stage_id}:runner_must_be_callable")


def _validate_stage_output(stage: StageSpec, output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        raise OrchestrationContractError(f"{stage.stage_id}:stage_output_must_be_dict")
    missing = sorted(REQUIRED_STAGE_OUTPUT_FIELDS.difference(output.keys()))
    if missing:
        raise OrchestrationContractError(
            f"{stage.stage_id}:stage_output_fields_missing:{','.join(missing)}"
        )
    if output.get("artifact_type") != stage.output_artifact_type:
        raise OrchestrationContractError(f"{stage.stage_id}:output_artifact_type_mismatch")
    if output.get("canonical_event_count") not in (None, "UNKNOWN"):
        raise OrchestrationContractError(
            f"{stage.stage_id}:canonical_event_count_truth_not_allowed"
        )
    return output


def _failure_artifact(
    *,
    run_id: str,
    stage: StageSpec,
    input_artifact: Mapping[str, Any],
    error_code: str,
) -> dict[str, Any]:
    return {
        "artifact_id": f"{run_id}:{stage.stage_id}:failure",
        "artifact_type": stage.output_artifact_type,
        "status": "FAIL_CLOSED",
        "decision": "BLOCK_PIPELINE",
        "claim_ceiling": CANDIDATE_ONLY,
        "hard_block_hits": [error_code],
        "review_hits": [],
        "upstream_artifact_id": input_artifact.get("artifact_id"),
        "canonical_event_count": "UNKNOWN",
    }


def run_pipeline(
    *,
    run_id: str,
    initial_artifact: dict[str, Any],
    stages: Sequence[StageSpec],
) -> dict[str, Any]:
    """Run an ordered, deterministic and fail-closed HPFA pipeline.

    The orchestrator does not calculate football metrics and does not rewrite
    producer outputs. It validates stage boundaries, propagates failure/review
    states and records a replayable stage ledger.
    """
    if not run_id.strip():
        raise OrchestrationContractError("run_id_required")
    if not isinstance(initial_artifact, dict):
        raise OrchestrationContractError("initial_artifact_must_be_dict")

    current = deepcopy(initial_artifact)
    ledger: list[dict[str, Any]] = []
    pipeline_halted = False
    halt_reason = ""
    first_failed_node: str | None = None
    first_failed_reason_code: str | None = None
    first_failed_artifact_id: str | None = None
    first_failed_stage_index: int | None = None
    initial_blocking = artifact_is_blocking(current)

    if initial_blocking:
        first_failed_node = "INITIAL_ARTIFACT"
        first_failed_reason_code = _blocking_reason(current) or "initial_artifact_failed_closed"
        first_failed_artifact_id = str(current.get("artifact_id") or "") or None
        first_failed_stage_index = -1

    for index, stage in enumerate(stages):
        _validate_stage_spec(stage)
        input_snapshot = deepcopy(current)
        input_fingerprint = artifact_fingerprint(input_snapshot)

        if input_snapshot.get("artifact_type") != stage.input_artifact_type:
            output = _failure_artifact(
                run_id=run_id,
                stage=stage,
                input_artifact=input_snapshot,
                error_code="input_artifact_type_mismatch",
            )
            error_code = "input_artifact_type_mismatch"
            output_fingerprint = artifact_fingerprint(output)
        elif artifact_is_blocking(input_snapshot):
            output = _failure_artifact(
                run_id=run_id,
                stage=stage,
                input_artifact=input_snapshot,
                error_code="upstream_artifact_failed_closed",
            )
            error_code = "upstream_artifact_failed_closed"
            output_fingerprint = artifact_fingerprint(output)
        else:
            try:
                output = _validate_stage_output(stage, stage.runner(deepcopy(input_snapshot)))
                output_fingerprint = artifact_fingerprint(output)
                error_code = ""
            except OrchestrationContractError as exc:
                output = _failure_artifact(
                    run_id=run_id,
                    stage=stage,
                    input_artifact=input_snapshot,
                    error_code=str(exc),
                )
                error_code = str(exc)
                output_fingerprint = artifact_fingerprint(output)
            except (TypeError, ValueError):
                output = _failure_artifact(
                    run_id=run_id,
                    stage=stage,
                    input_artifact=input_snapshot,
                    error_code="stage_output_not_json_serializable",
                )
                error_code = "stage_output_not_json_serializable"
                output_fingerprint = artifact_fingerprint(output)
            except Exception:
                output = _failure_artifact(
                    run_id=run_id,
                    stage=stage,
                    input_artifact=input_snapshot,
                    error_code="stage_runner_exception",
                )
                error_code = "stage_runner_exception"
                output_fingerprint = artifact_fingerprint(output)

        stage_record = {
            "run_id": run_id,
            "stage_index": index,
            "stage_module_id": stage.stage_id,
            "input_artifact_type": stage.input_artifact_type,
            "input_artifact_ids": [input_snapshot.get("artifact_id")],
            "input_fingerprint": input_fingerprint,
            "output_artifact_type": stage.output_artifact_type,
            "output_artifact_ids": [output.get("artifact_id")],
            "output_fingerprint": output_fingerprint,
            "status": output.get("status"),
            "decision": output.get("decision"),
            "claim_ceiling": output.get("claim_ceiling"),
            "hard_block_hits": _meaningful_list(output.get("hard_block_hits")),
            "review_hits": _meaningful_list(output.get("review_hits")),
            "error_code": error_code,
        }
        ledger.append(stage_record)
        current = output

        if artifact_is_blocking(output):
            if first_failed_node is None:
                first_failed_node = stage.stage_id
                first_failed_reason_code = error_code or _blocking_reason(output) or "blocking_stage_output"
                first_failed_artifact_id = str(output.get("artifact_id") or "") or None
                first_failed_stage_index = index
            pipeline_halted = True
            halt_reason = "blocking_stage_output"
            break
        if stage.halt_on_review and artifact_requires_review(output):
            pipeline_halted = True
            halt_reason = "review_required"
            break

    completed_all_stages = len(ledger) == len(stages) and not pipeline_halted and not initial_blocking
    has_block = initial_blocking or any(artifact_is_blocking(record) for record in ledger)
    has_review = any(artifact_requires_review(record) for record in ledger)

    if has_block:
        status = "FAIL_CLOSED"
        decision = "PIPELINE_BLOCKED"
    elif pipeline_halted or has_review:
        status = "REVIEW_REQUIRED"
        decision = "PIPELINE_HALTED_FOR_REVIEW"
    elif completed_all_stages:
        status = "SMOKE_PASS"
        decision = "PIPELINE_EXECUTION_COMPLETED"
    else:
        status = "REVIEW_REQUIRED"
        decision = "PIPELINE_INCOMPLETE"

    blocked_outputs = [stage.output_artifact_type for stage in stages[len(ledger):]] if pipeline_halted else []

    return {
        "module_id": MODULE_ID,
        "run_id": run_id,
        "status": status,
        "decision": decision,
        "claim_ceiling": CANDIDATE_ONLY,
        "completed_all_stages": completed_all_stages,
        "pipeline_halted": pipeline_halted,
        "halt_reason": halt_reason,
        "first_failed_node": first_failed_node,
        "first_failed_reason_code": first_failed_reason_code,
        "first_failed_artifact_id": first_failed_artifact_id,
        "first_failed_stage_index": first_failed_stage_index,
        "upstream_status": initial_artifact.get("status"),
        "blocked_outputs": blocked_outputs,
        "stage_count_declared": len(stages),
        "stage_count_executed": len(ledger),
        "stage_ledger": ledger,
        "final_artifact": current,
        "engineering_evidence": {
            "deterministic_stage_order": True,
            "input_output_fingerprints_recorded": True,
            "failure_propagation_enabled": True,
            "first_failure_disclosure_enabled": True,
            "review_halt_enabled": True,
        },
        "analyst_evidence": {
            "football_claim_produced": False,
            "analyst_output_produced": False,
            "message": "Orchestration evidence only; football interpretation requires producer outputs.",
        },
        "claim_boundary": {
            "canonical_event_count": "UNKNOWN",
            "phase_truth": False,
            "possession_truth": False,
            "sequence_truth": False,
            "rhythm_truth": False,
            "tactical_truth": False,
            "dominance_truth": False,
            "coach_intention_truth": False,
        },
        "release": {
            "active_match_evidence_pass": False,
            "production_release": False,
        },
    }
