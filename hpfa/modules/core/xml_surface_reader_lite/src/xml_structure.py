from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from xml_common import (
    MAX_XML_ATTRIBUTES_PER_ELEMENT,
    MAX_XML_DEPTH,
    MAX_XML_ELEMENTS,
    MAX_XML_TEXT_CHARS,
    PREFERRED_ROW_TAGS,
    XmlSurfaceError,
    local_name,
    namespace_uri,
    norm,
)


def _mode(counter: Counter[Any]) -> Any:
    return max(counter.items(), key=lambda pair: (pair[1], str(pair[0])))[0] if counter else None


def scan_structure(path: Path) -> dict[str, Any]:
    namespaces: dict[str, str] = {}
    tags: Counter[str] = Counter()
    structured: Counter[str] = Counter()
    leaves: Counter[str] = Counter()
    depths: dict[str, Counter[int]] = defaultdict(Counter)
    signatures: dict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    attributes: Counter[str] = Counter()
    namespace_counts: Counter[str] = Counter()
    stack: list[list[str]] = []
    root_tag: str | None = None
    total_elements = 0
    total_attributes = 0
    max_depth = 0

    try:
        for event, payload in ET.iterparse(path, events=("start", "end", "start-ns")):
            if event == "start-ns":
                prefix, uri = payload
                namespaces[str(prefix or "default")] = str(uri)
                continue

            elem = payload
            tag = local_name(elem.tag)
            if event == "start":
                depth = len(stack)
                root_tag = root_tag or tag
                total_elements += 1
                if total_elements > MAX_XML_ELEMENTS:
                    raise XmlSurfaceError("xml_element_budget_exceeded")
                if depth > MAX_XML_DEPTH:
                    raise XmlSurfaceError("xml_depth_budget_exceeded")
                if len(elem.attrib) > MAX_XML_ATTRIBUTES_PER_ELEMENT:
                    raise XmlSurfaceError("xml_attribute_budget_exceeded")
                tags[tag] += 1
                depths[tag][depth] += 1
                max_depth = max(max_depth, depth)
                total_attributes += len(elem.attrib)
                for key in elem.attrib:
                    attributes[local_name(key)] += 1
                uri = namespace_uri(elem.tag)
                if uri:
                    namespace_counts[uri] += 1
                stack.append([])
                continue

            children = tuple(stack.pop())
            signatures[tag][children] += 1
            if children or elem.attrib:
                structured[tag] += 1
            else:
                leaves[tag] += 1
            if len((elem.text or "").strip()) > MAX_XML_TEXT_CHARS:
                raise XmlSurfaceError("xml_text_budget_exceeded")
            if stack:
                stack[-1].append(tag)
            elem.clear()
    except ET.ParseError as exc:
        raise XmlSurfaceError("malformed_xml") from exc

    if not root_tag:
        raise XmlSurfaceError("xml_root_missing")

    candidates: list[dict[str, Any]] = []
    for tag, count in tags.items():
        if tag == root_tag or count < 2 or structured[tag] == 0:
            continue
        dominant = _mode(signatures[tag])
        signature_ratio = signatures[tag].get(dominant, 0) / count
        structured_ratio = structured[tag] / count
        score = min(count, 100_000) + structured_ratio * 100 + signature_ratio * 80
        if norm(tag) in PREFERRED_ROW_TAGS:
            score += 1_000_000
        candidates.append(
            {
                "tag": tag,
                "occurrence_count": count,
                "structured_occurrence_count": structured[tag],
                "structured_ratio": round(structured_ratio, 6),
                "dominant_depth": _mode(depths[tag]),
                "dominant_child_signature": list(dominant or ()),
                "dominant_signature_ratio": round(signature_ratio, 6),
                "score": round(score, 6),
            }
        )

    candidates.sort(key=lambda row: (-row["score"], row["tag"]))
    selected = candidates[0] if candidates else None
    ambiguous = bool(
        len(candidates) > 1
        and selected
        and abs(selected["score"] - candidates[1]["score"]) < 1
    )
    return {
        "root_tag": root_tag,
        "namespace_map": dict(sorted(namespaces.items())),
        "namespace_usage_counts": dict(sorted(namespace_counts.items())),
        "total_element_count": total_elements,
        "total_attribute_count": total_attributes,
        "max_depth": max_depth,
        "tag_inventory": [
            {
                "tag": tag,
                "occurrence_count": count,
                "structured_occurrence_count": structured[tag],
                "leaf_occurrence_count": leaves[tag],
                "dominant_depth": _mode(depths[tag]),
            }
            for tag, count in tags.most_common()
        ],
        "attribute_inventory": [
            {"attribute": key, "occurrence_count": count}
            for key, count in attributes.most_common()
        ],
        "row_container_candidates": candidates[:20],
        "selected_row_tag_candidate": selected["tag"] if selected else None,
        "row_candidate_ambiguous": ambiguous,
    }
