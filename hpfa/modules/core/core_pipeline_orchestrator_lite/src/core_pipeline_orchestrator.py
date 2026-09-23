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
class ContextInputSpec:
    context_id: str
    artifact_type: str
    epistemic_type: str = ""
    required: bool = True
    accepted_owner_ids: tuple[str, ...] = ()
    accepted_claim_ceilings: tuple[str, ...] = ()


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    input_artifact_type: str
    output_artifact_type: str
    runner: StageRunner
    halt_on_review: bool = True
    owner_id: str = ""
    owner_version: str = ""
    input_epistemic_type: str = ""
    output_epistemic_type: str = ""
    accepted_upstream_owner_ids: tuple[str, ...] = ()
    accepted_input_claim_ceilings: tuple[str, ...] = ()
    emitted_claim_ceiling: str = ""
    context_inputs: tuple[ContextInputSpec, ...] = ()


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


def _typed_stage(stage: StageSpec) -> bool:
    return any(
        (
            stage.owner_id,
            stage.owner_version,
            stage.input_epistemic_type,
            stage.output_epistemic_type,
            stage.accepted_upstream_owner_ids,
            stage.accepted_input_claim_ceilings,
            stage.emitted_claim_ceiling,
            stage.context_inputs,
        )
    )


def _validate_stage_spec(stage: StageSpec) -> None:
    if not stage.stage_id.strip():
        raise OrchestrationContractError("stage_id_required")
    if not stage.input_artifact_type.strip():
        raise OrchestrationContractError(f"{stage.stage_id}:input_artifact_type_required")
    if not stage.output_artifact_type.strip():
        raise OrchestrationContractError(f"{stage.stage_id}:output_artifact_type_required")
    if not callable(stage.runner):
        raise OrchestrationContractError(f"{stage.stage_id}:runner_must_be_callable")
    if _typed_stage(stage):
        if not stage.owner_id.strip():
            raise OrchestrationContractError(f"{stage.stage_id}:owner_id_required")
        if not stage.owner_version.strip():
            raise OrchestrationContractError(f"{stage.stage_id}:owner_version_required")
        if not stage.input_epistemic_type.strip():
            raise OrchestrationContractError(f"{stage.stage_id}:input_epistemic_type_required")
        if not stage.output_epistemic_type.strip():
            raise OrchestrationContractError(f"{stage.stage_id}:output_epistemic_type_required")
        if not stage.emitted_claim_ceiling.strip():
            raise OrchestrationContractError(f"{stage.stage_id}:emitted_claim_ceiling_required")
        seen_context_ids: set[str] = set()
        for context in stage.context_inputs:
            if not context.context_id.strip():
                raise OrchestrationContractError(f"{stage.stage_id}:context_id_required")
            if context.context_id in seen_context_ids:
                raise OrchestrationContractError(f"{stage.stage_id}:duplicate_context_id:{context.context_id}")
            seen_context_ids.add(context.context_id)
            if not context.artifact_type.strip():
                raise OrchestrationContractError(
                    f"{stage.stage_id}:context_artifact_type_required:{context.context_id}"
                )


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
    if _typed_stage(stage):
        if output.get("owner_id") != stage.owner_id:
            raise OrchestrationContractError(f"{stage.stage_id}:output_owner_id_mismatch")
        if output.get("epistemic_type") != stage.output_epistemic_type:
            raise OrchestrationContractError(f"{stage.stage_id}:output_epistemic_type_mismatch")
        if output.get("claim_ceiling") != stage.emitted_claim_ceiling:
            raise OrchestrationContractError(f"{stage.stage_id}:output_claim_ceiling_mismatch")
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
    context_artifacts: Mapping[str, dict[str, Any]] | None = None,
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
    contexts = {key: deepcopy(value) for key, value in (context_artifacts or {}).items()}
    ledger: list[dict[str, Any]] = []

    owner_versions: set[tuple[str, str]] = set()
    for stage in stages:
        _validate_stage_spec(stage)
        if _typed_stage(stage):
            owner_key = (stage.owner_id, stage.owner_version)
            if owner_key in owner_versions:
                raise OrchestrationContractError(
                    f"duplicate_owner_version:{stage.owner_id}:{stage.owner_version}"
                )
            owner_versions.add(owner_key)
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
        input_snapshot = deepcopy(current)
        input_fingerprint = artifact_fingerprint(input_snapshot)
        context_snapshot: dict[str, dict[str, Any]] = {}
        context_error = ""
        if _typed_stage(stage):
            if (
                stage.accepted_upstream_owner_ids
                and input_snapshot.get("owner_id") not in stage.accepted_upstream_owner_ids
            ):
                context_error = "upstream_owner_not_accepted"
            elif input_snapshot.get("epistemic_type") != stage.input_epistemic_type:
                context_error = "input_epistemic_type_mismatch"
            elif (
                stage.accepted_input_claim_ceilings
                and input_snapshot.get("claim_ceiling") not in stage.accepted_input_claim_ceilings
            ):
                context_error = "input_claim_ceiling_not_accepted"
            else:
                for context_spec in stage.context_inputs:
                    artifact = contexts.get(context_spec.context_id)
                    if artifact is None:
                        if context_spec.required:
                            context_error = f"required_context_input_missing:{context_spec.context_id}"
                            break
                        continue
                    if artifact.get("artifact_type") != context_spec.artifact_type:
                        context_error = f"context_artifact_type_mismatch:{context_spec.context_id}"
                        break
                    if (
                        context_spec.epistemic_type
                        and artifact.get("epistemic_type") != context_spec.epistemic_type
                    ):
                        context_error = f"context_epistemic_type_mismatch:{context_spec.context_id}"
                        break
                    if (
                        context_spec.accepted_owner_ids
                        and artifact.get("owner_id") not in context_spec.accepted_owner_ids
                    ):
                        context_error = f"context_owner_not_accepted:{context_spec.context_id}"
                        break
                    if (
                        context_spec.accepted_claim_ceilings
                        and artifact.get("claim_ceiling") not in context_spec.accepted_claim_ceilings
                    ):
                        context_error = f"context_claim_ceiling_not_accepted:{context_spec.context_id}"
                        break
                    context_snapshot[context_spec.context_id] = deepcopy(artifact)

        if context_error:
            output = _failure_artifact(
                run_id=run_id,
                stage=stage,
                input_artifact=input_snapshot,
                error_code=context_error,
            )
            error_code = context_error
            output_fingerprint = artifact_fingerprint(output)
        elif input_snapshot.get("artifact_type") != stage.input_artifact_type:
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
            "owner_id": stage.owner_id or None,
            "owner_version": stage.owner_version or None,
            "input_epistemic_type": stage.input_epistemic_type or input_snapshot.get("epistemic_type"),
            "context_input_artifact_ids": {
                key: value.get("artifact_id") for key, value in sorted(context_snapshot.items())
            },
            "context_input_fingerprints": {
                key: artifact_fingerprint(value) for key, value in sorted(context_snapshot.items())
            },
            "output_artifact_type": stage.output_artifact_type,
            "output_epistemic_type": stage.output_epistemic_type or output.get("epistemic_type"),
            "output_artifact_ids": [output.get("artifact_id")],
            "output_fingerprint": output_fingerprint,
            "status": output.get("status"),
            "decision": output.get("decision"),
            "input_claim_ceiling": input_snapshot.get("claim_ceiling"),
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
    has_review = artifact_requires_review(initial_artifact) or any(artifact_requires_review(record) for record in ledger)

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
            "typed_owner_validation_enabled": any(_typed_stage(stage) for stage in stages),
            "epistemic_type_validation_enabled": any(_typed_stage(stage) for stage in stages),
            "context_input_validation_enabled": any(stage.context_inputs for stage in stages),
            "claim_ceiling_contract_validation_enabled": any(_typed_stage(stage) for stage in stages),
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
