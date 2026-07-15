from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "active_match_pipeline_manifest_lite_v1"
RUNTIME_AUTHORITY = "runtime/active_single_match/current"
REQUIRED_STAGES = (
    "evidence_atom_contract_lite_v1",
    "base_event_label_semantic_classifier_lite_v1",
    "cross_role_reflection_resolver_lite_v1",
    "aggregate_event_reconciliation_gate_lite_v1",
    "residual_event_mismatch_diagnostic_lite_v1",
)


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _clean(value: Any) -> str:
    return " ".join("" if value is None else str(value).split()).strip()


def build_pipeline_manifest(
    runtime_authority: str,
    source_payload: dict[str, Any],
    stage_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    authority = _clean(runtime_authority).replace("\\", "/").rstrip("/")
    failures: list[str] = []
    if authority != RUNTIME_AUTHORITY:
        failures.append("INVALID_RUNTIME_AUTHORITY")

    source_sha256 = _canonical_sha256(source_payload)
    previous_sha256 = source_sha256
    rows: list[dict[str, Any]] = []
    seen: list[str] = []

    for position, payload in enumerate(stage_payloads):
        module_id = _clean(payload.get("module_id"))
        input_sha256 = _clean(payload.get("input_sha256"))
        output_sha256 = _canonical_sha256(payload)
        expected_module = REQUIRED_STAGES[position] if position < len(REQUIRED_STAGES) else None

        stage_failures: list[str] = []
        if expected_module is None:
            stage_failures.append("UNEXPECTED_EXTRA_STAGE")
        elif module_id != expected_module:
            stage_failures.append("STAGE_ORDER_OR_MODULE_MISMATCH")
        if not input_sha256:
            stage_failures.append("MISSING_INPUT_SHA256")
        elif input_sha256 != previous_sha256:
            stage_failures.append("STALE_OR_FOREIGN_STAGE_INPUT")

        if stage_failures:
            failures.extend(f"{module_id or 'UNKNOWN'}:{item}" for item in stage_failures)

        rows.append({
            "stage_position": position + 1,
            "module_id": module_id or "UNKNOWN",
            "expected_module_id": expected_module or "NONE",
            "input_sha256": input_sha256 or "MISSING",
            "expected_input_sha256": previous_sha256,
            "output_sha256": output_sha256,
            "stage_status": "PASS_FRESH_CHAIN_LINK" if not stage_failures else "BLOCKED_CHAIN_LINK",
            "stage_failures": stage_failures,
        })
        seen.append(module_id)
        previous_sha256 = output_sha256

    if len(stage_payloads) < len(REQUIRED_STAGES):
        for missing in REQUIRED_STAGES[len(stage_payloads):]:
            failures.append(f"{missing}:MISSING_REQUIRED_STAGE")

    if tuple(seen[: len(REQUIRED_STAGES)]) != REQUIRED_STAGES:
        failures.append("REQUIRED_STAGE_SEQUENCE_NOT_PROVEN")

    return {
        "module_id": MODULE_ID,
        "decision_state": "PASS_FRESH_ACTIVE_MATCH_PIPELINE_CHAIN" if not failures else "BLOCKED_STALE_OR_INCOMPLETE_PIPELINE_CHAIN",
        "runtime_authority": authority,
        "source_sha256": source_sha256,
        "stage_chain": rows,
        "chain_failure_reasons": sorted(set(failures)),
        "pipeline_chain_complete": not failures,
        "identity_bound_event_count": 0,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("json_payload_must_be_object")
    return payload
