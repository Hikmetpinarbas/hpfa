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


def nested_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "nested_manifest.json"
    write_json(
        path,
        {
            "manifest_id": "nested_test_manifest",
            "artifacts": [
                {
                    "stage_id": "M02",
                    "owner_id": "rich_multiformat_analysis_lattice_v1",
                    "artifact_name": "rich_multiformat_analysis_lattice_v1.json",
                    "object_path": "m02_progression_territory_synthesis",
                    "required_when_artifact_current": True,
                    "epistemic_type": "MATCH_LOCAL_VISIBLE_PROGRESSION_TERRITORY_SYNTHESIS_CANDIDATE",
                    "claim_ceiling": "MATCH_LOCAL_VISIBLE_PROGRESSION_TERRITORY_SYNTHESIS_CANDIDATE_ONLY",
                    "allowed_downstream_stage_classes": ["R", "F", "T"],
                }
            ],
        },
    )
    return path


def nested_rich_artifact(tmp_path: Path, *, include_m02: bool = True) -> Path:
    path = tmp_path / "rich_multiformat_analysis_lattice_v1.json"
    payload = {
        "module_id": "rich_multiformat_analysis_lattice_v1",
        "status": "REVIEW_REQUIRED",
        "production_release": False,
    }
    if include_m02:
        payload["m02_progression_territory_synthesis"] = {
            "synthesis_id": "M02_PROGRESSION_AND_TERRITORY",
            "status": "PASS",
            "claim_ceiling": "MATCH_LOCAL_VISIBLE_PROGRESSION_TERRITORY_SYNTHESIS_CANDIDATE_ONLY",
            "profiles": [],
        }
    write_json(path, payload)
    return path


def test_nested_m02_object_path_is_bound_and_fingerprinted(tmp_path: Path) -> None:
    artifact = nested_rich_artifact(tmp_path)
    result = project_information_reservoir(
        tmp_path,
        current_invocation_artifacts=[str(artifact)],
        manifest_path=nested_manifest(tmp_path),
    )
    assert result["status"] == "PASS"
    row = result["records"][0]
    assert row["binding_id"] == (
        "rich_multiformat_analysis_lattice_v1.json#m02_progression_territory_synthesis"
    )
    assert row["object_present"] is True
    assert row["object_fingerprint"]
    assert row["claim_ceiling_match_state"] == "MATCH"


def test_required_nested_m02_missing_in_current_artifact_fails_closed(tmp_path: Path) -> None:
    artifact = nested_rich_artifact(tmp_path, include_m02=False)
    result = project_information_reservoir(
        tmp_path,
        current_invocation_artifacts=[str(artifact)],
        manifest_path=nested_manifest(tmp_path),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["hard_block_hits"] == [
        "manifest_required_object_missing:rich_multiformat_analysis_lattice_v1.json:m02_progression_territory_synthesis"
    ]


def test_nested_m02_claim_ceiling_drift_fails_closed(tmp_path: Path) -> None:
    artifact = nested_rich_artifact(tmp_path)
    payload = json.loads(artifact.read_text())
    payload["m02_progression_territory_synthesis"]["claim_ceiling"] = "TOO_WIDE"
    write_json(artifact, payload)
    result = project_information_reservoir(
        tmp_path,
        current_invocation_artifacts=[str(artifact)],
        manifest_path=nested_manifest(tmp_path),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["hard_block_hits"] == [
        "manifest_claim_ceiling_mismatch:rich_multiformat_analysis_lattice_v1.json"
    ]
