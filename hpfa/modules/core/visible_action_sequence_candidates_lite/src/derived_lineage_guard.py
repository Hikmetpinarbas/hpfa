from __future__ import annotations

import hashlib
import json
from typing import Any

MODULE_ID = "derived_lineage_guard_v1"
ALLOWED_DERIVATION_TYPES = {"PROJECT", "AGGREGATE", "RELATE", "FILTER", "NARRATIVE", "OBSERVED"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _group_id(root_refs: list[str]) -> str | None:
    if not root_refs:
        return None
    raw = json.dumps(sorted(root_refs), ensure_ascii=False, separators=(",", ":"))
    return "lin_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def resolve_lineage(
    object_id: str,
    *,
    parent_refs: list[str] | None,
    derivation_type: str,
    lineage_index: dict[str, dict[str, Any]] | None = None,
    explicit_root_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Resolve a bounded derivation lineage envelope without inferring causality.

    Parent links mean derivation/projection ancestry only. They never mean temporal
    order, causal influence, tactical explanation, or independent support.
    Missing parents remain unresolved; roots are never fabricated.
    """
    node_id = _clean(object_id)
    parents = _refs(parent_refs)
    explicit_roots = _refs(explicit_root_refs)
    dtype = _clean(derivation_type).upper()
    index = lineage_index if isinstance(lineage_index, dict) else {}

    base = {
        "module_id": MODULE_ID,
        "object_id": node_id or None,
        "parent_refs": parents,
        "derivation_type": dtype or None,
        "parent_relation_is_causality": False,
        "parent_relation_is_temporal_order": False,
        "shared_root_is_independent_support": False,
        "lineage_can_strengthen_claim_ceiling": False,
        "lineage_creates_new_evidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    if not node_id:
        return {**base, "status": "FAIL_CLOSED", "reason": "OBJECT_ID_MISSING", "root_refs": [], "lineage_group_id": None}
    if dtype not in ALLOWED_DERIVATION_TYPES:
        return {**base, "status": "FAIL_CLOSED", "reason": "DERIVATION_TYPE_NOT_ALLOWLISTED", "root_refs": [], "lineage_group_id": None}
    if node_id in parents:
        return {**base, "status": "FAIL_CLOSED", "reason": "SELF_PARENT_CYCLE", "root_refs": [], "lineage_group_id": None}

    visiting: set[str] = set()
    visited: set[str] = set()
    unresolved: set[str] = set()
    roots: set[str] = set(explicit_roots)

    def walk(ref: str) -> bool:
        if ref == node_id or ref in visiting:
            return False
        if ref in visited:
            return True
        row = index.get(ref)
        if not isinstance(row, dict):
            unresolved.add(ref)
            return True
        visiting.add(ref)
        row_parents = _refs(row.get("parent_refs"))
        row_roots = _refs(row.get("root_refs"))
        row_type = _clean(row.get("derivation_type")).upper()
        if row_type and row_type not in ALLOWED_DERIVATION_TYPES:
            visiting.remove(ref)
            return False
        if row_roots:
            roots.update(row_roots)
        if not row_parents and not row_roots:
            # A parent with no further parents is a root only when explicitly marked OBSERVED.
            if row_type == "OBSERVED":
                roots.add(ref)
            else:
                unresolved.add(ref)
        for parent in row_parents:
            if not walk(parent):
                visiting.remove(ref)
                return False
        visiting.remove(ref)
        visited.add(ref)
        return True

    for parent in parents:
        if not walk(parent):
            return {**base, "status": "FAIL_CLOSED", "reason": "LINEAGE_CYCLE_DETECTED", "root_refs": [], "lineage_group_id": None}

    root_refs = sorted(roots)
    unresolved_refs = sorted(unresolved)
    if unresolved_refs:
        status = "REVIEW_REQUIRED"
        reason = "LINEAGE_PARENT_OR_ROOT_UNRESOLVED"
    elif not root_refs and dtype == "OBSERVED" and not parents:
        root_refs = [node_id]
        status = "PASS"
        reason = None
    elif not root_refs:
        status = "REVIEW_REQUIRED"
        reason = "LINEAGE_ROOT_UNRESOLVED"
    else:
        status = "PASS"
        reason = None

    return {
        **base,
        "status": status,
        "reason": reason,
        "root_refs": root_refs,
        "unresolved_lineage_refs": unresolved_refs,
        "lineage_group_id": _group_id(root_refs) if status == "PASS" else None,
    }


def lineage_independent_support_count(lineage_envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    """Count distinct proven root groups only; unresolved lineage cannot add support."""
    groups: set[str] = set()
    unresolved_count = 0
    for row in lineage_envelopes or []:
        if not isinstance(row, dict):
            unresolved_count += 1
            continue
        if row.get("status") != "PASS":
            unresolved_count += 1
            continue
        group_id = _clean(row.get("lineage_group_id"))
        if group_id:
            groups.add(group_id)
        else:
            unresolved_count += 1
    return {
        "lineage_independent_support_count": len(groups),
        "lineage_group_ids": sorted(groups),
        "unresolved_lineage_candidate_count": unresolved_count,
        "shared_root_candidates_collapsed": True,
        "lineage_count_can_exceed_input_candidate_count": False,
        "lineage_count_can_strengthen_existing_independent_support": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
