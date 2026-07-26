from __future__ import annotations

import argparse
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
    ("PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"),
    ("GOALKEEPER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"),
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


def _normalized_field(record: dict[str, Any], field: str) -> str:
    return _number_key(record.get(field)) if field in NUMERIC_FIELDS else _clean(record.get(field))


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def _validate_bundle(bundle: dict[str, Any], index: int, binding_id: str) -> list[str]:
    blocks: list[str] = []
    if not _clean(bundle.get("action_bundle_candidate_id")):
        blocks.append(f"action_bundle_candidate_id_missing:{index}")
    if bundle.get("match_surface_binding_id") != binding_id:
        blocks.append(f"bundle_match_surface_binding_mismatch:{index}")
    if bundle.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"bundle_source_role_rejected:{index}")
    if not _clean(bundle.get("action_family_candidate")):
        blocks.append(f"bundle_action_family_missing:{index}")
    if bundle.get("bundle_status") not in {"PASS", "REVIEW_REQUIRED"}:
        blocks.append(f"bundle_status_rejected:{index}")
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


def _validate_taxonomy_record(
    record: dict[str, Any],
    index: int,
    binding_id: str,
) -> list[str]:
    blocks: list[str] = []
    if not _clean(record.get("multi_family_review_record_id")):
        blocks.append(f"taxonomy_record_id_missing:{index}")
    if record.get("match_surface_binding_id") != binding_id:
        blocks.append(f"taxonomy_match_surface_binding_mismatch:{index}")
    if record.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"taxonomy_source_role_rejected:{index}")
    if record.get("record_status") not in {
        "PASS_CANDIDATE_CLASSIFICATION",
        "REVIEW_REQUIRED",
    }:
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
    normalized_bundle_ids = [_clean(item) for item in bundle_ids]
    if (
        not isinstance(bundle_ids, list)
        or len(bundle_ids) < 2
        or len(set(normalized_bundle_ids)) != len(bundle_ids)
        or not all(normalized_bundle_ids)
    ):
        blocks.append(f"taxonomy_supporting_bundle_ids_invalid:{index}")

    family_set = record.get("family_set") or []
    normalized_families = sorted({_clean(item) for item in family_set if _clean(item)})
    if not isinstance(family_set, list) or len(normalized_families) < 2:
        blocks.append(f"taxonomy_family_set_invalid:{index}")
    if record.get("family_count") != len(normalized_families):
        blocks.append(f"taxonomy_family_count_mismatch:{index}")

    role = _clean(record.get("source_role"))
    actor = _clean(record.get("actor_identity_candidate_id"))
    if role == "TEAM_SURFACE_CANDIDATE" and actor:
        blocks.append(f"taxonomy_team_actor_identity_present:{index}")
    if role != "TEAM_SURFACE_CANDIDATE" and not actor:
        blocks.append(f"taxonomy_primary_actor_identity_missing:{index}")
    return blocks


def _validate_taxonomy_core_against_bundles(
    record: dict[str, Any],
    supporting_bundles: list[dict[str, Any]],
) -> list[str]:
    record_id = _clean(record.get("multi_family_review_record_id")) or "UNKNOWN"
    blocks: list[str] = []
    if not supporting_bundles:
        return [f"{record_id}:taxonomy_supporting_bundles_missing"]

    for bundle in supporting_bundles:
        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        if bundle.get("bundle_status") != "REVIEW_REQUIRED":
            blocks.append(f"{record_id}:taxonomy_references_non_review_bundle:{bundle_id}")
        for field in TAXONOMY_CORE_FIELDS:
            if _normalized_field(bundle, field) != _normalized_field(record, field):
                blocks.append(
                    f"{record_id}:taxonomy_bundle_core_mismatch:{field}:{bundle_id}"
                )
        if _clean(bundle.get("coordinate_evidence_status")) != _clean(
            record.get("coordinate_evidence_status")
        ):
            blocks.append(
                f"{record_id}:taxonomy_bundle_core_mismatch:coordinate_evidence_status:{bundle_id}"
            )

    bundle_core_signatures = {
        tuple(_normalized_field(bundle, field) for field in TAXONOMY_CORE_FIELDS)
        + (_clean(bundle.get("coordinate_evidence_status")),)
        for bundle in supporting_bundles
    }
    if len(bundle_core_signatures) != 1:
        blocks.append(f"{record_id}:taxonomy_supporting_bundles_not_single_exact_core")

    record_family_set = sorted(
        {_clean(item) for item in (record.get("family_set") or []) if _clean(item)}
    )
    bundle_family_set = sorted(
        {_clean(bundle.get("action_family_candidate")) for bundle in supporting_bundles}
    )
    if bundle_family_set != record_family_set:
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
        bundle_id
        for bundle_id, bundle in bundle_by_id.items()
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

        supporting_bundles: list[dict[str, Any]] = []
        for raw_bundle_id in record.get("supporting_action_bundle_candidate_ids") or []:
            bundle_id = _clean(raw_bundle_id)
            bundle = bundle_by_id.get(bundle_id)
            if bundle is None:
                blocks.append(f"taxonomy_bundle_reference_missing:{bundle_id}")
                continue
            supporting_bundles.append(bundle)
            if bundle_id in taxonomy_by_bundle:
                blocks.append(f"taxonomy_bundle_mapped_multiple_times:{bundle_id}")
            taxonomy_by_bundle[bundle_id] = record
        blocks.extend(_validate_taxonomy_core_against_bundles(record, supporting_bundles))

    if set(taxonomy_by_bundle) != review_bundle_ids:
        blocks.append("taxonomy_review_bundle_coverage_mismatch")
    if taxonomy_payload.get("source_review_bundle_record_count") != len(review_bundle_ids):
        blocks.append("taxonomy_source_review_bundle_count_mismatch")

    relation_records: list[dict[str, Any]] = []
    relation_ids: set[str] = set()
    consumed_bundle_ids: set[str] = set()

    if not blocks:
        for index, relation in enumerate(relations):
            relation_blocks: list[str] = []
            relation_reviews: list[str] = []
            if not isinstance(relation, dict):
                blocks.append(f"relation_record_invalid:{index}")
                continue
            relation_id = _clean(relation.get("cross_role_relation_candidate_id"))
            if not relation_id:
                relation_blocks.append("relation_id_missing")
            if relation_id in relation_ids:
                relation_blocks.append("duplicate_relation_id")
            relation_ids.add(relation_id)
            if relation.get("match_surface_binding_id") != action_binding:
                relation_blocks.append("relation_match_surface_binding_mismatch")
            if relation.get("relation_status") != EXPECTED_RELATION_STATUS:
                relation_blocks.append("relation_status_contract_mismatch")
            if relation.get("cross_role_fusion_allowed") is True:
                relation_blocks.append("relation_cross_role_fusion_claimed")
            if relation.get("event_instance_allowed") is True:
                relation_blocks.append("relation_event_instance_admission_claimed")
            if relation.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
                relation_blocks.append("relation_canonical_event_count_claimed")

            bundle_ids = relation.get("action_bundle_candidate_ids") or []
            normalized_bundle_ids = [_clean(item) for item in bundle_ids]
            if (
                not isinstance(bundle_ids, list)
                or len(bundle_ids) != 2
                or len(set(normalized_bundle_ids)) != 2
            ):
                relation_blocks.append("relation_bundle_id_contract_invalid")
                bundle_ids = []
            linked: list[dict[str, Any]] = []
            for raw_bundle_id in bundle_ids:
                bundle_id = _clean(raw_bundle_id)
                bundle = bundle_by_id.get(bundle_id)
                if bundle is None:
                    relation_blocks.append(f"relation_bundle_reference_missing:{bundle_id}")
                    continue
                if bundle_id in consumed_bundle_ids:
                    relation_blocks.append(f"relation_bundle_reused:{bundle_id}")
                linked.append(bundle)
            consumed_bundle_ids.update(_clean(item) for item in bundle_ids)

            if len(linked) != 2:
                blocks.extend(f"{relation_id}:{item}" for item in relation_blocks)
                continue

            role_pair = tuple(sorted(_clean(bundle.get("source_role")) for bundle in linked))
            declared_roles = tuple(
                sorted(_clean(item) for item in (relation.get("source_roles") or []))
            )
            if role_pair not in ALLOWED_ROLE_PAIRS:
                relation_blocks.append("relation_source_role_pair_rejected")
            if declared_roles != role_pair:
                relation_blocks.append("relation_declared_source_roles_mismatch")

            team_bundles = [
                bundle
                for bundle in linked
                if bundle.get("source_role") == "TEAM_SURFACE_CANDIDATE"
            ]
            primary_bundles = [
                bundle
                for bundle in linked
                if bundle.get("source_role") != "TEAM_SURFACE_CANDIDATE"
            ]
            if len(team_bundles) != 1 or len(primary_bundles) != 1:
                relation_blocks.append("relation_primary_reflection_cardinality_invalid")
                team_bundle = primary_bundle = linked[0]
            else:
                team_bundle = team_bundles[0]
                primary_bundle = primary_bundles[0]

            if _clean(team_bundle.get("actor_identity_candidate_id")):
                relation_blocks.append("team_reflection_actor_identity_present")
            if not _clean(primary_bundle.get("actor_identity_candidate_id")):
                relation_blocks.append("primary_actor_identity_missing")

            for field in RELATION_EXACT_FIELDS:
                values = {_normalized_field(bundle, field) for bundle in linked}
                if len(values) != 1:
                    relation_blocks.append(f"relation_exact_field_mismatch:{field}")

            coordinate_present = all(
                bundle.get("coordinate_evidence_status") == "COORDINATE_PRESENT"
                and bundle.get("pos_x_candidate") is not None
                and bundle.get("pos_y_candidate") is not None
                for bundle in linked
            )
            if not coordinate_present:
                relation_reviews.append("coordinate_surface_missing_preserved")

            taxonomy_context_records: dict[str, dict[str, Any]] = {}
            for bundle in linked:
                if bundle.get("bundle_status") != "REVIEW_REQUIRED":
                    continue
                bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
                record = taxonomy_by_bundle.get(bundle_id)
                if record is None:
                    relation_blocks.append(f"taxonomy_context_missing:{bundle_id}")
                    continue
                taxonomy_context_records[
                    _clean(record.get("multi_family_review_record_id"))
                ] = record

            pair_prefix = (
                "PLAYER_TEAM"
                if primary_bundle.get("source_role") == "PLAYER_SURFACE_CANDIDATE"
                else "GOALKEEPER_TEAM"
            )
            if all(bundle.get("bundle_status") == "PASS" for bundle in linked) and coordinate_present:
                relation_classification = f"EXACT_{pair_prefix}_REFLECTION_CANDIDATE_CLEAR"
                relation_status = "PASS_CANDIDATE_CLASSIFICATION"
            elif (
                taxonomy_context_records
                and all(
                    record.get("record_status") == "PASS_CANDIDATE_CLASSIFICATION"
                    for record in taxonomy_context_records.values()
                )
                and coordinate_present
            ):
                relation_classification = (
                    f"EXACT_{pair_prefix}_REFLECTION_CANDIDATE_CLASSIFIED_CONTEXT"
                )
                relation_status = "PASS_CANDIDATE_CLASSIFICATION"
            else:
                relation_classification = (
                    f"REVIEW_REQUIRED_{pair_prefix}_UNRESOLVED_CONTEXT"
                )
                relation_status = "REVIEW_REQUIRED"
                relation_reviews.append("unresolved_multi_family_relation_context")

            if relation_blocks:
                blocks.extend(f"{relation_id}:{item}" for item in relation_blocks)
                continue

            relation_records.append(
                {
                    "resolved_relation_candidate_id": "crr_"
                    + _digest(action_binding, relation_id, bundle_ids)[:24],
                    "source_relation_candidate_id": relation_id,
                    "match_surface_binding_id": action_binding,
                    "relation_classification": relation_classification,
                    "relation_record_status": relation_status,
                    "source_roles": list(role_pair),
                    "team_identity_candidate_id": team_bundle.get(
                        "team_identity_candidate_id"
                    ),
                    "actor_identity_candidate_id": primary_bundle.get(
                        "actor_identity_candidate_id"
                    ),
                    "period_candidate": primary_bundle.get("period_candidate"),
                    "start_candidate": primary_bundle.get("start_candidate"),
                    "end_candidate": primary_bundle.get("end_candidate"),
                    "pos_x_candidate": primary_bundle.get("pos_x_candidate"),
                    "pos_y_candidate": primary_bundle.get("pos_y_candidate"),
                    "coordinate_evidence_status": (
                        "COORDINATE_PRESENT"
                        if coordinate_present
                        else "COORDINATE_MISSING"
                    ),
                    "action_family_candidate": primary_bundle.get(
                        "action_family_candidate"
                    ),
                    "primary_action_bundle_candidate_id": primary_bundle.get(
                        "action_bundle_candidate_id"
                    ),
                    "reflection_action_bundle_candidate_id": team_bundle.get(
                        "action_bundle_candidate_id"
                    ),
                    "taxonomy_context_record_ids": sorted(taxonomy_context_records),
                    "review_hits": sorted(set(relation_reviews)),
                    "counting_surface_candidate_policy": (
                        "PRIMARY_ROLE_ONLY_IF_LATER_EVENT_ADMISSION_PASSES"
                    ),
                    "primary_surface_role": "PRIMARY_COUNTING_SURFACE_CANDIDATE",
                    "team_surface_role": "REFLECTION_ONLY_SURFACE_CANDIDATE",
                    "double_count_suppression_candidate_state": (
                        "CANDIDATE_PRIMARY_ROLE_ONLY"
                        if relation_status == "PASS_CANDIDATE_CLASSIFICATION"
                        else "REVIEW_REQUIRED_CONTEXT_UNRESOLVED"
                    ),
                    "relation_candidate_is_event_truth": False,
                    "reflection_equivalence_truth": False,
                    "double_count_suppression_is_final": False,
                    "count_value_output_allowed": False,
                    "cross_role_fusion_allowed": False,
                    "event_instance_allowed": False,
                    "validated_event_identity": False,
                    "canonical_event_count": CANONICAL_EVENT_COUNT,
                    "claim_ceiling": CLAIM_CEILING,
                }
            )

    if len(relation_records) != len(relations) and not blocks:
        blocks.append("relation_output_coverage_mismatch")

    classification_counts = Counter(
        record.get("relation_classification") for record in relation_records
    )
    role_pair_counts = Counter(
        "+".join(record.get("source_roles") or []) for record in relation_records
    )
    family_counts = Counter(
        record.get("action_family_candidate") for record in relation_records
    )
    review_required_count = sum(
        record.get("relation_record_status") == "REVIEW_REQUIRED"
        for record in relation_records
    )
    candidate_clear_count = len(relation_records) - review_required_count
    double_count_suppression_candidate_count = sum(
        record.get("double_count_suppression_candidate_state")
        == "CANDIDATE_PRIMARY_ROLE_ONLY"
        for record in relation_records
    )

    action_status = str(
        action_payload.get("module_status") or action_payload.get("status") or "UNKNOWN"
    )
    taxonomy_status = str(
        taxonomy_payload.get("module_status")
        or taxonomy_payload.get("status")
        or "UNKNOWN"
    )
    for prefix, status in (("action", action_status), ("taxonomy", taxonomy_status)):
        if status == "FAIL_CLOSED":
            blocks.append(f"{prefix}_input_fail_closed")
        elif status == "REVIEW_REQUIRED":
            reviews.append(f"{prefix}_upstream_review_required")
        elif status != "PASS":
            reviews.append(f"{prefix}_upstream_status_review:{status}")
    if review_required_count:
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
        "resolved_relation_candidates": relation_records,
        "source_action_bundle_candidate_count": len(bundles),
        "source_cross_role_relation_candidate_count": len(relations),
        "resolved_relation_candidate_count": len(relation_records),
        "candidate_clear_relation_count": candidate_clear_count,
        "review_required_relation_count": review_required_count,
        "double_count_suppression_candidate_count": (
            double_count_suppression_candidate_count
        ),
        "relation_classification_counts": dict(sorted(classification_counts.items())),
        "relation_role_pair_counts": dict(sorted(role_pair_counts.items())),
        "relation_family_counts": dict(sorted(family_counts.items())),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "link_policy": (
            "EXACT_MATCH_BINDING_TEAM_PERIOD_START_END_COORDINATE_FAMILY_AND_ROLE_PAIR"
        ),
        "taxonomy_core_integrity_policy": (
            "EXACT_RECORD_TO_SUPPORTING_REVIEW_BUNDLE_CORE_AND_FAMILY_SET"
        ),
        "same_time_only_link_allowed": False,
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
        "production_release": False,
    }


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA CROSS-ROLE RELATION CANDIDATE RESOLVER LITE V1",
        f"status={payload.get('status')}",
        f"source_cross_role_relation_candidate_count={payload.get('source_cross_role_relation_candidate_count')}",
        f"resolved_relation_candidate_count={payload.get('resolved_relation_candidate_count')}",
        f"candidate_clear_relation_count={payload.get('candidate_clear_relation_count')}",
        f"review_required_relation_count={payload.get('review_required_relation_count')}",
        f"double_count_suppression_candidate_count={payload.get('double_count_suppression_candidate_count')}",
        f"relation_classification_counts={payload.get('relation_classification_counts')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def _analyst_audit(payload: dict[str, Any]) -> str:
    counts = payload.get("relation_classification_counts") or {}
    lines = [
        "HPFA ANALYST AUDIT — CROSS-ROLE RELATION CANDIDATES",
        f"Visible exact cross-role relation candidates: {payload.get('resolved_relation_candidate_count', 0)}",
        f"Clear relation candidate context: {payload.get('candidate_clear_relation_count', 0)}",
        f"Review-required relation context: {payload.get('review_required_relation_count', 0)}",
        f"Player-team clear: {counts.get('EXACT_PLAYER_TEAM_REFLECTION_CANDIDATE_CLEAR', 0)}",
        f"Player-team classified context: {counts.get('EXACT_PLAYER_TEAM_REFLECTION_CANDIDATE_CLASSIFIED_CONTEXT', 0)}",
        f"Player-team unresolved context: {counts.get('REVIEW_REQUIRED_PLAYER_TEAM_UNRESOLVED_CONTEXT', 0)}",
        f"Goalkeeper-team clear: {counts.get('EXACT_GOALKEEPER_TEAM_REFLECTION_CANDIDATE_CLEAR', 0)}",
        f"Goalkeeper-team classified context: {counts.get('EXACT_GOALKEEPER_TEAM_REFLECTION_CANDIDATE_CLASSIFIED_CONTEXT', 0)}",
        f"Goalkeeper-team unresolved context: {counts.get('REVIEW_REQUIRED_GOALKEEPER_TEAM_UNRESOLVED_CONTEXT', 0)}",
        (
            "Analyst-safe meaning: player or goalkeeper primary surfaces and team reflection "
            "surfaces were related only where exact time, location, team and family evidence matched."
        ),
        (
            "Taxonomy context was accepted only after exact source-role, identity, time, "
            "coordinate and family-set integrity checks against its supporting review bundles."
        ),
        (
            "The primary-role surface is only a future counting candidate; no event count, "
            "fusion or final double-count suppression was produced."
        ),
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {name: output / filename for name, filename in OUTPUTS.items()}
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(_analyst_audit(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-bundle", required=True)
    parser.add_argument("--multi-family-taxonomy", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    action_payload = load_json(
        args.action_bundle,
        "action_bundle_input_unreadable_or_malformed",
    )
    taxonomy_payload = load_json(
        args.multi_family_taxonomy,
        "multi_family_taxonomy_input_unreadable_or_malformed",
    )
    payload = build_cross_role_relation_candidate_resolver(
        action_payload,
        taxonomy_payload,
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source_cross_role_relation_candidate_count": payload[
                    "source_cross_role_relation_candidate_count"
                ],
                "resolved_relation_candidate_count": payload[
                    "resolved_relation_candidate_count"
                ],
                "candidate_clear_relation_count": payload[
                    "candidate_clear_relation_count"
                ],
                "review_required_relation_count": payload[
                    "review_required_relation_count"
                ],
                "canonical_event_count": payload["canonical_event_count"],
                "production_release": payload["production_release"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
