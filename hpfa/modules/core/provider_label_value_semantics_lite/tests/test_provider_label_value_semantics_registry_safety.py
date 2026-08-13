from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
REGISTRY_DIR = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "provider_label_value_semantics_lite"
    / "registry"
)
MANIFEST = REGISTRY_DIR / "sportsbase_label_semantics_seed_v1.json"
RULES = REGISTRY_DIR / "sportsbase_label_semantics_reviewed_v2.csv"


def test_registry_manifest_and_rules_are_match_agnostic() -> None:
    content = MANIFEST.read_text(encoding="utf-8") + RULES.read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798"]
    assert not any(token in content for token in forbidden)


def test_reviewed_rules_have_unique_role_scopes_and_required_fields() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["registry_id"] == "sportsbase_label_semantics_reviewed_v2"
    assert manifest["exact_rules_file"] == RULES.name

    seen: set[tuple[str, tuple[str, ...]]] = set()
    with RULES.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    for row in rows:
        label = (row.get("label") or "").strip().casefold()
        rule_id = (row.get("rule_id") or "").strip()
        semantic_role = (row.get("semantic_role") or "").strip()
        roles = tuple(sorted(value for value in (row.get("source_roles") or "").split("|") if value))
        assert label
        assert rule_id
        assert semantic_role
        key = (label, roles)
        assert key not in seen
        seen.add(key)
