from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING = "OBSERVED_PROCESS_VARIANT_BINDING_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _process_variant_state(*, exact_grammar: bool, left_outcome: str | None, right_outcome: str | None) -> str:
    resolved = bool(left_outcome and right_outcome)
    if not resolved:
        return "VISIBLE_OUTCOME_VARIANT_UNRESOLVED"
    different = left_outcome != right_outcome
    if exact_grammar and different:
        return "GRAMMAR_STABLE_DIFFERENT_VISIBLE_OUTCOME_VARIANT"
    if exact_grammar:
        return "GRAMMAR_STABLE_SAME_VISIBLE_OUTCOME_VARIANT"
    if different:
        return "GRAMMAR_DIVERGENT_DIFFERENT_VISIBLE_OUTCOME_VARIANT"
    return "GRAMMAR_DIVERGENT_SAME_VISIBLE_OUTCOME_VARIANT"


def build_observable_process_variant_binding(
    sequence_payload: dict[str, Any],
    grammar_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if grammar_payload.get("outcome_excluded_from_alignment") is not True:
        blocks.append("grammar_alignment_outcome_exclusion_missing")
    if grammar_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_internal_ordering_policy_breached")
    if grammar_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_temporal_policy_breached")
    if grammar_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if grammar_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if grammar_payload.get("production_release") is True:
        blocks.append("production_release_claimed")

    variants = {
        _clean(row.get("partial_order_occurrence_variant_id")): row
        for row in (sequence_payload.get("partial_order_occurrence_variants") or [])
        if isinstance(row, dict) and _clean(row.get("partial_order_occurrence_variant_id"))
    }
    outcome_records = {
        _clean(row.get("partial_order_similarity_pair_ref")): row
        for row in (sequence_payload.get("comparable_outcome_counterevidence_records") or [])
        if isinstance(row, dict) and _clean(row.get("partial_order_similarity_pair_ref"))
    }
    alignments = [
        row for row in (grammar_payload.get("supported_sequence_grammar_alignments") or [])
        if isinstance(row, dict)
    ]

    bindings: list[dict[str, Any]] = []
    exact_graph: dict[str, set[str]] = defaultdict(set)

    for alignment in alignments:
        alignment_id = _clean(alignment.get("supported_sequence_grammar_alignment_id"))
        pair_ref = _clean(alignment.get("source_similarity_pair_ref"))
        outcome = outcome_records.get(pair_ref)
        if not outcome:
            reviews.append(f"process_variant_outcome_record_missing:{alignment_id or pair_ref or 'UNKNOWN'}")
            continue
        if outcome.get("comparison_eligible") is not True:
            continue

        left_variant_ref = _clean(alignment.get("left_variant_ref"))
        right_variant_ref = _clean(alignment.get("right_variant_ref"))
        if left_variant_ref not in variants or right_variant_ref not in variants:
            reviews.append(f"process_variant_variant_missing:{alignment_id or pair_ref or 'UNKNOWN'}")
            continue

        left_outcome = _clean(outcome.get("left_visible_outcome_state")) or None
        right_outcome = _clean(outcome.get("right_visible_outcome_state")) or None
        distance = alignment.get("grammar_edit_distance")
        exact_grammar = (
            isinstance(distance, (int, float))
            and not isinstance(distance, bool)
            and float(distance) == 0.0
        )
        state = _process_variant_state(
            exact_grammar=exact_grammar,
            left_outcome=left_outcome,
            right_outcome=right_outcome,
        )
        different_visible_outcome = bool(left_outcome and right_outcome and left_outcome != right_outcome)

        bindings.append({
            "observable_process_variant_binding_id": "opvb_" + _digest(
                alignment_id,
                pair_ref,
                left_variant_ref,
                right_variant_ref,
                state,
            )[:24],
            "source_grammar_alignment_ref": alignment_id or None,
            "source_similarity_pair_ref": pair_ref or None,
            "source_comparable_outcome_ref": _clean(
                outcome.get("comparable_outcome_counterevidence_id")
            ) or None,
            "left_variant_ref": left_variant_ref,
            "right_variant_ref": right_variant_ref,
            "left_sequence_ref": outcome.get("left_sequence_ref"),
            "right_sequence_ref": outcome.get("right_sequence_ref"),
            "left_visible_outcome_state": left_outcome,
            "right_visible_outcome_state": right_outcome,
            "comparison_eligibility_state": outcome.get("comparison_eligibility_state"),
            "grammar_edit_distance": distance,
            "grammar_edit_distance_normalized": alignment.get("grammar_edit_distance_normalized"),
            "supported_common_core_tokens": list(alignment.get("supported_common_core_tokens") or []),
            "first_supported_grammar_divergence": alignment.get("first_supported_grammar_divergence"),
            "process_variant_state": state,
            "same_grammar_different_visible_outcome_candidate": exact_grammar and different_visible_outcome,
            "current_action_family_grammar_discriminates_visible_outcome": (
                False if exact_grammar and different_visible_outcome else None
            ),
            "outcome_excluded_from_grammar_alignment": True,
            "dependency_independence_proven": outcome.get("dependency_independence_proven") is True,
            "statistical_independence_proven": outcome.get("statistical_independence_proven") is True,
            "process_variant_binding_is_process_identity_truth": False,
            "process_variant_binding_is_tactical_pattern_truth": False,
            "process_variant_binding_is_causal_explanation": False,
            "outcome_difference_is_failure_cause_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        })

        if exact_grammar:
            exact_graph[left_variant_ref].add(right_variant_ref)
            exact_graph[right_variant_ref].add(left_variant_ref)

    sequence_by_variant: dict[str, str] = {}
    outcomes_by_variant: dict[str, set[str]] = defaultdict(set)
    for binding in bindings:
        for side in ("left", "right"):
            variant_ref = _clean(binding.get(f"{side}_variant_ref"))
            sequence_ref = _clean(binding.get(f"{side}_sequence_ref"))
            outcome_state = _clean(binding.get(f"{side}_visible_outcome_state"))
            if variant_ref and sequence_ref:
                sequence_by_variant[variant_ref] = sequence_ref
            if variant_ref and outcome_state:
                outcomes_by_variant[variant_ref].add(outcome_state)

    families: list[dict[str, Any]] = []
    seen: set[str] = set()
    for start in sorted(exact_graph):
        if start in seen:
            continue
        stack = [start]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            stack.extend(sorted(exact_graph[current] - seen))
        if len(component) < 2:
            continue

        component_alignments = [
            row for row in alignments
            if _clean(row.get("left_variant_ref")) in component
            and _clean(row.get("right_variant_ref")) in component
            and row.get("grammar_edit_distance") == 0.0
        ]
        grammar_signature = list(component_alignments[0].get("left_layer_tokens") or []) if component_alignments else []

        outcome_counts: Counter[str] = Counter()
        unresolved_members: list[str] = []
        member_records: list[dict[str, Any]] = []
        team_refs: set[str] = set()
        period_refs: set[str] = set()
        dependency_refs: set[str] = set()

        for variant_ref in sorted(component):
            variant = variants[variant_ref]
            states = sorted(outcomes_by_variant.get(variant_ref) or [])
            visible_outcome = states[0] if len(states) == 1 else None
            if visible_outcome:
                outcome_counts[visible_outcome] += 1
            else:
                unresolved_members.append(variant_ref)
            member_records.append({
                "variant_ref": variant_ref,
                "sequence_ref": sequence_by_variant.get(variant_ref),
                "visible_outcome_state": visible_outcome,
            })
            team_ref = _clean(variant.get("team_identity_candidate_id"))
            period_ref = _clean(variant.get("period_candidate"))
            if team_ref:
                team_refs.add(team_ref)
            if period_ref:
                period_refs.add(period_ref)
            for dependency_ref in variant.get("dependency_group_refs") or []:
                cleaned = _clean(dependency_ref)
                if cleaned:
                    dependency_refs.add(cleaned)

        visible_outcome_states = sorted(outcome_counts)
        if len(visible_outcome_states) >= 2:
            family_state = "GRAMMAR_STABLE_VISIBLE_OUTCOME_VARIATION"
        elif len(visible_outcome_states) == 1:
            family_state = "GRAMMAR_STABLE_SINGLE_VISIBLE_OUTCOME"
        else:
            family_state = "GRAMMAR_STABLE_OUTCOME_UNRESOLVED"
        outcome_variation = len(visible_outcome_states) >= 2

        families.append({
            "observable_process_variant_family_id": "opvf_" + _digest(
                sorted(component), grammar_signature
            )[:24],
            "member_variant_refs": sorted(component),
            "member_count": len(component),
            "member_records": member_records,
            "grammar_signature_tokens": grammar_signature,
            "grammar_signature_layer_count": len(grammar_signature),
            "visible_outcome_state_counts": dict(sorted(outcome_counts.items())),
            "resolved_visible_outcome_member_count": sum(outcome_counts.values()),
            "unresolved_visible_outcome_member_refs": sorted(unresolved_members),
            "process_variant_family_state": family_state,
            "same_grammar_visible_outcome_variation_observed": outcome_variation,
            "current_action_family_grammar_discriminates_visible_outcome": (
                False if outcome_variation else None
            ),
            "team_identity_candidate_ids": sorted(team_refs),
            "period_candidates": sorted(period_refs),
            "dependency_group_ref_count": len(dependency_refs),
            "dependency_group_refs": sorted(dependency_refs),
            "independent_recurrence_support_count": 0,
            "family_is_independent_recurrence_truth": False,
            "family_is_process_identity_truth": False,
            "family_is_tactical_pattern_truth": False,
            "family_is_causal_mechanism_truth": False,
            "next_supported_question": (
                "WHICH_ADMITTED_CONTEXT_OR_CONSEQUENCE_FEATURES_DIFFER_WITHIN_GRAMMAR_STABLE_OUTCOME_VARIANTS"
                if outcome_variation
                else None
            ),
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or str(grammar_payload.get("status") or "").upper() == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "status": status,
        "observable_process_variant_bindings": bindings if not blocks else [],
        "observable_process_variant_binding_count": len(bindings) if not blocks else 0,
        "observable_process_variant_families": families if not blocks else [],
        "observable_process_variant_family_count": len(families) if not blocks else 0,
        "grammar_stable_visible_outcome_variation_family_count": (
            sum(1 for row in families if row.get("same_grammar_visible_outcome_variation_observed") is True)
            if not blocks
            else 0
        ),
        "outcome_excluded_from_grammar_alignment": True,
        "process_variant_family_is_recurrence_truth": False,
        "process_variant_family_is_tactical_pattern_truth": False,
        "process_variant_family_is_causal_mechanism_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
