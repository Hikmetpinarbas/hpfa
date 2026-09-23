from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "core_pipeline_orchestrator_lite" / "src"
sys.path.insert(0, str(SRC))

from information_reservoir_runtime_projection import project_information_reservoir


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.json"
    write_json(
        path,
        {
            "manifest_id": "test_manifest",
            "artifacts": [
                {
                    "stage_id": "O03",
                    "owner_id": "episode_feature_vector_lite_v1",
                    "artifact_name": "episode_feature_vector_lite_v1.json",
                    "epistemic_type": "EPISODE_VISIBLE_FEATURE_CANDIDATE",
                    "claim_ceiling": "EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",
                    "allowed_downstream_stage_classes": ["O03", "P", "M"],
                }
            ],
        },
    )
    return path


def valid_feature(tmp_path: Path) -> Path:
    path = tmp_path / "episode_feature_vector_lite_v1.json"
    write_json(
        path,
        {
            "module_id": "episode_feature_vector_lite_v1",
            "status": "PASS",
            "claim_ceiling": "EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",
        },
    )
    return path


def test_projection_binds_current_artifact_without_creating_evidence(tmp_path: Path) -> None:
    artifact = valid_feature(tmp_path)
    result = project_information_reservoir(
        tmp_path,
        current_invocation_artifacts=[str(artifact)],
        manifest_path=manifest(tmp_path),
    )
    assert result["status"] == "PASS"
    assert result["current_invocation_binding_count"] == 1
    assert result["records"][0]["owner_match_state"] == "MATCH"
    assert result["records"][0]["claim_ceiling_match_state"] == "MATCH"
    assert result["pool_membership_creates_new_evidence"] is False


def test_current_strict_claim_ceiling_drift_fails_closed(tmp_path: Path) -> None:
    artifact = valid_feature(tmp_path)
    payload = json.loads(artifact.read_text())
    payload["claim_ceiling"] = "TOO_WIDE"
    write_json(artifact, payload)
    result = project_information_reservoir(
        tmp_path,
        current_invocation_artifacts=[str(artifact)],
        manifest_path=manifest(tmp_path),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["hard_block_hits"] == [
        "manifest_claim_ceiling_mismatch:episode_feature_vector_lite_v1.json"
    ]


def test_non_current_artifact_drift_does_not_become_runtime_failure(tmp_path: Path) -> None:
    artifact = valid_feature(tmp_path)
    payload = json.loads(artifact.read_text())
    payload["claim_ceiling"] = "TOO_WIDE"
    write_json(artifact, payload)
    result = project_information_reservoir(
        tmp_path,
        current_invocation_artifacts=[],
        manifest_path=manifest(tmp_path),
    )
    assert result["status"] == "PASS"
    assert result["records"][0]["claim_ceiling_match_state"] == "MISMATCH"


def test_missing_taxonomy_artifact_is_not_negative_evidence(tmp_path: Path) -> None:
    result = project_information_reservoir(
        tmp_path,
        current_invocation_artifacts=[],
        manifest_path=manifest(tmp_path),
    )
    assert result["status"] == "PASS"
    assert result["present_artifact_count"] == 0
    assert result["records"][0]["present_in_output_root"] is False
