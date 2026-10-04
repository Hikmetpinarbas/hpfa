from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

REGISTRY_ID = "single_action_anchor_admission_v1"
CLAIM_CEILING = "ACTION_OCCURRENCE_CANDIDATE_FROM_SINGLE_REVIEWED_ANCHOR_ONLY"
CONSUMER_STATES = {
    "CONSUMED",
    "NOT_ADMITTED_WITH_REASON",
    "NOT_APPLICABLE",
    "DOWNSTREAM_USAGE_UNKNOWN",
}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number_key(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    try:
        return f"{float(text):.6f}"
    except (TypeError, ValueError):
        return text


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_single_anchor_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parents[1] / "registry" / "single_action_anchor_admission_v1.json"
    )
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("registry_id") != REGISTRY_ID:
        raise ValueError("single_action_anchor_registry_invalid")
    states = set(payload.get("consumer_coverage_states") or [])
    if states != CONSUMER_STATES:
        raise ValueError("single_action_anchor_consumer_states_invalid")
    return payload


def _labels(bundle: dict[str, Any]) -> list[str]:
    values = {
        _text(value).casefold()
        for value in (bundle.get("raw_labels") or []) + (bundle.get("normalized_labels") or [])
        if _text(value)
    }
    return sorted(values)


def _evidence_by_id(evidence_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _text(atom.get("evidence_atom_id")): atom
        for atom in evidence_payload.get("evidence_atoms") or []
        if isinstance(atom, dict) and _text(atom.get("evidence_atom_id"))
    }


def _field_equal(bundle: dict[str, Any], atom: dict[str, Any], key: str) -> bool:
    if key in {"start_candidate", "end_candidate", "pos_x_candidate", "pos_y_candidate"}:
        return _number_key(bundle.get(key)) == _number_key(atom.get(key)) != ""
    return _text(bundle.get(key)) == _text(atom.get(key)) != ""


def _dimension_value(atom: dict[str, Any], singular: str, plural: str | None = None) -> list[str]:
    values: list[Any] = []
    if plural:
        raw = atom.get(plural)
        if isinstance(raw, list):
            values.extend(raw)
    raw_single = atom.get(singular)
    if isinstance(raw_single, list):
        values.extend(raw_single)
    elif raw_single not in (None, ""):
        values.append(raw_single)
    return sorted({_text(value) for value in values if _text(value)})


def _coverage_state(values: list[str]) -> dict[str, Any]:
    if values:
        return {"consumer_state": "CONSUMED", "visible_values": values}
    return {"consumer_state": "NOT_APPLICABLE", "visible_values": []}


def _semantic_dimensions(atom: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    dimensions = {
        "outcome_candidate": _dimension_value(atom, "outcome_candidate", "outcome_candidates"),
        "terminal_outcome_candidate": _dimension_value(atom, "terminal_outcome_candidate", "terminal_outcome_candidates"),
        "relation_candidate": _dimension_value(atom, "relation_candidate", "relation_candidates"),
        "context_candidate": _dimension_value(atom, "context_candidate", "context_candidates"),
        "progression_candidate": _dimension_value(atom, "progression_candidate", "progression_candidates"),
        "zone_candidate": _dimension_value(atom, "zone_candidate", "zone_candidates"),
    }
    coverage = {key: _coverage_state(values) for key, values in dimensions.items()}
    coverage["temporal_anchor"] = {
        "consumer_state": "CONSUMED",
        "visible_values": [
            _text(atom.get("period_candidate")),
            _text(atom.get("start_candidate")),
            _text(atom.get("end_candidate")),
        ],
    }
    coverage["action_occurrence_admission"] = {"consumer_state": "CONSUMED", "visible_values": []}
    coverage["consequence_consumer"] = {"consumer_state": "DOWNSTREAM_USAGE_UNKNOWN", "visible_values": []}
    coverage["episode_process_consumer"] = {"consumer_state": "DOWNSTREAM_USAGE_UNKNOWN", "visible_values": []}
    coverage["finding_eligibility"] = {"consumer_state": "DOWNSTREAM_USAGE_UNKNOWN", "visible_values": []}
    coverage["claim"] = {"consumer_state": "DOWNSTREAM_USAGE_UNKNOWN", "visible_values": []}
    return dimensions, coverage


def build_single_action_anchor_candidates(
    action_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    existing_occurrence_candidates: list[dict[str, Any]],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rule = registry or load_single_anchor_registry()
    allowed_roles = set(rule.get("allowed_source_roles") or [])
    expected_atom = rule.get("required_evidence_atom_state") or {}
    evidence_map = _evidence_by_id(evidence_payload)
    represented_bundle_ids = {
        _text(bundle_id)
        for row in existing_occurrence_candidates
        if isinstance(row, dict)
        for bundle_id in row.get("supporting_action_bundle_candidate_ids") or []
        if _text(bundle_id)
    }

    candidates: list[dict[str, Any]] = []
    not_admitted = Counter()
    family_counts = Counter()
    role_counts = Counter()

    for bundle in action_payload.get("action_bundle_candidates") or []:
        if not isinstance(bundle, dict):
            continue
        bundle_id = _text(bundle.get("action_bundle_candidate_id"))
        if not bundle_id or bundle_id in represented_bundle_ids:
            continue
        if bundle.get("source_role") not in allowed_roles:
            continue
        if _text(bundle.get("bundle_status")) != "PASS" or bundle.get("same_role_exact_grouping") is not True:
            continue
        if len(_labels(bundle)) != 1:
            continue

        evidence_ids = [_text(value) for value in bundle.get("supporting_evidence_atom_ids") or [] if _text(value)]
        if len(evidence_ids) != 1:
            not_admitted["supporting_evidence_atom_count_not_one"] += 1
            continue
        atom = evidence_map.get(evidence_ids[0])
        if atom is None:
            not_admitted["supporting_evidence_atom_missing"] += 1
            continue

        checks = {
            "atom_class": atom.get("atom_class") == expected_atom.get("atom_class"),
            "atom_status": atom.get("atom_status") == expected_atom.get("atom_status"),
            "semantic_role_candidate": atom.get("semantic_role_candidate") == expected_atom.get("semantic_role_candidate"),
            "semantic_mapping_status": atom.get("semantic_mapping_status") == expected_atom.get("semantic_mapping_status"),
            "downstream_eligibility": atom.get("downstream_eligibility") == expected_atom.get("downstream_eligibility"),
            "action_eligible": atom.get("action_eligible") is True,
            "semantic_rule_id": bool(_text(atom.get("semantic_rule_id"))),
            "independent_vote_closed": atom.get("independent_source_vote_allowed") is not True,
            "event_truth_closed": atom.get("validated_event_identity") is not True and atom.get("event_instance_allowed") is not True,
            "physical_action_truth_closed": atom.get("physical_action_identity_truth") is not True,
            "canonical_event_count_closed": atom.get("canonical_event_count") in {None, "UNKNOWN"},
            "bundle_cross_role_closed": bundle.get("cross_role_fusion_allowed") is not True,
            "bundle_event_truth_closed": bundle.get("validated_event_identity") is not True and bundle.get("event_instance_allowed") is not True,
            "bundle_canonical_event_count_closed": bundle.get("canonical_event_count") in {None, "UNKNOWN"},
            "coordinate_present": bundle.get("coordinate_evidence_status") == "COORDINATE_PRESENT",
            "team_identity_present": bool(_text(bundle.get("team_identity_candidate_id"))),
            "actor_identity_present": bool(_text(bundle.get("actor_identity_candidate_id"))),
        }
        failed = sorted(key for key, passed in checks.items() if not passed)
        if failed:
            for key in failed:
                not_admitted[key] += 1
            continue

        atom_families = sorted({_text(value).upper() for value in atom.get("action_family_candidates") or [] if _text(value)})
        bundle_family = _text(bundle.get("action_family_candidate")).upper()
        if len(atom_families) != 1 or atom_families[0] != bundle_family or not bundle_family:
            not_admitted["action_family_binding_mismatch"] += 1
            continue

        exact_fields = (
            "match_surface_binding_id",
            "source_role",
            "period_candidate",
            "start_candidate",
            "end_candidate",
            "pos_x_candidate",
            "pos_y_candidate",
        )
        failed_exact = [key for key in exact_fields if not _field_equal(bundle, atom, key)]
        if failed_exact:
            for key in failed_exact:
                not_admitted[f"exact_binding_mismatch:{key}"] += 1
            continue

        dimensions, coverage = _semantic_dimensions(atom)
        candidate_id = "aoc_anchor_" + _digest(
            bundle.get("match_surface_binding_id"),
            bundle_id,
            atom.get("evidence_atom_id"),
            atom.get("semantic_rule_id"),
            rule.get("rule_id"),
        )[:24]
        candidate = {
            "action_occurrence_candidate_id": candidate_id,
            "match_surface_binding_id": bundle.get("match_surface_binding_id"),
            "admission_class": "EXACT_SINGLE_ACTION_ANCHOR_SEMANTIC_ADMISSION",
            "interaction_type": "SINGLE_ACTION_ANCHOR_CANDIDATE",
            "occurrence_topology": "SINGLE_ACTOR_ACTION",
            "compatibility_rule_id": rule.get("rule_id"),
            "primary_family_candidate": bundle_family,
            "team_identity_candidate_id": bundle.get("team_identity_candidate_id"),
            "actor_identity_candidate_id": bundle.get("actor_identity_candidate_id"),
            "opponent_team_identity_candidate_id": None,
            "opponent_identity_candidate_id": None,
            "supporting_action_bundle_candidate_ids": [bundle_id],
            "supporting_evidence_atom_ids": evidence_ids,
            "provider_row_id_candidates": sorted({_text(value) for value in bundle.get("provider_row_id_candidates") or [] if _text(value)}),
            "raw_labels": sorted({_text(value) for value in bundle.get("raw_labels") or [] if _text(value)}),
            "semantic_components": [
                {
                    "label": _text(atom.get("raw_label")) or _text(atom.get("normalized_label")),
                    "semantic_rule_id": _text(atom.get("semantic_rule_id")),
                    "action_family_candidate": bundle_family,
                }
            ],
            "semantic_dimensions": dimensions,
            "semantic_consumer_coverage": coverage,
            "temporal_relation": {
                "period_candidate": bundle.get("period_candidate"),
                "start_candidate": bundle.get("start_candidate"),
                "end_candidate": bundle.get("end_candidate"),
                "relation": "EXACT_SINGLE_ACTION_ANCHOR_CORE",
                "internal_order": "UNKNOWN",
            },
            "location": {
                "pos_x_candidate": bundle.get("pos_x_candidate"),
                "pos_y_candidate": bundle.get("pos_y_candidate"),
                "semantic_role": "ANNOTATION_ANCHOR_LOCATION_CANDIDATE",
                "physical_player_position_truth": False,
            },
            "provider_semantics_binding_status": "PASS",
            "provider_semantics_registry_id": "sportsbase_label_semantics_reviewed_v2",
            "supporting_semantic_rule_ids": [_text(atom.get("semantic_rule_id"))],
            "single_provider_label_is_physical_action_truth": False,
            "independent_support_vote_count": 0,
            "same_time_total_order_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "action_occurrence_candidate_is_event_truth": False,
            "physical_action_identity_truth": False,
            "validated_event_identity": False,
            "event_instance_allowed": False,
            "sequence_truth": False,
            "possession_truth": False,
            "causality_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }
        candidates.append(candidate)
        represented_bundle_ids.add(bundle_id)
        family_counts[bundle_family] += 1
        role_counts[_text(bundle.get("source_role"))] += 1

    candidates.sort(key=lambda row: _text(row.get("action_occurrence_candidate_id")))
    return {
        "action_occurrence_candidates": candidates,
        "action_occurrence_candidate_count": len(candidates),
        "admitted_family_counts": dict(sorted(family_counts.items())),
        "admitted_source_role_counts": dict(sorted(role_counts.items())),
        "not_admitted_with_reason_counts": dict(sorted(not_admitted.items())),
        "consumer_coverage_state_vocabulary": sorted(CONSUMER_STATES),
        "unknown_downstream_usage_is_not_non_use": True,
        "single_label_is_event_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
