from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from xml_common import (
    MAX_FIELD_PATHS,
    MAX_XML_ROW_CANDIDATES,
    ROLE_ALIASES,
    XmlSurfaceError,
    local_name,
    norm,
    role_for_field,
    stable_json,
)


def _add(target: dict[str, list[str]], key: str, value: Any) -> None:
    text = str(value or "").strip()
    if text:
        target.setdefault(key, []).append(text)


def flatten_element(elem: ET.Element) -> dict[str, Any]:
    values: dict[str, list[str]] = {}
    root = local_name(elem.tag)

    def walk(node: ET.Element, path: tuple[str, ...]) -> None:
        current = (*path, local_name(node.tag))
        base = ".".join(current)
        for key, value in node.attrib.items():
            _add(values, f"{base}.@{local_name(key)}", value)
        _add(values, base, node.text)
        for child in list(node):
            walk(child, current)

    for key, value in elem.attrib.items():
        _add(values, f"{root}.@{local_name(key)}", value)
    _add(values, root, elem.text)
    for child in list(elem):
        walk(child, (root,))
    return {
        key: items[0] if len(items) == 1 else items
        for key, items in values.items()
    }


def profile_rows(path: Path, selected_tag: str) -> dict[str, Any]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise XmlSurfaceError("malformed_xml") from exc
    rows = [elem for elem in root.iter() if local_name(elem.tag) == selected_tag]
    if len(rows) > MAX_XML_ROW_CANDIDATES:
        raise XmlSurfaceError("xml_row_candidate_budget_exceeded")

    field_stats: dict[str, dict[str, Any]] = {}
    shape_counts: Counter[tuple[str, ...]] = Counter()
    hash_counts: Counter[str] = Counter()
    identity_values: dict[str, set[str]] = {role: set() for role in ROLE_ALIASES}
    identity_examples: dict[str, list[str]] = {role: [] for role in ROLE_ALIASES}
    examples: list[dict[str, Any]] = []

    for elem in rows:
        row = flatten_element(elem)
        if len(row) > MAX_FIELD_PATHS:
            raise XmlSurfaceError("xml_field_path_budget_exceeded")
        shape_counts[tuple(sorted(row))] += 1
        digest = hashlib.sha256(stable_json(row).encode("utf-8")).hexdigest()
        hash_counts[digest] += 1
        if len(examples) < 3:
            examples.append(dict(list(sorted(row.items()))[:20]))

        for field, raw in row.items():
            values = raw if isinstance(raw, list) else [raw]
            stat = field_stats.setdefault(
                field,
                {"occurrences": 0, "rows": 0, "unique": set(), "examples": []},
            )
            stat["rows"] += 1
            role = role_for_field(field)
            for value in values:
                text = str(value).strip()
                if not text:
                    continue
                stat["occurrences"] += 1
                if len(stat["unique"]) < 100_000:
                    stat["unique"].add(text)
                if len(stat["examples"]) < 5 and text not in stat["examples"]:
                    stat["examples"].append(text)
                if role:
                    if len(identity_values[role]) < 100_000:
                        identity_values[role].add(text)
                    if (
                        len(identity_examples[role]) < 5
                        and text not in identity_examples[role]
                    ):
                        identity_examples[role].append(text)

    count = len(rows)
    return {
        "row_candidate_count": count,
        "field_path_count": len(field_stats),
        "field_inventory": [
            {
                "raw_field_path": field,
                "normalized_field_path": norm(field),
                "occurrence_count": stat["occurrences"],
                "row_coverage_count": stat["rows"],
                "row_coverage_ratio": stat["rows"] / count if count else 0.0,
                "unique_value_count": len(stat["unique"]),
                "example_values": stat["examples"],
                "semantic_role_candidate": role_for_field(field),
                "validated_semantics": False,
                "claim_ceiling": "XML_FIELD_SURFACE_ONLY",
            }
            for field, stat in sorted(field_stats.items())
        ],
        "row_shape_count": len(shape_counts),
        "row_shape_inventory": [
            {"field_paths": list(shape), "row_count": number}
            for shape, number in shape_counts.most_common(20)
        ],
        "exact_duplicate_row_candidate_count": sum(
            number - 1 for number in hash_counts.values() if number > 1
        ),
        "example_rows": examples,
        "identity_binding": {
            role: {
                "binding_status": "CANDIDATE_ONLY" if values else "UNRESOLVED",
                "candidate_count": len(values),
                "example_candidates": identity_examples[role],
                "validated_identity": False,
            }
            for role, values in identity_values.items()
        },
    }
