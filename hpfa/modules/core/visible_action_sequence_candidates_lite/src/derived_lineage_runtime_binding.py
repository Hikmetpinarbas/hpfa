from __future__ import annotations

import copy
from collections import Counter, defaultdict
from typing import Any

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.derived_lineage_guard import (
    lineage_independent_support_count,
    resolve_lineage,
)

MODULE_ID = "derived_lineage_runtime_binding_v1"
ROOT_SCOPE = "BOUNDED_ADMITTED_OCCURRENCE_ANCESTRY_NOT_ABSOLUTE_EVIDENCE_ROOT"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _divergence_occurrence_ancestor_refs(row: dict[str, Any]) -> list[str]:
    refs: set[str] = set()
    for branch in row.get("branch_profiles") or []:
        if not isinstance(branch, dict):
            continue
        refs.update(_refs(branch.get("neighbor_supporting_action_occurrence_candidate_ids")))
    return sorted(refs)


def _root_envelope(divergence: dict[str, Any]) -> dict[str, Any]:
    divergence_id = _clean(divergence.get("first_supported_branch_divergence_id"))
    occurrence_ancestors = _divergence_occurrence_ancestor_refs(divergence)
    envelope = resolve_lineage(
        divergence_id,
        parent_refs=[],
        derivation_type="RELATE",
        explicit_root_refs=occurrence_ancestors,
    )
    envelope["lineage_root_scope"] = ROOT_SCOPE
    envelope["root_is_absolute_observation_or_evidence_root"] = False
    envelope["root_is_current_tracked_derived_chain_root"] = False
    envelope["root_is_bounded_admitted_occurrence_ancestor"] = bool(occurrence_ancestors)
    envelope["bounded_occurrence_ancestor_refs"] = occurrence_ancestors
    envelope["occurrence_ancestor_is_event_truth"] = False
    envelope["bounded_ancestry_proves_independence"] = False
    return envelope


def _child_envelope(
    object_id: str,
    parent_ref: str,
    derivation_type: str,
    lineage_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    envelope = resolve_lineage(
        object_id,
        parent_refs=[parent_ref] if parent_ref else [],
        derivation_type=derivation_type,
        lineage_index=lineage_index,
    )
    envelope["lineage_root_scope"] = ROOT_SCOPE
    envelope["root_is_absolute_observation_or_evidence_root"] = False
    envelope["root_is_current_tracked_derived_chain_root"] = False
    envelope["root_is_bounded_admitted_occurrence_ancestor"] = bool(envelope.get("root_refs"))
    envelope["bounded_occurrence_ancestor_refs"] = list(envelope.get("root_refs") or [])
    envelope["occurrence_ancestor_is_event_truth"] = False
    envelope["bounded_ancestry_proves_independence"] = False
    return envelope


def _annotate_shared_ancestor_overlap(
    divergence_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    ancestor_to_divergences: dict[str, set[str]] = defaultdict(set)
    resolved_ids: set[str] = set()
    unresolved_ids: set[str] = set()
    resolved_ancestry_edge_count = 0

    for row in divergence_rows:
        divergence_id = _clean(row.get("first_supported_branch_divergence_id"))
        envelope = row.get("derived_lineage") if isinstance(row.get("derived_lineage"), dict) else {}
        roots = _refs(envelope.get("root_refs"))
        if not divergence_id:
            continue
        if envelope.get("status") != "PASS" or not roots:
            unresolved_ids.add(divergence_id)
            row["shared_ancestor_overlap_state"] = "ANCESTRY_UNRESOLVED_REVIEW_REQUIRED"
            row["shared_ancestor_with_divergence_refs"] = []
            row["shared_ancestor_refs"] = []
            row["bounded_occurrence_ancestor_ref_count"] = 0
            row["shared_ancestor_ref_count"] = 0
            row["structural_multiplicity_is_independent_support"] = False
            row["bounded_ancestry_distinctness_is_independence_proof"] = False
            continue
        resolved_ids.add(divergence_id)
        resolved_ancestry_edge_count += len(roots)
        for root in roots:
            ancestor_to_divergences[root].add(divergence_id)

    divergence_by_id = {
        _clean(row.get("first_supported_branch_divergence_id")): row
        for row in divergence_rows
        if _clean(row.get("first_supported_branch_divergence_id"))
    }
    shared_ancestor_refs: set[str] = set()
    divergences_with_overlap: set[str] = set()

    for divergence_id in sorted(resolved_ids):
        row = divergence_by_id[divergence_id]
        envelope = row.get("derived_lineage") or {}
        roots = _refs(envelope.get("root_refs"))
        shared_with: set[str] = set()
        shared_refs_for_row: set[str] = set()
        for root in roots:
            peers = ancestor_to_divergences.get(root, set()) - {divergence_id}
            if peers:
                shared_with.update(peers)
                shared_refs_for_row.add(root)
                shared_ancestor_refs.add(root)
        if shared_with:
            divergences_with_overlap.add(divergence_id)
            row["shared_ancestor_overlap_state"] = "SHARED_ANCESTOR_OVERLAP"
        else:
            row["shared_ancestor_overlap_state"] = "NO_SHARED_ANCESTOR_WITHIN_TRACKED_SCOPE"
        row["shared_ancestor_with_divergence_refs"] = sorted(shared_with)
        row["shared_ancestor_refs"] = sorted(shared_refs_for_row)
        row["bounded_occurrence_ancestor_ref_count"] = len(roots)
        row["shared_ancestor_ref_count"] = len(shared_refs_for_row)
        row["structural_multiplicity_is_independent_support"] = False
        row["bounded_ancestry_distinctness_is_independence_proof"] = False
        row["shared_ancestor_can_add_independent_support"] = False

    reused_ancestry_edge_count = sum(
        max(0, len(divergence_ids) - 1)
        for divergence_ids in ancestor_to_divergences.values()
    )
    if not resolved_ancestry_edge_count:
        provenance_multiplicity_state = "NO_RESOLVED_ANCESTRY"
    elif reused_ancestry_edge_count:
        provenance_multiplicity_state = "ANCESTRY_REUSE_PRESENT"
    else:
        provenance_multiplicity_state = "NO_ANCESTRY_REUSE_WITHIN_TRACKED_SCOPE"

    return {
        "resolved_divergence_count": len(resolved_ids),
        "bounded_occurrence_ancestor_count": len(ancestor_to_divergences),
        "divergence_occurrence_ancestry_edge_count": resolved_ancestry_edge_count,
        "reused_occurrence_ancestry_edge_count": reused_ancestry_edge_count,
        "reused_occurrence_ancestry_edge_denominator": resolved_ancestry_edge_count,
        "provenance_multiplicity_state": provenance_multiplicity_state,
        "structural_multiplicity_equals_provenance_multiplicity": False,
        "structural_multiplicity_is_independent_support": False,
        "shared_occurrence_ancestor_count": len(shared_ancestor_refs),
        "divergence_with_shared_ancestor_count": len(divergences_with_overlap),
        "divergence_without_shared_ancestor_within_tracked_scope_count": len(
            resolved_ids - divergences_with_overlap
        ),
        "unresolved_divergence_ancestry_count": len(unresolved_ids),
        "shared_ancestor_overlap_detected": bool(shared_ancestor_refs),
        "bounded_ancestry_distinctness_is_independence_proof": False,
        "shared_ancestor_can_add_independent_support": False,
    }


def bind_derived_lineage(
    sequence_payload: dict[str, Any],
    puzzle_payload: dict[str, Any] | None,
    claim_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Attach bounded occurrence-ancestor lineage to current derived outputs.

    The current producer topology is not forced into a false linear chain. Divergence
    produces Safe Finding handoffs; Puzzle Finding and Analyst Claim contracts are sibling
    projections from that handoff. Existing admitted occurrence refs are used as bounded
    ancestors where available. Distinct bounded ancestry is never treated as proof of
    statistical or evidence independence, and shared ancestry can never add support.
    """
    sequence = copy.deepcopy(sequence_payload)
    puzzle = copy.deepcopy(puzzle_payload) if isinstance(puzzle_payload, dict) else {}
    claim = copy.deepcopy(claim_payload) if isinstance(claim_payload, dict) else {}

    lineage_index: dict[str, dict[str, Any]] = {}
    envelopes: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    review_hits: list[str] = []
    hard_blocks: list[str] = []

    divergences = []
    for row in sequence.get("first_supported_branch_divergence_candidates") or []:
        if not isinstance(row, dict):
            continue
        object_id = _clean(row.get("first_supported_branch_divergence_id"))
        if not object_id:
            continue
        envelope = _root_envelope(row)
        row["derived_lineage"] = envelope
        lineage_index[object_id] = envelope
        envelopes.append(envelope)
        status_counts[envelope.get("status") or "UNKNOWN"] += 1
        if envelope.get("status") == "FAIL_CLOSED":
            hard_blocks.append(f"divergence_lineage_fail_closed:{object_id}")
        elif envelope.get("status") != "PASS":
            review_hits.append(f"divergence_occurrence_ancestry_unresolved:{object_id}")
        divergences.append(row)
    overlap_summary = _annotate_shared_ancestor_overlap(divergences)
    sequence["first_supported_branch_divergence_candidates"] = divergences

    handoffs = []
    for row in sequence.get("safe_finding_handoff_candidates") or []:
        if not isinstance(row, dict):
            continue
        object_id = _clean(row.get("safe_finding_handoff_candidate_id"))
        parent_ref = _clean(row.get("source_first_supported_branch_divergence_ref"))
        envelope = _child_envelope(object_id, parent_ref, "PROJECT", lineage_index)
        row["derived_lineage"] = envelope
        lineage_index[object_id] = envelope
        envelopes.append(envelope)
        status_counts[envelope.get("status") or "UNKNOWN"] += 1
        if envelope.get("status") == "FAIL_CLOSED":
            hard_blocks.append(f"safe_finding_lineage_fail_closed:{object_id}")
        elif envelope.get("status") != "PASS":
            review_hits.append(f"safe_finding_lineage_unresolved:{object_id}")
        handoffs.append(row)
    sequence["safe_finding_handoff_candidates"] = handoffs

    findings = []
    finding_by_handoff: dict[str, list[str]] = {}
    for row in puzzle.get("puzzle_findings") or []:
        if not isinstance(row, dict):
            continue
        object_id = _clean(row.get("puzzle_finding_id"))
        parent_ref = _clean(row.get("source_safe_finding_handoff_ref"))
        dtype = "FILTER" if row.get("family_projection") else "PROJECT"
        envelope = _child_envelope(object_id, parent_ref, dtype, lineage_index)
        row["derived_lineage"] = envelope
        row["lineage_parent_is_safe_finding_handoff"] = True
        row["family_view_shares_source_lineage_root"] = row.get("family_projection") is not None
        row["shared_ancestor_can_add_independent_support"] = False
        lineage_index[object_id] = envelope
        envelopes.append(envelope)
        status_counts[envelope.get("status") or "UNKNOWN"] += 1
        if parent_ref and object_id:
            finding_by_handoff.setdefault(parent_ref, []).append(object_id)
        if envelope.get("status") == "FAIL_CLOSED":
            hard_blocks.append(f"puzzle_finding_lineage_fail_closed:{object_id}")
        elif envelope.get("status") != "PASS":
            review_hits.append(f"puzzle_finding_lineage_unresolved:{object_id}")
        findings.append(row)
    if findings or "puzzle_findings" in puzzle:
        puzzle["puzzle_findings"] = findings

    contracts = []
    for row in claim.get("analyst_output_contracts") or []:
        if not isinstance(row, dict):
            continue
        object_id = _clean(row.get("analyst_output_contract_id"))
        parent_ref = _clean(row.get("source_safe_finding_handoff_ref"))
        envelope = _child_envelope(object_id, parent_ref, "NARRATIVE", lineage_index)
        row["derived_lineage"] = envelope
        row["lineage_parent_is_safe_finding_handoff"] = True
        row["puzzle_sibling_refs"] = sorted(finding_by_handoff.get(parent_ref, []))
        row["puzzle_sibling_is_claim_parent"] = False
        row["shared_ancestor_can_add_independent_support"] = False
        lineage_index[object_id] = envelope
        envelopes.append(envelope)
        status_counts[envelope.get("status") or "UNKNOWN"] += 1
        if envelope.get("status") == "FAIL_CLOSED":
            hard_blocks.append(f"claim_lineage_fail_closed:{object_id}")
            row["professional_emit_allowed"] = False
            row["claim_scope"] = "NO_CLAIM_OUTPUT"
        elif envelope.get("status") != "PASS":
            review_hits.append(f"claim_lineage_unresolved:{object_id}")
            row["professional_emit_allowed"] = False
            row["claim_scope"] = "NO_CLAIM_OUTPUT"
        row["lineage_can_authorize_emit"] = False
        row["lineage_can_strengthen_claim_ceiling"] = False
        row["lineage_creates_new_evidence"] = False
        contracts.append(row)
    if contracts or "analyst_output_contracts" in claim:
        claim["analyst_output_contracts"] = contracts

    support_guard = lineage_independent_support_count(envelopes)
    result_status = "FAIL_CLOSED" if hard_blocks else "REVIEW_REQUIRED" if review_hits else "PASS"
    summary = {
        "module_id": MODULE_ID,
        "status": result_status,
        "tracked_object_count": len(envelopes),
        "lineage_status_counts": dict(sorted(status_counts.items())),
        "bounded_lineage_group_count": support_guard["lineage_independent_support_count"],
        "lineage_group_ids": support_guard["lineage_group_ids"],
        "unresolved_lineage_candidate_count": support_guard["unresolved_lineage_candidate_count"],
        "shared_root_candidates_collapsed": True,
        "lineage_root_scope": ROOT_SCOPE,
        "root_is_absolute_observation_or_evidence_root": False,
        "root_is_bounded_admitted_occurrence_ancestor": True,
        "current_topology": "BOUNDED_OCCURRENCE_ANCESTOR_TO_DIVERGENCE_TO_SAFE_FINDING_THEN_PUZZLE_AND_CLAIM_SIBLINGS",
        "puzzle_is_required_parent_of_claim": False,
        "lineage_group_count_is_admitted_independent_support_count": False,
        "bounded_ancestry_distinctness_is_independence_proof": False,
        "lineage_can_increase_existing_independent_support": False,
        "lineage_can_authorize_emit": False,
        "lineage_can_strengthen_claim_ceiling": False,
        "lineage_creates_new_evidence": False,
        **overlap_summary,
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    for payload in (sequence, puzzle, claim):
        if isinstance(payload, dict):
            payload["derived_lineage_runtime_binding"] = summary
            payload["derived_lineage_runtime_binding_consumed"] = True
            payload["canonical_event_count"] = "UNKNOWN"
            payload["true_action_count"] = "UNKNOWN"
            payload["production_release"] = False

    return {
        "status": result_status,
        "sequence_payload": sequence,
        "puzzle_payload": puzzle,
        "claim_payload": claim,
        "summary": summary,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
