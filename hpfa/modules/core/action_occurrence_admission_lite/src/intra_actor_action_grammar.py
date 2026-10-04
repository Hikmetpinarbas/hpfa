from __future__ import annotations

import hashlib
import json
from typing import Any

CLAIM_CEILING = "ACTION_OCCURRENCE_CANDIDATE_WITH_QUALIFIERS_ONLY"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _bundle_labels(bundle: dict[str, Any]) -> set[str]:
    return {
        _clean(value).casefold()
        for value in (bundle.get("raw_labels") or []) + (bundle.get("normalized_labels") or [])
        if _clean(value)
    }


def _evidence_by_id(evidence_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _clean(atom.get("evidence_atom_id")): atom
        for atom in evidence_payload.get("evidence_atoms") or []
        if isinstance(atom, dict) and _clean(atom.get("evidence_atom_id"))
    }


def _rule_label_map(rule: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    result: dict[str, tuple[str, dict[str, Any]]] = {}
    for raw_label, raw_meta in (rule.get("semantic_labels") or {}).items():
        if not isinstance(raw_meta, dict) or not _clean(raw_label):
            continue
        result[_clean(raw_label).casefold()] = (_clean(raw_label), raw_meta)
    return result


def _attribute_values(components: list[dict[str, Any]], key: str) -> list[str]:
    return sorted({_clean(item.get(key)) for item in components if _clean(item.get(key))})


def build_intra_actor_action_grammar_candidates(
    action_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    """Collapse compatible same-actor semantic annotations into one occurrence candidate.

    Upstream Action Bundle already establishes the exact same-role/team/actor/time/anchor core.
    This helper does not fuse bundles across time, space, actors, roles or action families. It only
    interprets multiple reviewed labels already co-located inside one PASS Action Bundle as semantic
    attributes of one candidate occurrence.
    """
    required_mapping_status = _clean(
        (registry.get("upstream_semantics_binding") or {}).get("semantic_mapping_status_required")
    )
    provider_registry_id = _clean(
        (registry.get("upstream_semantics_binding") or {}).get("registry_id")
    )
    evidence_map = _evidence_by_id(evidence_payload)
    rules = [
        rule
        for rule in registry.get("intra_actor_occurrence_rules") or []
        if isinstance(rule, dict) and _clean(rule.get("rule_id"))
    ]
    rules_by_family = {
        _clean(rule.get("action_family")).upper(): rule
        for rule in rules
        if _clean(rule.get("action_family"))
    }

    candidates: list[dict[str, Any]] = []
    review_hits: list[str] = []
    rejected_provider_binding_count = 0
    contradictory_semantics_count = 0

    for bundle in action_payload.get("action_bundle_candidates") or []:
        if not isinstance(bundle, dict):
            continue
        if bundle.get("source_role") != "PLAYER_SURFACE_CANDIDATE":
            continue
        if _clean(bundle.get("bundle_status")) != "PASS":
            continue
        if bundle.get("same_role_exact_grouping") is not True:
            continue
        if bundle.get("cross_role_fusion_allowed") is True:
            continue
        if bundle.get("validated_event_identity") is True or bundle.get("event_instance_allowed") is True:
            continue
        if bundle.get("canonical_event_count") not in {None, "UNKNOWN"}:
            continue

        family = _clean(bundle.get("action_family_candidate")).upper()
        rule = rules_by_family.get(family)
        if rule is None:
            continue
        label_map = _rule_label_map(rule)
        recognized = [
            (canonical_label, meta)
            for folded, (canonical_label, meta) in label_map.items()
            if folded in _bundle_labels(bundle)
        ]
        minimum = int(rule.get("minimum_distinct_semantic_labels") or 2)
        if len(recognized) < minimum:
            continue

        components: list[dict[str, Any]] = []
        expected_rule_ids: set[str] = set()
        for label, meta in sorted(recognized, key=lambda item: item[0].casefold()):
            semantic_rule_id = _clean(meta.get("semantic_rule_id"))
            if semantic_rule_id:
                expected_rule_ids.add(semantic_rule_id)
            components.append(
                {
                    "label": label,
                    "semantic_rule_id": semantic_rule_id or None,
                    "outcome": _clean(meta.get("outcome")) or None,
                    "direction": _clean(meta.get("direction")) or None,
                    "distance": _clean(meta.get("distance")) or None,
                    "zone_context": _clean(meta.get("zone_context")) or None,
                    "progression": _clean(meta.get("progression")) or None,
                    "key_action": _clean(meta.get("key_action")) or None,
                }
            )

        observed_rule_ids: set[str] = set()
        for raw_evidence_id in bundle.get("supporting_evidence_atom_ids") or []:
            atom = evidence_map.get(_clean(raw_evidence_id))
            if atom is None:
                continue
            if required_mapping_status and _clean(atom.get("semantic_mapping_status")) != required_mapping_status:
                continue
            semantic_rule_id = _clean(atom.get("semantic_rule_id"))
            if semantic_rule_id:
                observed_rule_ids.add(semantic_rule_id)

        if not expected_rule_ids or not expected_rule_ids.issubset(observed_rule_ids):
            rejected_provider_binding_count += 1
            review_hits.append("intra_actor_candidate_rejected_provider_semantics_binding")
            continue

        outcomes = _attribute_values(components, "outcome")
        if len(outcomes) > 1:
            contradictory_semantics_count += 1
            review_hits.append("intra_actor_candidate_contradictory_outcome_semantics")
            continue

        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        binding = _clean(bundle.get("match_surface_binding_id"))
        raw_labels = sorted({_clean(x) for x in bundle.get("raw_labels") or [] if _clean(x)})
        candidate = {
            "action_occurrence_candidate_id": "aoc_grammar_" + _digest(
                binding,
                bundle_id,
                _clean(rule.get("rule_id")),
                sorted(expected_rule_ids),
            )[:24],
            "match_surface_binding_id": binding,
            "admission_class": "EXACT_SAME_ACTOR_SEMANTIC_COLLAPSE",
            "interaction_type": "INTRA_ACTOR_ACTION_GRAMMAR_CANDIDATE",
            "occurrence_topology": "SINGLE_ACTOR_ACTION",
            "compatibility_rule_id": _clean(rule.get("rule_id")),
            "primary_family_candidate": family,
            "team_identity_candidate_id": bundle.get("team_identity_candidate_id"),
            "actor_identity_candidate_id": bundle.get("actor_identity_candidate_id"),
            "opponent_team_identity_candidate_id": None,
            "opponent_identity_candidate_id": None,
            "supporting_action_bundle_candidate_ids": [bundle_id],
            "supporting_evidence_atom_ids": sorted(
                {_clean(x) for x in bundle.get("supporting_evidence_atom_ids") or [] if _clean(x)}
            ),
            "provider_row_id_candidates": sorted(
                {_clean(x) for x in bundle.get("provider_row_id_candidates") or [] if _clean(x)}
            ),
            "raw_labels": raw_labels,
            "semantic_components": components,
            "attributes": {
                "outcome_candidate": outcomes[0] if outcomes else "UNKNOWN",
                "direction_candidates": _attribute_values(components, "direction"),
                "distance_candidates": _attribute_values(components, "distance"),
                "zone_context_candidates": _attribute_values(components, "zone_context"),
                "progression_candidates": _attribute_values(components, "progression"),
                "key_action_candidates": _attribute_values(components, "key_action"),
                "distinct_semantic_label_count": len(components),
            },
            "temporal_relation": {
                "period_candidate": bundle.get("period_candidate"),
                "start_candidate": bundle.get("start_candidate"),
                "end_candidate": bundle.get("end_candidate"),
                "relation": "EXACT_SAME_ACTOR_ANNOTATION_CORE",
                "internal_order": "UNKNOWN",
            },
            "location": {
                "pos_x_candidate": bundle.get("pos_x_candidate"),
                "pos_y_candidate": bundle.get("pos_y_candidate"),
                "semantic_role": "ANNOTATION_ANCHOR_LOCATION_CANDIDATE",
                "physical_player_position_truth": False,
            },
            "relation_bundle": None,
            "counterevidence": [],
            "alternative_explanations": [
                "provider semantic annotations may overlap without establishing canonical physical action identity"
            ],
            "withdrawal_conditions": [
                "provider_semantic_rule_binding_revised",
                "action_bundle_exact_grouping_revised",
                "identity_or_time_space_binding_revised",
            ],
            "grammar_decision": "ONE_OCCURRENCE_CANDIDATE_MULTIPLE_SEMANTIC_ANNOTATIONS",
            "provider_semantics_binding_status": "PASS",
            "provider_semantics_registry_id": provider_registry_id or None,
            "supporting_semantic_rule_ids": sorted(observed_rule_ids & expected_rule_ids),
            "conditional_review_passthrough_used": False,
            "conditional_review_passthrough_provenance": [],
            "upstream_taxonomy_truth_changed": False,
            "admission_score": None,
            "probability_output_allowed": False,
            "independent_support_vote_count": 0,
            "same_time_total_order_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "action_occurrence_candidate_is_event_truth": False,
            "validated_event_identity": False,
            "event_instance_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": CLAIM_CEILING,
        }
        candidates.append(candidate)

    return {
        "action_occurrence_candidates": candidates,
        "action_occurrence_candidate_count": len(candidates),
        "rejected_provider_semantics_binding_count": rejected_provider_binding_count,
        "contradictory_semantics_count": contradictory_semantics_count,
        "review_hits": sorted(set(review_hits)),
        "same_timestamp_alone_is_merge_authority": False,
        "cross_bundle_merge_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
