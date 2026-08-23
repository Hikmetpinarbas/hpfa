from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "trackable_action_trace_candidates_lite_v1"
ACTION_MODULE_ID = "semantic_role_action_bundle_candidates_lite_v1"
TAXONOMY_MODULE_ID = "action_bundle_multi_family_review_taxonomy_lite_v1"
RELATION_MODULE_ID = "cross_role_relation_candidate_resolver_lite_v1"
EVIDENCE_MODULE_ID = "evidence_atom_inventory_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "TRACKABLE_ACTION_TRACE_CANDIDATE_ONLY"

PRIMARY_SOURCE_ROLES = {
    "PLAYER_SURFACE_CANDIDATE",
    "GOALKEEPER_SURFACE_CANDIDATE",
}
TEAM_SOURCE_ROLE = "TEAM_SURFACE_CANDIDATE"
ALLOWED_SOURCE_ROLES = PRIMARY_SOURCE_ROLES | {TEAM_SOURCE_ROLE}

OUTPUTS = {
    "json": "trackable_action_trace_candidates_lite_v1.json",
    "summary": "trackable_action_trace_candidates_lite_v1.txt",
    "analyst": "trackable_action_trace_candidates_analyst_audit_v1.txt",
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _number_key(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    try:
        return f"{float(text):.6f}"
    except (TypeError, ValueError):
        return text


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _core_key(record: dict[str, Any]) -> tuple[str, ...]:
    return (
        _clean(record.get("match_surface_binding_id")),
        _clean(record.get("source_role")),
        _clean(record.get("team_identity_candidate_id")),
        _clean(record.get("actor_identity_candidate_id")),
        _clean(record.get("period_candidate")),
        _number_key(record.get("start_candidate")),
        _number_key(record.get("end_candidate")),
        _number_key(record.get("pos_x_candidate")),
        _number_key(record.get("pos_y_candidate")),
    )


def _selection_record(
    bundle: dict[str, Any],
    state: str,
    basis: str,
    relation: dict[str, Any] | None = None,
    taxonomy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "action_bundle_candidate_id": bundle.get("action_bundle_candidate_id"),
        "match_surface_binding_id": bundle.get("match_surface_binding_id"),
        "source_role": bundle.get("source_role"),
        "team_identity_candidate_id": bundle.get("team_identity_candidate_id"),
        "actor_identity_candidate_id": bundle.get("actor_identity_candidate_id"),
        "period_candidate": bundle.get("period_candidate"),
        "start_candidate": bundle.get("start_candidate"),
        "end_candidate": bundle.get("end_candidate"),
        "pos_x_candidate": bundle.get("pos_x_candidate"),
        "pos_y_candidate": bundle.get("pos_y_candidate"),
        "coordinate_evidence_status": bundle.get("coordinate_evidence_status"),
        "action_family_candidate": bundle.get("action_family_candidate"),
        "bundle_status": bundle.get("bundle_status"),
        "supporting_evidence_atom_ids": list(bundle.get("supporting_evidence_atom_ids") or []),
        "provider_row_id_candidates": list(bundle.get("provider_row_id_candidates") or []),
        "raw_labels": list(bundle.get("raw_labels") or []),
        "normalized_labels": list(bundle.get("normalized_labels") or []),
        "selection_state": state,
        "selection_basis": basis,
        "supporting_relation_candidate_id": (
            relation.get("resolved_relation_candidate_id") if relation else None
        ),
        "relation_classification": (
            relation.get("relation_classification") if relation else None
        ),
        "reflection_action_bundle_candidate_id": (
            relation.get("reflection_action_bundle_candidate_id") if relation else None
        ),
        "supporting_taxonomy_record_id": (
            taxonomy.get("multi_family_review_record_id") if taxonomy else None
        ),
        "trackable_action_candidate_is_event_truth": False,
        "physical_action_identity_truth": False,
        "event_instance_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "claim_ceiling": CLAIM_CEILING,
    }


def _validate_inputs(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
    relation_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> tuple[
    list[str],
    list[str],
    str,
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    blocks: list[str] = []
    reviews: list[str] = []
    expected_modules = {
        "action": (action_payload, ACTION_MODULE_ID),
        "taxonomy": (taxonomy_payload, TAXONOMY_MODULE_ID),
        "relation": (relation_payload, RELATION_MODULE_ID),
        "evidence": (evidence_payload, EVIDENCE_MODULE_ID),
    }
    for name, (payload, module_id) in expected_modules.items():
        if payload.get("module_id") != module_id:
            blocks.append(f"{name}_module_id_mismatch")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")
        status = str(payload.get("module_status") or payload.get("status") or "UNKNOWN")
        if status == "FAIL_CLOSED":
            blocks.append(f"{name}_input_fail_closed")
        elif status == "REVIEW_REQUIRED":
            reviews.append(f"{name}_upstream_review_required")
        elif status != "PASS":
            reviews.append(f"{name}_upstream_status_review:{status}")

    bindings = {
        _clean(payload.get("match_surface_binding_id"))
        for payload, _ in expected_modules.values()
    }
    bindings.discard("")
    if len(bindings) != 1:
        blocks.append("match_surface_binding_mismatch")
    binding = next(iter(bindings), "")

    atoms = evidence_payload.get("evidence_atoms") or []
    bundles = action_payload.get("action_bundle_candidates") or []
    taxonomy_records = taxonomy_payload.get("multi_family_review_records") or []
    relations = relation_payload.get("resolved_relation_candidates") or []
    inventories = (
        (atoms, evidence_payload.get("evidence_atom_count"), "evidence_atom"),
        (bundles, action_payload.get("action_bundle_candidate_count"), "action_bundle"),
        (taxonomy_records, taxonomy_payload.get("multi_family_review_core_count"), "taxonomy"),
        (relations, relation_payload.get("resolved_relation_candidate_count"), "relation"),
    )
    for rows, declared, name in inventories:
        if not isinstance(rows, list):
            blocks.append(f"{name}_inventory_invalid")
        elif declared != len(rows):
            blocks.append(f"{name}_count_mismatch")

    atom_by_id: dict[str, dict[str, Any]] = {}
    for index, atom in enumerate(atoms if isinstance(atoms, list) else []):
        if not isinstance(atom, dict):
            blocks.append(f"evidence_atom_record_invalid:{index}")
            continue
        atom_id = _clean(atom.get("evidence_atom_id"))
        if not atom_id or atom_id in atom_by_id:
            blocks.append(f"evidence_atom_id_invalid_or_duplicate:{index}")
        if atom.get("match_surface_binding_id") != binding:
            blocks.append(f"evidence_atom_binding_mismatch:{index}")
        if atom.get("source_role") not in ALLOWED_SOURCE_ROLES:
            blocks.append(f"evidence_atom_source_role_rejected:{index}")
        if atom.get("event_instance_allowed") is True or atom.get("validated_event_identity") is True:
            blocks.append(f"evidence_atom_event_truth_boundary_breached:{index}")
        atom_by_id[atom_id] = atom

    bundle_by_id: dict[str, dict[str, Any]] = {}
    for index, bundle in enumerate(bundles if isinstance(bundles, list) else []):
        if not isinstance(bundle, dict):
            blocks.append(f"action_bundle_record_invalid:{index}")
            continue
        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        if not bundle_id or bundle_id in bundle_by_id:
            blocks.append(f"action_bundle_id_invalid_or_duplicate:{index}")
        role = _clean(bundle.get("source_role"))
        if role not in ALLOWED_SOURCE_ROLES:
            blocks.append(f"action_bundle_source_role_rejected:{index}")
        if bundle.get("match_surface_binding_id") != binding:
            blocks.append(f"action_bundle_binding_mismatch:{index}")
        if bundle.get("bundle_status") not in {"PASS", "REVIEW_REQUIRED"}:
            blocks.append(f"action_bundle_status_rejected:{index}")
        if bundle.get("cross_role_fusion_allowed") is True:
            blocks.append(f"action_bundle_cross_role_fusion_claimed:{index}")
        if bundle.get("event_instance_allowed") is True or bundle.get("validated_event_identity") is True:
            blocks.append(f"action_bundle_event_truth_boundary_breached:{index}")
        evidence_ids = [_clean(item) for item in (bundle.get("supporting_evidence_atom_ids") or [])]
        if not evidence_ids or not all(evidence_ids):
            blocks.append(f"action_bundle_evidence_ids_invalid:{index}")
        for evidence_id in evidence_ids:
            atom = atom_by_id.get(evidence_id)
            if atom is None:
                blocks.append(f"action_bundle_evidence_reference_missing:{bundle_id}:{evidence_id}")
            elif _clean(atom.get("source_role")) != role:
                blocks.append(f"action_bundle_evidence_source_role_mismatch:{bundle_id}:{evidence_id}")
        bundle_by_id[bundle_id] = bundle

    taxonomy_by_bundle: dict[str, dict[str, Any]] = {}
    taxonomy_by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(taxonomy_records if isinstance(taxonomy_records, list) else []):
        if not isinstance(record, dict):
            blocks.append(f"taxonomy_record_invalid:{index}")
            continue
        record_id = _clean(record.get("multi_family_review_record_id"))
        if not record_id or record_id in taxonomy_by_id:
            blocks.append(f"taxonomy_record_id_invalid_or_duplicate:{index}")
        if record.get("match_surface_binding_id") != binding:
            blocks.append(f"taxonomy_binding_mismatch:{index}")
        if record.get("record_status") not in {"PASS_CANDIDATE_CLASSIFICATION", "REVIEW_REQUIRED"}:
            blocks.append(f"taxonomy_status_rejected:{index}")
        if record.get("classification_is_event_truth") is True or record.get("event_instance_allowed") is True:
            blocks.append(f"taxonomy_event_truth_boundary_breached:{index}")
        taxonomy_by_id[record_id] = record
        for raw_bundle_id in record.get("supporting_action_bundle_candidate_ids") or []:
            bundle_id = _clean(raw_bundle_id)
            if bundle_id not in bundle_by_id:
                blocks.append(f"taxonomy_bundle_reference_missing:{record_id}:{bundle_id}")
                continue
            if bundle_id in taxonomy_by_bundle:
                blocks.append(f"taxonomy_bundle_mapped_multiple_times:{bundle_id}")
            taxonomy_by_bundle[bundle_id] = record

    review_bundle_ids = {
        bundle_id
        for bundle_id, bundle in bundle_by_id.items()
        if bundle.get("bundle_status") == "REVIEW_REQUIRED"
    }
    if set(taxonomy_by_bundle) != review_bundle_ids:
        blocks.append("taxonomy_review_bundle_coverage_mismatch")

    relation_by_id: dict[str, dict[str, Any]] = {}
    relation_by_bundle: dict[str, dict[str, Any]] = {}
    for index, relation in enumerate(relations if isinstance(relations, list) else []):
        if not isinstance(relation, dict):
            blocks.append(f"relation_record_invalid:{index}")
            continue
        relation_id = _clean(relation.get("resolved_relation_candidate_id"))
        if not relation_id or relation_id in relation_by_id:
            blocks.append(f"relation_id_invalid_or_duplicate:{index}")
        if relation.get("match_surface_binding_id") != binding:
            blocks.append(f"relation_binding_mismatch:{index}")
        if relation.get("relation_record_status") not in {"PASS_CANDIDATE_CLASSIFICATION", "REVIEW_REQUIRED"}:
            blocks.append(f"relation_status_rejected:{index}")
        if relation.get("relation_candidate_is_event_truth") is True:
            blocks.append(f"relation_event_truth_claimed:{index}")
        if relation.get("reflection_equivalence_truth") is True:
            blocks.append(f"relation_reflection_equivalence_claimed:{index}")
        if relation.get("double_count_suppression_is_final") is True:
            blocks.append(f"relation_final_suppression_claimed:{index}")
        if relation.get("count_value_output_allowed") is True:
            blocks.append(f"relation_count_output_claimed:{index}")
        if relation.get("cross_role_fusion_allowed") is True:
            blocks.append(f"relation_cross_role_fusion_claimed:{index}")
        primary_id = _clean(relation.get("primary_action_bundle_candidate_id"))
        reflection_id = _clean(relation.get("reflection_action_bundle_candidate_id"))
        if not primary_id or not reflection_id or primary_id == reflection_id:
            blocks.append(f"relation_bundle_ids_invalid:{relation_id}")
            continue
        primary = bundle_by_id.get(primary_id)
        reflection = bundle_by_id.get(reflection_id)
        if primary is None or reflection is None:
            blocks.append(f"relation_bundle_reference_missing:{relation_id}")
            continue
        if _clean(primary.get("source_role")) not in PRIMARY_SOURCE_ROLES:
            blocks.append(f"relation_primary_role_rejected:{relation_id}")
        if _clean(reflection.get("source_role")) != TEAM_SOURCE_ROLE:
            blocks.append(f"relation_reflection_role_rejected:{relation_id}")
        if not _clean(primary.get("actor_identity_candidate_id")):
            blocks.append(f"relation_primary_actor_missing:{relation_id}")
        if _clean(reflection.get("actor_identity_candidate_id")):
            blocks.append(f"relation_team_reflection_actor_present:{relation_id}")
        for bundle_id in (primary_id, reflection_id):
            if bundle_id in relation_by_bundle:
                blocks.append(f"relation_bundle_reused:{bundle_id}")
            relation_by_bundle[bundle_id] = relation
        relation_by_id[relation_id] = relation

    return (
        sorted(set(blocks)),
        sorted(set(reviews)),
        binding,
        atom_by_id,
        bundle_by_id,
        taxonomy_by_bundle,
        relation_by_bundle,
    )


def build_trackable_action_trace_candidates(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
    relation_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> dict[str, Any]:
    (
        blocks,
        reviews,
        binding,
        atom_by_id,
        bundle_by_id,
        taxonomy_by_bundle,
        relation_by_bundle,
    ) = _validate_inputs(action_payload, taxonomy_payload, relation_payload, evidence_payload)

    selected: list[dict[str, Any]] = []
    reflection_context: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []

    if not blocks:
        for bundle_id in sorted(bundle_by_id):
            bundle = bundle_by_id[bundle_id]
            role = _clean(bundle.get("source_role"))
            relation = relation_by_bundle.get(bundle_id)
            taxonomy = taxonomy_by_bundle.get(bundle_id)

            if relation is not None:
                primary_id = _clean(relation.get("primary_action_bundle_candidate_id"))
                reflection_id = _clean(relation.get("reflection_action_bundle_candidate_id"))
                relation_status = relation.get("relation_record_status")
                if relation_status == "PASS_CANDIDATE_CLASSIFICATION":
                    if bundle_id == primary_id:
                        if relation.get("double_count_suppression_candidate_state") != "CANDIDATE_PRIMARY_ROLE_ONLY":
                            blocks.append(f"clear_relation_primary_counting_candidate_state_invalid:{bundle_id}")
                            continue
                        basis = (
                            "CLEAR_CROSS_ROLE_PRIMARY_CLASSIFIED_CONTEXT"
                            if "CLASSIFIED_CONTEXT" in _clean(relation.get("relation_classification"))
                            else "CLEAR_CROSS_ROLE_PRIMARY_EXACT_CONTEXT"
                        )
                        selected.append(
                            _selection_record(
                                bundle,
                                "TRACKABLE_PRIMARY_SURFACE_CANDIDATE",
                                basis,
                                relation,
                                taxonomy,
                            )
                        )
                    elif bundle_id == reflection_id:
                        reflection_context.append(
                            _selection_record(
                                bundle,
                                "REFLECTION_CONTEXT_ONLY_CANDIDATE",
                                "CLEAR_CROSS_ROLE_TEAM_REFLECTION_CONTEXT",
                                relation,
                                taxonomy,
                            )
                        )
                    else:
                        blocks.append(f"relation_bundle_membership_inconsistent:{bundle_id}")
                else:
                    quarantined.append(
                        _selection_record(
                            bundle,
                            "QUARANTINED_UNRESOLVED_SURFACE",
                            "UNRESOLVED_CROSS_ROLE_RELATION_CONTEXT",
                            relation,
                            taxonomy,
                        )
                    )
                continue

            if role == TEAM_SOURCE_ROLE:
                quarantined.append(
                    _selection_record(
                        bundle,
                        "QUARANTINED_UNMATCHED_TEAM_CONTEXT",
                        "UNMATCHED_TEAM_SURFACE_NOT_PRIMARY_TRACE",
                        None,
                        taxonomy,
                    )
                )
                continue

            if role not in PRIMARY_SOURCE_ROLES:
                blocks.append(f"unregistered_primary_role:{bundle_id}")
                continue
            if not _clean(bundle.get("actor_identity_candidate_id")):
                blocks.append(f"standalone_primary_actor_missing:{bundle_id}")
                continue

            if bundle.get("bundle_status") == "PASS":
                selected.append(
                    _selection_record(
                        bundle,
                        "TRACKABLE_PRIMARY_SURFACE_CANDIDATE",
                        "STANDALONE_PRIMARY_PASS_BUNDLE",
                    )
                )
            elif taxonomy and taxonomy.get("record_status") == "PASS_CANDIDATE_CLASSIFICATION":
                selected.append(
                    _selection_record(
                        bundle,
                        "TRACKABLE_PRIMARY_SURFACE_CANDIDATE",
                        "CLASSIFIED_MULTI_FAMILY_PRIMARY_BUNDLE",
                        None,
                        taxonomy,
                    )
                )
            else:
                quarantined.append(
                    _selection_record(
                        bundle,
                        "QUARANTINED_UNRESOLVED_SURFACE",
                        "UNRESOLVED_MULTI_FAMILY_PRIMARY_CONTEXT",
                        None,
                        taxonomy,
                    )
                )

    blocks = sorted(set(blocks))
    all_partition_ids = [
        _clean(row.get("action_bundle_candidate_id"))
        for row in selected + reflection_context + quarantined
    ]
    if not blocks:
        if len(all_partition_ids) != len(bundle_by_id):
            blocks.append("selection_partition_count_mismatch")
        if set(all_partition_ids) != set(bundle_by_id):
            blocks.append("selection_partition_coverage_mismatch")
        if len(set(all_partition_ids)) != len(all_partition_ids):
            blocks.append("selection_partition_duplicate_assignment")

    trace_groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        trace_groups[_core_key(row)].append(row)

    trace_candidates: list[dict[str, Any]] = []
    if not blocks:
        for core, rows in sorted(trace_groups.items()):
            rows = sorted(rows, key=lambda item: _clean(item.get("action_bundle_candidate_id")))
            first = rows[0]
            role = _clean(first.get("source_role"))
            actor = _clean(first.get("actor_identity_candidate_id"))
            if role not in PRIMARY_SOURCE_ROLES or not actor:
                blocks.append("trace_primary_role_or_actor_invalid")
                continue

            bundle_ids = sorted(_clean(row.get("action_bundle_candidate_id")) for row in rows)
            families = sorted({_clean(row.get("action_family_candidate")) for row in rows})
            relation_ids = sorted(
                {
                    _clean(row.get("supporting_relation_candidate_id"))
                    for row in rows
                    if _clean(row.get("supporting_relation_candidate_id"))
                }
            )
            reflection_bundle_ids = sorted(
                {
                    _clean(row.get("reflection_action_bundle_candidate_id"))
                    for row in rows
                    if _clean(row.get("reflection_action_bundle_candidate_id"))
                }
            )
            taxonomy_ids = sorted(
                {
                    _clean(row.get("supporting_taxonomy_record_id"))
                    for row in rows
                    if _clean(row.get("supporting_taxonomy_record_id"))
                }
            )
            evidence_ids = sorted(
                {
                    _clean(evidence_id)
                    for row in rows
                    for evidence_id in (row.get("supporting_evidence_atom_ids") or [])
                    if _clean(evidence_id)
                }
            )
            provider_row_ids = sorted(
                {
                    _clean(provider_id)
                    for row in rows
                    for provider_id in (row.get("provider_row_id_candidates") or [])
                    if _clean(provider_id)
                }
            )
            raw_labels = sorted(
                {
                    _clean(label)
                    for row in rows
                    for label in (row.get("raw_labels") or [])
                    if _clean(label)
                }
            )
            normalized_labels = sorted(
                {
                    _clean(label)
                    for row in rows
                    for label in (row.get("normalized_labels") or [])
                    if _clean(label)
                }
            )

            primary_lineage: list[dict[str, Any]] = []
            seen_primary_lineage: set[str] = set()
            for evidence_id in evidence_ids:
                atom = atom_by_id.get(evidence_id)
                if atom is None:
                    blocks.append(f"trace_evidence_reference_missing:{evidence_id}")
                    continue
                for lineage in atom.get("source_lineage_records") or []:
                    if not isinstance(lineage, dict):
                        continue
                    signature = json.dumps(lineage, ensure_ascii=False, sort_keys=True)
                    if signature not in seen_primary_lineage:
                        seen_primary_lineage.add(signature)
                        primary_lineage.append(dict(lineage))

            reflection_evidence_ids: list[str] = []
            reflection_lineage: list[dict[str, Any]] = []
            seen_reflection_lineage: set[str] = set()
            for reflection_bundle_id in reflection_bundle_ids:
                reflection_bundle = bundle_by_id.get(reflection_bundle_id)
                if reflection_bundle is None:
                    blocks.append(f"trace_reflection_bundle_missing:{reflection_bundle_id}")
                    continue
                for evidence_id in reflection_bundle.get("supporting_evidence_atom_ids") or []:
                    evidence_id = _clean(evidence_id)
                    if evidence_id:
                        reflection_evidence_ids.append(evidence_id)
                    atom = atom_by_id.get(evidence_id)
                    if atom is None:
                        blocks.append(f"trace_reflection_evidence_missing:{evidence_id}")
                        continue
                    for lineage in atom.get("source_lineage_records") or []:
                        if not isinstance(lineage, dict):
                            continue
                        signature = json.dumps(lineage, ensure_ascii=False, sort_keys=True)
                        if signature not in seen_reflection_lineage:
                            seen_reflection_lineage.add(signature)
                            reflection_lineage.append(dict(lineage))

            trace_candidates.append(
                {
                    "trackable_action_trace_candidate_id": "tat_"
                    + _digest(binding, core, bundle_ids)[:24],
                    "match_surface_binding_id": binding,
                    "source_role": role,
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
                    "supporting_relation_candidate_ids": relation_ids,
                    "reflection_context_action_bundle_candidate_ids": reflection_bundle_ids,
                    "supporting_taxonomy_record_ids": taxonomy_ids,
                    "supporting_evidence_atom_ids": evidence_ids,
                    "reflection_evidence_atom_ids": sorted(set(reflection_evidence_ids)),
                    "provider_row_id_candidates": provider_row_ids,
                    "raw_labels": raw_labels,
                    "normalized_labels": normalized_labels,
                    "primary_source_lineage_records": primary_lineage,
                    "reflection_source_lineage_records": reflection_lineage,
                    "selection_bases": sorted({_clean(row.get("selection_basis")) for row in rows}),
                    "same_surface_multi_family_grouping_candidate": len(families) > 1,
                    "relation_support_visible": bool(relation_ids),
                    "team_reflection_context_visible": bool(reflection_bundle_ids),
                    "trace_count_is_physical_action_count": False,
                    "trackable_action_candidate_is_event_truth": False,
                    "physical_action_identity_truth": False,
                    "reflection_context_is_event_equivalence_truth": False,
                    "final_double_count_suppression_admitted": False,
                    "count_value_output_allowed": False,
                    "consequence_classification_allowed": False,
                    "sequence_link_allowed": False,
                    "same_time_order_truth_admitted": False,
                    "source_row_order_is_temporal_truth": False,
                    "event_instance_allowed": False,
                    "validated_event_identity": False,
                    "canonical_event_count": CANONICAL_EVENT_COUNT,
                    "claim_ceiling": CLAIM_CEILING,
                }
            )

    blocks = sorted(set(blocks))
    selected_basis_counts = Counter(row.get("selection_basis") for row in selected)
    quarantine_basis_counts = Counter(row.get("selection_basis") for row in quarantined)
    trace_role_counts = Counter(row.get("source_role") for row in trace_candidates)
    trace_family_count_counts = Counter(len(row.get("action_family_candidates") or []) for row in trace_candidates)
    relation_supported_trace_count = sum(bool(row.get("relation_support_visible")) for row in trace_candidates)
    standalone_trace_count = len(trace_candidates) - relation_supported_trace_count
    multi_family_trace_count = sum(
        bool(row.get("same_surface_multi_family_grouping_candidate")) for row in trace_candidates
    )

    if quarantined:
        reviews.append("quarantined_surface_candidates_present")
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "selection_records": {
            "selected_primary_surfaces": selected,
            "reflection_context_surfaces": reflection_context,
            "quarantined_surfaces": quarantined,
        },
        "source_action_bundle_candidate_count": len(bundle_by_id),
        "selected_primary_surface_candidate_count": len(selected),
        "reflection_context_surface_candidate_count": len(reflection_context),
        "quarantined_surface_candidate_count": len(quarantined),
        "selection_partition_coverage_count": len(all_partition_ids),
        "selection_partition_complete": (
            not blocks
            and len(all_partition_ids) == len(bundle_by_id)
            and len(set(all_partition_ids)) == len(bundle_by_id)
        ),
        "selected_surface_basis_counts": dict(sorted(selected_basis_counts.items())),
        "quarantine_basis_counts": dict(sorted(quarantine_basis_counts.items())),
        "trackable_action_trace_candidates": trace_candidates,
        "trackable_action_trace_candidate_count": len(trace_candidates),
        "relation_supported_trace_candidate_count": relation_supported_trace_count,
        "standalone_primary_trace_candidate_count": standalone_trace_count,
        "same_surface_multi_family_trace_candidate_count": multi_family_trace_count,
        "trace_source_role_counts": dict(sorted(trace_role_counts.items())),
        "trace_action_family_cardinality_counts": dict(sorted(trace_family_count_counts.items())),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "trackable_action_candidate_is_event_truth": False,
        "physical_action_identity_truth": False,
        "trace_count_is_physical_action_count": False,
        "reflection_context_is_event_equivalence_truth": False,
        "final_double_count_suppression_admitted": False,
        "count_value_output_allowed": False,
        "consequence_classification_allowed": False,
        "sequence_link_allowed": False,
        "same_time_order_truth_admitted": False,
        "source_row_order_is_temporal_truth": False,
        "cross_role_fusion_allowed": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / filename for key, filename in OUTPUTS.items()}
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = [
        "HPFA TRACKABLE ACTION TRACE CANDIDATES LITE V1",
        f"status={payload.get('status')}",
        f"source_action_bundle_candidate_count={payload.get('source_action_bundle_candidate_count')}",
        f"selected_primary_surface_candidate_count={payload.get('selected_primary_surface_candidate_count')}",
        f"reflection_context_surface_candidate_count={payload.get('reflection_context_surface_candidate_count')}",
        f"quarantined_surface_candidate_count={payload.get('quarantined_surface_candidate_count')}",
        f"trackable_action_trace_candidate_count={payload.get('trackable_action_trace_candidate_count')}",
        f"relation_supported_trace_candidate_count={payload.get('relation_supported_trace_candidate_count')}",
        f"standalone_primary_trace_candidate_count={payload.get('standalone_primary_trace_candidate_count')}",
        f"same_surface_multi_family_trace_candidate_count={payload.get('same_surface_multi_family_trace_candidate_count')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ]
    paths["summary"].write_text("\n".join(summary) + "\n", encoding="utf-8")
    analyst = [
        "HPFA ANALYST AUDIT — TRACKABLE ACTION TRACE CANDIDATES",
        f"Primary visible surfaces admitted as trackable candidates: {payload.get('selected_primary_surface_candidate_count', 0)}",
        f"TEAM reflection surfaces kept as context-only candidates: {payload.get('reflection_context_surface_candidate_count', 0)}",
        f"Unresolved or unmatched surfaces quarantined: {payload.get('quarantined_surface_candidate_count', 0)}",
        f"Trackable action trace candidates: {payload.get('trackable_action_trace_candidate_count', 0)}",
        f"Relation-supported trace candidates: {payload.get('relation_supported_trace_candidate_count', 0)}",
        f"Standalone primary trace candidates: {payload.get('standalone_primary_trace_candidate_count', 0)}",
        "Analyst-safe meaning: actor-bearing PLAYER/GK primary surfaces are traceable with exact TEAM reflection context where available.",
        "TEAM-only surfaces are never promoted to primary action traces at this layer.",
        "Trace candidates are not canonical events, physical-action truth or final counting units.",
        "No consequence or sequence link is admitted at this layer.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    paths["analyst"].write_text("\n".join(analyst) + "\n", encoding="utf-8")
    return paths
