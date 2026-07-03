from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODULE_ID = "provider_alias_registry_binding_lite_v1"
REQUIRED_RECORD_FIELDS = {
    "provider",
    "raw_alias",
    "normalized_alias",
    "canonical_key_candidate",
    "mapping_direction",
    "reverse_mapping_supported",
    "alias_reliability",
    "vendor_leakage_risk",
    "rule_id",
}
ALLOWED_RELIABILITY = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}


def normalize_alias(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(field for field in REQUIRED_RECORD_FIELDS if field not in record)
    for field in missing:
        errors.append(f"missing_field:{field}")

    if record.get("normalized_alias") != normalize_alias(record.get("raw_alias")):
        errors.append("normalized_alias_mismatch")
    if record.get("alias_reliability") not in ALLOWED_RELIABILITY:
        errors.append("invalid_alias_reliability")
    if not str(record.get("rule_id", "")).strip():
        errors.append("missing_rule_id")

    return errors


def load_registry(payload: dict[str, Any]) -> dict[str, Any]:
    records = payload.get("records", []) or []
    if not isinstance(records, list):
        records = []

    validated: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append({"index": idx, "errors": ["record_not_object"]})
            continue
        key = (str(record.get("provider", "")), str(record.get("normalized_alias", "")))
        record_errors = validate_record(record)
        if key in seen:
            record_errors.append("duplicate_provider_alias")
        seen.add(key)
        if record_errors:
            errors.append({"index": idx, "errors": record_errors, "record": record})
        else:
            validated.append(record)

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if errors else "SMOKE_PASS",
        "runtime_verified": False,
        "registry_id": payload.get("registry_id", "UNKNOWN"),
        "records_loaded": len(validated),
        "records_rejected": len(errors),
        "records": validated,
        "errors": errors,
        "authority_tier": "DONOR_SUPPORT_SEED",
        "claim_boundary": "provider_alias_candidate_not_truth",
    }


def find_alias(registry: dict[str, Any], provider: str, raw_alias: str) -> dict[str, Any]:
    normalized = normalize_alias(raw_alias)
    for record in registry.get("records", []) or []:
        if record.get("provider") == provider and record.get("normalized_alias") == normalized:
            return {
                "provider_alias_status": "CANDIDATE_MATCH",
                "canonical_key_candidate": record.get("canonical_key_candidate"),
                "rule_id": record.get("rule_id"),
                "alias_reliability": record.get("alias_reliability"),
                "runtime_verified": False,
            }
    return {
        "provider_alias_status": "REVIEW_REQUIRED",
        "canonical_key_candidate": None,
        "rule_id": None,
        "alias_reliability": "UNKNOWN",
        "runtime_verified": False,
        "abstain_reason": "unknown_provider_alias",
    }
