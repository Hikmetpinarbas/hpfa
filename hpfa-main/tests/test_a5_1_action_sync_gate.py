"""A5.1 Action Sync Gate Contract Test

Fail-Closed: Every `canon_action` referenced in mappings/engine_action_map.json must exist
in canon/action_registry.json under `actions`.

If a single action is missing, this test fails hard (AssertionError) and points to
`tools/regen_action_registry.py`.
"""

import json
import os

MAPPING_FILE = os.path.join("mappings", "engine_action_map.json")
REGISTRY_FILE = os.path.join("canon", "action_registry.json")
MAX_MISSING_DISPLAY = 30


def _load_json(path: str):
    assert os.path.exists(path), f"Missing required file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_a5_1_action_sync_gate():
    mapping = _load_json(MAPPING_FILE)
    registry = _load_json(REGISTRY_FILE)

    actions = registry.get("actions")
    assert isinstance(actions, dict), "Registry must contain an 'actions' dict"

    registry_actions = set(actions.keys())

    canon_actions = set()
    if not isinstance(mapping, dict):
        raise AssertionError(f"Mapping root must be dict, got {type(mapping).__name__}")

    for vendor_action_id, payload in mapping.items():
        if not isinstance(payload, dict):
            continue
        ca = payload.get("canon_action")
        if isinstance(ca, str) and ca.strip():
            canon_actions.add(ca)

    missing = canon_actions - registry_actions

    if missing:
        missing_sorted = sorted(missing)
        show = missing_sorted[:MAX_MISSING_DISPLAY]
        rest = len(missing_sorted) - len(show)
        msg = [
            f"A5.1 Action Sync Gate FAILED: {len(missing)} canon_action(s) missing in registry.",
            f"Mapping:  {MAPPING_FILE}",
            f"Registry: {REGISTRY_FILE}",
            "",
            "First missing actions:",
            *[f"  - {a}" for a in show],
        ]
        if rest > 0:
            msg.append(f"  ... and {rest} more")
        msg.extend(
            [
                "",
                "Action: run tools/regen_action_registry.py",
                "Principle: Fail-Closed — registry must be 100% complete.",
            ]
        )
        raise AssertionError("\n".join(msg))
