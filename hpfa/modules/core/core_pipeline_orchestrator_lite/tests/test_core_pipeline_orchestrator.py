from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "core_pipeline_orchestrator_lite" / "src"
sys.path.insert(0, str(SRC))

from core_pipeline_orchestrator import (  # noqa: E402
    OrchestrationContractError,
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
    }


def stage_output(artifact: dict, *, artifact_id: str, artifact_type: str) -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "status": "SMOKE_PASS",
        "decision": "READY_FOR_NEXT_STAGE",
        "claim_ceiling": f"{artifact_type}_only",
        "hard_block_hits": [],
        "review_hits": [],
        "upstream_artifact_id": artifact["artifact_id"],
        "canonical_event_count": "UNKNOWN",
    }


def test_two_stage_pipeline_completes_in_declared_order():
    stages = [
        StageSpec(
            "stage_a",
            "surface_candidate",
            "feature_candidate",
            lambda artifact: stage_output(
                artifact,
                artifact_id="feature_001",
                artifact_type="feature_candidate",
            ),
        ),
        StageSpec(
            "stage_b",
            "feature_candidate",
            "evidence_candidate",
            lambda artifact: stage_output(
                artifact,
                artifact_id="evidence_001",
                artifact_type="evidence_candidate",
            ),
        ),
    ]
    result = run_pipeline(run_id="run_001", initial_artifact=initial_artifact(), stages=stages)
    assert result["status"] == "SMOKE_PASS"
    assert result["completed_all_stages"] is True
    assert [row["stage_module_id"] for row in result["stage_ledger"]] == ["stage_a", "stage_b"]


def test_input_artifact_type_mismatch_fails_closed():
    stages = [
        StageSpec(
            "stage_a",
            "wrong_type",
            "feature_candidate",
            lambda artifact: stage_output(
                artifact,
                artifact_id="feature_001",
                artifact_type="feature_candidate",
            ),
        )
    ]
    result = run_pipeline(run_id="run_002", initial_artifact=initial_artifact(), stages=stages)
    assert result["status"] == "FAIL_CLOSED"
    assert result["stage_ledger"][0]["hard_block_hits"] == ["input_artifact_type_mismatch"]


def test_failed_upstream_artifact_never_reaches_runner():
    called = {"value": False}

    def runner(artifact: dict) -> dict:
        called["value"] = True
        return stage_output(artifact, artifact_id="feature_001", artifact_type="feature_candidate")

    artifact = initial_artifact()
    artifact["status"] = "FAIL_CLOSED"
    artifact["decision"] = "BLOCK_SURFACE"
    artifact["hard_block_hits"] = ["source_authority_failed"]
    stages = [StageSpec("stage_a", "surface_candidate", "feature_candidate", runner)]
    result = run_pipeline(run_id="run_003", initial_artifact=artifact, stages=stages)
    assert called["value"] is False
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_artifact_failed_closed" in result["stage_ledger"][0]["hard_block_hits"]


def test_review_state_halts_before_later_stage():
    called = {"later": False}

    def review_runner(artifact: dict) -> dict:
        output = stage_output(artifact, artifact_id="review_001", artifact_type="review_candidate")
        output["status"] = "REVIEW_REQUIRED"
        output["decision"] = "ROUTE_TO_REVIEW"
        output["review_hits"] = ["identity_ambiguity"]
        return output

    def later_runner(artifact: dict) -> dict:
        called["later"] = True
        return stage_output(artifact, artifact_id="later_001", artifact_type="later_candidate")

    stages = [
        StageSpec("review_stage", "surface_candidate", "review_candidate", review_runner),
        StageSpec("later_stage", "review_candidate", "later_candidate", later_runner),
    ]
    result = run_pipeline(run_id="run_004", initial_artifact=initial_artifact(), stages=stages)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["halt_reason"] == "review_required"
    assert called["later"] is False


def test_stage_exception_is_sanitized_and_fails_closed():
    def exploding_runner(_: dict) -> dict:
        raise RuntimeError("sensitive implementation detail")

    stages = [StageSpec("stage_a", "surface_candidate", "feature_candidate", exploding_runner)]
    result = run_pipeline(run_id="run_005", initial_artifact=initial_artifact(), stages=stages)
    record = result["stage_ledger"][0]
    assert result["status"] == "FAIL_CLOSED"
    assert record["error_code"] == "stage_runner_exception"
    assert "sensitive implementation detail" not in str(result)


def test_non_dict_stage_output_fails_closed():
    stages = [
        StageSpec(
            "stage_a",
            "surface_candidate",
            "feature_candidate",
            lambda _: [],  # type: ignore[arg-type]
        )
    ]
    result = run_pipeline(run_id="run_006", initial_artifact=initial_artifact(), stages=stages)
    assert result["status"] == "FAIL_CLOSED"
    assert "stage_output_must_be_dict" in result["stage_ledger"][0]["error_code"]


def test_stage_output_requires_contract_fields():
    stages = [
        StageSpec(
            "stage_a",
            "surface_candidate",
            "feature_candidate",
            lambda _: {"artifact_id": "broken", "artifact_type": "feature_candidate"},
        )
    ]
    result = run_pipeline(run_id="run_007", initial_artifact=initial_artifact(), stages=stages)
    assert result["status"] == "FAIL_CLOSED"
    assert "stage_output_fields_missing" in result["stage_ledger"][0]["error_code"]


def test_canonical_event_count_truth_is_rejected():
    def runner(artifact: dict) -> dict:
        output = stage_output(artifact, artifact_id="feature_001", artifact_type="feature_candidate")
        output["canonical_event_count"] = 100
        return output

    result = run_pipeline(
        run_id="run_008",
        initial_artifact=initial_artifact(),
        stages=[StageSpec("stage_a", "surface_candidate", "feature_candidate", runner)],
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "canonical_event_count_truth_not_allowed" in result["stage_ledger"][0]["error_code"]


def test_artifact_fingerprint_is_order_independent_for_dict_keys():
    assert artifact_fingerprint({"a": 1, "b": 2}) == artifact_fingerprint({"b": 2, "a": 1})


def test_run_is_deterministic_for_same_inputs():
    stages = [
        StageSpec(
            "stage_a",
            "surface_candidate",
            "feature_candidate",
            lambda artifact: stage_output(
                artifact,
                artifact_id="feature_001",
                artifact_type="feature_candidate",
            ),
        )
    ]
    first = run_pipeline(run_id="run_009", initial_artifact=initial_artifact(), stages=stages)
    second = run_pipeline(run_id="run_009", initial_artifact=initial_artifact(), stages=stages)
    assert first == second


def test_run_id_is_required():
    try:
        run_pipeline(run_id="", initial_artifact=initial_artifact(), stages=[])
    except OrchestrationContractError as exc:
        assert str(exc) == "run_id_required"
    else:
        raise AssertionError("run_id_required was not raised")


def test_non_serializable_stage_output_fails_closed():
    def runner(artifact: dict) -> dict:
        output = stage_output(artifact, artifact_id="feature_001", artifact_type="feature_candidate")
        output["auxiliary"] = {"not", "json", "serializable"}
        return output

    result = run_pipeline(
        run_id="run_010",
        initial_artifact=initial_artifact(),
        stages=[StageSpec("stage_a", "surface_candidate", "feature_candidate", runner)],
    )
    record = result["stage_ledger"][0]
    assert result["status"] == "FAIL_CLOSED"
    assert record["error_code"] == "stage_output_not_json_serializable"
    assert record["hard_block_hits"] == ["stage_output_not_json_serializable"]


def test_no_sample_match_identity_leak():
    source = (SRC / "core_pipeline_orchestrator.py").read_text(encoding="utf-8").lower()
    forbidden = ["france", "morocco", "galatasaray", "fenerbahce", "world cup"]
    assert not any(token in source for token in forbidden)
