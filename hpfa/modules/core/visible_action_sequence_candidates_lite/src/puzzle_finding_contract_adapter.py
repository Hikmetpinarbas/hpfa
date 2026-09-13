from __future__ import annotations

from collections import Counter
from typing import Any

MODULE_ID = "puzzle_finding_contract_adapter_v1"
CONTRACT_VERSION = "PUZZLE_FINDING_V1"
PUZZLE_ID = "P6_PROCESS_VARIANT_DIVERGENCE"
PUZZLE_FAMILY = "PROCESS_VARIANT_AND_DIVERGENCE"
CLAIM_CEILING = "MATCH_LOCAL_PUZZLE_FINDING_CONTRACT_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _admission_index(admission_payload: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    if admission_payload is None:
        return {}, [], []
    blocks: list[str] = []
    reviews: list[str] = []
    if admission_payload.get("production_release") is True:
        blocks.append("admission_production_release_claimed")
    if admission_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("admission_canonical_event_count_claimed")
    if admission_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("admission_true_action_count_claimed")
    status = _clean(admission_payload.get("status")).upper()
    if status == "FAIL_CLOSED":
        blocks.append("safe_finding_admission_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("safe_finding_admission_review_required")
    elif status != "PASS":
        reviews.append(f"safe_finding_admission_status_unrecognized:{status or 'UNKNOWN'}")

    index: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(admission_payload.get("safe_finding_admission_decisions") or []):
        if not isinstance(row, dict):
            reviews.append(f"admission_row_not_object:{position}")
            continue
        source_ref = _clean(row.get("source_safe_finding_handoff_ref"))
        if not source_ref:
            reviews.append(f"admission_source_ref_missing:{position}")
            continue
        if source_ref in index:
            blocks.append(f"duplicate_admission_decision:{source_ref}")
            continue
        index[source_ref] = dict(row)
    return index, blocks, reviews


def _finding_decision(
    handoff: dict[str, Any],
    admission_row: dict[str, Any] | None,
    admission_supplied: bool,
) -> tuple[str, bool, str]:
    if not admission_supplied:
        return "NOT_EVALUATED", False, "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"
    if admission_row is None:
        return "ABSTAIN", False, "NO_CLAIM_OUTPUT"
    decision = _clean(admission_row.get("decision")).upper()
    if decision not in {"EMIT", "DOWNGRADE", "ABSTAIN"}:
        return "ABSTAIN", False, "NO_CLAIM_OUTPUT"
    claim_allowed = decision == "EMIT" and admission_row.get("claim_output_allowed") is True
    if decision == "EMIT" and not claim_allowed:
        return "ABSTAIN", False, "NO_CLAIM_OUTPUT"
    return decision, claim_allowed, _clean(admission_row.get("claim_ceiling")) or "NO_CLAIM_OUTPUT"


def _context_refs(where_when: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in (
        "team_identity_candidate_id",
        "period_candidate",
        "shared_anchor_time_layer_ref",
        "anchor_centered_sequence_branch_map_ref",
    ):
        value = _clean(where_when.get(key))
        if value:
            refs.append(f"{key}:{value}")
    return refs


def build_puzzle_finding_contract(
    sequence_payload: dict[str, Any],
    admission_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project existing Safe Finding handoffs into a shared puzzle-facing contract.

    This adapter does not discover actions, rebuild sequences, create evidence, or infer a
    tactical mechanism. It only makes already-admitted Safe Finding surfaces explicit as
    Discovery / Comparison / Falsification / Evolution / Fusion inputs. The first bound
    producer is Puzzle 6 (Process Variant & Divergence); other puzzle producers may later
    emit the same contract without changing downstream fusion semantics.
    """
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("production_release") is True:
        blocks.append("sequence_production_release_claimed")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("sequence_canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("sequence_true_action_count_claimed")
    if sequence_payload.get("safe_finding_handoff_professional_emit_allowed") is not False:
        blocks.append("sequence_professional_emit_lock_not_false")

    admission_by_ref, admission_blocks, admission_reviews = _admission_index(admission_payload)
    blocks.extend(admission_blocks)
    reviews.extend(admission_reviews)

    findings: list[dict[str, Any]] = []
    if not blocks:
        for position, handoff in enumerate(sequence_payload.get("safe_finding_handoff_candidates") or []):
            if not isinstance(handoff, dict):
                reviews.append(f"safe_finding_handoff_not_object:{position}")
                continue
            handoff_id = _clean(handoff.get("safe_finding_handoff_candidate_id"))
            if not handoff_id:
                reviews.append(f"safe_finding_handoff_id_missing:{position}")
                continue
            if handoff.get("professional_finding_emit_allowed") is not False:
                reviews.append(f"handoff_emit_lock_not_false:{handoff_id}")
                continue
            if any(
                handoff.get(key) is not False
                for key in (
                    "safe_finding_handoff_is_professional_finding_truth",
                    "safe_finding_handoff_is_tactical_truth",
                    "safe_finding_handoff_is_causal_truth",
                    "safe_finding_handoff_is_coach_intention_truth",
                    "same_timestamp_internal_ordering_allowed",
                    "source_row_order_is_temporal_truth",
                )
            ):
                reviews.append(f"handoff_truth_lock_missing:{handoff_id}")
                continue

            what_visible = handoff.get("what_visible") if isinstance(handoff.get("what_visible"), dict) else {}
            where_when = handoff.get("where_when") if isinstance(handoff.get("where_when"), dict) else {}
            support = handoff.get("support") if isinstance(handoff.get("support"), dict) else {}
            counterevidence = handoff.get("counterevidence") if isinstance(handoff.get("counterevidence"), dict) else {}
            sufficiency = handoff.get("evidence_sufficiency") if isinstance(handoff.get("evidence_sufficiency"), dict) else {}
            uncertainty = handoff.get("uncertainty") if isinstance(handoff.get("uncertainty"), dict) else {}
            alternatives = handoff.get("alternative_explanations") if isinstance(handoff.get("alternative_explanations"), list) else []
            withdrawals = _refs(handoff.get("withdrawal_conditions"))
            forbidden = _refs(handoff.get("forbidden_inference"))

            success_refs = _refs(support.get("visible_success_sequence_refs"))
            failure_refs = _refs(counterevidence.get("visible_failure_sequence_refs"))
            counterexample_refs = _refs(counterevidence.get("comparable_counterexample_refs"))
            context_refs = _context_refs(where_when)
            independent_support = support.get("admitted_independent_support_count")
            dependency_independence_proven = support.get("dependency_independence_proven") is True
            statistical_independence_proven = support.get("statistical_independence_proven") is True
            if isinstance(independent_support, bool) or not isinstance(independent_support, int) or independent_support < 0:
                independent_support = 0
                reviews.append(f"independent_support_count_invalid:{handoff_id}")

            decision, claim_allowed, admission_claim_ceiling = _finding_decision(
                handoff,
                admission_by_ref.get(handoff_id),
                admission_payload is not None,
            )
            if admission_payload is not None and handoff_id not in admission_by_ref:
                reviews.append(f"admission_decision_missing:{handoff_id}")

            if dependency_independence_proven and statistical_independence_proven and independent_support > 0:
                dependency_state = "INDEPENDENT_SUPPORT_ADMITTED"
            elif independent_support > 0 or dependency_independence_proven:
                dependency_state = "DEPENDENT_OR_PARTIAL_LINEAGE"
            else:
                dependency_state = "INDEPENDENCE_UNKNOWN"

            finding_id = f"pf_{handoff_id}"
            findings.append({
                "puzzle_finding_id": finding_id,
                "puzzle_finding_contract_version": CONTRACT_VERSION,
                "puzzle_id": PUZZLE_ID,
                "puzzle_family": PUZZLE_FAMILY,
                "source_safe_finding_handoff_ref": handoff_id,
                "source_first_supported_branch_divergence_ref": handoff.get(
                    "source_first_supported_branch_divergence_ref"
                ),
                "finding_status": decision,
                "claim_output_allowed": claim_allowed,
                "admission_claim_ceiling": admission_claim_ceiling,
                "what_visible": what_visible,
                "where_when": where_when,
                "support": support,
                "counterevidence": counterevidence,
                "evidence_sufficiency": sufficiency,
                "alternative_explanations": alternatives,
                "safe_meaning": handoff.get("safe_meaning"),
                "forbidden_inference": forbidden,
                "uncertainty": uncertainty,
                "withdrawal_conditions": withdrawals,
                "analyst_action": handoff.get("analyst_action"),
                "analyst_summary_tr": handoff.get("analyst_summary_tr"),
                "discovery_surface": {
                    "state": "VISIBLE_PROCESS_VARIANT_DIVERGENCE_DISCOVERY_BOUND",
                    "source_divergence_ref": handoff.get("source_first_supported_branch_divergence_ref"),
                    "visible_success_sequence_refs": success_refs,
                    "visible_failure_sequence_refs": failure_refs,
                    "creates_new_evidence": False,
                },
                "comparison_surface": {
                    "comparison_unit": "COMPARABLE_PARTIAL_ORDER_PROCESS_VARIANT",
                    "comparison_eligibility_required": True,
                    "visible_success_numerator": support.get("visible_success_numerator"),
                    "eligible_denominator": support.get("eligible_denominator"),
                    "visible_success_sequence_refs": success_refs,
                    "visible_failure_sequence_refs": failure_refs,
                    "raw_rate_is_true_probability": False,
                },
                "falsification_surface": {
                    "comparable_counterexample_refs": counterexample_refs,
                    "alternative_explanation_count": len(alternatives),
                    "withdrawal_conditions": withdrawals,
                    "absence_used_as_counterevidence": counterevidence.get("absence_used_as_counterevidence") is True,
                    "counterexample_pair_count_is_independent_evidence_count": False,
                },
                "evolution_surface": {
                    "period_candidate": where_when.get("period_candidate"),
                    "score_state": "NOT_AVAILABLE",
                    "game_state_conditioning_ready": False,
                    "period_only_is_full_game_state_truth": False,
                },
                "fusion_surface": {
                    "support_refs": success_refs,
                    "counterevidence_refs": counterexample_refs,
                    "context_refs": context_refs,
                    "dependency_state": dependency_state,
                    "admitted_independent_support_count": independent_support,
                    "dependency_independence_proven": dependency_independence_proven,
                    "statistical_independence_proven": statistical_independence_proven,
                    "relation_candidates": [
                        "SUPPORTS_PUZZLE_FINDING",
                        "COUNTEREXAMPLE_TO_PUZZLE_FINDING",
                        "CONTEXTUALIZES_PUZZLE_FINDING",
                        "SHARES_PROCESS_FAMILY_CANDIDATE",
                    ],
                    "same_process_truth": False,
                    "same_episode_truth": False,
                    "mechanism_candidate_truth": False,
                    "creates_new_evidence": False,
                },
                "puzzle_finding_is_professional_finding_truth": False,
                "puzzle_finding_is_tactical_truth": False,
                "puzzle_finding_is_causal_truth": False,
                "puzzle_finding_is_coach_intention_truth": False,
                "absence_is_counterevidence": False,
                "same_timestamp_internal_ordering_allowed": False,
                "source_row_order_is_temporal_truth": False,
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    counts = Counter(row.get("finding_status") for row in findings)
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "puzzle_finding_contract_version": CONTRACT_VERSION,
        "puzzle_findings": findings if not blocks else [],
        "puzzle_finding_count": len(findings) if not blocks else 0,
        "puzzle_finding_status_counts": dict(sorted(counts.items())) if not blocks else {},
        "bound_puzzle_ids": [PUZZLE_ID] if findings and not blocks else [],
        "safe_finding_handoff_consumed": True,
        "safe_finding_admission_consumed": admission_payload is not None,
        "discovery_recomputed": False,
        "comparison_recomputed": False,
        "falsification_recomputed": False,
        "creates_new_evidence": False,
        "creates_new_finding": False,
        "cross_mechanism_fusion_performed": False,
        "mechanism_candidate_emitted": False,
        "game_state_conditioning_ready": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
