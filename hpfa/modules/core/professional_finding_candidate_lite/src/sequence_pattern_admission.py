from __future__ import annotations

import hashlib
import json
from typing import Any

MODULE_ID = "sequence_pattern_admission_lite_v1"
VARIANT_MODULE_ID = "partial_order_trace_variant_lite_v1"
CONTRAST_MODULE_ID = "trace_contrast_packet_lite_v1"
ROBUSTNESS_MODULE_ID = "recurrence_robustness_envelope_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "RECURRENT_VISIBLE_TRACE_CANDIDATE_ONLY"

ADMISSION_STATES = {
    "DISCOVERY_ONLY",
    "PROXY_CANDIDATE",
    "RECURRENT_VISIBLE_TRACE",
    "ROBUST_RECURRENT_VISIBLE_TRACE",
    "REVIEW_REQUIRED",
    "REJECTED_INSUFFICIENT_EVIDENCE",
}
FORBIDDEN_ADMISSION_STATES = {"TACTICAL_PATTERN", "COACH_INTENTION", "TEAM_STYLE_TRUTH"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _status(payload: dict[str, Any]) -> str:
    return _clean(payload.get("status") or payload.get("module_status")).upper() or "UNKNOWN"


def _validate(name: str, payload: dict[str, Any], module_id: str) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != module_id:
        blocks.append(f"{name}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{name}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append(f"{name}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{name}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{name}_hard_blocks_present")
    status = _status(payload)
    if status == "FAIL_CLOSED":
        blocks.append(f"{name}_input_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append(f"{name}_upstream_review_required")
    elif status != "PASS":
        reviews.append(f"{name}_upstream_status_review:{status}")
    return blocks, reviews


def _fail(blocks: list[str], reviews: list[str]) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "SEQUENCE_PATTERN_ADMISSION_INPUT_REJECTED",
        "sequence_pattern_admissions": [],
        "sequence_pattern_admission_count": 0,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _envelope_trace_refs(envelope: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for row in envelope.get("threshold_sensitivity") or []:
        if isinstance(row, dict):
            refs.update(_clean(ref) for ref in (row.get("trace_refs") or []) if _clean(ref))
    refs.update(_clean(ref) for ref in (envelope.get("stable_core_trace_refs") or []) if _clean(ref))
    refs.update(_clean(ref) for ref in (envelope.get("fragile_trace_refs") or []) if _clean(ref))
    return refs


def _validated_independent_support(packet: dict[str, Any], eligible_refs: list[str]) -> tuple[int | str, str | None]:
    declared = packet.get("independent_support_count")
    mapping = packet.get("independence_group_by_trace_ref")
    if not isinstance(mapping, dict):
        return "UNKNOWN", None
    normalized = {_clean(ref): _clean(group) for ref, group in mapping.items() if _clean(ref) and _clean(group)}
    if set(normalized) != set(eligible_refs):
        return "UNKNOWN", "independence_mapping_does_not_cover_eligible_traces"
    recomputed = len(set(normalized.values()))
    declared_groups = sorted({_clean(value) for value in (packet.get("independence_groups") or []) if _clean(value)})
    if set(declared_groups) != set(normalized.values()):
        return "UNKNOWN", "independence_group_set_mismatch"
    if not isinstance(declared, int) or declared != recomputed:
        return "UNKNOWN", "declared_independent_support_mismatch"
    return recomputed, None


def build_sequence_pattern_admissions(
    variant_payload: dict[str, Any],
    contrast_payload: dict[str, Any],
    robustness_payload: dict[str, Any],
) -> dict[str, Any]:
    """Admit recurrent visible-trace evidence without promoting tactical-pattern truth."""
    blocks: list[str] = []
    reviews: list[str] = []
    for name, payload, expected in (
        ("variant", variant_payload, VARIANT_MODULE_ID),
        ("contrast", contrast_payload, CONTRAST_MODULE_ID),
        ("robustness", robustness_payload, ROBUSTNESS_MODULE_ID),
    ):
        b, r = _validate(name, payload, expected)
        blocks.extend(b)
        reviews.extend(r)

    if variant_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("variant_same_timestamp_policy_breached")
    if variant_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("variant_source_row_order_policy_breached")
    if contrast_payload.get("no_visible_followup_is_failure") is not False:
        blocks.append("contrast_no_visible_followup_failure_policy_breached")
    if contrast_payload.get("absence_of_evidence_is_counterevidence") is not False:
        blocks.append("contrast_absence_counterevidence_policy_breached")

    variants = [row for row in (variant_payload.get("partial_order_trace_variants") or []) if isinstance(row, dict)]
    packets = [row for row in (contrast_payload.get("trace_contrast_packets") or []) if isinstance(row, dict)]
    envelopes = [row for row in (robustness_payload.get("recurrence_robustness_envelopes") or []) if isinstance(row, dict)]
    by_variant = {_clean(row.get("trace_variant_id")): row for row in variants if _clean(row.get("trace_variant_id"))}
    by_packet = {_clean(row.get("anchor_trace_family")): row for row in packets if _clean(row.get("anchor_trace_family"))}
    by_envelope = {_clean(row.get("pattern_family_ref")): row for row in envelopes if _clean(row.get("pattern_family_ref"))}

    if not envelopes:
        blocks.append("recurrence_robustness_envelopes_empty")
    if len(by_envelope) != len(envelopes):
        blocks.append("robustness_pattern_family_missing_or_duplicate")
    if set(by_envelope) - set(by_packet):
        blocks.append("robustness_without_trace_contrast_packet")
    if set(by_envelope) - set(by_variant):
        blocks.append("robustness_anchor_variant_missing")
    if blocks:
        return _fail(blocks, reviews)

    admissions: list[dict[str, Any]] = []
    for family_ref, envelope in sorted(by_envelope.items()):
        packet = by_packet[family_ref]
        anchor = by_variant[family_ref]
        eligible_refs = sorted({_clean(value) for value in (packet.get("eligible_trace_refs") or []) if _clean(value)})
        missing_refs = [ref for ref in eligible_refs if ref not in by_variant]
        if missing_refs:
            blocks.append(f"eligible_trace_ref_missing:{family_ref}")
            continue

        observed_support = len(eligible_refs)
        envelope_refs = _envelope_trace_refs(envelope)
        try:
            envelope_nominal = int(envelope.get("nominal_recurrence"))
        except (TypeError, ValueError):
            envelope_nominal = -1
        cohort_match = envelope_nominal == observed_support and envelope_refs == set(eligible_refs)
        if not cohort_match:
            reviews.append(f"robustness_cohort_mismatch:{family_ref}")

        variant_count = observed_support
        failure_count = int(packet.get("failure_count") or 0)
        divergence_count = int(packet.get("divergence_count") or 0)
        no_visible_followup_count = int(packet.get("no_visible_followup_count") or 0)
        robustness_state = _clean(envelope.get("robustness_state"))
        ordering_states = sorted({_clean(by_variant[ref].get("ordering_completeness")) for ref in eligible_refs if _clean(by_variant[ref].get("ordering_completeness"))})
        contexts = [by_variant[ref].get("context_signature") or {} for ref in eligible_refs]

        dependency_groups = sorted({_clean(value) for value in (packet.get("dependency_groups") or []) if _clean(value)})
        independence_groups = sorted({_clean(value) for value in (packet.get("independence_groups") or []) if _clean(value)})
        independent_support_count, independence_issue = _validated_independent_support(packet, eligible_refs)
        if independence_issue:
            reviews.append(f"{independence_issue}:{family_ref}")

        counterevidence_refs = sorted({_clean(value) for value in (packet.get("counterevidence_refs") or []) if _clean(value)})
        alternative_explanations: list[dict[str, Any]] = []
        if robustness_state == "THRESHOLD_SENSITIVE":
            alternative_explanations.append({"type": "THRESHOLD_SELECTION_SENSITIVITY", "causal_truth": False})
        if robustness_state == "ORDER_SENSITIVE":
            alternative_explanations.append({"type": "ORDERING_UNCERTAINTY", "causal_truth": False})
        if robustness_state == "CONTEXT_SENSITIVE":
            alternative_explanations.append({"type": "CONTEXT_DEPENDENCE", "causal_truth": False})
        if not cohort_match:
            alternative_explanations.append({"type": "ROBUSTNESS_COHORT_MISMATCH", "causal_truth": False})
        if counterevidence_refs:
            alternative_explanations.append({"type": "DIFFERENT_VISIBLE_OUTCOME_OR_FAILURE", "causal_truth": False})

        if observed_support < 2 or robustness_state == "INSUFFICIENT_EVIDENCE":
            admission_state = "REJECTED_INSUFFICIENT_EVIDENCE"
        elif not cohort_match:
            admission_state = "REVIEW_REQUIRED"
        elif packet.get("packet_state") != "CONTRAST_AVAILABLE":
            admission_state = "REVIEW_REQUIRED"
        elif robustness_state == "FRAGILE":
            admission_state = "DISCOVERY_ONLY"
        elif robustness_state in {"THRESHOLD_SENSITIVE", "ORDER_SENSITIVE", "CONTEXT_SENSITIVE"}:
            admission_state = "PROXY_CANDIDATE"
        elif robustness_state == "ROBUST_WITHIN_TESTED_RANGE":
            admission_state = (
                "ROBUST_RECURRENT_VISIBLE_TRACE"
                if isinstance(independent_support_count, int) and independent_support_count >= 2
                else "RECURRENT_VISIBLE_TRACE"
            )
        else:
            admission_state = "REVIEW_REQUIRED"

        if admission_state in FORBIDDEN_ADMISSION_STATES or admission_state not in ADMISSION_STATES:
            blocks.append(f"forbidden_or_unknown_admission_state:{family_ref}:{admission_state}")
            continue

        uncertainty = {
            "independent_support_count_unknown": independent_support_count == "UNKNOWN",
            "similarity_threshold_is_objective_truth": False,
            "recurrence_is_tactical_intention_truth": False,
            "no_visible_followup_is_failure": False,
            "absence_of_evidence_is_counterevidence": False,
            "robustness_is_tactical_pattern_truth": False,
            "robustness_cohort_exact_match": cohort_match,
        }
        if independent_support_count == "UNKNOWN":
            reviews.append(f"independent_support_unproven:{family_ref}")

        admissions.append({
            "pattern_id": "spa_" + _digest(family_ref, eligible_refs, robustness_state, admission_state)[:24],
            "trace_family_ref": family_ref,
            "eligible_trace_count": len(eligible_refs),
            "observed_support": observed_support,
            "independent_support_count": independent_support_count,
            "context_scope": contexts,
            "ordering_completeness": ordering_states,
            "variant_count": variant_count,
            "failure_variant_count": failure_count,
            "divergence_count": divergence_count,
            "no_visible_followup_count": no_visible_followup_count,
            "robustness_state": robustness_state,
            "counterevidence_state": "VISIBLE" if counterevidence_refs else "NO_VISIBLE_COUNTEREVIDENCE_CURRENT_SCOPE",
            "counterevidence_refs": counterevidence_refs,
            "alternative_explanations": alternative_explanations,
            "dependency_summary": {
                "dependency_groups": dependency_groups,
                "independence_groups": independence_groups,
                "independence_group_by_trace_ref": packet.get("independence_group_by_trace_ref") or {},
                "independence_proven": isinstance(independent_support_count, int),
                "object_views_or_reflections_may_not_create_independent_support": True,
            },
            "uncertainty": uncertainty,
            "claim_ceiling": CLAIM_CEILING,
            "admission_state": admission_state,
            "safe_meaning": "A recurrent visible trace candidate may be described only within the admitted evidence and tested robustness scope.",
            "forbidden_inference": [
                "TACTICAL_PATTERN_TRUTH",
                "COACH_INTENTION",
                "TEAM_STYLE_TRUTH",
                "CAUSALITY",
                "POSSESSION_TRUTH",
                "PHASE_TRUTH",
            ],
            "withdrawal_condition": "Withdraw or downgrade if occurrence identity, dependency accounting, order admission, similarity eligibility, consequence classification, or robustness evidence changes materially.",
            "source_anchor_context": anchor.get("context_signature") or {},
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        })

    if blocks:
        return _fail(blocks, reviews)

    state_counts: dict[str, int] = {}
    for row in admissions:
        state = row["admission_state"]
        state_counts[state] = state_counts.get(state, 0) + 1
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "SEQUENCE_PATTERN_ADMISSION_EVALUATED",
        "sequence_pattern_admissions": admissions,
        "sequence_pattern_admission_count": len(admissions),
        "admission_state_counts": dict(sorted(state_counts.items())),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "tactical_pattern_state_allowed": False,
        "coach_intention_state_allowed": False,
        "team_style_truth_state_allowed": False,
        "independent_support_inferred_from_nominal_count": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
