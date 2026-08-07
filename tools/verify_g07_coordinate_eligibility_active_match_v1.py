#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_ADMIN_ROLES = {
    "PERIOD_OR_META",
    "MATCH_BOUNDARY",
    "ADMINISTRATIVE",
    "ADMINISTRATIVE_MARKER",
}
_ACTIVE_MATCH_STATUSES = {
    "ACTIVE_MATCH_EVIDENCE_PASS",
    "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED",
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("row_nucleus_payload_not_object")
    return payload


def _is_missing(record: dict[str, Any]) -> bool:
    return record.get("pos_x_candidate") is None or record.get("pos_y_candidate") is None


def _is_admin_exempt(record: dict[str, Any]) -> bool:
    roles = {
        str(value)
        for value in (record.get("semantic_role_candidates") or [])
        if value
    }
    eligibilities = {
        str(value)
        for value in (record.get("downstream_eligibility_candidates") or [])
        if value
    }
    return bool(roles) and roles <= _ADMIN_ROLES and eligibilities == {"ADMIN_ONLY"}


def verify(
    payload: dict[str, Any], *, expected_head: str, expected_authority: str
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []

    if payload.get("runtime_code_head_sha") != expected_head:
        errors.append("runtime_code_head_sha_mismatch")
    if payload.get("runtime_authority") != expected_authority:
        errors.append("runtime_authority_mismatch")
    if payload.get("active_match_execution_completed") is not True:
        errors.append("active_match_execution_not_completed")
    if payload.get("runtime_evidence_status") not in _ACTIVE_MATCH_STATUSES:
        errors.append("runtime_evidence_status_not_active_match")
    if payload.get("canonical_event_count") != "UNKNOWN":
        errors.append("canonical_event_count_claimed")
    if payload.get("production_release") is not False:
        errors.append("production_release_claimed")

    nuclei = payload.get("row_nuclei") or []
    if not isinstance(nuclei, list):
        errors.append("row_nuclei_invalid")
        nuclei = []

    missing = [record for record in nuclei if isinstance(record, dict) and _is_missing(record)]
    exempt = [record for record in missing if _is_admin_exempt(record)]
    required = [record for record in missing if not _is_admin_exempt(record)]

    reported_total = payload.get("coordinate_missing_nucleus_count")
    reported_exempt = payload.get("coordinate_missing_exempt_nucleus_count")
    reported_required = payload.get("coordinate_missing_required_nucleus_count")

    if reported_total != len(missing):
        errors.append("coordinate_missing_total_mismatch")
    if reported_exempt != len(exempt):
        errors.append("coordinate_missing_exempt_mismatch")
    if reported_required != len(required):
        errors.append("coordinate_missing_required_mismatch")
    if isinstance(reported_total, int) and isinstance(reported_exempt, int) and isinstance(reported_required, int):
        if reported_total != reported_exempt + reported_required:
            errors.append("coordinate_missing_partition_mismatch")

    rollup = payload.get("g01_g18_rollup") or {}
    gates = rollup.get("gates") if isinstance(rollup, dict) else None
    if not isinstance(gates, list):
        errors.append("g01_g18_gates_invalid")
        gates = []

    g07 = next(
        (
            gate
            for gate in gates
            if isinstance(gate, dict) and gate.get("gate_id") == "G07"
        ),
        None,
    )
    g16 = next(
        (
            gate
            for gate in gates
            if isinstance(gate, dict) and gate.get("gate_id") == "G16"
        ),
        None,
    )
    if not isinstance(g07, dict):
        errors.append("g07_missing")
        g07_status = "MISSING"
    else:
        g07_status = str(g07.get("status") or "UNKNOWN")
        expected_g07 = "PASS" if not required else "REVIEW_REQUIRED"
        if g07_status != expected_g07:
            errors.append("g07_status_not_eligibility_consistent")
        evidence = g07.get("evidence") or {}
        if not isinstance(evidence, dict):
            errors.append("g07_evidence_invalid")
        else:
            if evidence.get("coordinate_missing_nucleus_count") != len(missing):
                errors.append("g07_total_evidence_mismatch")
            if evidence.get("coordinate_missing_exempt_nucleus_count") != len(exempt):
                errors.append("g07_exempt_evidence_mismatch")
            if evidence.get("coordinate_missing_required_nucleus_count") != len(required):
                errors.append("g07_required_evidence_mismatch")

    summary = {
        "coordinate_missing_nucleus_count": len(missing),
        "coordinate_missing_exempt_nucleus_count": len(exempt),
        "coordinate_missing_required_nucleus_count": len(required),
        "g07_status": g07_status,
        "g16_status": (str(g16.get("status") or "UNKNOWN") if isinstance(g16, dict) else "MISSING"),
        "g01_g18_status": (str(rollup.get("status") or "UNKNOWN") if isinstance(rollup, dict) else "UNKNOWN"),
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify eligibility-aware G07 against exact-head ACTIVE_MATCH Row Nucleus output."
    )
    parser.add_argument("--row-nucleus", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-authority", required=True)
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.expected_head):
        print("status=FAIL_CLOSED\nreason=expected_head_invalid", file=sys.stderr)
        return 2
    expected_head = args.expected_head.lower()
    path = Path(args.row_nucleus)
    if not path.is_file():
        print("status=FAIL_CLOSED\nreason=row_nucleus_output_missing", file=sys.stderr)
        return 2

    try:
        payload = _load(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"status=FAIL_CLOSED\nreason=row_nucleus_output_invalid:{exc}", file=sys.stderr)
        return 2

    errors, summary = verify(
        payload,
        expected_head=expected_head,
        expected_authority=args.expected_authority,
    )
    if errors:
        print("status=ACTIVE_MATCH_REVALIDATION_FAILED")
        for error in sorted(set(errors)):
            print(f"error={error}")
        for key, value in summary.items():
            print(f"{key}={value}")
        print("canonical_event_count=UNKNOWN")
        print("production_release=false")
        return 1

    print("status=ACTIVE_MATCH_G07_ELIGIBILITY_EVIDENCE_VERIFIED")
    print(f"runtime_code_head_sha={expected_head}")
    print(f"runtime_authority={args.expected_authority}")
    for key, value in summary.items():
        print(f"{key}={value}")
    print("canonical_event_count=UNKNOWN")
    print("production_release=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
