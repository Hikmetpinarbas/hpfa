from __future__ import annotations

from collections import Counter
from typing import Any

FINDING_MODULE_ID = "professional_finding_candidate_lite_v1"
RECIPROCAL_MODULE_ID = "reciprocal_process_chain_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
EVIDENCE_MODULE_ID = "evidence_atom_inventory_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _validate(label: str, payload: dict[str, Any], module_id: str) -> list[str]:
    blocks: list[str] = []
    if payload.get("module_id") != module_id:
        blocks.append(f"{label}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{label}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append(f"{label}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{label}_production_release_claimed")
    if _status(payload.get("status") or payload.get("module_status")) == "FAIL_CLOSED":
        blocks.append(f"{label}_input_fail_closed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{label}_hard_blocks_present")
    return blocks


def attach_duplicate_reflection_risk(
    finding_payload: dict[str, Any],
    reciprocal_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> dict[str, Any]:
    """Audit nominal support inflation using existing trace->Evidence Atom lineage.

    No new deduplication truth is invented. Explicit serialization-reflection dependency
    from Evidence Atom is preserved, repeated memberships are collapsed for accounting,
    and independence-unknown atoms remain review debt. Counts are not canonical events.
    """
    blocks: list[str] = []
    for label, payload, module_id in (
        ("finding", finding_payload, FINDING_MODULE_ID),
        ("reciprocal", reciprocal_payload, RECIPROCAL_MODULE_ID),
        ("trace", trace_payload, TRACE_MODULE_ID),
        ("evidence", evidence_payload, EVIDENCE_MODULE_ID),
    ):
        blocks.extend(_validate(label, payload, module_id))

    result = dict(finding_payload)
    rows = [dict(row) for row in (finding_payload.get("professional_finding_candidates") or []) if isinstance(row, dict)]
    result["professional_finding_candidates"] = rows
    if blocks:
        result["status"] = "FAIL_CLOSED"
        result["duplicate_reflection_risk_status"] = "FAIL_CLOSED"
        result["hard_block_hits"] = sorted(set((finding_payload.get("hard_block_hits") or []) + blocks))
        result["claim_output_allowed_count"] = 0
        result["professional_finding_emitted_count"] = 0
        result["canonical_event_count"] = CANONICAL_EVENT_COUNT
        result["true_action_count"] = TRUE_ACTION_COUNT
        result["production_release"] = False
        return result

    chain_by_id = {
        _clean(row.get("reciprocal_process_chain_candidate_id")): row
        for row in (reciprocal_payload.get("reciprocal_process_chain_candidates") or [])
        if isinstance(row, dict) and _clean(row.get("reciprocal_process_chain_candidate_id"))
    }
    trace_by_id = {
        _clean(row.get("trackable_action_trace_candidate_id")): row
        for row in (trace_payload.get("trackable_action_trace_candidates") or [])
        if isinstance(row, dict) and _clean(row.get("trackable_action_trace_candidate_id"))
    }
    atom_by_id = {
        _clean(row.get("evidence_atom_id")): row
        for row in (evidence_payload.get("evidence_atoms") or [])
        if isinstance(row, dict) and _clean(row.get("evidence_atom_id"))
    }

    dependent_present = 0
    unknown_independence = 0
    membership_reuse = 0

    for finding in rows:
        support = finding.get("support") if isinstance(finding.get("support"), dict) else {}
        chain_ids = [
            _clean(value)
            for value in (support.get("supporting_reciprocal_process_chain_candidate_ids") or [])
            if _clean(value)
        ]
        trace_ids: set[str] = set()
        missing_chain_ids: list[str] = []
        for chain_id in chain_ids:
            chain = chain_by_id.get(chain_id)
            if not isinstance(chain, dict):
                missing_chain_ids.append(chain_id)
                continue
            trace_ids.update(
                _clean(value)
                for value in (chain.get("supporting_trackable_action_trace_candidate_ids") or [])
                if _clean(value)
            )

        atom_memberships: list[str] = []
        reflection_context_memberships: list[str] = []
        missing_trace_ids: list[str] = []
        for trace_id in sorted(trace_ids):
            trace = trace_by_id.get(trace_id)
            if not isinstance(trace, dict):
                missing_trace_ids.append(trace_id)
                continue
            atom_memberships.extend(
                _clean(value) for value in (trace.get("supporting_evidence_atom_ids") or []) if _clean(value)
            )
            reflection_context_memberships.extend(
                _clean(value) for value in (trace.get("reflection_evidence_atom_ids") or []) if _clean(value)
            )

        all_memberships = atom_memberships + reflection_context_memberships
        membership_counts = Counter(all_memberships)
        unique_atom_ids = sorted(membership_counts)
        repeated_atom_ids = sorted(atom_id for atom_id, count in membership_counts.items() if count > 1)
        missing_atom_ids = sorted(atom_id for atom_id in unique_atom_ids if atom_id not in atom_by_id)

        dependent_atom_ids: list[str] = []
        unknown_atom_ids: list[str] = []
        row_nucleus_ids: set[str] = set()
        source_sha_lineage: set[str] = set()
        for atom_id in unique_atom_ids:
            atom = atom_by_id.get(atom_id)
            if not isinstance(atom, dict):
                continue
            nucleus_id = _clean(atom.get("row_nucleus_candidate_id"))
            if nucleus_id:
                row_nucleus_ids.add(nucleus_id)
            source_sha_lineage.update(
                _clean(value) for value in (atom.get("source_sha256_lineage") or []) if _clean(value)
            )
            dep_state = _clean(atom.get("reflection_dependency_state"))
            if dep_state == "DEPENDENT_SERIALIZATION_REFLECTION":
                dependent_atom_ids.append(atom_id)
            elif dep_state == "INDEPENDENCE_UNKNOWN_REVIEW_REQUIRED" or not dep_state:
                unknown_atom_ids.append(atom_id)

        if missing_chain_ids or missing_trace_ids or missing_atom_ids:
            state = "PARTIAL_REFLECTION_LINEAGE_COVERAGE_REVIEW_REQUIRED"
        elif dependent_atom_ids or repeated_atom_ids or reflection_context_memberships:
            state = "DEPENDENT_OR_REUSED_REFLECTION_SUPPORT_PRESENT"
            dependent_present += 1
        elif unknown_atom_ids:
            state = "INDEPENDENCE_UNKNOWN_REVIEW_REQUIRED"
            unknown_independence += 1
        else:
            state = "NO_DUPLICATE_MEMBERSHIP_VISIBLE_CURRENT_EXPLICIT_LINEAGE_SCOPE"

        if repeated_atom_ids:
            membership_reuse += 1

        audit = {
            "state_candidate": state,
            "supporting_trace_candidate_count": len(trace_ids),
            "nominal_evidence_atom_membership_count": len(all_memberships),
            "unique_evidence_atom_candidate_count": len(unique_atom_ids),
            "unique_row_nucleus_candidate_count": len(row_nucleus_ids),
            "unique_source_sha_lineage_count": len(source_sha_lineage),
            "dependent_serialization_reflection_atom_ids": sorted(dependent_atom_ids),
            "independence_unknown_atom_ids": sorted(unknown_atom_ids),
            "reused_evidence_atom_ids_across_support_memberships": repeated_atom_ids,
            "reflection_context_evidence_atom_membership_count": len(reflection_context_memberships),
            "missing_supporting_chain_candidate_ids": sorted(missing_chain_ids),
            "missing_trace_candidate_ids": missing_trace_ids,
            "missing_evidence_atom_ids": missing_atom_ids,
            "scope": "EXPLICIT_CURRENT_TRACE_TO_EVIDENCE_ATOM_LINEAGE_ONLY",
            "raw_atom_count_is_independent_evidence_count": False,
            "csv_xml_reflections_are_independent_votes": False,
            "xlsx_is_independent_event_evidence": False,
            "dependent_reflection_adds_support_vote": False,
            "absence_of_duplicate_membership_proves_independence": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
        }

        challenge = dict(finding.get("finding_challenge_packet") or {})
        evaluated = list(challenge.get("evaluated_falsifier_families") or [])
        if "DUPLICATE_REFLECTION_RISK" not in evaluated:
            evaluated.append("DUPLICATE_REFLECTION_RISK")
        challenge["evaluated_falsifier_families"] = evaluated
        challenge["pending_falsifier_families"] = [
            value for value in (challenge.get("pending_falsifier_families") or [])
            if value != "DUPLICATE_REFLECTION_RISK"
        ]
        challenge["duplicate_reflection_risk"] = audit
        challenge["duplicate_reflection_search_complete_for_current_explicit_lineage_scope"] = True
        challenge["duplicate_reflection_search_complete_for_final_finding"] = False
        challenge["counter_search_complete_for_final_finding"] = False
        challenge["challenge_packet_is_final_finding"] = False
        finding["finding_challenge_packet"] = challenge

        uncertainty = dict(finding.get("uncertainty") or {})
        uncertainty["duplicate_reflection_risk_state_candidate"] = state
        uncertainty["independent_evidence_count_admitted"] = False
        uncertainty["duplicate_reflection_search_complete_for_final_finding"] = False
        finding["uncertainty"] = uncertainty
        finding["claim_output_allowed"] = False
        finding["professional_finding_emitted"] = False

    result["duplicate_reflection_risk_status"] = "REVIEW_REQUIRED"
    result["duplicate_reflection_risk_evaluated_candidate_count"] = len(rows)
    result["findings_with_dependent_or_reused_reflection_support_count"] = dependent_present
    result["findings_with_independence_unknown_count"] = unknown_independence
    result["findings_with_reused_atom_membership_count"] = membership_reuse
    result["duplicate_reflection_search_complete_for_final_finding"] = False
    result["status"] = "REVIEW_REQUIRED"
    result["claim_output_allowed_count"] = 0
    result["professional_finding_emitted_count"] = 0
    result["canonical_event_count"] = CANONICAL_EVENT_COUNT
    result["true_action_count"] = TRUE_ACTION_COUNT
    result["production_release"] = False
    return result
