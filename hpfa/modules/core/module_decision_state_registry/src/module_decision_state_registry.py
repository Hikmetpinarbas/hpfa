from __future__ import annotations

ALLOWED_STATES = {
    "READY",
    "READY_WITH_WARNINGS",
    "DESCRIPTIVE_ONLY",
    "BLOCKED",
    "REVIEW_REQUIRED",
}


def validate_decision(record: dict) -> dict:
    errors = []
    if not record.get("module_id"):
        errors.append("missing_module_id")
    if record.get("decision_state") not in ALLOWED_STATES:
        errors.append("invalid_decision_state")
    if not record.get("reason"):
        errors.append("missing_reason")
    if not record.get("release_status"):
        errors.append("missing_release_status")
    if record.get("decision_state") == "BLOCKED" and not record.get("blocked_downstream_modules"):
        errors.append("blocked_state_requires_downstream_list")
    return {"valid": not errors, "errors": errors}


def build_decision(module_id: str, decision_state: str, reason: str, release_status: str = "REVIEW_REQUIRED") -> dict:
    record = {
        "module_id": module_id,
        "decision_state": decision_state,
        "reason": reason,
        "release_status": release_status,
        "missing_inputs": [],
        "next_allowed_module": [],
        "blocked_downstream_modules": [],
    }
    record["validation"] = validate_decision(record)
    return record
