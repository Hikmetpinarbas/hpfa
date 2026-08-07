from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
VERIFIER = REPO_ROOT / "tools" / "verify_coordinate_frame_active_match_bundle_v1.py"
HEAD = "a" * 40
AUTHORITY = "/runtime/active_single_match/current"
BRANCH = "agent/coordinate-frame-precondition-lite-v1"


def dumps(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


def build_bundle(
    path: Path,
    *,
    include_audits: bool = True,
    output_head: str = HEAD,
) -> None:
    members: dict[str, bytes] = {
        "coordinate_frame_precondition_lite_v1.json": dumps(
            {
                "runtime_code_head_sha": output_head,
                "runtime_authority": AUTHORITY,
                "active_match_execution_completed": True,
                "runtime_evidence_status": (
                    "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED"
                ),
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
            }
        ),
        "coordinate_frame_precondition_active_match_v1.txt": (
            b"status=REVIEW_REQUIRED\n"
        ),
        "coordinate_frame_precondition_operator_state_v1.txt": (
            f"status=COMPLETED\nruntime_authority={AUTHORITY}\nbranch={BRANCH}\n"
            f"runtime_code_head_sha={HEAD}\nexpected_head_sha={HEAD}\n"
            "canonical_event_count=UNKNOWN\nproduction_release=false\n"
        ).encode("utf-8"),
    }
    if include_audits:
        members["coordinate_frame_precondition_runtime_audit_v1.txt"] = (
            b"runtime_evidence_status="
            b"ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED\n"
        )
        members["coordinate_frame_precondition_dependency_audit_v1.json"] = dumps(
            {
                "source_role": "ACTIVE_MATCH_EXACT_RUN_AUDIT",
                "runtime_code_head_sha": HEAD,
                "runtime_authority": AUTHORITY,
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
            }
        )

    rows = [
        {
            "name": name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        }
        for name, data in members.items()
    ]
    manifest = {
        "branch": BRANCH,
        "runtime_code_head_sha": HEAD,
        "runtime_authority": AUTHORITY,
        "files": rows,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    members[
        "coordinate_frame_precondition_active_match_bundle_manifest_v1.json"
    ] = dumps(manifest)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def run_verifier(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--bundle",
            str(path),
            "--expected-head",
            HEAD,
            "--expected-authority",
            AUTHORITY,
            "--expected-branch",
            BRANCH,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_accepts_coherent_exact_head_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "ok.zip"
    build_bundle(bundle)
    completed = run_verifier(bundle)
    assert completed.returncode == 0
    assert "ACTIVE_MATCH_EVIDENCE_PACKAGE_VERIFIED" in completed.stdout


def test_rejects_missing_runtime_audit_artifacts(tmp_path: Path) -> None:
    bundle = tmp_path / "missing-audits.zip"
    build_bundle(bundle, include_audits=False)
    completed = run_verifier(bundle)
    assert completed.returncode == 1
    assert "required_bundle_member_missing" in completed.stdout


def test_rejects_output_head_mismatch(tmp_path: Path) -> None:
    bundle = tmp_path / "wrong-head.zip"
    build_bundle(bundle, output_head="b" * 40)
    completed = run_verifier(bundle)
    assert completed.returncode == 1
    assert "output_runtime_head_mismatch" in completed.stdout


def test_no_sample_match_identity_leak() -> None:
    text = VERIFIER.read_text(encoding="utf-8")
    forbidden = (
        "Galatasaray",
        "Fenerbahce",
        "Fenerbahçe",
        "Besiktas",
        "Beşiktaş",
        "match001",
    )
    assert not any(token in text for token in forbidden)
