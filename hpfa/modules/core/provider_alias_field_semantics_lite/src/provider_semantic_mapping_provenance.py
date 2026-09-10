from __future__ import annotations

from collections import Counter
from typing import Any

MAPPING_PROVENANCE_VERSION = "provider_semantic_mapping_provenance_v1"
SEMANTIC_EQUIVALENCE_STATE = "NOT_VALIDATED"
MAPPING_VALIDATION_STATE = "NOT_VALIDATED"
SCHEMA_VERSION_UNKNOWN = "UNKNOWN"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _schema_version(payload: dict[str, Any]) -> str:
    for key in ("provider_schema_version", "schema_version", "source_schema_version", "version"):
        value = _clean(payload.get(key))
        if value:
            return value
    return SCHEMA_VERSION_UNKNOWN


def _provider_ref(payload: dict[str, Any]) -> str:
    for key in ("provider", "provider_ref", "source_provider", "vendor"):
        value = _clean(payload.get(key))
        if value:
            return value
    return "UNKNOWN_PROVIDER"


def _mapping_semantics(row: dict[str, Any]) -> tuple[str, str, list[str], list[str]]:
    status = _clean(row.get("mapping_status"))
    canonical = _clean(row.get("canonical_key_candidate"))
    if status == "UNKNOWN_PRESERVED" or not canonical:
        return (
            "UNVERIFIED",
            "UNRESOLVED",
            [],
            ["provider_field_semantics_not_admitted"],
        )
    if status == "AGGREGATE_METRIC_SURFACE_CANDIDATE":
        return (
            "MANY_TO_ONE",
            "LOSSY",
            ["metric_specific_definition", "qualifier_granularity"],
            ["aggregate_label_surface_only", "metric_definition_not_bound"],
        )
    if status == "UPSTREAM_IDENTITY_ROLE_CANDIDATE":
        return (
            "CONDITIONAL_MAPPING",
            "POTENTIALLY_LOSSY",
            ["provider_identity_definition"],
            ["upstream_identity_role_candidate_only"],
        )
    if status == "EXACT_RULE_CANDIDATE":
        return (
            "RENAMED_ONLY",
            "UNKNOWN_LOSS",
            [],
            ["field_name_rule_only", "semantic_equivalence_not_validated"],
        )
    return (
        "CONDITIONAL_MAPPING",
        "UNKNOWN_LOSS",
        [],
        ["upstream_candidate_semantics_only"],
    )


def enrich_mapping_provenance(
    result: dict[str, Any],
    *,
    csv_payload: dict[str, Any],
    xlsx_payload: dict[str, Any],
    xml_payload: dict[str, Any],
) -> dict[str, Any]:
    payload_by_format = {"csv": csv_payload, "xlsx": xlsx_payload, "xml": xml_payload}
    rows = result.get("field_semantic_records") or []
    mapping_type_counts: Counter[str] = Counter()
    loss_state_counts: Counter[str] = Counter()
    unknown_schema_count = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        fmt = _clean(row.get("format")).lower()
        source_payload = payload_by_format.get(fmt, {})
        provider = _provider_ref(source_payload)
        schema_version = _schema_version(source_payload)
        mapping_type, loss_state, lost_information, assumptions = _mapping_semantics(row)
        mapping_type_counts[mapping_type] += 1
        loss_state_counts[loss_state] += 1
        if schema_version == SCHEMA_VERSION_UNKNOWN:
            unknown_schema_count += 1

        row["provider_semantic_mapping_version"] = MAPPING_PROVENANCE_VERSION
        row["provider_ref"] = provider
        row["provider_schema_version"] = schema_version
        row["mapping_type"] = mapping_type
        row["mapping_cardinality"] = (
            "MANY_TO_ONE" if mapping_type == "MANY_TO_ONE" else "ONE_TO_ONE_CANDIDATE"
        )
        row["mapping_loss_state"] = loss_state
        row["lost_information"] = lost_information
        row["introduced_assumptions"] = assumptions
        row["coordinate_transform"] = "NONE_DECLARED"
        row["time_transform"] = "NONE_DECLARED"
        row["unit_transform"] = "NONE_DECLARED"
        row["mapping_validation_state"] = MAPPING_VALIDATION_STATE
        row["semantic_equivalence_state"] = SEMANTIC_EQUIVALENCE_STATE
        row["schema_version_binding_state"] = (
            "SCHEMA_VERSION_BOUND" if schema_version != SCHEMA_VERSION_UNKNOWN else "SCHEMA_VERSION_UNKNOWN"
        )
        row["schema_change_requires_revalidation"] = True
        row["mapping_creates_evidence_independence"] = False
        row["canonicalization_creates_new_observation_truth"] = False

    for group in result.get("candidate_equivalence_groups") or []:
        if not isinstance(group, dict):
            continue
        group["semantic_equivalence_state"] = SEMANTIC_EQUIVALENCE_STATE
        group["member_count_is_independent_evidence_count"] = False
        group["canonical_key_match_is_definition_match"] = False
        group["cross_format_candidate_is_empirical_equivalence"] = False

    result["provider_semantic_mapping_provenance"] = {
        "version": MAPPING_PROVENANCE_VERSION,
        "mapping_type_counts": dict(sorted(mapping_type_counts.items())),
        "mapping_loss_state_counts": dict(sorted(loss_state_counts.items())),
        "schema_version_unknown_record_count": unknown_schema_count,
        "format_normalization_is_semantic_normalization": False,
        "field_name_match_is_definition_match": False,
        "ontology_alignment_is_construct_validity": False,
        "lossy_mapping_is_equivalence": False,
        "coordinate_normalization_is_measurement_equivalence": False,
        "timestamp_normalization_is_temporal_precision_equivalence": False,
        "canonicalization_creates_evidence_independence": False,
        "production_release": False,
    }
    return result
