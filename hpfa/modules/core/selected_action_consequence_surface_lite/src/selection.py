from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

try:
    from .common import (
        CANONICAL_EVENT_COUNT, SUPPORT_ATOM_CLASSES, bundle_core, clean, digest,
        number, selection_record, support_core, timeline_key,
    )
except ImportError:  # direct src-path test import
    from common import (
        CANONICAL_EVENT_COUNT, SUPPORT_ATOM_CLASSES, bundle_core, clean, digest,
        number, selection_record, support_core, timeline_key,
    )


def select_surfaces(
    bundles: list[dict[str, Any]],
    tax_records: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    binding: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    blocks: list[str] = []
    bundle_by_id: dict[str, dict[str, Any]] = {}
    for index, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            blocks.append(f"bundle_record_invalid:{index}")
            continue
        bundle_id = clean(bundle.get("action_bundle_candidate_id"))
        if not bundle_id or bundle_id in bundle_by_id:
            blocks.append(f"bundle_id_invalid_or_duplicate:{index}")
            continue
        if bundle.get("match_surface_binding_id") != binding:
            blocks.append(f"bundle_binding_mismatch:{bundle_id}")
        if bundle.get("bundle_status") not in {"PASS", "REVIEW_REQUIRED"}:
            blocks.append(f"bundle_status_invalid:{bundle_id}")
        if number(bundle.get("start_candidate")) is None or number(bundle.get("end_candidate")) is None:
            blocks.append(f"bundle_time_invalid:{bundle_id}")
        if bundle.get("cross_role_fusion_allowed") is True or bundle.get("event_instance_allowed") is True:
            blocks.append(f"bundle_truth_boundary_breached:{bundle_id}")
        bundle_by_id[bundle_id] = bundle

    tax_by_bundle: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(tax_records):
        if not isinstance(record, dict):
            blocks.append(f"taxonomy_record_invalid:{index}")
            continue
        if record.get("record_status") not in {"PASS_CANDIDATE_CLASSIFICATION", "REVIEW_REQUIRED"}:
            blocks.append(f"taxonomy_status_invalid:{index}")
        for raw_id in record.get("supporting_action_bundle_candidate_ids") or []:
            bundle_id = clean(raw_id)
            if bundle_id not in bundle_by_id or bundle_id in tax_by_bundle:
                blocks.append(f"taxonomy_bundle_mapping_invalid:{bundle_id}")
            tax_by_bundle[bundle_id] = record

    clear_primary: dict[str, dict[str, Any]] = {}
    clear_reflection: dict[str, dict[str, Any]] = {}
    unresolved: set[str] = set()
    for index, record in enumerate(relations):
        if not isinstance(record, dict):
            blocks.append(f"relation_record_invalid:{index}")
            continue
        status = record.get("relation_record_status")
        primary = clean(record.get("primary_action_bundle_candidate_id"))
        reflection = clean(record.get("reflection_action_bundle_candidate_id"))
        relation_id = clean(record.get("resolved_relation_candidate_id"))
        if status not in {"PASS_CANDIDATE_CLASSIFICATION", "REVIEW_REQUIRED"}:
            blocks.append(f"relation_status_invalid:{relation_id}")
        if primary not in bundle_by_id or reflection not in bundle_by_id:
            blocks.append(f"relation_bundle_reference_missing:{relation_id}")
            continue
        if status == "PASS_CANDIDATE_CLASSIFICATION":
            if primary in clear_primary or primary in clear_reflection or reflection in clear_primary or reflection in clear_reflection:
                blocks.append(f"relation_bundle_reuse:{relation_id}")
            clear_primary[primary] = record
            clear_reflection[reflection] = record
        else:
            unresolved.update({primary, reflection})

    selected: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    if blocks:
        return selected, suppressed, quarantined, sorted(set(blocks))
    for bundle_id in sorted(bundle_by_id):
        bundle = bundle_by_id[bundle_id]
        tax = tax_by_bundle.get(bundle_id)
        tax_id = clean(tax.get("multi_family_review_record_id")) if tax else None
        if bundle_id in clear_primary:
            record = clear_primary[bundle_id]
            selected.append(selection_record(bundle, "SELECTED_ACTION_SURFACE_CANDIDATE", "CLEAR_CROSS_ROLE_PRIMARY_SURFACE", clean(record.get("resolved_relation_candidate_id")), tax_id))
        elif bundle_id in clear_reflection:
            record = clear_reflection[bundle_id]
            suppressed.append(selection_record(bundle, "SUPPRESSED_TEAM_REFLECTION_CANDIDATE", "CLEAR_CROSS_ROLE_REFLECTION_SURFACE", clean(record.get("resolved_relation_candidate_id")), tax_id))
        elif bundle_id in unresolved:
            quarantined.append(selection_record(bundle, "QUARANTINED_UNRESOLVED_ACTION_SURFACE", "UNRESOLVED_CROSS_ROLE_RELATION_CONTEXT", None, tax_id))
        elif bundle.get("bundle_status") == "PASS":
            selected.append(selection_record(bundle, "SELECTED_ACTION_SURFACE_CANDIDATE", "STANDALONE_PASS_BUNDLE"))
        elif tax and tax.get("record_status") == "PASS_CANDIDATE_CLASSIFICATION":
            selected.append(selection_record(bundle, "SELECTED_ACTION_SURFACE_CANDIDATE", "CLASSIFIED_MULTI_FAMILY_BUNDLE", None, tax_id))
        else:
            quarantined.append(selection_record(bundle, "QUARANTINED_UNRESOLVED_ACTION_SURFACE", "UNRESOLVED_MULTI_FAMILY_CONTEXT", None, tax_id))
    ids = [clean(row.get("action_bundle_candidate_id")) for row in selected + suppressed + quarantined]
    if len(ids) != len(bundle_by_id) or set(ids) != set(bundle_by_id):
        blocks.append("selection_partition_mismatch")
    return selected, suppressed, quarantined, sorted(set(blocks))


def build_nodes(selected: list[dict[str, Any]], binding: str, atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in selected:
        groups[bundle_core(record)].append(record)
    support: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for atom in atoms:
        if isinstance(atom, dict) and atom.get("atom_class") in SUPPORT_ATOM_CLASSES and atom.get("atom_status") == "PASS":
            support[support_core(atom)].append(atom)
    nodes: list[dict[str, Any]] = []
    for _, rows in sorted(groups.items()):
        rows = sorted(rows, key=lambda row: clean(row.get("action_bundle_candidate_id")))
        first = rows[0]
        families = sorted({clean(row.get("action_family_candidate")) for row in rows})
        bundle_ids = sorted(clean(row.get("action_bundle_candidate_id")) for row in rows)
        node = {
            "selected_action_node_id": "sacn_" + digest(binding, bundle_core(first), bundle_ids)[:24],
            "match_surface_binding_id": binding,
            "source_role": first.get("source_role"),
            "team_identity_candidate_id": first.get("team_identity_candidate_id"),
            "actor_identity_candidate_id": first.get("actor_identity_candidate_id"),
            "period_candidate": first.get("period_candidate"),
            "start_candidate": first.get("start_candidate"),
            "end_candidate": first.get("end_candidate"),
            "pos_x_candidate": first.get("pos_x_candidate"),
            "pos_y_candidate": first.get("pos_y_candidate"),
            "coordinate_evidence_status": first.get("coordinate_evidence_status"),
            "action_family_candidates": families,
            "selected_action_bundle_candidate_ids": bundle_ids,
            "selection_bases": sorted({clean(row.get("selection_basis")) for row in rows}),
            "same_time_multi_family_grouping": len(families) > 1,
            "selected_surface_is_canonical_event": False,
            "event_instance_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
        }
        exact_support = support.get(support_core(node), [])
        class_counts = Counter(clean(atom.get("atom_class")) for atom in exact_support)
        node.update(
            {
                "supporting_evidence_atom_ids": sorted(clean(atom.get("evidence_atom_id")) for atom in exact_support),
                "support_atom_class_counts": dict(sorted(class_counts.items())),
                "support_normalized_labels": sorted({clean(atom.get("normalized_label")) for atom in exact_support if clean(atom.get("normalized_label"))}),
                "terminal_outcome_support_visible": class_counts.get("TERMINAL_OUTCOME_ATOM", 0) > 0,
                "derived_consequence_support_visible": class_counts.get("DERIVED_CONSEQUENCE_ATOM", 0) > 0,
            }
        )
        nodes.append(node)
    return sorted(nodes, key=timeline_key)
