from __future__ import annotations

from collections import Counter
from typing import Any

CLAIM_CEILING = "SEMANTICALLY_RECONSTRUCTED_FOOTBALL_OCCURRENCE_CANDIDATE"
CARDINALITY_PATTERNS = (
    "ONE_OBSERVATION_ONE_OCCURRENCE",
    "MULTIPLE_OBSERVATIONS_ONE_OCCURRENCE",
    "ONE_OBSERVATION_MULTIPLE_OCCURRENCE_CANDIDATES",
    "CARDINALITY_AMBIGUOUS",
    "NOT_RECONSTRUCTABLE",
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _labels(bundle: dict[str, Any]) -> set[str]:
    return {
        _clean(value).casefold()
        for value in (bundle.get("raw_labels") or []) + (bundle.get("normalized_labels") or [])
        if _clean(value)
    }


def _evidence_map(evidence_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _clean(atom.get("evidence_atom_id")): atom
        for atom in evidence_payload.get("evidence_atoms") or []
        if isinstance(atom, dict) and _clean(atom.get("evidence_atom_id"))
    }


def _semantic_rule_map(rule: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    result: dict[str, tuple[str, dict[str, Any]]] = {}
    for label, meta in (rule.get("semantic_labels") or {}).items():
        if isinstance(meta, dict) and _clean(label):
            result[_clean(label).casefold()] = (_clean(label), meta)
    return result


def _record_base(
    *,
    bundle: dict[str, Any],
    source_observation_refs: list[str],
    provider_row_refs: list[str],
    pattern: str,
    rule_id: str | None,
    rule_version: str | None,
    contradiction_state: str,
    information_loss_state: str,
    alternative_cardinality_state: str,
    semantic_components: list[dict[str, Any]],
    occurrence_candidate_id: str | None,
) -> dict[str, Any]:
    family = _clean(bundle.get("action_family_candidate")).upper()
    qualifiers: list[str] = []
    outcomes: list[str] = []
    contexts: list[str] = []
    for component in semantic_components:
        if not isinstance(component, dict):
            continue
        outcome = _clean(component.get("outcome"))
        if outcome:
            outcomes.append(outcome)
        for key in ("direction", "distance", "progression", "key_action"):
            value = _clean(component.get(key))
            if value:
                qualifiers.append(f"{key}:{value}")
        value = _clean(component.get("zone_context"))
        if value:
            contexts.append(value)
    return {
        "occurrence_candidate_id": occurrence_candidate_id,
        "source_observation_refs": sorted(set(source_observation_refs)),
        "provider_row_refs": sorted(set(provider_row_refs)),
        "source_observation_count": len(set(source_observation_refs)),
        "provider_row_ref_count": len(set(provider_row_refs)),
        "cardinality_pattern": pattern,
        "action_family_candidate": family or None,
        "actor_binding": _clean(bundle.get("actor_identity_candidate_id")) or None,
        "team_binding": _clean(bundle.get("team_identity_candidate_id")) or None,
        "temporal_binding": {
            "period_candidate": bundle.get("period_candidate"),
            "start_candidate": bundle.get("start_candidate"),
            "end_candidate": bundle.get("end_candidate"),
        },
        "semantic_binding_refs": sorted(
            {
                _clean(component.get("semantic_rule_id"))
                for component in semantic_components
                if isinstance(component, dict) and _clean(component.get("semantic_rule_id"))
            }
        ),
        "shared_base_construct": family or None,
        "qualifier_attributes": sorted(set(qualifiers)),
        "outcome_attributes": sorted(set(outcomes)),
        "context_attributes": sorted(set(contexts)),
        "contradiction_state": contradiction_state,
        "collapse_rule_id": rule_id,
        "collapse_rule_version": rule_version,
        "information_loss_state": information_loss_state,
        "alternative_cardinality_state": alternative_cardinality_state,
        "cardinality_resolution_is_physical_action_truth": False,
        "cardinality_resolution_is_canonical_event_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "claim_ceiling": CLAIM_CEILING,
    }


def bind_observation_occurrence_cardinality(
    action_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    registry: dict[str, Any],
    occurrence_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_by_id = _evidence_map(evidence_payload)
    rule_version = _clean(registry.get("version")) or None
    required_mapping_status = _clean(
        (registry.get("upstream_semantics_binding") or {}).get("semantic_mapping_status_required")
    )
    rules = {
        _clean(rule.get("action_family")).upper(): rule
        for rule in registry.get("intra_actor_occurrence_rules") or []
        if isinstance(rule, dict) and _clean(rule.get("rule_id")) and _clean(rule.get("action_family"))
    }
    candidates_by_bundle: dict[str, list[dict[str, Any]]] = {}
    for candidate in occurrence_candidates:
        if not isinstance(candidate, dict):
            continue
        for bundle_id in candidate.get("supporting_action_bundle_candidate_ids") or []:
            cleaned = _clean(bundle_id)
            if cleaned:
                candidates_by_bundle.setdefault(cleaned, []).append(candidate)

    records: list[dict[str, Any]] = []
    hard_blocks: list[str] = []
    review_hits: list[str] = []
    state_counts: Counter[str] = Counter()
    annotated_ids: set[str] = set()

    for bundle in action_payload.get("action_bundle_candidates") or []:
        if not isinstance(bundle, dict):
            continue
        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        if not bundle_id:
            continue
        family = _clean(bundle.get("action_family_candidate")).upper()
        rule = rules.get(family)
        if rule is None:
            continue
        label_map = _semantic_rule_map(rule)
        recognized = [
            (label, meta)
            for folded, (label, meta) in label_map.items()
            if folded in _labels(bundle)
        ]
        minimum = int(rule.get("minimum_distinct_semantic_labels") or 2)
        if len(recognized) < minimum:
            continue

        semantic_components = [
            {
                "label": label,
                "semantic_rule_id": _clean(meta.get("semantic_rule_id")) or None,
                "outcome": _clean(meta.get("outcome")) or None,
                "direction": _clean(meta.get("direction")) or None,
                "distance": _clean(meta.get("distance")) or None,
                "zone_context": _clean(meta.get("zone_context")) or None,
                "progression": _clean(meta.get("progression")) or None,
                "key_action": _clean(meta.get("key_action")) or None,
            }
            for label, meta in sorted(recognized, key=lambda item: item[0].casefold())
        ]
        expected_rule_ids = {
            _clean(meta.get("semantic_rule_id"))
            for _, meta in recognized
            if _clean(meta.get("semantic_rule_id"))
        }
        observed_rule_ids: set[str] = set()
        source_observation_refs: list[str] = []
        for evidence_id in bundle.get("supporting_evidence_atom_ids") or []:
            cleaned_id = _clean(evidence_id)
            atom = evidence_by_id.get(cleaned_id)
            if atom is None:
                continue
            if required_mapping_status and _clean(atom.get("semantic_mapping_status")) != required_mapping_status:
                continue
            semantic_rule_id = _clean(atom.get("semantic_rule_id"))
            if semantic_rule_id in expected_rule_ids:
                observed_rule_ids.add(semantic_rule_id)
                source_observation_refs.append(cleaned_id)
        provider_rows = [_clean(value) for value in bundle.get("provider_row_id_candidates") or [] if _clean(value)]
        outcomes = sorted({_clean(component.get("outcome")) for component in semantic_components if _clean(component.get("outcome"))})

        matched_candidates = [
            row for row in candidates_by_bundle.get(bundle_id, [])
            if _clean(row.get("admission_class")) == "EXACT_SAME_ACTOR_SEMANTIC_COLLAPSE"
        ]

        if not expected_rule_ids or not expected_rule_ids.issubset(observed_rule_ids):
            record = _record_base(
                bundle=bundle,
                source_observation_refs=source_observation_refs,
                provider_row_refs=provider_rows,
                pattern="NOT_RECONSTRUCTABLE",
                rule_id=_clean(rule.get("rule_id")) or None,
                rule_version=rule_version,
                contradiction_state="NOT_EVALUATED_PROVIDER_BINDING_INCOMPLETE",
                information_loss_state="NOT_APPLICABLE_NO_COLLAPSE",
                alternative_cardinality_state="MULTIPLE_ACTIONS_POSSIBLE_OR_UNRESOLVED",
                semantic_components=semantic_components,
                occurrence_candidate_id=None,
            )
            records.append(record)
            state_counts[record["cardinality_pattern"]] += 1
            review_hits.append("cardinality_not_reconstructable_provider_semantics_binding")
            continue

        if len(outcomes) > 1:
            record = _record_base(
                bundle=bundle,
                source_observation_refs=source_observation_refs,
                provider_row_refs=provider_rows,
                pattern="CARDINALITY_AMBIGUOUS",
                rule_id=_clean(rule.get("rule_id")) or None,
                rule_version=rule_version,
                contradiction_state="CONTRADICTORY_OUTCOME_SEMANTICS",
                information_loss_state="NOT_APPLICABLE_NO_COLLAPSE",
                alternative_cardinality_state="MULTIPLE_ACTIONS_POSSIBLE_OR_CONTRADICTORY_ANNOTATIONS",
                semantic_components=semantic_components,
                occurrence_candidate_id=None,
            )
            records.append(record)
            state_counts[record["cardinality_pattern"]] += 1
            review_hits.append("cardinality_ambiguous_contradictory_semantics")
            continue

        if len(matched_candidates) != 1:
            record = _record_base(
                bundle=bundle,
                source_observation_refs=source_observation_refs,
                provider_row_refs=provider_rows,
                pattern="NOT_RECONSTRUCTABLE",
                rule_id=_clean(rule.get("rule_id")) or None,
                rule_version=rule_version,
                contradiction_state="NONE_VISIBLE",
                information_loss_state="NOT_APPLICABLE_NO_ADMITTED_COLLAPSE",
                alternative_cardinality_state="CARDINALITY_RESOLUTION_WITHHELD",
                semantic_components=semantic_components,
                occurrence_candidate_id=None,
            )
            records.append(record)
            state_counts[record["cardinality_pattern"]] += 1
            review_hits.append("compatible_cardinality_bundle_without_unique_occurrence")
            continue

        candidate = matched_candidates[0]
        candidate_components = [row for row in candidate.get("semantic_components") or [] if isinstance(row, dict)]
        expected_labels = sorted(_clean(row.get("label")).casefold() for row in semantic_components if _clean(row.get("label")))
        observed_labels = sorted(_clean(row.get("label")).casefold() for row in candidate_components if _clean(row.get("label")))
        expected_semantic_ids = sorted(expected_rule_ids)
        observed_semantic_ids = sorted(
            {
                _clean(row.get("semantic_rule_id"))
                for row in candidate_components
                if _clean(row.get("semantic_rule_id"))
            }
        )
        lossless = expected_labels == observed_labels and expected_semantic_ids == observed_semantic_ids
        info_state = "LOSSLESS_SEMANTIC_COMPONENT_PRESERVATION" if lossless else "INFORMATION_LOSS_DETECTED"
        if not lossless:
            hard_blocks.append(f"cardinality_information_loss:{bundle_id}")

        record = _record_base(
            bundle=bundle,
            source_observation_refs=source_observation_refs,
            provider_row_refs=provider_rows,
            pattern="MULTIPLE_OBSERVATIONS_ONE_OCCURRENCE",
            rule_id=_clean(rule.get("rule_id")) or None,
            rule_version=rule_version,
            contradiction_state="NONE_VISIBLE",
            information_loss_state=info_state,
            alternative_cardinality_state="PHYSICAL_MULTIPLE_ACTIONS_NOT_EXCLUDED_WITHOUT_EXTERNAL_VERIFICATION",
            semantic_components=candidate_components,
            occurrence_candidate_id=_clean(candidate.get("action_occurrence_candidate_id")) or None,
        )
        records.append(record)
        state_counts[record["cardinality_pattern"]] += 1
        candidate["observation_occurrence_cardinality"] = record
        annotated_ids.add(_clean(candidate.get("action_occurrence_candidate_id")))

    for candidate in occurrence_candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_id = _clean(candidate.get("action_occurrence_candidate_id"))
        if not candidate_id or candidate_id in annotated_ids:
            continue
        if _clean(candidate.get("admission_class")) != "EXACT_SINGLE_ACTION_ANCHOR_SEMANTIC_ADMISSION":
            continue
        source_refs = [_clean(value) for value in candidate.get("supporting_evidence_atom_ids") or [] if _clean(value)]
        provider_rows = [_clean(value) for value in candidate.get("provider_row_id_candidates") or [] if _clean(value)]
        pattern = "ONE_OBSERVATION_ONE_OCCURRENCE" if len(source_refs) == 1 else "CARDINALITY_AMBIGUOUS"
        record = {
            "occurrence_candidate_id": candidate_id,
            "source_observation_refs": sorted(set(source_refs)),
            "provider_row_refs": sorted(set(provider_rows)),
            "source_observation_count": len(set(source_refs)),
            "provider_row_ref_count": len(set(provider_rows)),
            "cardinality_pattern": pattern,
            "action_family_candidate": _clean(candidate.get("primary_family_candidate")) or None,
            "actor_binding": _clean(candidate.get("actor_identity_candidate_id")) or None,
            "team_binding": _clean(candidate.get("team_identity_candidate_id")) or None,
            "temporal_binding": candidate.get("temporal_relation") or {},
            "semantic_binding_refs": sorted({_clean(value) for value in candidate.get("supporting_semantic_rule_ids") or [] if _clean(value)}),
            "shared_base_construct": _clean(candidate.get("primary_family_candidate")) or None,
            "qualifier_attributes": [],
            "outcome_attributes": [],
            "context_attributes": [],
            "contradiction_state": "NONE_VISIBLE" if pattern == "ONE_OBSERVATION_ONE_OCCURRENCE" else "SOURCE_OBSERVATION_COUNT_NOT_ONE",
            "collapse_rule_id": _clean(candidate.get("compatibility_rule_id")) or None,
            "collapse_rule_version": "1.0.0",
            "information_loss_state": "SINGLE_REVIEWED_ANCHOR_PRESERVED" if pattern == "ONE_OBSERVATION_ONE_OCCURRENCE" else "NOT_APPLICABLE_AMBIGUOUS",
            "alternative_cardinality_state": "PHYSICAL_ACTION_TRUTH_UNRESOLVED",
            "cardinality_resolution_is_physical_action_truth": False,
            "cardinality_resolution_is_canonical_event_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": CLAIM_CEILING,
        }
        records.append(record)
        state_counts[pattern] += 1
        candidate["observation_occurrence_cardinality"] = record
        if pattern == "CARDINALITY_AMBIGUOUS":
            review_hits.append("single_anchor_cardinality_ambiguous")

    out_of_scope_interactions = sum(
        1
        for candidate in occurrence_candidates
        if isinstance(candidate, dict) and _clean(candidate.get("occurrence_topology")) != "SINGLE_ACTOR_ACTION"
    )
    return {
        "records": records,
        "record_count": len(records),
        "state_counts": dict(sorted(state_counts.items())),
        "state_vocabulary": list(CARDINALITY_PATTERNS),
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
        "out_of_scope_interaction_occurrence_candidate_count": out_of_scope_interactions,
        "row_count_is_action_count": False,
        "label_count_is_action_count": False,
        "same_actor_same_timestamp_is_single_action_authority": False,
        "shared_base_label_is_sufficient_collapse_authority": False,
        "multiple_rows_automatically_single_occurrence": False,
        "xlsx_can_create_action_identity": False,
        "cardinality_resolution_is_physical_action_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
