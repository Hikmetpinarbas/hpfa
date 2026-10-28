from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "core_pipeline_orchestrator_lite" / "src"
sys.path.insert(0, str(SRC))

from core_pipeline_orchestrator import ContextInputSpec, OrchestrationContractError, StageSpec, run_pipeline


def primary() -> dict:
    return {
        "artifact_id": "episode_001",
        "artifact_type": "episode_candidate",
        "owner_id": "analyst_episode_locator_lite_v1",
        "epistemic_type": "ANALYST_EPISODE_NAVIGATION_CANDIDATE",
        "claim_ceiling": "ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY",
        "status": "SMOKE_PASS",
        "decision": "READY",
        "hard_block_hits": [],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
    }


def semantics() -> dict:
    return {
        "artifact_id": "semantics_001",
        "artifact_type": "semantic_context",
        "owner_id": "context_action_semantics_rebind_lite_v1",
        "epistemic_type": "REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE",
        "claim_ceiling": "REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE_ONLY",
        "status": "SMOKE_PASS",
        "decision": "READY",
        "hard_block_hits": [],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
    }


def typed_stage() -> StageSpec:
    def runner(artifact: dict) -> dict:
        return {
            "artifact_id": "feature_001",
            "artifact_type": "feature_candidate",
            "owner_id": "episode_feature_vector_lite_v1",
            "epistemic_type": "EPISODE_VISIBLE_FEATURE_CANDIDATE",
            "claim_ceiling": "EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",
            "status": "SMOKE_PASS",
            "decision": "READY",
            "hard_block_hits": [],
            "review_hits": [],
            "upstream_artifact_id": artifact["artifact_id"],
            "canonical_event_count": "UNKNOWN",
        }

    return StageSpec(
        stage_id="feature",
        input_artifact_type="episode_candidate",
        output_artifact_type="feature_candidate",
        runner=runner,
        owner_id="episode_feature_vector_lite_v1",
        owner_version="v1",
        input_epistemic_type="ANALYST_EPISODE_NAVIGATION_CANDIDATE",
        output_epistemic_type="EPISODE_VISIBLE_FEATURE_CANDIDATE",
        accepted_upstream_owner_ids=("analyst_episode_locator_lite_v1",),
        accepted_input_claim_ceilings=("ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY",),
        emitted_claim_ceiling="EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",
        context_inputs=(
            ContextInputSpec(
                context_id="semantics",
                artifact_type="semantic_context",
                epistemic_type="REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE",
                accepted_owner_ids=("context_action_semantics_rebind_lite_v1",),
                accepted_claim_ceilings=("REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE_ONLY",),
            ),
        ),
    )


def test_typed_stage_accepts_primary_context_and_claim_contract() -> None:
    result = run_pipeline(
        run_id="typed_ok",
        initial_artifact=primary(),
        stages=[typed_stage()],
        context_artifacts={"semantics": semantics()},
    )
    assert result["status"] == "SMOKE_PASS"
    row = result["stage_ledger"][0]
    assert row["owner_id"] == "episode_feature_vector_lite_v1"
    assert row["context_input_artifact_ids"] == {"semantics": "semantics_001"}


def test_wrong_primary_epistemic_type_fails_closed() -> None:
    artifact = primary()
    artifact["epistemic_type"] = "WRONG"
    result = run_pipeline(
        run_id="typed_bad_primary",
        initial_artifact=artifact,
        stages=[typed_stage()],
        context_artifacts={"semantics": semantics()},
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["stage_ledger"][0]["error_code"] == "input_epistemic_type_mismatch"


def test_missing_required_context_fails_closed() -> None:
    result = run_pipeline(run_id="typed_missing_context", initial_artifact=primary(), stages=[typed_stage()])
    assert result["status"] == "FAIL_CLOSED"
    assert result["stage_ledger"][0]["error_code"] == "required_context_input_missing:semantics"


def test_wrong_context_owner_fails_closed() -> None:
    context = semantics()
    context["owner_id"] = "wrong_owner"
    result = run_pipeline(
        run_id="typed_bad_context_owner",
        initial_artifact=primary(),
        stages=[typed_stage()],
        context_artifacts={"semantics": context},
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["stage_ledger"][0]["error_code"] == "context_owner_not_accepted:semantics"


def test_wrong_input_claim_ceiling_fails_closed() -> None:
    artifact = primary()
    artifact["claim_ceiling"] = "TOO_WIDE"
    result = run_pipeline(
        run_id="typed_bad_claim",
        initial_artifact=artifact,
        stages=[typed_stage()],
        context_artifacts={"semantics": semantics()},
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["stage_ledger"][0]["error_code"] == "input_claim_ceiling_not_accepted"


def test_output_claim_ceiling_mismatch_fails_closed() -> None:
    stage = typed_stage()

    def runner(artifact: dict) -> dict:
        output = stage.runner(artifact)
        output["claim_ceiling"] = "TOO_WIDE"
        return output

    bad_stage = StageSpec(**{**stage.__dict__, "runner": runner})
    result = run_pipeline(
        run_id="typed_bad_output_claim",
        initial_artifact=primary(),
        stages=[bad_stage],
        context_artifacts={"semantics": semantics()},
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "output_claim_ceiling_mismatch" in result["stage_ledger"][0]["error_code"]


def test_duplicate_owner_version_is_rejected_before_execution() -> None:
    stage = typed_stage()
    try:
        run_pipeline(
            run_id="typed_duplicate_owner",
            initial_artifact=primary(),
            stages=[stage, stage],
            context_artifacts={"semantics": semantics()},
        )
    except OrchestrationContractError as exc:
        assert str(exc) == "duplicate_owner_version:episode_feature_vector_lite_v1:v1"
    else:
        raise AssertionError("duplicate owner/version was not rejected")
