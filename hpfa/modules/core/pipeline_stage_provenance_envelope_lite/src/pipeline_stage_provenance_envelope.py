from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "pipeline_stage_provenance_envelope_lite_v1"
OUTPUT_JSON = "pipeline_stage_provenance_envelope_lite_v1.json"


def canonical_payload_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_stage_envelope(
    input_payload: dict[str, Any],
    stage_payload: dict[str, Any],
    expected_stage_module_id: str,
) -> dict[str, Any]:
    actual_stage_module_id = str(stage_payload.get("module_id") or "").strip()
    expected_stage_module_id = str(expected_stage_module_id or "").strip()
    stage_decision_state = str(stage_payload.get("decision_state") or "").strip()

    blockers: list[dict[str, str]] = []
    if not expected_stage_module_id:
        blockers.append({
            "code": "MISSING_EXPECTED_STAGE_MODULE_ID",
            "detail": "expected stage module id is required",
        })
    elif actual_stage_module_id != expected_stage_module_id:
        blockers.append({
            "code": "STAGE_MODULE_ID_MISMATCH",
            "detail": f"expected={expected_stage_module_id};actual={actual_stage_module_id or 'MISSING'}",
        })

    if not stage_decision_state:
        blockers.append({
            "code": "MISSING_STAGE_DECISION_STATE",
            "detail": "stage decision_state is required for provenance admission",
        })
    elif stage_decision_state.startswith("BLOCKED"):
        blockers.append({
            "code": "BLOCKED_STAGE_DECISION_NOT_ADMISSIBLE",
            "detail": f"stage decision_state={stage_decision_state}",
        })

    if stage_payload.get("canonical_event_count") != "UNKNOWN":
        blockers.append({
            "code": "CANONICAL_EVENT_COUNT_CLAIM_VIOLATION",
            "detail": "canonical_event_count must remain UNKNOWN",
        })
    if stage_payload.get("production_release") is not False:
        blockers.append({
            "code": "PRODUCTION_RELEASE_CLAIM_VIOLATION",
            "detail": "production_release must remain false",
        })

    return {
        "module_id": MODULE_ID,
        "stage_module_id": actual_stage_module_id,
        "expected_stage_module_id": expected_stage_module_id,
        "stage_decision_state": stage_decision_state or "MISSING",
        "input_sha256": canonical_payload_sha256(input_payload),
        "stage_payload_sha256": canonical_payload_sha256(stage_payload),
        "stage_payload": stage_payload,
        "decision_state": "PASS_STAGE_PROVENANCE_ENVELOPE" if not blockers else "BLOCKED_STAGE_PROVENANCE_ENVELOPE",
        "provenance_blockers": blockers,
        "provenance_blocker_count": len(blockers),
        "identity_bound_event_count": 0,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def write_output(
    input_json: str | Path,
    stage_json: str | Path,
    expected_stage_module_id: str,
    output_json: str | Path,
) -> dict[str, Any]:
    input_payload = json.loads(Path(input_json).read_text(encoding="utf-8"))
    stage_payload = json.loads(Path(stage_json).read_text(encoding="utf-8"))
    result = build_stage_envelope(input_payload, stage_payload, expected_stage_module_id)
    destination = Path(output_json)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--stage-json", required=True)
    parser.add_argument("--expected-stage-module-id", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()
    result = write_output(
        args.input_json,
        args.stage_json,
        args.expected_stage_module_id,
        args.output_json,
    )
    print(json.dumps({
        "decision_state": result["decision_state"],
        "stage_module_id": result["stage_module_id"],
        "stage_decision_state": result["stage_decision_state"],
        "input_sha256": result["input_sha256"],
        "stage_payload_sha256": result["stage_payload_sha256"],
        "provenance_blocker_count": result["provenance_blocker_count"],
        "canonical_event_count": result["canonical_event_count"],
        "production_release": result["production_release"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["decision_state"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
