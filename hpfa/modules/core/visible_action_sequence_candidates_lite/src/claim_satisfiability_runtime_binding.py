from __future__ import annotations

from collections import Counter
from typing import Any

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.claim_satisfiability_gate import (
    SATISFIED,
    assess_claim_satisfiability,
)

MODULE_ID = "claim_satisfiability_runtime_binding_v1"
BASE_CLAIM_FAMILY = "MATCH_LOCAL_VISIBLE_VARIATION"
ALWAYS_ASSESSED_FAMILIES = (
    BASE_CLAIM_FAMILY,
    "MATCH_LOCAL_RECURRENCE_CANDIDATE",
    "CAUSALITY",
    "TACTICAL_PATTERN_TRUTH",
    "COACH_INTENTION",
    "CROSS_MATCH_GENERALIZATION",
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _handoff_index(sequence_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in sequence_payload.get("safe_finding_handoff_candidates") or []:
        if not isinstance(row, dict):
            continue
        ref = _clean(row.get("safe_finding_handoff_candidate_id"))
        if ref and ref not in out:
            out[ref] = row
    return out


def _divergence_index(sequence_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in sequence_payload.get("first_supported_branch_divergence_candidates") or []:
        if not isinstance(row, dict):
            continue
        ref = _clean(row.get("first_supported_branch_divergence_id"))
        if ref and ref not in out:
            out[ref] = row
    return out


def _admission_index(admission_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in admission_payload.get("safe_finding_admission_decisions") or []:
        if not isinstance(row, dict):
            continue
        ref = _clean(row.get("source_safe_finding_handoff_ref"))
        if ref and ref not in out:
            out[ref] = row
    return out


def _family_signals(divergence: dict[str, Any] | None) -> dict[str, Any]:
    progression_values: set[str] = set()
    action_families: Counter[str] = Counter()
    if not isinstance(divergence, dict):
        return {
            "progression_values": [],
            "turnover_family_visible_count": 0,
        }

    for branch in divergence.get("branch_profiles") or []:
        if not isinstance(branch, dict):
            continue
        for family, raw_count in (branch.get("neighbor_action_family_counts") or {}).items():
            family_name = _clean(family).upper()
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                count = 0
            if family_name and count > 0:
                action_families[family_name] += count
        for profile in branch.get("semantic_profiles") or []:
            if not isinstance(profile, dict):
                continue
            for value in profile.get("progression_values") or []:
                cleaned = _clean(value).upper()
                if cleaned:
                    progression_values.add(cleaned)

    return {
        "progression_values": sorted(progression_values),
        "turnover_family_visible_count": int(action_families.get("TURNOVER", 0)),
    }


def _admitted_capabilities(
    handoff: dict[str, Any],
    divergence: dict[str, Any] | None,
    signals: dict[str, Any],
) -> list[str]:
    # Safe Finding handoffs in this producer are admitted visible-branch variation
    # projections. We expose only the capabilities structurally required by that
    # existing producer and add provider-derived semantics only when the source
    # divergence actually carries an admitted progression semantic signal.
    if not isinstance(divergence, dict):
        return []
    if divergence.get("production_release") is True:
        return []
    if divergence.get("canonical_event_count") != "UNKNOWN":
        return []
    if divergence.get("true_action_count") != "UNKNOWN":
        return []
    if divergence.get("same_timestamp_internal_ordering_allowed") is not False:
        return []
    if divergence.get("source_row_order_is_temporal_truth") is not False:
        return []

    support = handoff.get("support") if isinstance(handoff.get("support"), dict) else {}
    what_visible = handoff.get("what_visible") if isinstance(handoff.get("what_visible"), dict) else {}
    if not support or not what_visible:
        return []

    capabilities = {"ACTION", "TEMPORAL", "OUTCOME", "PROVENANCE"}
    if signals.get("progression_values"):
        capabilities.add("PROVIDER_DERIVED")
    return sorted(capabilities)


def _support_inputs(
    handoff: dict[str, Any],
    admission_row: dict[str, Any] | None,
) -> dict[str, Any]:
    support = handoff.get("support") if isinstance(handoff.get("support"), dict) else {}
    independent = support.get("admitted_independent_support_count", 0)
    try:
        independent_count = max(int(independent or 0), 0)
    except (TypeError, ValueError):
        independent_count = 0
    return {
        "admitted_independent_support_count": independent_count,
        "dependency_independence_proven": support.get("dependency_independence_proven") is True,
        "statistical_independence_proven": support.get("statistical_independence_proven") is True,
        "episode_spread_observed": (
            isinstance(admission_row, dict)
            and admission_row.get("variant_support_episode_spread_observed") is True
        ),
    }


def _assessments_for_contract(
    handoff: dict[str, Any],
    divergence: dict[str, Any] | None,
    admission_row: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    signals = _family_signals(divergence)
    capabilities = _admitted_capabilities(handoff, divergence, signals)
    support_inputs = _support_inputs(handoff, admission_row)

    families = list(ALWAYS_ASSESSED_FAMILIES)
    if signals.get("progression_values"):
        families.append("PROGRESSION_ACCESS_DESCRIPTION")
    if int(signals.get("turnover_family_visible_count") or 0) > 0:
        families.append("RETENTION_LOSS_DESCRIPTION")

    assessments = [
        assess_claim_satisfiability(
            family,
            admitted_capabilities=capabilities,
            **support_inputs,
        )
        for family in families
    ]
    return assessments, capabilities, signals


def bind_claim_satisfiability(
    sequence_payload: dict[str, Any],
    admission_payload: dict[str, Any],
    claim_payload: dict[str, Any],
) -> dict[str, Any]:
    """Bind the deterministic claim-satisfiability gate to current output contracts.

    This binding creates no evidence and can never open EMIT. It may only preserve an
    already-open professional output permission when the base match-local claim family
    is satisfiable, or close that permission when required capability lineage is absent.
    """
    result = dict(claim_payload)
    contracts = [
        dict(row)
        for row in (claim_payload.get("analyst_output_contracts") or [])
        if isinstance(row, dict)
    ]
    handoffs = _handoff_index(sequence_payload)
    divergences = _divergence_index(sequence_payload)
    admissions = _admission_index(admission_payload)
    review_hits = [str(value) for value in (claim_payload.get("review_hits") or [])]
    state_counts: Counter[str] = Counter()
    blocked_emit_refs: list[str] = []

    bound_contracts: list[dict[str, Any]] = []
    for contract in contracts:
        ref = _clean(contract.get("source_safe_finding_handoff_ref"))
        handoff = handoffs.get(ref)
        if not ref or not isinstance(handoff, dict):
            contract["professional_emit_allowed"] = False
            contract["claim_scope"] = "NO_CLAIM_OUTPUT"
            contract["claim_satisfiability_gate_state"] = "REVIEW_REQUIRED_SOURCE_HANDOFF_MISSING"
            contract["claim_satisfiability_assessments"] = []
            contract["claim_satisfiability_admitted_capabilities"] = []
            contract["claim_satisfiability_family_signals"] = {}
            contract["claim_satisfiability_gate_can_authorize_emit"] = False
            contract["claim_satisfiability_gate_creates_new_evidence"] = False
            review_hits.append(f"claim_satisfiability_source_handoff_missing:{ref or 'UNKNOWN'}")
            bound_contracts.append(contract)
            continue

        divergence_ref = _clean(handoff.get("source_first_supported_branch_divergence_ref"))
        divergence = divergences.get(divergence_ref)
        assessments, capabilities, signals = _assessments_for_contract(
            handoff,
            divergence,
            admissions.get(ref),
        )
        for assessment in assessments:
            state_counts[_clean(assessment.get("state")) or "UNKNOWN"] += 1
        base = next(
            (
                assessment
                for assessment in assessments
                if _clean(assessment.get("claim_family")) == BASE_CLAIM_FAMILY
            ),
            None,
        )
        base_state = _clean(base.get("state")) if isinstance(base, dict) else "REVIEW_REQUIRED"
        prior_emit = contract.get("professional_emit_allowed") is True
        preserve_emit = prior_emit and base_state == SATISFIED
        if prior_emit and not preserve_emit:
            blocked_emit_refs.append(ref)
            review_hits.append(f"claim_satisfiability_blocks_emit:{ref}:{base_state or 'UNKNOWN'}")
            contract["professional_emit_allowed"] = False
            contract["claim_scope"] = "NO_CLAIM_OUTPUT"

        contract["claim_satisfiability_gate_state"] = base_state or "REVIEW_REQUIRED"
        contract["claim_satisfiability_assessments"] = assessments
        contract["claim_satisfiability_admitted_capabilities"] = capabilities
        contract["claim_satisfiability_family_signals"] = signals
        contract["claim_satisfiability_gate_preserved_professional_emit"] = preserve_emit
        contract["claim_satisfiability_gate_blocked_professional_emit"] = prior_emit and not preserve_emit
        contract["claim_satisfiability_gate_can_authorize_emit"] = False
        contract["claim_satisfiability_gate_creates_new_evidence"] = False
        contract["claim_satisfiability_gate_can_strengthen_claim_ceiling"] = False
        bound_contracts.append(contract)

    result["analyst_output_contracts"] = bound_contracts
    result["analyst_output_contract_count"] = len(bound_contracts)
    emitted_count = sum(1 for row in bound_contracts if row.get("professional_emit_allowed") is True)
    result["professional_emit_allowed_count"] = emitted_count
    result["professional_emit_allowed"] = emitted_count > 0
    result["claim_satisfiability_gate_consumed"] = True
    result["claim_satisfiability_gate_module_id"] = MODULE_ID
    result["claim_satisfiability_gate_state_counts"] = dict(sorted(state_counts.items()))
    result["claim_satisfiability_blocked_professional_emit_refs"] = sorted(set(blocked_emit_refs))
    result["claim_satisfiability_gate_can_authorize_emit"] = False
    result["claim_satisfiability_gate_creates_new_evidence"] = False
    result["claim_satisfiability_gate_can_strengthen_claim_ceiling"] = False
    result["review_hits"] = sorted(set(review_hits))
    if result.get("status") != "FAIL_CLOSED" and review_hits:
        result["status"] = "REVIEW_REQUIRED"
    result["canonical_event_count"] = "UNKNOWN"
    result["true_action_count"] = "UNKNOWN"
    result["production_release"] = False
    return result
