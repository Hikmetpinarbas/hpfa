from __future__ import annotations

import copy
from typing import Any

from hpfa.modules.core.action_occurrence_admission_lite.src import action_occurrence_admission as occurrence

EVIDENCE_MODULE_ID = "evidence_atom_inventory_lite_v1"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _labels(bundle: dict[str, Any]) -> set[str]:
    return {
        _clean(item).casefold()
        for item in (bundle.get("raw_labels") or []) + (bundle.get("normalized_labels") or [])
        if _clean(item)
    }


def _normalized_family_set(record: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted({_clean(item).upper() for item in record.get("family_set") or [] if _clean(item)}))


def _rule_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _clean(rule.get("rule_id")): rule
        for rule in registry.get("interaction_rules") or []
        if isinstance(rule, dict) and _clean(rule.get("rule_id"))
    }


def _fail_closed(reason: str, binding: str = "") -> dict[str, Any]:
    return {
        "module_id": occurrence.MODULE_ID,
        "status": "FAIL_CLOSED",
        "module_status": "FAIL_CLOSED",
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding,
        "action_occurrence_candidates": [],
        "action_occurrence_candidate_count": 0,
        "admission_class_counts": {},
        "interaction_type_counts": {},
        "conditional_review_passthrough_record_count": 0,
        "conditional_review_passthrough_records": [],
        "conditional_review_passthrough_candidate_count": 0,
        "candidate_rejected_missing_primary_support_count": 0,
        "candidate_rejected_provider_semantics_binding_count": 0,
        "provider_semantics_binding_required": True,
        "provider_semantics_binding_status": "FAIL_CLOSED",
        "hard_block_hits": [reason],
        "review_hits": [],
        "precision_first_exact_rule_policy": True,
        "near_time_or_space_admission_enabled": False,
        "probability_output_allowed": False,
        "same_time_total_order_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "coordinate_is_physical_player_position": False,
        "independent_csv_xml_vote_allowed": False,
        "action_occurrence_candidate_is_event_truth": False,
        "validated_event_identity": False,
        "event_instance_count": 0,
        "count_value_output_allowed": False,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _candidate_primary_support_present(
    candidate: dict[str, Any],
    bundle_by_id: dict[str, dict[str, Any]],
    rule: dict[str, Any],
) -> bool:
    required = {
        _clean(item).casefold()
        for item in rule.get("primary_support_any_labels") or []
        if _clean(item)
    }
    if not required:
        return True
    actor = _clean(candidate.get("actor_identity_candidate_id"))
    team = _clean(candidate.get("team_identity_candidate_id"))
    visible: set[str] = set()
    for raw_id in candidate.get("supporting_action_bundle_candidate_ids") or []:
        bundle = bundle_by_id.get(_clean(raw_id))
        if bundle is None:
            continue
        if _clean(bundle.get("actor_identity_candidate_id")) != actor:
            continue
        if _clean(bundle.get("team_identity_candidate_id")) != team:
            continue
        visible.update(_labels(bundle))
    return bool(required & visible)


def _evidence_by_id(evidence_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _clean(atom.get("evidence_atom_id")): atom
        for atom in evidence_payload.get("evidence_atoms") or []
        if isinstance(atom, dict) and _clean(atom.get("evidence_atom_id"))
    }


def _candidate_semantic_binding_valid(
    candidate: dict[str, Any],
    bundle_by_id: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
    rule: dict[str, Any],
    registry: dict[str, Any],
) -> tuple[bool, list[str]]:
    binding_cfg = registry.get("upstream_semantics_binding") or {}
    required_mapping_status = _clean(binding_cfg.get("semantic_mapping_status_required"))
    label_bindings = {
        _clean(label).casefold(): _clean(rule_id)
        for label, rule_id in (rule.get("semantic_rule_bindings") or {}).items()
        if _clean(label) and _clean(rule_id)
    }
    if not label_bindings:
        return False, []

    observed_rule_ids: set[str] = set()
    matched_bound_label = False
    for raw_id in candidate.get("supporting_action_bundle_candidate_ids") or []:
        bundle = bundle_by_id.get(_clean(raw_id))
        if bundle is None:
            return False, sorted(observed_rule_ids)
        expected_for_bundle = {
            label_bindings[label]
            for label in _labels(bundle)
            if label in label_bindings
        }
        if not expected_for_bundle:
            continue
        matched_bound_label = True
        bundle_rule_ids: set[str] = set()
        for evidence_id in bundle.get("supporting_evidence_atom_ids") or []:
            atom = evidence_by_id.get(_clean(evidence_id))
            if atom is None:
                continue
            if required_mapping_status and _clean(atom.get("semantic_mapping_status")) != required_mapping_status:
                continue
            rule_id = _clean(atom.get("semantic_rule_id"))
            if rule_id:
                bundle_rule_ids.add(rule_id)
                observed_rule_ids.add(rule_id)
        if not expected_for_bundle.issubset(bundle_rule_ids):
            return False, sorted(observed_rule_ids)

    primary_any = {_clean(x) for x in rule.get("primary_semantic_rule_ids_any") or [] if _clean(x)}
    support_any = {_clean(x) for x in rule.get("primary_support_semantic_rule_ids_any") or [] if _clean(x)}
    counterpart_any = {_clean(x) for x in rule.get("counterpart_semantic_rule_ids_any") or [] if _clean(x)}
    if primary_any and not (primary_any & observed_rule_ids):
        return False, sorted(observed_rule_ids)
    if support_any and not (support_any & observed_rule_ids):
        return False, sorted(observed_rule_ids)
    if counterpart_any and not (counterpart_any & observed_rule_ids):
        return False, sorted(observed_rule_ids)
    return matched_bound_label, sorted(observed_rule_ids)


def build_action_occurrence_admission_with_conditional_review(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
    relation_payload: dict[str, Any],
    evidence_payload: dict[str, Any] | None = None,
    registry_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Claim-safe public occurrence admission entrypoint.

    The raw occurrence builder remains an internal deterministic matcher. This wrapper is the
    authority boundary: it preserves upstream taxonomy truth, rejects chronology promotion,
    and requires reviewed evidence-atom semantic-rule bindings before a provider-label rule can
    admit an occurrence candidate.
    """
    registry = registry_payload or occurrence.load_registry()
    binding = _clean(action_payload.get("match_surface_binding_id"))

    if evidence_payload is None:
        return _fail_closed("provider_semantics_evidence_missing", binding)
    if evidence_payload.get("module_id") != EVIDENCE_MODULE_ID:
        return _fail_closed("provider_semantics_evidence_module_id_mismatch", binding)
    if evidence_payload.get("canonical_event_count") != "UNKNOWN":
        return _fail_closed("provider_semantics_evidence_canonical_event_count_claimed", binding)
    if evidence_payload.get("production_release") is True:
        return _fail_closed("provider_semantics_evidence_production_release_claimed", binding)
    if _clean(evidence_payload.get("match_surface_binding_id")) != binding:
        return _fail_closed("provider_semantics_evidence_binding_mismatch", binding)

    for bundle in action_payload.get("action_bundle_candidates") or []:
        if not isinstance(bundle, dict):
            continue
        if bundle.get("source_row_order_is_temporal_truth") is True:
            return _fail_closed("unsafe_source_row_order_truth_admitted", binding)
        if bundle.get("same_time_order_truth_admitted") is True:
            return _fail_closed("unsafe_same_time_order_truth_admitted", binding)

    action_copy = copy.deepcopy(action_payload)
    taxonomy_copy = copy.deepcopy(taxonomy_payload)
    relation_copy = copy.deepcopy(relation_payload)
    evidence_copy = copy.deepcopy(evidence_payload)

    bundle_by_id = {
        _clean(bundle.get("action_bundle_candidate_id")): bundle
        for bundle in action_copy.get("action_bundle_candidates") or []
        if isinstance(bundle, dict) and _clean(bundle.get("action_bundle_candidate_id"))
    }
    evidence_map = _evidence_by_id(evidence_copy)

    passthrough_records: dict[str, dict[str, Any]] = {}
    rules = [rule for rule in registry.get("interaction_rules") or [] if isinstance(rule, dict)]
    for record in taxonomy_copy.get("multi_family_review_records") or []:
        if not isinstance(record, dict) or _clean(record.get("record_status")) != "REVIEW_REQUIRED":
            continue
        classification = _clean(record.get("classification"))
        family_set = _normalized_family_set(record)
        supporting_ids = [_clean(item) for item in record.get("supporting_action_bundle_candidate_ids") or []]
        record_labels: set[str] = set()
        for bundle_id in supporting_ids:
            bundle = bundle_by_id.get(bundle_id)
            if bundle is not None:
                record_labels.update(_labels(bundle))

        matched_rule: dict[str, Any] | None = None
        for rule in rules:
            policy = rule.get("conditional_review_passthrough") or {}
            allowed_classes = {_clean(item) for item in policy.get("allowed_taxonomy_classifications") or [] if _clean(item)}
            forbidden_classes = {_clean(item) for item in policy.get("forbidden_taxonomy_classifications") or [] if _clean(item)}
            allowed_family_sets = {
                tuple(sorted({_clean(item).upper() for item in values if _clean(item)}))
                for values in policy.get("allowed_family_sets") or []
                if isinstance(values, list)
            }
            required_support = {
                _clean(item).casefold()
                for item in policy.get("required_primary_support_labels") or []
                if _clean(item)
            }
            if classification in forbidden_classes:
                continue
            if classification not in allowed_classes:
                continue
            if family_set not in allowed_family_sets:
                continue
            if required_support and not (required_support & record_labels):
                continue
            matched_rule = rule
            break

        if matched_rule is None:
            continue

        record_id = _clean(record.get("multi_family_review_record_id"))
        original_status = _clean(record.get("record_status"))
        record["record_status"] = "PASS_CANDIDATE_CLASSIFICATION"
        passthrough_records[record_id] = {
            "multi_family_review_record_id": record_id,
            "compatibility_rule_id": _clean(matched_rule.get("rule_id")),
            "original_record_status": original_status,
            "original_classification": classification,
            "family_set": list(family_set),
            "supporting_action_bundle_candidate_ids": supporting_ids,
            "passthrough_scope": "OCCURRENCE_ADMISSION_LOCAL_COPY_ONLY",
            "upstream_taxonomy_truth_changed": False,
        }

    payload = occurrence.build_action_occurrence_admission(
        action_copy,
        taxonomy_copy,
        relation_copy,
        registry,
    )

    rule_map = _rule_by_id(registry)
    passthrough_bundle_to_record: dict[str, dict[str, Any]] = {}
    for provenance in passthrough_records.values():
        for bundle_id in provenance.get("supporting_action_bundle_candidate_ids") or []:
            passthrough_bundle_to_record[_clean(bundle_id)] = provenance

    admitted: list[dict[str, Any]] = []
    rejected_missing_primary_support = 0
    rejected_provider_binding = 0
    for candidate in payload.get("action_occurrence_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        rule = rule_map.get(_clean(candidate.get("compatibility_rule_id")), {})
        if not _candidate_primary_support_present(candidate, bundle_by_id, rule):
            rejected_missing_primary_support += 1
            continue
        semantic_ok, observed_rule_ids = _candidate_semantic_binding_valid(
            candidate,
            bundle_by_id,
            evidence_map,
            rule,
            registry,
        )
        if not semantic_ok:
            rejected_provider_binding += 1
            continue
        provenance = []
        seen: set[str] = set()
        for raw_id in candidate.get("supporting_action_bundle_candidate_ids") or []:
            record = passthrough_bundle_to_record.get(_clean(raw_id))
            if record is None:
                continue
            record_id = _clean(record.get("multi_family_review_record_id"))
            if record_id and record_id not in seen:
                seen.add(record_id)
                provenance.append(copy.deepcopy(record))
        candidate["conditional_review_passthrough_used"] = bool(provenance)
        candidate["conditional_review_passthrough_provenance"] = provenance
        candidate["upstream_taxonomy_truth_changed"] = False
        candidate["provider_semantics_binding_status"] = "PASS"
        candidate["provider_semantics_registry_id"] = _clean(
            (registry.get("upstream_semantics_binding") or {}).get("registry_id")
        )
        candidate["supporting_semantic_rule_ids"] = observed_rule_ids
        admitted.append(candidate)

    payload["action_occurrence_candidates"] = admitted
    payload["action_occurrence_candidate_count"] = len(admitted)
    class_counts: dict[str, int] = {}
    interaction_counts: dict[str, int] = {}
    for candidate in admitted:
        admission_class = _clean(candidate.get("admission_class"))
        interaction = _clean(candidate.get("interaction_type"))
        if admission_class:
            class_counts[admission_class] = class_counts.get(admission_class, 0) + 1
        if interaction:
            interaction_counts[interaction] = interaction_counts.get(interaction, 0) + 1
    payload["admission_class_counts"] = dict(sorted(class_counts.items()))
    payload["interaction_type_counts"] = dict(sorted(interaction_counts.items()))
    payload["conditional_review_passthrough_record_count"] = len(passthrough_records)
    payload["conditional_review_passthrough_records"] = list(passthrough_records.values())
    payload["conditional_review_passthrough_candidate_count"] = sum(
        bool(candidate.get("conditional_review_passthrough_used")) for candidate in admitted
    )
    payload["candidate_rejected_missing_primary_support_count"] = rejected_missing_primary_support
    payload["candidate_rejected_provider_semantics_binding_count"] = rejected_provider_binding
    payload["conditional_review_passthrough_changes_upstream_taxonomy_truth"] = False
    payload["provider_semantics_binding_required"] = True
    payload["provider_semantics_registry_id"] = _clean(
        (registry.get("upstream_semantics_binding") or {}).get("registry_id")
    )
    payload["provider_semantics_binding_status"] = "PASS" if admitted or not payload.get("action_occurrence_candidates") else "REVIEW_REQUIRED"
    reviews = list(payload.get("review_hits") or [])
    if passthrough_records:
        reviews.append("conditional_review_passthrough_used")
    if rejected_missing_primary_support:
        reviews.append("candidate_rejected_missing_primary_support")
    if rejected_provider_binding:
        reviews.append("candidate_rejected_provider_semantics_binding")
    payload["review_hits"] = sorted(set(reviews))
    return payload
