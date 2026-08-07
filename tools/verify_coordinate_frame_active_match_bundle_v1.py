#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

ACTIVE_STATUSES = {
    "ACTIVE_MATCH_EVIDENCE_PASS",
    "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED",
}
REQUIRED_FILES = {
    "coordinate_frame_precondition_lite_v1.json",
    "coordinate_frame_precondition_active_match_v1.txt",
    "coordinate_frame_precondition_runtime_audit_v1.txt",
    "coordinate_frame_precondition_dependency_audit_v1.json",
    "coordinate_frame_precondition_operator_state_v1.txt",
    "coordinate_frame_precondition_active_match_bundle_manifest_v1.json",
}
MANIFEST_NAME = "coordinate_frame_precondition_active_match_bundle_manifest_v1.json"


def parse_state(text: str) -> dict[str, str]:
    state: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        state[key.strip()] = value.strip()
    return state


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(archive.read(name).decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(name) from exc
    if not isinstance(payload, dict):
        raise ValueError(name)
    return payload


def verify_archive(
    archive: zipfile.ZipFile,
    *,
    expected_head: str,
    expected_authority: str,
    expected_branch: str | None,
) -> list[str]:
    errors: list[str] = []
    bad = archive.testzip()
    if bad:
        errors.append(f"zip_crc_failure:{bad}")

    names = set(archive.namelist())
    missing = sorted(REQUIRED_FILES - names)
    if missing:
        errors.append("required_bundle_member_missing:" + ",".join(missing))
        return errors

    try:
        payload = read_json(archive, "coordinate_frame_precondition_lite_v1.json")
        dependency = read_json(
            archive, "coordinate_frame_precondition_dependency_audit_v1.json"
        )
        manifest = read_json(archive, MANIFEST_NAME)
        state = parse_state(
            archive.read("coordinate_frame_precondition_operator_state_v1.txt").decode(
                "utf-8"
            )
        )
    except (ValueError, UnicodeDecodeError) as exc:
        errors.append(f"bundle_member_invalid:{exc}")
        return errors

    if payload.get("runtime_code_head_sha") != expected_head:
        errors.append("output_runtime_head_mismatch")
    if payload.get("runtime_authority") != expected_authority:
        errors.append("output_runtime_authority_mismatch")
    if payload.get("active_match_execution_completed") is not True:
        errors.append("output_active_match_execution_not_completed")
    if payload.get("runtime_evidence_status") not in ACTIVE_STATUSES:
        errors.append("output_runtime_evidence_status_not_active_match")
    if payload.get("canonical_event_count") != "UNKNOWN":
        errors.append("canonical_event_count_claimed")
    if payload.get("production_release") is not False:
        errors.append("production_release_claimed")

    if state.get("status") != "COMPLETED":
        errors.append("operator_state_not_completed")
    if state.get("runtime_code_head_sha") != expected_head:
        errors.append("operator_state_runtime_head_mismatch")
    if state.get("expected_head_sha") != expected_head:
        errors.append("operator_state_expected_head_mismatch")
    if state.get("runtime_authority") != expected_authority:
        errors.append("operator_state_runtime_authority_mismatch")
    if expected_branch and state.get("branch") != expected_branch:
        errors.append("operator_state_branch_mismatch")
    if state.get("canonical_event_count") != "UNKNOWN":
        errors.append("operator_state_canonical_event_count_claimed")
    if state.get("production_release") != "false":
        errors.append("operator_state_production_release_claimed")

    if dependency.get("source_role") != "ACTIVE_MATCH_EXACT_RUN_AUDIT":
        errors.append("dependency_audit_source_role_invalid")
    if dependency.get("runtime_code_head_sha") != expected_head:
        errors.append("dependency_audit_runtime_head_mismatch")
    if dependency.get("runtime_authority") != expected_authority:
        errors.append("dependency_audit_runtime_authority_mismatch")
    if dependency.get("canonical_event_count") != "UNKNOWN":
        errors.append("dependency_audit_canonical_event_count_claimed")
    if dependency.get("production_release") is not False:
        errors.append("dependency_audit_production_release_claimed")

    if manifest.get("runtime_code_head_sha") != expected_head:
        errors.append("manifest_runtime_head_mismatch")
    if manifest.get("runtime_authority") != expected_authority:
        errors.append("manifest_runtime_authority_mismatch")
    if expected_branch and manifest.get("branch") != expected_branch:
        errors.append("manifest_branch_mismatch")

    rows = manifest.get("files")
    if not isinstance(rows, list):
        errors.append("manifest_files_invalid")
        return errors

    row_map = {
        row.get("name"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }
    for name in sorted(REQUIRED_FILES - {MANIFEST_NAME}):
        row = row_map.get(name)
        if not isinstance(row, dict):
            errors.append(f"manifest_required_member_missing:{name}")
            continue
        data = archive.read(name)
        if row.get("sha256") != sha256_bytes(data):
            errors.append(f"manifest_sha_mismatch:{name}")
        if row.get("size_bytes") != len(data):
            errors.append(f"manifest_size_mismatch:{name}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify exact-head HPFA coordinate-frame ACTIVE_MATCH evidence bundle."
    )
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-authority", required=True)
    parser.add_argument("--expected-branch")
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.expected_head):
        print("status=FAIL_CLOSED\nreason=expected_head_invalid", file=sys.stderr)
        return 2
    expected_head = args.expected_head.lower()

    bundle = Path(args.bundle)
    if not bundle.is_file():
        print("status=FAIL_CLOSED\nreason=bundle_missing", file=sys.stderr)
        return 2

    try:
        with zipfile.ZipFile(bundle) as archive:
            errors = verify_archive(
                archive,
                expected_head=expected_head,
                expected_authority=args.expected_authority,
                expected_branch=args.expected_branch,
            )
    except (OSError, zipfile.BadZipFile):
        print("status=FAIL_CLOSED\nreason=bundle_zip_invalid", file=sys.stderr)
        return 2

    if errors:
        print("status=ACTIVE_MATCH_REVALIDATION_REQUIRED")
        for error in sorted(set(errors)):
            print(f"error={error}")
        print("canonical_event_count=UNKNOWN")
        print("production_release=false")
        return 1

    print("status=ACTIVE_MATCH_EVIDENCE_PACKAGE_VERIFIED")
    print(f"runtime_code_head_sha={expected_head}")
    print(f"runtime_authority={args.expected_authority}")
    if args.expected_branch:
        print(f"branch={args.expected_branch}")
    print("canonical_event_count=UNKNOWN")
    print("production_release=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
