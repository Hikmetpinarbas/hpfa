"""A5.0 Action Registry Self-Integrity Test

Validates canon/action_registry.json against its own minimal constitutional rules.

Fail-Closed, Canon-First:
- Does NOT check mapping.
- Any violation => AssertionError.

Rules
1) Top-level keys: schema_version (non-empty str), actions (dict)
2) actions must be non-empty dict
3) Each action key: non-empty, UPPER_SNAKE_CASE ([A-Z0-9]+(_[A-Z0-9]+)*)
4) Each action value: dict with required 'status'
5) status ∈ {core, aurelia, deprecated}
6) Raw-text vendor purity: forbidden keywords must not appear anywhere
"""

import json
import os
import re

REGISTRY_FILE = os.path.join("canon", "action_registry.json")

VALID_STATUSES = {"core", "aurelia", "deprecated"}
UPPER_SNAKE_CASE = re.compile(r"^[A-Z0-9]+(?:_[A-Z0-9]+)*$")
FORBIDDEN_KEYWORDS = ("vendor", "opta", "statsbomb", "skillcorner", "wyscout", "sportsbase")


def test_a5_0_action_registry_integrity():
    assert os.path.exists(REGISTRY_FILE), f"Registry file not found: {REGISTRY_FILE}"

    raw = open(REGISTRY_FILE, "r", encoding="utf-8").read()
    raw_lower = raw.lower()

    leaked = [kw for kw in FORBIDDEN_KEYWORDS if kw in raw_lower]
    assert not leaked, f"VULNERABILITY: vendor keyword(s) leaked into Action Registry: {leaked}"

    try:
        reg = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON in {REGISTRY_FILE}: {e}")

    assert isinstance(reg, dict), f"Registry root must be object, got {type(reg).__name__}"

    assert "schema_version" in reg, "Missing required field: schema_version"
    assert isinstance(reg["schema_version"], str) and reg["schema_version"].strip(), "schema_version must be non-empty string"

    assert "actions" in reg, "Missing required field: actions"
    assert isinstance(reg["actions"], dict), f"actions must be dict, got {type(reg['actions']).__name__}"
    assert reg["actions"], "actions dict cannot be empty (regen should populate it)"

    errors = []
    for k, v in reg["actions"].items():
        # key
        if not isinstance(k, str) or not k.strip():
            errors.append((k, "Action key must be a non-empty string"))
        else:
            if not UPPER_SNAKE_CASE.match(k):
                errors.append((k, "Action key must be UPPER_SNAKE_CASE with single underscores only"))
            if "__" in k:
                errors.append((k, "Action key must not contain double underscores '__'"))

        # value
        if not isinstance(v, dict):
            errors.append((k, f"Action value must be dict, got {type(v).__name__}"))
            continue

        if "status" not in v:
            errors.append((k, "Missing required field 'status'"))
            continue

        status = v.get("status")
        if not isinstance(status, str):
            errors.append((k, f"status must be string, got {type(status).__name__}"))
            continue

        if status not in VALID_STATUSES:
            errors.append((k, f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}"))

    assert not errors, "A5.0 FAILED:\n" + "\n".join([f"- {k}: {msg}" for k, msg in errors])
