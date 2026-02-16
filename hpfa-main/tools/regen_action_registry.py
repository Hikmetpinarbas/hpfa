#!/usr/bin/env python3
"""HPFA Action Registry Sync Automation

Synchronizes Canon Action Registry with Action Mappings via `canon_action`.

Repo-relative paths
- Mapping source: mappings/engine_action_map.json
- Registry target: canon/action_registry.json

Principles
- Canon-First
- Fail-Closed (missing/invalid inputs abort)
- Verbose logs mandatory (audit trail)

Behavior
- Add-only: mapping introduces a canon_action that is missing from registry -> add.
- No-delete: registry-only actions are NOT removed (but logged).
- Deterministic output: actions are written sorted by key.
- Safety: creates a `.bak` of the registry before writing.

Stdlib-only: json, os, shutil, sys, collections.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from collections import OrderedDict
from typing import Any, Dict, Set, Tuple


# === CONFIG ===
MAPPING_FILE = os.path.join("mappings", "engine_action_map.json")
REGISTRY_FILE = os.path.join("canon", "action_registry.json")
REGISTRY_BACKUP = f"{REGISTRY_FILE}.bak"

DEFAULT_ACTION_SCHEMA: Dict[str, Any] = {"status": "aurelia"}
VALID_STATUSES = {"core", "aurelia", "deprecated"}


# === LOGGING ===
def log_info(msg: str) -> None:
    print(f"[INFO] {msg}", file=sys.stdout)


def log_warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


# === FILE I/O ===
def load_json(filepath: str) -> Any:
    """Load JSON file. Fail-Closed: exit if file missing or malformed."""
    if not os.path.exists(filepath):
        log_error(f"File not found: {filepath}")
        sys.exit(1)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log_error(f"JSON decode error in {filepath}: {e}")
        sys.exit(1)
    except Exception as e:
        log_error(f"Failed to read {filepath}: {e}")
        sys.exit(1)


def save_json(filepath: str, data: Any, backup: bool = True) -> None:
    """Write JSON deterministically (sorted keys), with optional backup."""
    if backup and os.path.exists(filepath):
        try:
            shutil.copy2(filepath, REGISTRY_BACKUP)
            log_info(f"Backup created: {REGISTRY_BACKUP}")
        except Exception as e:
            log_error(f"Backup failed: {e}")
            sys.exit(1)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        log_info(f"Action Registry saved: {filepath}")
    except Exception as e:
        log_error(f"Failed to save {filepath}: {e}")
        sys.exit(1)


# === SYNC LOGIC ===
def extract_canon_actions(mapping: Dict[str, Any]) -> Set[str]:
    """Extract canon_action values from mappings/engine_action_map.json.

    Expected mapping shape:
      {
        "VENDOR_ACTION_KEY": {"canon_action": "PASS", "lossy": false, ...},
        ...
      }

    Returns: set of canon_action strings.
    """
    canon_actions: Set[str] = set()

    for vendor_action_id, payload in mapping.items():
        if not isinstance(payload, dict):
            log_warn(f"Skipping non-dict mapping entry: {vendor_action_id}")
            continue

        canon_action = payload.get("canon_action")
        if isinstance(canon_action, str) and canon_action.strip():
            canon_actions.add(canon_action.strip())
        else:
            log_warn(f"Missing/invalid canon_action for vendor_action_id '{vendor_action_id}'")

    return canon_actions


def normalize_registry(registry: Any) -> Dict[str, Any]:
    """Ensure registry has {schema_version, actions} top-level keys."""
    if not isinstance(registry, dict):
        log_error(f"Registry must be a JSON object, got {type(registry).__name__}")
        sys.exit(1)

    schema_version = registry.get("schema_version")
    if schema_version is None:
        # tolerate missing schema_version but set default (still logged)
        log_warn("registry missing schema_version; defaulting to '1.0'")
        schema_version = "1.0"
    elif not isinstance(schema_version, str):
        log_error(f"schema_version must be string, got {type(schema_version).__name__}")
        sys.exit(1)

    actions = registry.get("actions")
    if actions is None:
        log_warn("registry missing actions dict; creating empty actions")
        actions = {}
    elif not isinstance(actions, dict):
        log_error(f"actions must be dict, got {type(actions).__name__}")
        sys.exit(1)

    # Validate existing statuses (fail-closed)
    for action, meta in actions.items():
        if not isinstance(meta, dict):
            log_error(f"Action '{action}' must map to an object; got {type(meta).__name__}")
            sys.exit(1)
        status = meta.get("status")
        if status is None:
            log_error(f"Action '{action}' missing required field: status")
            sys.exit(1)
        if status not in VALID_STATUSES:
            log_error(f"Action '{action}' has invalid status '{status}' (allowed: {sorted(VALID_STATUSES)})")
            sys.exit(1)

    return {"schema_version": schema_version, "actions": actions}


def sync_action_registry(mapping: Dict[str, Any], registry: Dict[str, Any]) -> Tuple[Dict[str, Any], int, int]:
    """Synchronize registry.actions with mapping canon_actions."""
    canon_actions_from_mapping = extract_canon_actions(mapping)

    actions = registry["actions"]
    registry_action_ids = set(actions.keys())

    added: list[str] = []
    for canon_action in canon_actions_from_mapping:
        if canon_action not in actions:
            actions[canon_action] = dict(DEFAULT_ACTION_SCHEMA)
            added.append(canon_action)

    if added:
        log_info(f"Added {len(added)} new action(s) to registry:")
        for a in sorted(added):
            log_info(f"  + {a}")
    else:
        log_info("No new actions to add (registry up-to-date)")

    registry_only = registry_action_ids - canon_actions_from_mapping
    if registry_only:
        log_info("Registry-only actions (not in mapping, not deleted):")
        for a in sorted(registry_only):
            log_info(f"  ○ {a}")

    # Deterministic ordering
    sorted_actions = OrderedDict(sorted(actions.items(), key=lambda kv: kv[0]))
    updated_registry = {
        "schema_version": registry["schema_version"],
        "actions": dict(sorted_actions),
    }

    return updated_registry, len(added), len(registry_only)


def main() -> None:
    log_info("HPFA Action Registry Sync Started")
    log_info(f"Mapping source: {MAPPING_FILE}")
    log_info(f"Registry target: {REGISTRY_FILE}")

    mapping = load_json(MAPPING_FILE)
    if not isinstance(mapping, dict):
        log_error(f"Mapping must be a JSON object, got {type(mapping).__name__}")
        sys.exit(1)

    registry_raw = load_json(REGISTRY_FILE)
    registry = normalize_registry(registry_raw)

    log_info(f"Loaded mapping with {len(mapping)} vendor_action_id(s)")
    log_info(f"Loaded registry with {len(registry['actions'])} action(s)")

    updated_registry, added, registry_only = sync_action_registry(mapping, registry)
    save_json(REGISTRY_FILE, updated_registry, backup=True)

    log_info(f"Sync complete: +{added} added, {registry_only} registry-only")
    log_info(f"Final registry size: {len(updated_registry['actions'])} action(s)")
    log_info("Status: SUCCESS")


if __name__ == "__main__":
    main()
