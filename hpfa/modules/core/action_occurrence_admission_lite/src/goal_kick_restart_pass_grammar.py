from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REGISTRY_ID = "goal_kick_restart_pass_semantic_compatibility_v1"
CLAIM_CEILING = "GOAL_KICK_SEMANTIC_OCCURRENCE_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number_key(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    try:
        return f"{float(text):.6f}"
    except (TypeError, ValueError):
        return text


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parents[1]
        / "registry"
        / "goal_kick_restart_pass_semantic_compatibility_v1.json"
    )
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("registry_id") != REGISTRY_ID:
        raise ValueError("goal_kick_restart_pass_registry_invalid")
    return payload


def _labels(bundle: dict[str, Any]) -> set[str]:
    return {
        _clean(value).casefold()
        for value in (bundle.get("raw_labels") or []) + (bundle.get("normalized_labels") or [])
        if _clean(value)
    }


def _exact_core(bundle: dict[str, Any]) -> tuple[str, ...]:
    return (
        _clean(bundle.get("match_surface_binding_id")),
        _clean(bundle.get("source_role")),
        _clean(bundle.get("team_identity_candidate_id")),
        _clean(bundle.get("actor_identity_candidate_id")),
        _clean(bundle.get("period_candidate")),
        _number_key(bundle.get("start_candidate")),
        _number_key(bundle.get("end_candidate")),
        _number_key(bundle.get("pos_x_candidate")),
        _number_key(bundle.get("pos_y_candidate")),
    )


def _evidence_by_id(evidence_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _clean(atom.get("evidence_atom_id")): atom
        for atom in evidence_payload.get("evidence_atoms") or []
        if isinstance(atom, dict) and _clean(atom.get("evidence_atom_id"))
    }


def _bundle_semantic_rule_ids(
    bundle: dict[str, Any],
    evidence_map: dict[str, dict[str, Any]],
    *,
    required_source_role: str,
) -> tuple[set[str], bool]:
    observed: set[str] = set()
    valid = True
    for raw_id in bundle.get("supporting_evidence_atom_ids") or []:
        evidence_id = _clean(raw_id)
        atom = evidence_map.get(evidence_id)
        if atom is None:
            valid = False
            continue
        checks = (
            atom.get("semantic_mapping_status") == "EXACT_REVIEWED_CANDIDATE",
            atom.get("source_role") == required_source_role,
            atom.get("validated_event_identity") is not True,
            atom.get("event_instance_allowed") is not True,
            atom.get("physical_action_identity_truth") is not True,
            atom.get("canonical_event_count") in {None, "UNKNOWN"},
        )
        if not all(checks):
            valid = False
        semantic_rule_id = _clean(atom.get("semantic_rule_id"))
        if semantic_rule_id:
            observed.add(semantic_rule_id)
        else:
            valid = False
    return observed, valid


def _bundle_base_eligible(bundle: dict[str, Any], *, source_role: str, review_hit: str) -> bool:
    if bundle.get("source_role") != source_role:
        return False
    if bundle.get("same_role_exact_grouping") is not True:
        return False
    if bundle.get("cross_role_fusion_allowed") is True:
        return False
    if bundle.get("validated_event_identity") is True or bundle.get("event_instance_allowed") is True:
        return False
    if bundle.get("canonical_event_count") not in {None, "UNKNOWN"}:
        return False
    if _clean(bundle.get("bundle_status")) != "REVIEW_REQUIRED":
        return False
    review_hits = {_clean(value) for value in bundle.get("review_hits") or [] if _clean(value)}
    return review_hits == {review_hit}


def build_goal_kick_restart_pass_candidates(
    action_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind only exact reviewed goalkeeper goal-kick RESTART+PASS annotation clusters.

    Provider distance buckets are preserved as provider classifications. They are not
    promoted to measured displacement, tactical strategy, build-up intention or
    canonical physical-action truth.
    """
    rule = registry or load_registry()
    source_role = _clean(rule.get("source_role"))
    review_hit = _clean(rule.get("required_upstream_review_hit"))
    evidence_map = _evidence_by_id(evidence_payload)
    common = rule.get("common_restart_label") or {}
    common_label = _clean(common.get("label")).casefold()
    common_rule_id = _clean(common.get("semantic_rule_id"))
    distance_patterns = rule.get("distance_patterns") or {}

    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for bundle in action_payload.get("action_bundle_candidates") or []:
        if not isinstance(bundle, dict):
            continue
        if _bundle_base_eligible(bundle, source_role=source_role, review_hit=review_hit):
            grouped[_exact_core(bundle)].append(bundle)

    candidates: list[dict[str, Any]] = []
    rejected = Counter()
    for core, bundles in sorted(grouped.items()):
        by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for bundle in bundles:
            family = _clean(bundle.get("action_family_candidate")).upper()
            if family:
                by_family[family].append(bundle)

        if set(by_family) != {"PASS", "RESTART"}:
            continue
        if len(by_family["PASS"]) != 1 or len(by_family["RESTART"]) != 1:
            rejected["family_bundle_cardinality_not_exact"] += 1
            continue

        pass_bundle = by_family["PASS"][0]
        restart_bundle = by_family["RESTART"][0]
        restart_labels = _labels(restart_bundle)
        pass_labels = _labels(pass_bundle)

        matched: tuple[str, dict[str, Any], dict[str, Any]] | None = None
        for distance, pattern in sorted(distance_patterns.items()):
            if not isinstance(pattern, dict):
                continue
            restart_distance_label = _clean(pattern.get("restart_label")).casefold()
            if restart_labels != {common_label, restart_distance_label}:
                continue
            for pass_pattern in pattern.get("pass_patterns") or []:
                if not isinstance(pass_pattern, dict):
                    continue
                expected_pass_labels = {
                    _clean(value).casefold()
                    for value in pass_pattern.get("labels") or []
                    if _clean(value)
                }
                if pass_labels == expected_pass_labels:
                    matched = (_clean(distance).upper(), pattern, pass_pattern)
                    break
            if matched is not None:
                break

        if matched is None:
            continue

        distance, distance_pattern, pass_pattern = matched
        expected_restart_rule_ids = {
            common_rule_id,
            _clean(distance_pattern.get("restart_semantic_rule_id")),
        }
        expected_pass_rule_ids = {
            _clean(value)
            for value in pass_pattern.get("semantic_rule_ids") or []
            if _clean(value)
        }
        observed_restart_ids, restart_binding_valid = _bundle_semantic_rule_ids(
            restart_bundle, evidence_map, required_source_role=source_role
        )
        observed_pass_ids, pass_binding_valid = _bundle_semantic_rule_ids(
            pass_bundle, evidence_map, required_source_role=source_role
        )
        if (
            not restart_binding_valid
            or not pass_binding_valid
            or observed_restart_ids != expected_restart_rule_ids
            or observed_pass_ids != expected_pass_rule_ids
        ):
            rejected["provider_semantics_binding_mismatch"] += 1
            continue

        bundle_ids = sorted(
            [
                _clean(restart_bundle.get("action_bundle_candidate_id")),
                _clean(pass_bundle.get("action_bundle_candidate_id")),
            ]
        )
        evidence_ids = sorted(
            {
                _clean(value)
                for bundle in (restart_bundle, pass_bundle)
                for value in bundle.get("supporting_evidence_atom_ids") or []
                if _clean(value)
            }
        )
        provider_rows = sorted(
            {
                _clean(value)
                for bundle in (restart_bundle, pass_bundle)
                for value in bundle.get("provider_row_id_candidates") or []
                if _clean(value)
            }
        )
        raw_labels = sorted(
            {
                _clean(value)
                for bundle in (restart_bundle, pass_bundle)
                for value in bundle.get("raw_labels") or []
                if _clean(value)
            }
        )
        semantic_rule_ids = sorted(expected_restart_rule_ids | expected_pass_rule_ids)
        outcome = _clean(pass_pattern.get("outcome")) or "UNKNOWN"
        bucket_text = _clean(distance_pattern.get("provider_bucket_text"))

        semantic_components = [
            {
                "label": _clean(common.get("label")),
                "semantic_rule_id": common_rule_id,
                "semantic_role": "RESTART_BASE",
            },
            {
                "label": _clean(distance_pattern.get("restart_label")),
                "semantic_rule_id": _clean(distance_pattern.get("restart_semantic_rule_id")),
                "semantic_role": "PROVIDER_DISTANCE_BUCKET",
                "provider_distance_bucket_candidate": distance,
                "provider_bucket_text": bucket_text,
            },
        ]
        for label, semantic_id in zip(
            pass_pattern.get("labels") or [],
            pass_pattern.get("semantic_rule_ids") or [],
        ):
            semantic_components.append(
                {
                    "label": _clean(label),
                    "semantic_rule_id": _clean(semantic_id),
                    "semantic_role": "PASS_QUALIFIER_OR_OUTCOME",
                }
            )

        occurrence_id = "aoc_goal_kick_" + _digest(
            core,
            bundle_ids,
            semantic_rule_ids,
            rule.get("registry_id"),
            rule.get("version"),
        )[:24]
        cardinality_record = {
            "occurrence_candidate_id": occurrence_id,
            "source_observation_refs": evidence_ids,
            "provider_row_refs": provider_rows,
            "source_observation_count": len(evidence_ids),
            "provider_row_ref_count": len(provider_rows),
            "cardinality_pattern": "MULTIPLE_OBSERVATIONS_ONE_OCCURRENCE",
            "action_family_candidate": "RESTART",
            "actor_binding": restart_bundle.get("actor_identity_candidate_id"),
            "team_binding": restart_bundle.get("team_identity_candidate_id"),
            "temporal_binding": {
                "period_candidate": restart_bundle.get("period_candidate"),
                "start_candidate": restart_bundle.get("start_candidate"),
                "end_candidate": restart_bundle.get("end_candidate"),
            },
            "semantic_binding_refs": semantic_rule_ids,
            "shared_base_construct": "GOAL_KICK_RESTART_CANDIDATE",
            "qualifier_attributes": [
                "restart_type:GOAL_KICK",
                f"provider_distance_bucket:{distance}",
            ],
            "outcome_attributes": [outcome] if outcome != "UNKNOWN" else [],
            "context_attributes": [],
            "contradiction_state": "NONE_VISIBLE",
            "collapse_rule_id": "goal_kick_restart_pass_annotation_collapse_exact_v1",
            "collapse_rule_version": _clean(rule.get("version")) or None,
            "information_loss_state": "LOSSLESS_REVIEWED_GOAL_KICK_SEMANTIC_COMPONENT_PRESERVATION",
            "alternative_cardinality_state": "PHYSICAL_ACTION_TRUTH_UNRESOLVED_WITHOUT_EXTERNAL_VERIFICATION",
            "cardinality_resolution_is_physical_action_truth": False,
            "cardinality_resolution_is_canonical_event_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": "SEMANTICALLY_RECONSTRUCTED_FOOTBALL_OCCURRENCE_CANDIDATE",
        }
        candidates.append(
            {
                "action_occurrence_candidate_id": occurrence_id,
                "match_surface_binding_id": restart_bundle.get("match_surface_binding_id"),
                "admission_class": "EXACT_GOAL_KICK_RESTART_PASS_SEMANTIC_BINDING",
                "interaction_type": "GOAL_KICK_RESTART_PASS_SEMANTIC_CANDIDATE",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "compatibility_rule_id": "goal_kick_restart_pass_annotation_collapse_exact_v1",
                "primary_family_candidate": "RESTART",
                "team_identity_candidate_id": restart_bundle.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": restart_bundle.get("actor_identity_candidate_id"),
                "opponent_team_identity_candidate_id": None,
                "opponent_identity_candidate_id": None,
                "supporting_action_bundle_candidate_ids": bundle_ids,
                "supporting_evidence_atom_ids": evidence_ids,
                "provider_row_id_candidates": provider_rows,
                "action_family_candidates": ["PASS", "RESTART"],
                "raw_labels": raw_labels,
                "semantic_components": semantic_components,
                "attributes": {
                    "restart_type_candidate": "GOAL_KICK",
                    "provider_distance_bucket_candidate": distance,
                    "provider_distance_bucket_text": bucket_text,
                    "pass_outcome_candidate": outcome,
                    "provider_distance_bucket_basis": "REVIEWED_PROVIDER_LABEL_CLASSIFICATION",
                    "provider_distance_bucket_is_measured_physical_distance": False,
                    "provider_distance_bucket_is_ball_displacement_truth": False,
                    "provider_distance_bucket_is_tactical_strategy_truth": False,
                    "provider_distance_bucket_is_build_up_intention_truth": False,
                },
                "temporal_relation": {
                    "period_candidate": restart_bundle.get("period_candidate"),
                    "start_candidate": restart_bundle.get("start_candidate"),
                    "end_candidate": restart_bundle.get("end_candidate"),
                    "relation": "EXACT_SAME_ACTOR_GOAL_KICK_ANNOTATION_CORE",
                    "internal_order": "UNKNOWN",
                },
                "location": {
                    "pos_x_candidate": restart_bundle.get("pos_x_candidate"),
                    "pos_y_candidate": restart_bundle.get("pos_y_candidate"),
                    "semantic_role": "ANNOTATION_ANCHOR_LOCATION_CANDIDATE",
                    "physical_player_position_truth": False,
                },
                "relation_bundle": None,
                "counterevidence": [],
                "alternative_explanations": [
                    "provider annotations may encode one semantic football occurrence without establishing canonical physical-action identity",
                    "provider distance bucket may be a provider classification rather than independently measured HPFA displacement"
                ],
                "withdrawal_conditions": [
                    "provider_goal_kick_semantic_rule_binding_revised",
                    "exact_same_actor_time_anchor_binding_revised",
                    "goal_kick_distance_bucket_definition_revised"
                ],
                "grammar_decision": "ONE_GOAL_KICK_OCCURRENCE_CANDIDATE_RESTART_PLUS_PASS_SEMANTICS",
                "provider_semantics_binding_status": "PASS",
                "provider_semantics_registry_id": _clean(rule.get("provider_semantics_registry_id")) or None,
                "supporting_semantic_rule_ids": semantic_rule_ids,
                "observation_occurrence_cardinality": cardinality_record,
                "conditional_review_passthrough_used": False,
                "conditional_review_passthrough_provenance": [],
                "upstream_taxonomy_truth_changed": False,
                "admission_score": None,
                "probability_output_allowed": False,
                "independent_support_vote_count": 0,
                "same_time_total_order_allowed": False,
                "same_timestamp_alone_is_merge_authority": False,
                "source_row_order_is_temporal_truth": False,
                "provider_distance_bucket_is_measured_physical_distance": False,
                "provider_distance_bucket_is_tactical_strategy_truth": False,
                "action_occurrence_candidate_is_event_truth": False,
                "physical_action_identity_truth": False,
                "validated_event_identity": False,
                "event_instance_allowed": False,
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    review_hits: list[str] = []
    if rejected.get("provider_semantics_binding_mismatch"):
        review_hits.append("goal_kick_candidate_rejected_provider_semantics_binding")
    return {
        "action_occurrence_candidates": candidates,
        "action_occurrence_candidate_count": len(candidates),
        "provider_distance_bucket_counts": dict(
            sorted(Counter(
                _clean(row.get("attributes", {}).get("provider_distance_bucket_candidate"))
                for row in candidates
                if _clean(row.get("attributes", {}).get("provider_distance_bucket_candidate"))
            ).items())
        ),
        "pass_outcome_counts": dict(
            sorted(Counter(
                _clean(row.get("attributes", {}).get("pass_outcome_candidate"))
                for row in candidates
                if _clean(row.get("attributes", {}).get("pass_outcome_candidate"))
            ).items())
        ),
        "rejected_reason_counts": dict(sorted(rejected.items())),
        "review_hits": review_hits,
        "goal_kick_exact_cross_bundle_semantic_binding_allowed": True,
        "global_cross_bundle_action_grammar_merge_allowed": False,
        "same_timestamp_alone_is_merge_authority": False,
        "near_time_or_space_admission_enabled": False,
        "provider_distance_bucket_is_measured_physical_distance": False,
        "provider_distance_bucket_is_tactical_strategy_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def bind_goal_kick_restart_pass_grammar(
    occurrence_payload: dict[str, Any],
    action_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> dict[str, Any]:
    """Append exact goal-kick semantic occurrence candidates to current occurrence product."""
    if occurrence_payload.get("status") == "FAIL_CLOSED":
        return occurrence_payload

    result = build_goal_kick_restart_pass_candidates(action_payload, evidence_payload)
    goal_candidates = [
        row
        for row in result.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]
    existing = [
        row
        for row in occurrence_payload.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]
    existing_bundle_ids = {
        _clean(bundle_id)
        for row in existing
        for bundle_id in row.get("supporting_action_bundle_candidate_ids") or []
        if _clean(bundle_id)
    }

    admitted: list[dict[str, Any]] = []
    duplicate_support_count = 0
    for candidate in goal_candidates:
        bundle_ids = {
            _clean(value)
            for value in candidate.get("supporting_action_bundle_candidate_ids") or []
            if _clean(value)
        }
        if bundle_ids & existing_bundle_ids:
            duplicate_support_count += 1
            continue
        admitted.append(candidate)
        existing_bundle_ids.update(bundle_ids)

    combined = existing + admitted
    occurrence_payload["action_occurrence_candidates"] = combined
    occurrence_payload["action_occurrence_candidate_count"] = len(combined)
    occurrence_payload["goal_kick_restart_pass_candidate_count"] = len(admitted)
    occurrence_payload["goal_kick_restart_pass_candidates"] = admitted
    occurrence_payload["goal_kick_provider_distance_bucket_counts"] = result.get(
        "provider_distance_bucket_counts"
    ) or {}
    occurrence_payload["goal_kick_pass_outcome_counts"] = result.get(
        "pass_outcome_counts"
    ) or {}
    occurrence_payload["goal_kick_rejected_reason_counts"] = result.get(
        "rejected_reason_counts"
    ) or {}
    occurrence_payload["goal_kick_duplicate_support_rejection_count"] = duplicate_support_count
    occurrence_payload["goal_kick_exact_cross_bundle_semantic_binding_allowed"] = True
    occurrence_payload["global_cross_bundle_action_grammar_merge_allowed"] = False
    occurrence_payload["provider_goal_kick_distance_bucket_is_measured_physical_distance"] = False
    occurrence_payload["provider_goal_kick_distance_bucket_is_tactical_strategy_truth"] = False
    occurrence_payload["provider_goal_kick_distance_bucket_is_build_up_intention_truth"] = False

    class_counts = Counter()
    interaction_counts = Counter()
    for candidate in combined:
        admission_class = _clean(candidate.get("admission_class"))
        interaction_type = _clean(candidate.get("interaction_type"))
        if admission_class:
            class_counts[admission_class] += 1
        if interaction_type:
            interaction_counts[interaction_type] += 1
    occurrence_payload["admission_class_counts"] = dict(sorted(class_counts.items()))
    occurrence_payload["interaction_type_counts"] = dict(sorted(interaction_counts.items()))

    extra_cardinality = [
        row.get("observation_occurrence_cardinality")
        for row in admitted
        if isinstance(row.get("observation_occurrence_cardinality"), dict)
    ]
    cardinality_records = [
        row
        for row in occurrence_payload.get("observation_occurrence_cardinality_records") or []
        if isinstance(row, dict)
    ]
    cardinality_records.extend(extra_cardinality)
    occurrence_payload["observation_occurrence_cardinality_records"] = cardinality_records
    occurrence_payload["observation_occurrence_cardinality_record_count"] = len(cardinality_records)
    state_counts = Counter(
        _clean(row.get("cardinality_pattern"))
        for row in cardinality_records
        if _clean(row.get("cardinality_pattern"))
    )
    occurrence_payload["observation_occurrence_cardinality_state_counts"] = dict(
        sorted(state_counts.items())
    )

    reviews = list(occurrence_payload.get("review_hits") or [])
    reviews.extend(result.get("review_hits") or [])
    if duplicate_support_count:
        reviews.append("goal_kick_candidate_support_already_represented")
    occurrence_payload["review_hits"] = sorted(
        set(_clean(value) for value in reviews if _clean(value))
    )
    if occurrence_payload.get("hard_block_hits"):
        occurrence_payload["status"] = "FAIL_CLOSED"
        occurrence_payload["module_status"] = "FAIL_CLOSED"
    elif result.get("review_hits") or duplicate_support_count:
        occurrence_payload["status"] = "REVIEW_REQUIRED"
        occurrence_payload["module_status"] = "REVIEW_REQUIRED"

    occurrence_payload["canonical_event_count"] = "UNKNOWN"
    occurrence_payload["true_action_count"] = "UNKNOWN"
    occurrence_payload["production_release"] = False
    return occurrence_payload
