from __future__ import annotations

from pathlib import Path
import argparse
import json

try:
    from .core_pipeline_orchestrator import ContextInputSpec, StageSpec, artifact_fingerprint, run_pipeline
except ImportError:
    from core_pipeline_orchestrator import ContextInputSpec, StageSpec, artifact_fingerprint, run_pipeline


SEMANTICS_FILE = "context_action_semantics_rebind_lite_v1.json"
EPISODE_FILE = "analyst_episode_locator_lite_v1.json"
FEATURE_FILE = "episode_feature_vector_lite_v1.json"
TEMPORAL_FILE = "temporal_episode_signature_lite_v1.json"

SEMANTICS_OWNER = "context_action_semantics_rebind_lite_v1"
EPISODE_OWNER = "analyst_episode_locator_lite_v1"
FEATURE_OWNER = "episode_feature_vector_lite_v1"
TEMPORAL_OWNER = "temporal_episode_signature_lite_v1"


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact_not_object:{path.name}")
    return payload


def _status(payload: dict) -> str:
    value = str(payload.get("status") or "UNKNOWN").upper()
    return "SMOKE_PASS" if value == "PASS" else value


def _wrap(
    payload: dict,
    *,
    filename: str,
    artifact_type: str,
    owner_id: str,
    epistemic_type: str,
    expected_claim_ceiling: str,
) -> dict:
    if payload.get("module_id") != owner_id:
        raise ValueError(f"owner_module_id_mismatch:{filename}")
    if payload.get("claim_ceiling") != expected_claim_ceiling:
        raise ValueError(f"claim_ceiling_mismatch:{filename}")
    return {
        "artifact_id": f"{filename}:{artifact_fingerprint(payload)}",
        "artifact_type": artifact_type,
        "owner_id": owner_id,
        "epistemic_type": epistemic_type,
        "claim_ceiling": expected_claim_ceiling,
        "status": _status(payload),
        "decision": payload.get("decision") or "UPSTREAM_ARTIFACT_PRESENT",
        "hard_block_hits": list(payload.get("hard_block_hits") or []),
        "review_hits": list(payload.get("review_hits") or []),
        "canonical_event_count": payload.get("canonical_event_count", "UNKNOWN"),
        "source_payload_fingerprint": artifact_fingerprint(payload),
        "source_filename": filename,
    }


def validate_episode_feature_temporal_chain(output_dir: str | Path, *, run_id: str) -> dict:
    root = Path(output_dir)
    semantics_payload = _load(root / SEMANTICS_FILE)
    episode_payload = _load(root / EPISODE_FILE)
    feature_payload = _load(root / FEATURE_FILE)
    temporal_payload = _load(root / TEMPORAL_FILE)

    semantics = _wrap(
        semantics_payload,
        filename=SEMANTICS_FILE,
        artifact_type="context_action_semantics_artifact",
        owner_id=SEMANTICS_OWNER,
        epistemic_type="REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE",
        expected_claim_ceiling="REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE_ONLY",
    )
    episode = _wrap(
        episode_payload,
        filename=EPISODE_FILE,
        artifact_type="analyst_episode_locator_artifact",
        owner_id=EPISODE_OWNER,
        epistemic_type="ANALYST_EPISODE_NAVIGATION_CANDIDATE",
        expected_claim_ceiling="ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY",
    )
    feature = _wrap(
        feature_payload,
        filename=FEATURE_FILE,
        artifact_type="episode_feature_vector_artifact",
        owner_id=FEATURE_OWNER,
        epistemic_type="EPISODE_VISIBLE_FEATURE_CANDIDATE",
        expected_claim_ceiling="EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",
    )
    temporal = _wrap(
        temporal_payload,
        filename=TEMPORAL_FILE,
        artifact_type="temporal_episode_signature_artifact",
        owner_id=TEMPORAL_OWNER,
        epistemic_type="TEMPORAL_EPISODE_CHANGE_CANDIDATE",
        expected_claim_ceiling="TEMPORAL_EPISODE_CHANGE_CANDIDATES_ONLY",
    )

    feature_stage = StageSpec(
        stage_id="episode_to_feature",
        input_artifact_type="analyst_episode_locator_artifact",
        output_artifact_type="episode_feature_vector_artifact",
        runner=lambda _: dict(feature),
        halt_on_review=False,
        owner_id=FEATURE_OWNER,
        owner_version="v1",
        input_epistemic_type="ANALYST_EPISODE_NAVIGATION_CANDIDATE",
        output_epistemic_type="EPISODE_VISIBLE_FEATURE_CANDIDATE",
        accepted_upstream_owner_ids=(EPISODE_OWNER,),
        accepted_input_claim_ceilings=("ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY",),
        emitted_claim_ceiling="EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",
        context_inputs=(
            ContextInputSpec(
                context_id="semantics",
                artifact_type="context_action_semantics_artifact",
                epistemic_type="REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE",
                accepted_owner_ids=(SEMANTICS_OWNER,),
                accepted_claim_ceilings=("REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE_ONLY",),
            ),
        ),
    )
    temporal_stage = StageSpec(
        stage_id="feature_to_temporal",
        input_artifact_type="episode_feature_vector_artifact",
        output_artifact_type="temporal_episode_signature_artifact",
        runner=lambda _: dict(temporal),
        halt_on_review=False,
        owner_id=TEMPORAL_OWNER,
        owner_version="v1",
        input_epistemic_type="EPISODE_VISIBLE_FEATURE_CANDIDATE",
        output_epistemic_type="TEMPORAL_EPISODE_CHANGE_CANDIDATE",
        accepted_upstream_owner_ids=(FEATURE_OWNER,),
        accepted_input_claim_ceilings=("EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",),
        emitted_claim_ceiling="TEMPORAL_EPISODE_CHANGE_CANDIDATES_ONLY",
    )

    result = run_pipeline(
        run_id=run_id,
        initial_artifact=episode,
        stages=[feature_stage, temporal_stage],
        context_artifacts={"semantics": semantics},
    )
    result["adapter_id"] = "episode_feature_temporal_typed_adapter_v1"
    result["source_files"] = [SEMANTICS_FILE, EPISODE_FILE, FEATURE_FILE, TEMPORAL_FILE]
    result["football_claim_produced"] = False
    result["production_release"] = False
    return result


def write_episode_feature_temporal_typed_ledger(
    output_dir: str | Path,
    *,
    run_id: str,
    filename: str = "episode_feature_temporal_typed_orchestration_v1.json",
) -> dict:
    root = Path(output_dir)
    result = validate_episode_feature_temporal_chain(root, run_id=run_id)
    (root / filename).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = write_episode_feature_temporal_typed_ledger(args.output_dir, run_id=args.run_id)
    print(json.dumps({"status": result["status"], "decision": result["decision"]}, sort_keys=True))
    return 0 if result["status"] != "FAIL_CLOSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
