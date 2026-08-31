from __future__ import annotations

import copy
from typing import Any

from hpfa.modules.core.action_occurrence_admission_lite.src import action_occurrence_admission as occurrence


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


def build_action_occurrence_admission_with_conditional_review(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
    relation_payload: dict[str, Any],
    registry_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply narrowly allowlisted taxonomy-review passthrough for occurrence adjudication only.

    Input payloads remain unchanged. The copied taxonomy record is locally eligible only when
    its exact classification, family set, and required support labels satisfy a reviewed rule.
    This does not alter upstream taxonomy truth or promote a canonical event.
    """
    registry = registry_payload or occurrence.load_registry()
    action_copy = copy.deepcopy(action_payload)
    taxonomy_copy = copy.deepcopy(taxonomy_payload)
    relation_copy = copy.deepcopy(relation_payload)

    bundle_by_id = {
        _clean(bundle.get("action_bundle_candidate_id")): bundle
        for bundle in action_copy.get("action_bundle_candidates") or []
        if isinstance(bundle, dict) and _clean(bundle.get("action_bundle_candidate_id"))
    }

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
    for candidate in payload.get("action_occurrence_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        rule = rule_map.get(_clean(candidate.get("compatibility_rule_id")), {})
        if not _candidate_primary_support_present(candidate, bundle_by_id, rule):
            rejected_missing_primary_support += 1
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
    payload["conditional_review_passthrough_changes_upstream_taxonomy_truth"] = False
    reviews = list(payload.get("review_hits") or [])
    if passthrough_records:
        reviews.append("conditional_review_passthrough_used")
    if rejected_missing_primary_support:
        reviews.append("candidate_rejected_missing_primary_support")
    payload["review_hits"] = sorted(set(reviews))
    return payload
