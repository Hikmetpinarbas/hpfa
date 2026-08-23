from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "cross_role_relation_candidate_resolver_lite_v1"
ACTION_MODULE_ID = "semantic_role_action_bundle_candidates_lite_v1"
TAXONOMY_MODULE_ID = "action_bundle_multi_family_review_taxonomy_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "CROSS_ROLE_RELATION_CANDIDATE_ONLY"
EXPECTED_RELATION_STATUS = "CANDIDATE_EXACT_SURFACE_OVERLAP_NOT_FUSED"

ALLOWED_SOURCE_ROLES = {
    "GOALKEEPER_SURFACE_CANDIDATE",
    "PLAYER_SURFACE_CANDIDATE",
    "TEAM_SURFACE_CANDIDATE",
}
ALLOWED_ROLE_PAIRS = {
    ("GOALKEEPER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"),
    ("PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"),
}
RELATION_EXACT_FIELDS = (
    "match_surface_binding_id",
    "team_identity_candidate_id",
    "period_candidate",
    "start_candidate",
    "end_candidate",
    "pos_x_candidate",
    "pos_y_candidate",
    "action_family_candidate",
)
TAXONOMY_CORE_FIELDS = (
    "match_surface_binding_id",
    "source_role",
    "team_identity_candidate_id",
    "actor_identity_candidate_id",
    "period_candidate",
    "start_candidate",
    "end_candidate",
    "pos_x_candidate",
    "pos_y_candidate",
)
NUMERIC_FIELDS = {"start_candidate", "end_candidate", "pos_x_candidate", "pos_y_candidate"}

OUTPUTS = {
    "json": "cross_role_relation_candidate_resolver_lite_v1.json",
    "summary": "cross_role_relation_candidate_resolver_lite_v1.txt",
    "analyst": "cross_role_relation_candidate_resolver_analyst_audit_v1.txt",
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


def _norm(record: dict[str, Any], field: str) -> str:
    if field in NUMERIC_FIELDS:
        return _number_key(record.get(field))
    return _clean(record.get(field))


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _validate_bundle(bundle: dict[str, Any], index: int, binding_id: str) -> list[str]:
    blocks: list[str] = []
    if not _clean(bundle.get("action_bundle_candidate_id")):
        blocks.append(f"action_bundle_candidate_id_missing:{index}")
    if bundle.get("match_surface_binding_id") != binding_id:
        blocks.append(f"bundle_match_surface_binding_mismatch:{index}")
    if bundle.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"bundle_source_role_rejected:{index}")
    if bundle.get("bundle_status") not in {"PASS", "REVIEW_REQUIRED"}:
        blocks.append(f"bundle_status_rejected:{index}")
    if not _clean(bundle.get("action_family_candidate")):
        blocks.append(f"bundle_action_family_missing:{index}")
    if bundle.get("same_role_exact_grouping") is not True:
        blocks.append(f"bundle_same_role_exact_grouping_not_true:{index}")
    if bundle.get("cross_role_fusion_allowed") is True:
        blocks.append(f"bundle_cross_role_fusion_claimed:{index}")
    if bundle.get("validated_event_identity") is True:
        blocks.append(f"bundle_validated_event_identity_claimed:{index}")
    if bundle.get("event_instance_allowed") is True:
        blocks.append(f"bundle_event_instance_admission_claimed:{index}")
    if bundle.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"bundle_canonical_event_count_claimed:{index}")
    return blocks


def _validate_taxonomy_record(record: dict[str, Any], index: int, binding_id: str) -> list[str]:
    blocks: list[str] = []
    if not _clean(record.get("multi_family_review_record_id")):
        blocks.append(f"taxonomy_record_id_missing:{index}")
    if record.get("match_surface_binding_id") != binding_id:
        blocks.append(f"taxonomy_match_surface_binding_mismatch:{index}")
    if record.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"taxonomy_source_role_rejected:{index}")
    if record.get("record_status") not in {"PASS_CANDIDATE_CLASSIFICATION", "REVIEW_REQUIRED"}:
        blocks.append(f"taxonomy_record_status_rejected:{index}")
    if record.get("classification_is_event_truth") is True:
        blocks.append(f"taxonomy_event_truth_claimed:{index}")
    if record.get("cross_role_fusion_allowed") is True:
        blocks.append(f"taxonomy_cross_role_fusion_claimed:{index}")
    if record.get("event_instance_allowed") is True:
        blocks.append(f"taxonomy_event_instance_admission_claimed:{index}")
    if record.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"taxonomy_canonical_event_count_claimed:{index}")
    bundle_ids = record.get("supporting_action_bundle_candidate_ids") or []
    normalized = [_clean(item) for item in bundle_ids]
    if not isinstance(bundle_ids, list) or len(bundle_ids) < 2 or len(set(normalized)) != len(bundle_ids) or not all(normalized):
        blocks.append(f"taxonomy_supporting_bundle_ids_invalid:{index}")
    family_set = sorted({_clean(item) for item in (record.get("family_set") or []) if _clean(item)})
    if len(family_set) < 2 or record.get("family_count") != len(family_set):
        blocks.append(f"taxonomy_family_set_invalid:{index}")
    role = _clean(record.get("source_role"))
    actor = _clean(record.get("actor_identity_candidate_id"))
    if role == "TEAM_SURFACE_CANDIDATE" and actor:
        blocks.append(f"taxonomy_team_actor_identity_present:{index}")
    if role != "TEAM_SURFACE_CANDIDATE" and not actor:
        blocks.append(f"taxonomy_primary_actor_identity_missing:{index}")
    return blocks


def _validate_taxonomy_core(record: dict[str, Any], bundles: list[dict[str, Any]]) -> list[str]:
    record_id = _clean(record.get("multi_family_review_record_id")) or "UNKNOWN"
    if not bundles:
        return [f"{record_id}:taxonomy_supporting_bundles_missing"]
    blocks: list[str] = []
    signatures: set[tuple[str, ...]] = set()
    for bundle in bundles:
        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        if bundle.get("bundle_status") != "REVIEW_REQUIRED":
            blocks.append(f"{record_id}:taxonomy_references_non_review_bundle:{bundle_id}")
        sig: list[str] = []
        for field in TAXONOMY_CORE_FIELDS:
            bval = _norm(bundle, field)
            rval = _norm(record, field)
            sig.append(bval)
            if bval != rval:
                blocks.append(f"{record_id}:taxonomy_bundle_core_mismatch:{field}:{bundle_id}")
        coord = _clean(bundle.get("coordinate_evidence_status"))
        sig.append(coord)
        if coord != _clean(record.get("coordinate_evidence_status")):
            blocks.append(f"{record_id}:taxonomy_bundle_core_mismatch:coordinate_evidence_status:{bundle_id}")
        signatures.add(tuple(sig))
    if len(signatures) != 1:
        blocks.append(f"{record_id}:taxonomy_supporting_bundles_not_single_exact_core")
    record_families = sorted({_clean(item) for item in (record.get("family_set") or []) if _clean(item)})
    bundle_families = sorted({_clean(bundle.get("action_family_candidate")) for bundle in bundles})
    if record_families != bundle_families:
        blocks.append(f"{record_id}:taxonomy_bundle_family_set_mismatch")
    return blocks


def build_cross_role_relation_candidate_resolver(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if action_payload.get("module_id") != ACTION_MODULE_ID:
        blocks.append("action_input_module_id_mismatch")
    if taxonomy_payload.get("module_id") != TAXONOMY_MODULE_ID:
        blocks.append("taxonomy_input_module_id_mismatch")
    for prefix, payload in (("action", action_payload), ("taxonomy", taxonomy_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{prefix}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{prefix}_hard_blocks_present")

    action_binding = _clean(action_payload.get("match_surface_binding_id"))
    taxonomy_binding = _clean(taxonomy_payload.get("match_surface_binding_id"))
    if not action_binding or action_binding != taxonomy_binding:
        blocks.append("match_surface_binding_mismatch")

    bundles = action_payload.get("action_bundle_candidates") or []
    relations = action_payload.get("cross_role_relation_candidates") or []
    taxonomy_records = taxonomy_payload.get("multi_family_review_records") or []
    if not isinstance(bundles, list) or not bundles:
        blocks.append("action_bundle_candidates_empty_or_invalid")
        bundles = []
    if not isinstance(relations, list):
        blocks.append("cross_role_relation_candidates_invalid")
        relations = []
    if not isinstance(taxonomy_records, list):
        blocks.append("taxonomy_records_invalid")
        taxonomy_records = []
    if action_payload.get("action_bundle_candidate_count") != len(bundles):
        blocks.append("action_bundle_candidate_count_mismatch")
    if action_payload.get("cross_role_relation_candidate_count") != len(relations):
        blocks.append("cross_role_relation_candidate_count_mismatch")
    if taxonomy_payload.get("multi_family_review_core_count") != len(taxonomy_records):
        blocks.append("taxonomy_record_count_mismatch")

    bundle_by_id: dict[str, dict[str, Any]] = {}
    for index, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            blocks.append(f"action_bundle_record_invalid:{index}")
            continue
        blocks.extend(_validate_bundle(bundle, index, action_binding))
        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        if bundle_id in bundle_by_id:
            blocks.append(f"duplicate_action_bundle_candidate_id:{bundle_id}")
        bundle_by_id[bundle_id] = bundle

    review_bundle_ids = {
        bundle_id for bundle_id, bundle in bundle_by_id.items()
        if bundle.get("bundle_status") == "REVIEW_REQUIRED"
    }
    taxonomy_by_bundle: dict[str, dict[str, Any]] = {}
    taxonomy_record_ids: set[str] = set()
    for index, record in enumerate(taxonomy_records):
        if not isinstance(record, dict):
            blocks.append(f"taxonomy_record_invalid:{index}")
            continue
        blocks.extend(_validate_taxonomy_record(record, index, action_binding))
        record_id = _clean(record.get("multi_family_review_record_id"))
        if record_id in taxonomy_record_ids:
            blocks.append(f"duplicate_taxonomy_record_id:{record_id}")
        taxonomy_record_ids.add(record_id)
        supporting: list[dict[str, Any]] = []
        for raw_id in record.get("supporting_action_bundle_candidate_ids") or []:
            bundle_id = _clean(raw_id)
            bundle = bundle_by_id.get(bundle_id)
            if bundle is None:
                blocks.append(f"taxonomy_bundle_reference_missing:{bundle_id}")
                continue
            supporting.append(bundle)
            if bundle_id in taxonomy_by_bundle:
                blocks.append(f"taxonomy_bundle_mapped_multiple_times:{bundle_id}")
            taxonomy_by_bundle[bundle_id] = record
        blocks.extend(_validate_taxonomy_core(record, supporting))

    if set(taxonomy_by_bundle) != review_bundle_ids:
        blocks.append("taxonomy_review_bundle_coverage_mismatch")
    if taxonomy_payload.get("source_review_bundle_record_count") != len(review_bundle_ids):
        blocks.append("taxonomy_source_review_bundle_count_mismatch")

    resolved: list[dict[str, Any]] = []
    relation_ids: set[str] = set()
    consumed_bundle_ids: set[str] = set()

    if not blocks:
        for index, relation in enumerate(relations):
            rblocks: list[str] = []
            rreviews: list[str] = []
            if not isinstance(relation, dict):
                blocks.append(f"relation_record_invalid:{index}")
                continue
            relation_id = _clean(relation.get("cross_role_relation_candidate_id"))
            if not relation_id:
                rblocks.append("relation_id_missing")
            if relation_id in relation_ids:
                rblocks.append("duplicate_relation_id")
            relation_ids.add(relation_id)
            if relation.get("match_surface_binding_id") != action_binding:
                rblocks.append("relation_match_surface_binding_mismatch")
            if relation.get("relation_status") != EXPECTED_RELATION_STATUS:
                rblocks.append("relation_status_contract_mismatch")
            if relation.get("cross_role_fusion_allowed") is True:
                rblocks.append("relation_cross_role_fusion_claimed")
            if relation.get("event_instance_allowed") is True:
                rblocks.append("relation_event_instance_admission_claimed")
            if relation.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
                rblocks.append("relation_canonical_event_count_claimed")

            ids = relation.get("action_bundle_candidate_ids") or []
            normalized_ids = [_clean(item) for item in ids]
            if not isinstance(ids, list) or len(ids) != 2 or len(set(normalized_ids)) != 2:
                rblocks.append("relation_bundle_id_contract_invalid")
                ids = []
            linked: list[dict[str, Any]] = []
            for raw_id in ids:
                bundle_id = _clean(raw_id)
                bundle = bundle_by_id.get(bundle_id)
                if bundle is None:
                    rblocks.append(f"relation_bundle_reference_missing:{bundle_id}")
                    continue
                if bundle_id in consumed_bundle_ids:
                    rblocks.append(f"relation_bundle_reused:{bundle_id}")
                linked.append(bundle)
            consumed_bundle_ids.update(_clean(item) for item in ids)
            if len(linked) != 2:
                blocks.extend(f"{relation_id}:{item}" for item in rblocks)
                continue

            role_pair = tuple(sorted(_clean(bundle.get("source_role")) for bundle in linked))
            declared_roles = tuple(sorted(_clean(item) for item in (relation.get("source_roles") or [])))
            if role_pair not in ALLOWED_ROLE_PAIRS:
                rblocks.append("relation_source_role_pair_rejected")
            if declared_roles != role_pair:
                rblocks.append("relation_declared_source_roles_mismatch")

            team_bundles = [bundle for bundle in linked if bundle.get("source_role") == "TEAM_SURFACE_CANDIDATE"]
            primary_bundles = [bundle for bundle in linked if bundle.get("source_role") != "TEAM_SURFACE_CANDIDATE"]
            if len(team_bundles) != 1 or len(primary_bundles) != 1:
                rblocks.append("relation_primary_reflection_cardinality_invalid")
                team_bundle = primary_bundle = linked[0]
            else:
                team_bundle = team_bundles[0]
                primary_bundle = primary_bundles[0]
            if _clean(team_bundle.get("actor_identity_candidate_id")):
                rblocks.append("team_reflection_actor_identity_present")
            if not _clean(primary_bundle.get("actor_identity_candidate_id")):
                rblocks.append("primary_actor_identity_missing")
            for field in RELATION_EXACT_FIELDS:
                if len({_norm(bundle, field) for bundle in linked}) != 1:
                    rblocks.append(f"relation_exact_field_mismatch:{field}")

            coordinate_present = all(
                bundle.get("coordinate_evidence_status") == "COORDINATE_PRESENT"
                and bundle.get("pos_x_candidate") is not None
                and bundle.get("pos_y_candidate") is not None
                for bundle in linked
            )
            if not coordinate_present:
                rreviews.append("coordinate_surface_missing_preserved")

            taxonomy_context: dict[str, dict[str, Any]] = {}
            for bundle in linked:
                if bundle.get("bundle_status") != "REVIEW_REQUIRED":
                    continue
                bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
                record = taxonomy_by_bundle.get(bundle_id)
                if record is None:
                    rblocks.append(f"taxonomy_context_missing:{bundle_id}")
                    continue
                taxonomy_context[_clean(record.get("multi_family_review_record_id"))] = record

            pair_prefix = (
                "PLAYER_TEAM"
                if primary_bundle.get("source_role") == "PLAYER_SURFACE_CANDIDATE"
                else "GOALKEEPER_TEAM"
            )
            if all(bundle.get("bundle_status") == "PASS" for bundle in linked) and coordinate_present:
                classification = f"EXACT_{pair_prefix}_REFLECTION_CANDIDATE_CLEAR"
                record_status = "PASS_CANDIDATE_CLASSIFICATION"
            elif (
                taxonomy_context
                and all(record.get("record_status") == "PASS_CANDIDATE_CLASSIFICATION" for record in taxonomy_context.values())
                and coordinate_present
            ):
                classification = f"EXACT_{pair_prefix}_REFLECTION_CANDIDATE_CLASSIFIED_CONTEXT"
                record_status = "PASS_CANDIDATE_CLASSIFICATION"
            else:
                classification = f"REVIEW_REQUIRED_{pair_prefix}_UNRESOLVED_CONTEXT"
                record_status = "REVIEW_REQUIRED"
                rreviews.append("unresolved_multi_family_relation_context")

            if rblocks:
                blocks.extend(f"{relation_id}:{item}" for item in rblocks)
                continue

            resolved.append({
                "resolved_relation_candidate_id": "crr_" + _digest(action_binding, relation_id, normalized_ids)[:24],
                "source_relation_candidate_id": relation_id,
                "match_surface_binding_id": action_binding,
                "relation_classification": classification,
                "relation_record_status": record_status,
                "source_roles": list(role_pair),
                "team_identity_candidate_id": team_bundle.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": primary_bundle.get("actor_identity_candidate_id"),
                "period_candidate": primary_bundle.get("period_candidate"),
                "start_candidate": primary_bundle.get("start_candidate"),
                "end_candidate": primary_bundle.get("end_candidate"),
                "pos_x_candidate": primary_bundle.get("pos_x_candidate"),
                "pos_y_candidate": primary_bundle.get("pos_y_candidate"),
                "coordinate_evidence_status": "COORDINATE_PRESENT" if coordinate_present else "COORDINATE_MISSING",
                "action_family_candidate": primary_bundle.get("action_family_candidate"),
                "primary_action_bundle_candidate_id": primary_bundle.get("action_bundle_candidate_id"),
                "reflection_action_bundle_candidate_id": team_bundle.get("action_bundle_candidate_id"),
                "taxonomy_context_record_ids": sorted(taxonomy_context),
                "review_hits": sorted(set(rreviews)),
                "counting_surface_candidate_policy": "PRIMARY_ROLE_ONLY_IF_LATER_EVENT_ADMISSION_PASSES",
                "primary_surface_role": "PRIMARY_COUNTING_SURFACE_CANDIDATE",
                "team_surface_role": "REFLECTION_ONLY_SURFACE_CANDIDATE",
                "double_count_suppression_candidate_state": (
                    "CANDIDATE_PRIMARY_ROLE_ONLY"
                    if record_status == "PASS_CANDIDATE_CLASSIFICATION"
                    else "REVIEW_REQUIRED_CONTEXT_UNRESOLVED"
                ),
                "relation_candidate_is_event_truth": False,
                "reflection_equivalence_truth": False,
                "double_count_suppression_is_final": False,
                "count_value_output_allowed": False,
                "same_time_only_link_allowed": False,
                "cross_role_fusion_allowed": False,
                "event_instance_allowed": False,
                "validated_event_identity": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "claim_ceiling": CLAIM_CEILING,
            })

    if len(resolved) != len(relations) and not blocks:
        blocks.append("relation_output_coverage_mismatch")

    classification_counts = Counter(item.get("relation_classification") for item in resolved)
    role_pair_counts = Counter("+".join(item.get("source_roles") or []) for item in resolved)
    family_counts = Counter(item.get("action_family_candidate") for item in resolved)
    review_count = sum(item.get("relation_record_status") == "REVIEW_REQUIRED" for item in resolved)
    clear_count = len(resolved) - review_count
    suppression_count = sum(
        item.get("double_count_suppression_candidate_state") == "CANDIDATE_PRIMARY_ROLE_ONLY"
        for item in resolved
    )

    for prefix, payload in (("action", action_payload), ("taxonomy", taxonomy_payload)):
        status = str(payload.get("module_status") or payload.get("status") or "UNKNOWN")
        if status == "FAIL_CLOSED":
            blocks.append(f"{prefix}_input_fail_closed")
        elif status == "REVIEW_REQUIRED":
            reviews.append(f"{prefix}_upstream_review_required")
        elif status != "PASS":
            reviews.append(f"{prefix}_upstream_status_review:{status}")
    if review_count:
        reviews.append("unresolved_cross_role_relation_context_present")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": action_binding or None,
        "resolved_relation_candidates": resolved,
        "source_action_bundle_candidate_count": len(bundles),
        "source_cross_role_relation_candidate_count": len(relations),
        "resolved_relation_candidate_count": len(resolved),
        "candidate_clear_relation_count": clear_count,
        "review_required_relation_count": review_count,
        "double_count_suppression_candidate_count": suppression_count,
        "relation_classification_counts": dict(sorted(classification_counts.items())),
        "relation_role_pair_counts": dict(sorted(role_pair_counts.items())),
        "relation_family_counts": dict(sorted(family_counts.items())),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "link_policy": "EXACT_MATCH_BINDING_TEAM_PERIOD_START_END_COORDINATE_FAMILY_AND_ROLE_PAIR",
        "taxonomy_core_integrity_policy": "EXACT_RECORD_TO_SUPPORTING_REVIEW_BUNDLE_CORE_AND_FAMILY_SET",
        "same_time_only_link_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "relation_candidate_is_event_truth": False,
        "reflection_equivalence_truth": False,
        "double_count_suppression_is_final": False,
        "count_value_output_allowed": False,
        "cross_role_fusion_allowed": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def render_summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "source_cross_role_relation_candidate_count",
        "resolved_relation_candidate_count",
        "candidate_clear_relation_count",
        "review_required_relation_count",
        "double_count_suppression_candidate_count",
    )
    lines = ["HPFA CROSS-ROLE RELATION CANDIDATE RESOLVER LITE V1"]
    lines.extend(f"{key}={payload.get(key)}" for key in keys)
    lines.extend([
        f"relation_classification_counts={payload.get('relation_classification_counts')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
    ])
    return "\n".join(lines)


def render_analyst(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA Cross-Role Relation Analyst Audit V1",
        "==========================================",
        f"resolved relation candidates={payload.get('resolved_relation_candidate_count')}",
        f"candidate-clear relations={payload.get('candidate_clear_relation_count')}",
        f"review-required relations={payload.get('review_required_relation_count')}",
        "",
        "Safe meaning:",
        "PLAYER/GK primary surfaces and TEAM reflection surfaces are related only where exact match-local team, time, coordinate and family evidence match.",
        "Taxonomy context can clear a relation candidate only after exact supporting review-bundle core and family-set integrity checks.",
        "Primary-role-only counting remains a future candidate policy; no event count or final double-count suppression is produced here.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
    ])


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    out = validate_out(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {key: out / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(render_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(render_analyst(payload), encoding="utf-8")
    return paths
