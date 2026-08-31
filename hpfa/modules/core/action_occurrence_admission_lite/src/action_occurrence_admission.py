from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "action_occurrence_admission_lite_v1"
ACTION_MODULE_ID = "semantic_role_action_bundle_candidates_lite_v1"
TAXONOMY_MODULE_ID = "action_bundle_multi_family_review_taxonomy_lite_v1"
RELATION_MODULE_ID = "cross_role_relation_candidate_resolver_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "ACTION_OCCURRENCE_CANDIDATE_ONLY"
REGISTRY_ID = "action_occurrence_semantic_compatibility_v1"

OUTPUTS = {
    "json": "action_occurrence_admission_lite_v1.json",
    "summary": "action_occurrence_admission_lite_v1.txt",
    "analyst": "action_occurrence_admission_analyst_audit_v1.txt",
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


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


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parents[1]
        / "registry"
        / "action_occurrence_semantic_compatibility_v1.json"
    )
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("occurrence_compatibility_registry_invalid") from exc
    if not isinstance(payload, dict) or payload.get("registry_id") != REGISTRY_ID:
        raise ValueError("occurrence_compatibility_registry_invalid")
    return payload


def _exact_interaction_core(bundle: dict[str, Any]) -> tuple[str, ...]:
    return (
        _clean(bundle.get("match_surface_binding_id")),
        _clean(bundle.get("period_candidate")),
        _number_key(bundle.get("start_candidate")),
        _number_key(bundle.get("end_candidate")),
        _number_key(bundle.get("pos_x_candidate")),
        _number_key(bundle.get("pos_y_candidate")),
    )


def _participant_key(bundle: dict[str, Any]) -> tuple[str, str]:
    return (
        _clean(bundle.get("team_identity_candidate_id")),
        _clean(bundle.get("actor_identity_candidate_id")),
    )


def _bundle_labels(bundle: dict[str, Any]) -> set[str]:
    labels = {
        _clean(item).casefold()
        for item in (bundle.get("raw_labels") or []) + (bundle.get("normalized_labels") or [])
        if _clean(item)
    }
    return labels


def _bundle_families(bundles: list[dict[str, Any]]) -> set[str]:
    return {
        _clean(bundle.get("action_family_candidate")).upper()
        for bundle in bundles
        if _clean(bundle.get("action_family_candidate"))
    }


def _participant_labels(bundles: list[dict[str, Any]]) -> set[str]:
    labels: set[str] = set()
    for bundle in bundles:
        labels.update(_bundle_labels(bundle))
    return labels


def _taxonomy_clearance_by_bundle(taxonomy_payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in taxonomy_payload.get("multi_family_review_records") or []:
        if not isinstance(record, dict):
            continue
        state = _clean(record.get("record_status"))
        for raw_id in record.get("supporting_action_bundle_candidate_ids") or []:
            bundle_id = _clean(raw_id)
            if bundle_id:
                result[bundle_id] = state
    return result


def _bundle_eligible(bundle: dict[str, Any], taxonomy_state: dict[str, str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if bundle.get("source_role") != "PLAYER_SURFACE_CANDIDATE":
        reasons.append("non_player_surface")
    if not _clean(bundle.get("team_identity_candidate_id")):
        reasons.append("team_identity_missing")
    if not _clean(bundle.get("actor_identity_candidate_id")):
        reasons.append("actor_identity_missing")
    if not _clean(bundle.get("period_candidate")):
        reasons.append("period_missing")
    if _number_key(bundle.get("start_candidate")) == "" or _number_key(bundle.get("end_candidate")) == "":
        reasons.append("time_missing")
    if bundle.get("coordinate_evidence_status") != "COORDINATE_PRESENT":
        reasons.append("coordinate_not_present")
    if _number_key(bundle.get("pos_x_candidate")) == "" or _number_key(bundle.get("pos_y_candidate")) == "":
        reasons.append("coordinate_missing")
    if bundle.get("cross_role_fusion_allowed") is True:
        reasons.append("cross_role_fusion_claimed")
    if bundle.get("validated_event_identity") is True or bundle.get("event_instance_allowed") is True:
        reasons.append("event_truth_boundary_breached")
    if bundle.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        reasons.append("canonical_event_count_claimed")

    status = _clean(bundle.get("bundle_status"))
    if status == "PASS":
        pass
    elif status == "REVIEW_REQUIRED":
        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        if taxonomy_state.get(bundle_id) != "PASS_CANDIDATE_CLASSIFICATION":
            reasons.append("review_bundle_not_taxonomy_cleared")
    else:
        reasons.append("bundle_status_rejected")
    return not reasons, reasons


def _rule_matches(
    rule: dict[str, Any],
    primary_bundles: list[dict[str, Any]],
    counterpart_bundles: list[dict[str, Any]],
) -> bool:
    primary_families = _bundle_families(primary_bundles)
    counterpart_families = _bundle_families(counterpart_bundles)
    primary_labels = _participant_labels(primary_bundles)
    counterpart_labels = _participant_labels(counterpart_bundles)

    required_primary_families = {
        _clean(item).upper() for item in rule.get("primary_required_families") or [] if _clean(item)
    }
    if required_primary_families and not required_primary_families.issubset(primary_families):
        return False

    required_counterpart_families = {
        _clean(item).upper()
        for item in rule.get("counterpart_required_any_families") or []
        if _clean(item)
    }
    if required_counterpart_families and not (required_counterpart_families & counterpart_families):
        return False

    primary_required_labels = {
        _clean(item).casefold()
        for item in rule.get("primary_required_any_labels") or []
        if _clean(item)
    }
    if primary_required_labels and not (primary_required_labels & primary_labels):
        return False

    counterpart_required_labels = {
        _clean(item).casefold()
        for item in rule.get("counterpart_required_any_labels") or []
        if _clean(item)
    }
    if counterpart_required_labels and not (counterpart_required_labels & counterpart_labels):
        return False

    return True


def _relation_support_by_primary_bundle(relation_payload: dict[str, Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = defaultdict(list)
    for relation in relation_payload.get("resolved_relation_candidates") or []:
        if not isinstance(relation, dict):
            continue
        if relation.get("relation_record_status") != "PASS_CANDIDATE_CLASSIFICATION":
            continue
        bundle_id = _clean(relation.get("primary_action_bundle_candidate_id"))
        relation_id = _clean(relation.get("resolved_relation_candidate_id"))
        if bundle_id and relation_id:
            mapping[bundle_id].append(relation_id)
    return {key: sorted(set(value)) for key, value in mapping.items()}


def build_action_occurrence_admission(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
    relation_payload: dict[str, Any],
    registry_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    registry = registry_payload or load_registry()

    expected = {
        "action": (action_payload, ACTION_MODULE_ID),
        "taxonomy": (taxonomy_payload, TAXONOMY_MODULE_ID),
        "relation": (relation_payload, RELATION_MODULE_ID),
    }
    for name, (payload, module_id) in expected.items():
        if payload.get("module_id") != module_id:
            blocks.append(f"{name}_module_id_mismatch")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")
        state = _clean(payload.get("module_status") or payload.get("status") or "UNKNOWN")
        if state == "FAIL_CLOSED":
            blocks.append(f"{name}_input_fail_closed")
        elif state == "REVIEW_REQUIRED":
            reviews.append(f"{name}_upstream_review_required")
        elif state != "PASS":
            reviews.append(f"{name}_upstream_status_review:{state}")

    if registry.get("registry_id") != REGISTRY_ID:
        blocks.append("occurrence_compatibility_registry_id_mismatch")
    boundary = registry.get("global_claim_boundary") or {}
    if boundary.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("registry_canonical_event_boundary_open")
    if boundary.get("production_release") is True:
        blocks.append("registry_production_release_open")

    bindings = {
        _clean(payload.get("match_surface_binding_id"))
        for payload, _ in expected.values()
        if _clean(payload.get("match_surface_binding_id"))
    }
    if len(bindings) != 1:
        blocks.append("match_surface_binding_mismatch")
    binding = next(iter(bindings), "")

    bundles = action_payload.get("action_bundle_candidates") or []
    taxonomy_records = taxonomy_payload.get("multi_family_review_records") or []
    relations = relation_payload.get("resolved_relation_candidates") or []
    if not isinstance(bundles, list):
        blocks.append("action_bundle_inventory_invalid")
        bundles = []
    if not isinstance(taxonomy_records, list):
        blocks.append("taxonomy_inventory_invalid")
        taxonomy_records = []
    if not isinstance(relations, list):
        blocks.append("relation_inventory_invalid")
        relations = []
    if action_payload.get("action_bundle_candidate_count") != len(bundles):
        blocks.append("action_bundle_count_mismatch")
    if taxonomy_payload.get("multi_family_review_core_count") != len(taxonomy_records):
        blocks.append("taxonomy_count_mismatch")
    if relation_payload.get("resolved_relation_candidate_count") != len(relations):
        blocks.append("relation_count_mismatch")

    taxonomy_state = _taxonomy_clearance_by_bundle(taxonomy_payload)
    relation_support = _relation_support_by_primary_bundle(relation_payload)

    eligible_bundles: list[dict[str, Any]] = []
    rejected_bundle_reasons: dict[str, list[str]] = {}
    seen_bundle_ids: set[str] = set()
    for index, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            blocks.append(f"action_bundle_record_invalid:{index}")
            continue
        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        if not bundle_id or bundle_id in seen_bundle_ids:
            blocks.append(f"action_bundle_id_invalid_or_duplicate:{index}")
            continue
        seen_bundle_ids.add(bundle_id)
        if bundle.get("match_surface_binding_id") != binding:
            blocks.append(f"action_bundle_binding_mismatch:{bundle_id}")
            continue
        ok, reasons = _bundle_eligible(bundle, taxonomy_state)
        if ok:
            eligible_bundles.append(bundle)
        else:
            rejected_bundle_reasons[bundle_id] = reasons

    exact_groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for bundle in eligible_bundles:
        exact_groups[_exact_interaction_core(bundle)].append(bundle)

    candidates: list[dict[str, Any]] = []
    candidate_bundle_usage: Counter[str] = Counter()
    rules = [rule for rule in registry.get("interaction_rules") or [] if isinstance(rule, dict)]

    if not blocks:
        for core, grouped in sorted(exact_groups.items()):
            participants: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            for bundle in grouped:
                participants[_participant_key(bundle)].append(bundle)
            participant_items = sorted(participants.items())
            for primary_key, primary_bundles in participant_items:
                primary_team, primary_actor = primary_key
                if not primary_team or not primary_actor:
                    continue
                for counterpart_key, counterpart_bundles in participant_items:
                    counterpart_team, counterpart_actor = counterpart_key
                    if primary_key >= counterpart_key:
                        continue
                    if not counterpart_team or not counterpart_actor:
                        continue
                    if primary_team == counterpart_team or primary_actor == counterpart_actor:
                        continue

                    matched: tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]] | None = None
                    for rule in rules:
                        if _rule_matches(rule, primary_bundles, counterpart_bundles):
                            matched = (rule, primary_bundles, counterpart_bundles)
                            break
                        if _rule_matches(rule, counterpart_bundles, primary_bundles):
                            matched = (rule, counterpart_bundles, primary_bundles)
                            break
                    if matched is None:
                        continue

                    rule, attacker_bundles, defender_bundles = matched
                    attacker = _participant_key(attacker_bundles[0])
                    defender = _participant_key(defender_bundles[0])
                    supporting_bundles = sorted(
                        attacker_bundles + defender_bundles,
                        key=lambda item: _clean(item.get("action_bundle_candidate_id")),
                    )
                    bundle_ids = [_clean(item.get("action_bundle_candidate_id")) for item in supporting_bundles]
                    evidence_ids = sorted(
                        {
                            _clean(eid)
                            for item in supporting_bundles
                            for eid in (item.get("supporting_evidence_atom_ids") or [])
                            if _clean(eid)
                        }
                    )
                    provider_row_ids = sorted(
                        {
                            _clean(pid)
                            for item in supporting_bundles
                            for pid in (item.get("provider_row_id_candidates") or [])
                            if _clean(pid)
                        }
                    )
                    raw_labels = sorted(
                        {
                            _clean(label)
                            for item in supporting_bundles
                            for label in (item.get("raw_labels") or [])
                            if _clean(label)
                        }
                    )
                    families = sorted(_bundle_families(supporting_bundles))
                    supporting_relation_ids = sorted(
                        {
                            rel_id
                            for bid in bundle_ids
                            for rel_id in relation_support.get(bid, [])
                        }
                    )
                    final_third = any("final third" in label.casefold() for label in raw_labels)
                    success = any("successful" in label.casefold() or "won" in label.casefold() for label in raw_labels)
                    challenge_won = any(label.casefold() == "challenges won" for label in raw_labels)
                    tackle_unsuccessful = any(label.casefold() == "tackles unsuccessful" for label in raw_labels)

                    for bid in bundle_ids:
                        candidate_bundle_usage[bid] += 1

                    candidates.append({
                        "action_occurrence_candidate_id": "aoc_" + _digest(binding, core, bundle_ids, rule.get("rule_id"))[:24],
                        "match_surface_binding_id": binding,
                        "admission_class": "EXACT_COMPATIBLE",
                        "interaction_type": rule.get("interaction_type"),
                        "compatibility_rule_id": rule.get("rule_id"),
                        "primary_family_candidate": "DRIBBLE" if "DRIBBLE" in families else families[0],
                        "team_identity_candidate_id": attacker[0],
                        "actor_identity_candidate_id": attacker[1],
                        "opponent_team_identity_candidate_id": defender[0],
                        "opponent_identity_candidate_id": defender[1],
                        "supporting_action_bundle_candidate_ids": bundle_ids,
                        "supporting_evidence_atom_ids": evidence_ids,
                        "provider_row_id_candidates": provider_row_ids,
                        "supporting_relation_candidate_ids": supporting_relation_ids,
                        "action_family_candidates": families,
                        "raw_labels": raw_labels,
                        "attributes": {
                            "success_candidate": success,
                            "final_third_candidate": final_third,
                        },
                        "relation_bundle": {
                            "relation_type": rule.get("interaction_type"),
                            "opponent_identity_candidate_id": defender[1],
                            "challenge_result_candidate": "ACTOR_WON" if challenge_won else "UNKNOWN",
                            "opponent_tackle_attempt_candidate": "UNSUCCESSFUL" if tackle_unsuccessful else "UNKNOWN",
                            "relation_status": "SUPPORTED_CANDIDATE",
                        },
                        "temporal_relation": {
                            "period_candidate": supporting_bundles[0].get("period_candidate"),
                            "start_candidate": supporting_bundles[0].get("start_candidate"),
                            "end_candidate": supporting_bundles[0].get("end_candidate"),
                            "relation": "EXACT_ANNOTATION_INTERVAL_CORE",
                            "internal_order": "UNKNOWN",
                        },
                        "location": {
                            "pos_x_candidate": supporting_bundles[0].get("pos_x_candidate"),
                            "pos_y_candidate": supporting_bundles[0].get("pos_y_candidate"),
                            "semantic_role": rule.get("coordinate_semantic_role") or "ANNOTATION_ANCHOR_LOCATION_CANDIDATE",
                            "physical_player_position_truth": False,
                        },
                        "counterevidence": [],
                        "alternative_explanations": [
                            "shared provider annotation interval may contain more than one physical action"
                        ],
                        "withdrawal_conditions": [
                            "semantic_compatibility_registry_rule_withdrawn",
                            "identity_binding_revised",
                            "provider_interval_or_anchor_semantics_revised"
                        ],
                        "admission_score": None,
                        "probability_output_allowed": False,
                        "independent_support_vote_count": 0,
                        "same_time_total_order_allowed": False,
                        "source_row_order_is_temporal_truth": False,
                        "action_occurrence_candidate_is_event_truth": False,
                        "validated_event_identity": False,
                        "event_instance_allowed": False,
                        "canonical_event_count": CANONICAL_EVENT_COUNT,
                        "true_action_count": "UNKNOWN",
                        "claim_ceiling": CLAIM_CEILING,
                    })

    duplicate_bundle_candidate_ids = sorted(
        bid for bid, count in candidate_bundle_usage.items() if count > 1
    )
    if duplicate_bundle_candidate_ids:
        reviews.append("action_bundle_supports_multiple_occurrence_candidates")

    class_counts = Counter(item.get("admission_class") for item in candidates)
    interaction_counts = Counter(item.get("interaction_type") for item in candidates)
    if rejected_bundle_reasons:
        reviews.append("ineligible_or_unreviewed_action_bundles_preserved")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "semantic_compatibility_registry_id": registry.get("registry_id"),
        "semantic_compatibility_registry_version": registry.get("version"),
        "action_occurrence_candidates": candidates,
        "action_occurrence_candidate_count": len(candidates),
        "admission_class_counts": dict(sorted(class_counts.items())),
        "interaction_type_counts": dict(sorted(interaction_counts.items())),
        "eligible_player_action_bundle_count": len(eligible_bundles),
        "rejected_action_bundle_count": len(rejected_bundle_reasons),
        "rejected_action_bundle_reasons": rejected_bundle_reasons,
        "multi_candidate_bundle_ids": duplicate_bundle_candidate_ids,
        "hard_block_hits": blocks,
        "review_hits": reviews,
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
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def render_summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ACTION OCCURRENCE ADMISSION LITE V1",
        f"status={payload.get('status')}",
        f"action_occurrence_candidate_count={payload.get('action_occurrence_candidate_count')}",
        f"admission_class_counts={payload.get('admission_class_counts')}",
        f"interaction_type_counts={payload.get('interaction_type_counts')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]
    return "\n".join(lines)


def render_analyst(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA Action Occurrence Admission Analyst Audit V1",
        "===============================================",
        f"candidate occurrences={payload.get('action_occurrence_candidate_count')}",
        "",
        "Safe meaning:",
        "Exact reviewed multi-annotation player interactions can be represented once as ACTION_OCCURRENCE_CANDIDATE objects with actor/opponent relations.",
        "CSV/XML or multiple semantic labels are not promoted to independent evidence or canonical event counts.",
        "Annotation anchors are not physical player positions and same-time evidence never creates internal order.",
        "",
        "Forbidden inference:",
        "Do not convert candidate count to true action count, physical chronology, tactical intention, dominance, causality, formation or player position truth.",
        "",
    ])


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    paths["summary"].write_text(render_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(render_analyst(payload), encoding="utf-8")
    return paths
