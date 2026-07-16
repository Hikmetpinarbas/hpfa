from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

MODULE_ID = "active_match_pipeline_manifest_lite_v1"
ENVELOPE_MODULE_ID = "pipeline_stage_provenance_envelope_lite_v1"
RUNTIME_AUTHORITY = "runtime/active_single_match/current"
GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
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


def _stage_link(payload: dict[str, Any]) -> tuple[str, str, str, list[str], str, str]:
    """Return module, input hash, output hash, failures, payload mode and code head."""
    if _clean(payload.get("module_id")) != ENVELOPE_MODULE_ID:
        return (
            _clean(payload.get("module_id")),
            _clean(payload.get("input_sha256")),
            _canonical_sha256(payload),
            [],
            "RAW_STAGE_PAYLOAD",
            "",
        )

    failures: list[str] = []
    stage_payload = payload.get("stage_payload")
    if not isinstance(stage_payload, dict):
        stage_payload = {}
        failures.append("ENVELOPE_STAGE_PAYLOAD_MISSING_OR_INVALID")

    stage_module_id = _clean(payload.get("stage_module_id"))
    embedded_module_id = _clean(stage_payload.get("module_id"))
    expected_stage_module_id = _clean(payload.get("expected_stage_module_id"))
    if not stage_module_id or stage_module_id != embedded_module_id:
        failures.append("ENVELOPE_STAGE_MODULE_ID_MISMATCH")
    if expected_stage_module_id and expected_stage_module_id != stage_module_id:
        failures.append("ENVELOPE_EXPECTED_MODULE_ID_MISMATCH")

    declared_stage_sha256 = _clean(payload.get("stage_payload_sha256"))
    computed_stage_sha256 = _canonical_sha256(stage_payload)
    if not declared_stage_sha256:
        failures.append("ENVELOPE_STAGE_PAYLOAD_SHA256_MISSING")
    elif declared_stage_sha256 != computed_stage_sha256:
        failures.append("ENVELOPE_STAGE_PAYLOAD_SHA256_MISMATCH")

    code_head_sha = _clean(payload.get("runtime_code_head_sha")).lower()
    if not code_head_sha or code_head_sha == "missing":
        failures.append("ENVELOPE_RUNTIME_CODE_HEAD_SHA_MISSING")
    elif not GIT_SHA_PATTERN.fullmatch(code_head_sha):
        failures.append("ENVELOPE_RUNTIME_CODE_HEAD_SHA_INVALID")

    if _clean(payload.get("decision_state")) != "PASS_STAGE_PROVENANCE_ENVELOPE":
        failures.append("ENVELOPE_NOT_PASSING")
    if payload.get("provenance_blocker_count") not in (0, "0"):
        failures.append("ENVELOPE_HAS_PROVENANCE_BLOCKERS")
    if payload.get("canonical_event_count") != "UNKNOWN":
        failures.append("ENVELOPE_CANONICAL_EVENT_COUNT_CLAIM_VIOLATION")
    if payload.get("production_release") is not False:
        failures.append("ENVELOPE_PRODUCTION_RELEASE_CLAIM_VIOLATION")

    return (
        stage_module_id or embedded_module_id,
        _clean(payload.get("input_sha256")),
        computed_stage_sha256,
        failures,
        "PROVENANCE_ENVELOPE",
        code_head_sha,
    )


def build_pipeline_manifest(
    runtime_authority: str,
    source_payload: dict[str, Any],
    stage_payloads: list[dict[str, Any]],
    *,
    require_provenance_envelopes: bool = True,
    expected_runtime_code_head_sha: str = "",
) -> dict[str, Any]:
    authority = _clean(runtime_authority).replace("\\", "/").rstrip("/")
    expected_code_head = _clean(expected_runtime_code_head_sha).lower()
    failures: list[str] = []
    if authority != RUNTIME_AUTHORITY:
        failures.append("INVALID_RUNTIME_AUTHORITY")
    if require_provenance_envelopes:
        if not expected_code_head:
            failures.append("MISSING_EXPECTED_RUNTIME_CODE_HEAD_SHA")
        elif not GIT_SHA_PATTERN.fullmatch(expected_code_head):
            failures.append("INVALID_EXPECTED_RUNTIME_CODE_HEAD_SHA")

    source_sha256 = _canonical_sha256(source_payload)
    previous_sha256 = source_sha256
    rows: list[dict[str, Any]] = []
    seen: list[str] = []

    for position, payload in enumerate(stage_payloads):
        module_id, input_sha256, output_sha256, envelope_failures, payload_mode, code_head_sha = _stage_link(payload)
        expected_module = REQUIRED_STAGES[position] if position < len(REQUIRED_STAGES) else None

        stage_failures: list[str] = list(envelope_failures)
        if require_provenance_envelopes and payload_mode != "PROVENANCE_ENVELOPE":
            stage_failures.append("RAW_STAGE_PAYLOAD_NOT_ADMISSIBLE")
        if require_provenance_envelopes and payload_mode == "PROVENANCE_ENVELOPE" and code_head_sha != expected_code_head:
            stage_failures.append("RUNTIME_CODE_HEAD_SHA_MISMATCH")
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
            "payload_mode": payload_mode,
            "runtime_code_head_sha": code_head_sha or "MISSING",
            "expected_runtime_code_head_sha": expected_code_head or "MISSING",
            "input_sha256": input_sha256 or "MISSING",
            "expected_input_sha256": previous_sha256,
            "output_sha256": output_sha256,
            "stage_status": "PASS_FRESH_CHAIN_LINK" if not stage_failures else "BLOCKED_CHAIN_LINK",
            "stage_failures": sorted(set(stage_failures)),
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
        "expected_runtime_code_head_sha": expected_code_head or "MISSING",
        "source_sha256": source_sha256,
        "stage_chain": rows,
        "chain_failure_reasons": sorted(set(failures)),
        "pipeline_chain_complete": not failures,
        "provenance_envelopes_required": require_provenance_envelopes,
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
