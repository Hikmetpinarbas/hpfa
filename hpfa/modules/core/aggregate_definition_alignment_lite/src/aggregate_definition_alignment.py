from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "aggregate_definition_alignment_lite_v1"
REGISTRY_VERSION = "2.0.0"
RESEARCH_HARDENING_VERSION = "R18_R19_R22_R24_R36_SOURCE_ROLE_v2"
CANONICAL_EVENT_COUNT = "UNKNOWN"

REQUIRED_DEFINITION_FIELDS = {
    "definition_id",
    "provider_id",
    "provider_version",
    "source_roles",
    "aggregate_label",
    "metric_id",
    "metric_definition_fingerprint_sha256",
    "value_type",
    "unit",
    "numerator_definition",
    "denominator_definition",
    "required_occurrence_semantics",
    "definition_evidence_status",
    "derivation_dependency",
    "independence_status",
    "claim_ceiling",
}
ACCEPTED_SEMANTIC_STATUSES = {
    "EXACT_REVIEWED_CANDIDATE",
    "EXACT_ALIAS_CANDIDATE",
    "PREFIX_RULE_REVIEWED_CANDIDATE",
}
REVIEWED_DEFINITION_STATUS = "REVIEWED_PROVIDER_DEFINITION_CANDIDATE"
RATE_TYPES = {"rate", "percentage", "ratio", "per_90"}
ALLOWED_SOURCE_FORMATS = {"csv", "xml"}

SOURCE_SURFACE_CONTRACT = {
    "csv": {
        "role": "ACTION_COORDINATE_CANDIDATE_SURFACE",
        "allows": ["action_candidate", "coordinate_candidate"],
        "does_not_establish": ["physical_event_identity", "validated_event_time"],
    },
    "xml": {
        "role": "ACTION_TYPE_SOURCE_INTERVAL_CANDIDATE_SURFACE",
        "allows": ["action_type_candidate", "source_start_end_interval_candidate"],
        "does_not_establish": ["physical_event_identity", "true_action_duration", "sequence_truth"],
    },
    "xlsx": {
        "role": "AGGREGATE_CANDIDATE_SURFACE",
        "allows": ["aggregate_label_candidate", "aggregate_value_surface_candidate"],
        "does_not_establish": ["event_identity", "occurrence_identity", "independent_confirmation"],
    },
}


def normalize_label(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("%", " percent ")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _fail(code: str, detail: Any = None) -> dict[str, Any]:
    item = {"code": code, "severity": "FAIL_CLOSED"}
    if detail is not None:
        item["detail"] = detail
    return item


def _review(code: str, detail: Any = None) -> dict[str, Any]:
    item = {"code": code, "severity": "REVIEW_REQUIRED"}
    if detail is not None:
        item["detail"] = detail
    return item


def _upstream_guard(
    payload: dict[str, Any],
    expected_module_id: str,
    *,
    allowed_statuses: set[str],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if payload.get("module_id") != expected_module_id:
        hits.append(_fail("upstream_module_id_mismatch", expected_module_id))
    status = str(payload.get("status") or "")
    if status not in allowed_statuses:
        hits.append(_fail("upstream_status_not_admitted", {"module": expected_module_id, "status": status}))
    elif status == "REVIEW_REQUIRED":
        hits.append(_review("upstream_review_required", {"module": expected_module_id, "status": status}))
    if payload.get("canonical_event_count") not in (None, CANONICAL_EVENT_COUNT):
        hits.append(_fail("upstream_canonical_event_count_claimed", expected_module_id))
    if payload.get("production_release") is True:
        hits.append(_fail("upstream_production_release_claimed", expected_module_id))
    return hits


def _reconciliation_guard(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hits = _upstream_guard(
        payload,
        "cross_format_reconciliation_lite_v1",
        allowed_statuses={"PASS", "SMOKE_PASS", "REVIEW_REQUIRED"},
    )
    forbidden_truth_keys = (
        "validated_cross_format_equivalence",
        "validated_team_identity",
        "validated_player_identity",
        "validated_event_identity",
        "global_event_identity",
    )
    for key in forbidden_truth_keys:
        if payload.get(key) is True:
            hits.append(_fail("reconciliation_truth_overclaim", key))
    if payload.get("production_release") is True:
        hits.append(_fail("reconciliation_production_overclaim"))
    return hits


def _aggregate_surfaces(xlsx_payload: dict[str, Any]) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    for file_row in xlsx_payload.get("files", []) or []:
        file_role = str(file_row.get("source_role") or "UNKNOWN")
        source_sha256 = _text(file_row.get("sha256"))
        relative_path = _text(file_row.get("relative_path") or file_row.get("file_name"))
        for sheet in file_row.get("sheets", []) or []:
            role = str(sheet.get("source_role") or file_role)
            for metric in sheet.get("metric_inventory", []) or []:
                label = normalize_label(metric.get("normalized_metric_label") or metric.get("raw_metric_label"))
                if label:
                    surfaces.append(
                        {
                            "source_role": role,
                            "normalized_label": label,
                            "source_sha256": source_sha256 or None,
                            "source_relative_path": relative_path or None,
                        }
                    )
    return surfaces


def _semantic_records(label_payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in label_payload.get("provider_label_records", []) or []:
        fmt = str(row.get("source_format") or "").casefold()
        if fmt in ALLOWED_SOURCE_FORMATS and row.get("mapping_status") in ACCEPTED_SEMANTIC_STATUSES:
            records.append(row)
    return records


def _semantic_match(row: dict[str, Any], required: dict[str, Any]) -> bool:
    for key, expected in required.items():
        if key == "source_formats":
            allowed = {str(item).casefold() for item in _list(expected)}
            if str(row.get("source_format") or "").casefold() not in allowed:
                return False
            continue
        if key == "source_roles":
            if str(row.get("source_role")) not in {str(item) for item in _list(expected)}:
                return False
            continue
        if key == "normalized_label":
            actual = normalize_label(row.get("normalized_label") or row.get("raw_label") or row.get("provider_label"))
            if actual != normalize_label(expected):
                return False
            continue
        if row.get(key) not in _list(expected):
            return False
    return True


def _provider_provenance_records(reconciliation_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = reconciliation_payload.get("provider_semantic_provenance_records", []) or []
    return [row for row in rows if isinstance(row, dict)]


def _surface_provenance_matches(
    *,
    source_sha256: Any,
    source_role: Any,
    normalized_label: Any,
    provenance_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sha = _text(source_sha256).casefold()
    role = _text(source_role)
    label = normalize_label(normalized_label)
    if not sha or not role or not label:
        return []
    return [
        row
        for row in provenance_records
        if _text(row.get("source_sha256")).casefold() == sha
        and _text(row.get("source_role")) == role
        and normalize_label(row.get("normalized_label") or row.get("raw_label")) == label
    ]


def _provider_binding(
    provenance_records: list[dict[str, Any]],
    *,
    expected_provider_id: Any,
    expected_provider_version: Any,
    provider_semantics_validated: bool,
) -> dict[str, Any]:
    expected_id = normalize_label(expected_provider_id)
    expected_version = _text(expected_provider_version)
    result = {
        "admitted": False,
        "expected_provider_id": _text(expected_provider_id),
        "expected_provider_version": expected_version,
        "observed_provider_ids": [],
        "observed_provider_versions": [],
        "candidate_provider_values": [],
        "binding_hits": [],
    }
    candidates = sorted(
        {
            _text(row.get("provider_candidate"))
            for row in provenance_records
            if _text(row.get("provider_candidate"))
        }
    )
    result["candidate_provider_values"] = candidates

    if not provenance_records:
        result["binding_hits"].append(_review("provider_provenance_missing"))
        return result

    if not provider_semantics_validated:
        result["binding_hits"].append(_review("provider_semantics_not_validated"))
        return result

    admitted_records = [
        row for row in provenance_records if row.get("provider_provenance_admitted") is True
    ]
    if not admitted_records:
        result["binding_hits"].append(_review("provider_provenance_not_admitted"))
        return result

    provider_ids = sorted(
        {
            _text(row.get("provider_id"))
            for row in admitted_records
            if _text(row.get("provider_id"))
        }
    )
    versions = sorted(
        {
            _text(row.get("provider_version"))
            for row in admitted_records
            if _text(row.get("provider_version"))
        }
    )
    result["observed_provider_ids"] = provider_ids
    result["observed_provider_versions"] = versions

    if not provider_ids:
        result["binding_hits"].append(_review("provider_id_missing"))
    elif len({normalize_label(value) for value in provider_ids}) != 1:
        result["binding_hits"].append(_review("provider_id_ambiguous", provider_ids))
    elif normalize_label(provider_ids[0]) != expected_id:
        result["binding_hits"].append(
            _review(
                "provider_id_mismatch",
                {"expected": _text(expected_provider_id), "observed": provider_ids[0]},
            )
        )

    if not versions:
        result["binding_hits"].append(_review("provider_version_missing"))
    elif len(set(versions)) != 1:
        result["binding_hits"].append(_review("provider_version_ambiguous", versions))
    elif versions[0] != expected_version:
        result["binding_hits"].append(
            _review(
                "provider_version_mismatch",
                {"expected": expected_version, "observed": versions[0]},
            )
        )

    result["admitted"] = not result["binding_hits"]
    return result


def _metric_index(metric_policy: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    index: dict[str, dict[str, Any]] = {}
    hits: list[dict[str, Any]] = []
    for row in metric_policy.get("metrics", []) or []:
        metric_id = str(row.get("metric_id") or "").strip()
        if not metric_id:
            hits.append(_fail("metric_id_missing"))
        elif metric_id in index:
            hits.append(_fail("duplicate_metric_id", metric_id))
        else:
            index[metric_id] = row
    return index, hits


def _validate_definition(row: dict[str, Any], seen: set[str]) -> tuple[str | None, list[dict[str, Any]]]:
    definition_id = str(row.get("definition_id") or "").strip()
    hits: list[dict[str, Any]] = []
    if not definition_id:
        return None, [_fail("definition_id_missing")]
    if definition_id in seen:
        return None, [_fail("duplicate_definition_id", definition_id)]
    seen.add(definition_id)
    missing = sorted(
        field for field in REQUIRED_DEFINITION_FIELDS
        if row.get(field) in (None, "", [])
    )
    for field in missing:
        hits.append(_fail("definition_field_missing", f"{definition_id}:{field}"))
    fingerprint = _text(row.get("metric_definition_fingerprint_sha256"))
    if fingerprint and not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        hits.append(_fail("metric_definition_fingerprint_invalid", definition_id))
    if not isinstance(row.get("required_occurrence_semantics"), list):
        hits.append(_fail("required_occurrence_semantics_must_be_array", definition_id))
    independence = str(row.get("independence_status") or "").upper()
    if "INDEPENDENT" in independence and not independence.startswith("NON_"):
        hits.append(_fail("independence_overclaim_same_provider_surface", independence))
    return definition_id, hits


def build_alignment(
    xlsx_payload: dict[str, Any],
    label_semantics_payload: dict[str, Any],
    reconciliation_payload: dict[str, Any],
    metric_policy_payload: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    hits = (
        _upstream_guard(
            xlsx_payload,
            "xlsx_surface_reader_lite_v1",
            allowed_statuses={"PASS", "SMOKE_PASS"},
        )
        + _upstream_guard(
            label_semantics_payload,
            "provider_label_value_semantics_lite_v1",
            allowed_statuses={"PASS", "SMOKE_PASS", "REVIEW_REQUIRED"},
        )
        + _reconciliation_guard(reconciliation_payload)
        + _upstream_guard(
            metric_policy_payload,
            "metric_definition_policy_lite_v1",
            allowed_statuses={"SMOKE_PASS", "REVIEW_REQUIRED"},
        )
    )
    if registry.get("registry_version") != REGISTRY_VERSION:
        hits.append(_fail("registry_version_mismatch", registry.get("registry_version")))

    metric_index, metric_hits = _metric_index(metric_policy_payload)
    hits.extend(metric_hits)
    aggregate_surfaces = _aggregate_surfaces(xlsx_payload)
    semantic_records = _semantic_records(label_semantics_payload)
    provenance_records = _provider_provenance_records(reconciliation_payload)
    provider_semantics_validated = reconciliation_payload.get("validated_provider_semantics") is True
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw in registry.get("definitions", []) or []:
        if not isinstance(raw, dict):
            hits.append(_fail("definition_record_not_object"))
            continue
        definition_id, definition_hits = _validate_definition(raw, seen)
        hits.extend(definition_hits)
        if definition_id is None:
            continue

        row_hits: list[dict[str, Any]] = list(definition_hits)
        roles = {str(role) for role in _list(raw.get("source_roles"))}
        label = normalize_label(raw.get("aggregate_label"))
        expected_provider_id = raw.get("provider_id")
        expected_provider_version = raw.get("provider_version")

        matching_aggregate_surfaces = [
            surface
            for surface in aggregate_surfaces
            if surface["source_role"] in roles and surface["normalized_label"] == label
        ]
        aggregate_label_surface_observed = bool(matching_aggregate_surfaces)
        aggregate_bindings: list[dict[str, Any]] = []
        for surface in matching_aggregate_surfaces:
            matches = _surface_provenance_matches(
                source_sha256=surface.get("source_sha256"),
                source_role=surface.get("source_role"),
                normalized_label=surface.get("normalized_label"),
                provenance_records=provenance_records,
            )
            binding = _provider_binding(
                matches,
                expected_provider_id=expected_provider_id,
                expected_provider_version=expected_provider_version,
                provider_semantics_validated=provider_semantics_validated,
            )
            aggregate_bindings.append({**surface, **binding})

        aggregate_label_observed = any(binding["admitted"] for binding in aggregate_bindings)
        if not aggregate_label_surface_observed:
            row_hits.append(_review("aggregate_label_not_observed", label))
        elif not aggregate_label_observed:
            detail = [
                hit
                for binding in aggregate_bindings
                for hit in binding.get("binding_hits", [])
            ]
            row_hits.append(
                _review(
                    "aggregate_provider_binding_unresolved",
                    detail or [{"code": "provider_provenance_missing"}],
                )
            )

        metric_id = str(raw.get("metric_id") or "")
        metric = metric_index.get(metric_id)
        metric_fp = None
        denominator_closure_status = "UNRESOLVED"
        rate_calculation_admitted = False
        metric_definition_bound = False
        if metric is None:
            row_hits.append(_fail("metric_definition_unresolved", metric_id))
        else:
            metric_fp = _text(metric.get("definition_fingerprint_sha256"))
            expected_fp = _text(raw.get("metric_definition_fingerprint_sha256"))
            if metric.get("definition_status") != "DEFINITION_CANDIDATE_READY":
                row_hits.append(_fail("metric_policy_not_ready", metric_id))
            if str(metric.get("value_type") or "").lower() != str(raw.get("value_type") or "").lower():
                row_hits.append(_fail("metric_value_type_mismatch", metric_id))
            if str(metric.get("unit") or "") != str(raw.get("unit") or ""):
                row_hits.append(_review("metric_unit_surface_mismatch", metric_id))
            if expected_fp != metric_fp:
                row_hits.append(_fail("metric_definition_fingerprint_mismatch", {"metric_id": metric_id, "expected": expected_fp, "actual": metric_fp}))
            if _text(raw.get("numerator_definition")) != _text(metric.get("numerator_definition")):
                row_hits.append(_fail("metric_numerator_definition_mismatch", metric_id))
            if _text(raw.get("denominator_definition")) != _text(metric.get("denominator_definition")):
                row_hits.append(_fail("metric_denominator_definition_mismatch", metric_id))
            metric_definition_bound = not any(
                hit["code"] in {
                    "metric_definition_fingerprint_mismatch",
                    "metric_numerator_definition_mismatch",
                    "metric_denominator_definition_mismatch",
                }
                for hit in row_hits
            )
            denominator_closure_status = str(metric.get("denominator_closure_status") or "UNKNOWN")
            rate_calculation_admitted = bool(metric.get("rate_calculation_admitted", False))
            if str(raw.get("value_type") or "").lower() in RATE_TYPES:
                if not metric_definition_bound:
                    row_hits.append(_fail("denominator_closure_not_bound_to_aligned_definition", metric_id))
                    denominator_closure_status = "UNBOUND"
                    rate_calculation_admitted = False
                elif denominator_closure_status != "CLOSED":
                    row_hits.append(_review("metric_denominator_closure_unresolved", denominator_closure_status))
                if not rate_calculation_admitted:
                    row_hits.append(_review("metric_rate_calculation_not_admitted", metric_id))

        semantic_support: list[dict[str, Any]] = []
        for requirement in raw.get("required_occurrence_semantics", []) or []:
            matches = [
                record for record in semantic_records
                if isinstance(requirement, dict) and _semantic_match(record, requirement)
            ]
            provider_bound_record_ids: list[str] = []
            binding_details: list[dict[str, Any]] = []
            for record in matches:
                provenance_matches = _surface_provenance_matches(
                    source_sha256=record.get("source_sha256"),
                    source_role=record.get("source_role"),
                    normalized_label=record.get("normalized_label") or record.get("raw_label"),
                    provenance_records=provenance_records,
                )
                binding = _provider_binding(
                    provenance_matches,
                    expected_provider_id=expected_provider_id,
                    expected_provider_version=expected_provider_version,
                    provider_semantics_validated=provider_semantics_validated,
                )
                binding_details.append(
                    {
                        "record_id": str(record.get("record_id")),
                        **binding,
                    }
                )
                if binding["admitted"]:
                    provider_bound_record_ids.append(str(record.get("record_id")))

            formats = sorted({str(record.get("source_format") or "").casefold() for record in matches})
            semantic_support.append(
                {
                    "requirement": requirement,
                    "match_count": len(matches),
                    "provider_bound_match_count": len(provider_bound_record_ids),
                    "source_formats": formats,
                    "record_ids": [str(record.get("record_id")) for record in matches[:20]],
                    "provider_bound_record_ids": provider_bound_record_ids[:20],
                    "provider_bindings": binding_details[:20],
                    "independent_confirmation": False,
                }
            )
            if not matches:
                row_hits.append(_review("required_occurrence_semantics_not_observed", requirement))
            elif not provider_bound_record_ids:
                row_hits.append(
                    _review(
                        "required_occurrence_provider_binding_unresolved",
                        requirement,
                    )
                )

        if raw.get("definition_evidence_status") != REVIEWED_DEFINITION_STATUS:
            row_hits.append(_review("provider_definition_evidence_unresolved", raw.get("definition_evidence_status")))

        unresolved_dependencies = [
            item for item in _list(raw.get("derivation_dependency"))
            if str(item).upper().endswith(("UNRESOLVED", "UNKNOWN"))
        ]
        if unresolved_dependencies:
            row_hits.append(_review("derivation_dependency_unresolved", unresolved_dependencies))

        structural_block = any(hit["severity"] == "FAIL_CLOSED" for hit in row_hits)
        review_required = any(hit["severity"] == "REVIEW_REQUIRED" for hit in row_hits)
        if structural_block:
            decision = "BLOCKED_INVALID_DEFINITION"
        elif review_required:
            decision = "REVIEW_REQUIRED_DEFINITION_ALIGNMENT"
        else:
            decision = "DEFINITION_ALIGNMENT_CANDIDATE"

        rows.append(
            {
                "definition_id": definition_id,
                "metric_id": metric_id,
                "metric_definition_fingerprint_sha256": metric_fp,
                "metric_definition_bound": metric_definition_bound,
                "provider_id": raw.get("provider_id"),
                "provider_version": raw.get("provider_version"),
                "source_roles": sorted(roles),
                "aggregate_label": raw.get("aggregate_label"),
                "normalized_aggregate_label": label,
                "aggregate_label_surface_observed": aggregate_label_surface_observed,
                "aggregate_label_observed": aggregate_label_observed,
                "aggregate_provider_bindings": aggregate_bindings,
                "provider_semantics_validated_upstream": provider_semantics_validated,
                "semantic_support": semantic_support,
                "definition_evidence_status": raw.get("definition_evidence_status"),
                "derivation_dependency": raw.get("derivation_dependency"),
                "independence_status": raw.get("independence_status"),
                "denominator_closure_status": denominator_closure_status,
                "rate_calculation_admitted": rate_calculation_admitted,
                "alignment_decision": decision,
                "alignment_hits": row_hits,
                "comparison_allowed": False,
                "aggregate_equivalence_truth": False,
                "independent_confirmation_allowed": False,
                "measurement_invariance_truth": False,
                "cross_group_comparability_status": "R36_REQUIRED_BEFORE_GROUP_COMPARISON",
                "metric_value_output_allowed": False,
                "claim_allowed": False,
                "claim_ceiling": raw.get("claim_ceiling"),
            }
        )

    if not registry.get("definitions"):
        hits.append(_fail("definition_registry_empty"))

    hits.extend(
        hit for row in rows for hit in row["alignment_hits"]
        if hit["severity"] == "FAIL_CLOSED"
    )
    deduped = {
        json.dumps(hit, sort_keys=True, ensure_ascii=False): hit for hit in hits
    }
    hits = list(deduped.values())

    row_review_hits = [
        hit for row in rows for hit in row["alignment_hits"]
        if hit["severity"] == "REVIEW_REQUIRED"
    ]
    top_review_hits = [hit for hit in hits if hit["severity"] == "REVIEW_REQUIRED"]
    review_hits = list({
        json.dumps(hit, sort_keys=True, ensure_ascii=False): hit
        for hit in (top_review_hits + row_review_hits)
    }.values())

    status = (
        "FAIL_CLOSED"
        if any(hit["severity"] == "FAIL_CLOSED" for hit in hits)
        else (
            "REVIEW_REQUIRED"
            if review_hits or any(row["alignment_decision"] == "REVIEW_REQUIRED_DEFINITION_ALIGNMENT" for row in rows)
            else "SMOKE_PASS"
        )
    )

    return {
        "module_id": MODULE_ID,
        "status": status,
        "registry_version": REGISTRY_VERSION,
        "research_hardening_version": RESEARCH_HARDENING_VERSION,
        "definition_candidate_count": len(rows),
        "alignment_decision_counts": dict(sorted(Counter(row["alignment_decision"] for row in rows).items())),
        "alignment_rows": rows,
        "hard_block_hits": [hit for hit in hits if hit["severity"] == "FAIL_CLOSED"],
        "review_hits": review_hits,
        "source_surface_contract": SOURCE_SURFACE_CONTRACT,
        "source_role_separation_required": True,
        "provider_provenance_binding_required": True,
        "provider_candidate_is_validated_provider_identity": False,
        "csv_xml_candidate_linkage_is_physical_event_identity": False,
        "xlsx_row_is_event_identity": False,
        "same_label_is_same_definition": False,
        "count_parity_is_definition_equivalence": False,
        "same_provider_multi_surface_is_independent_confirmation": False,
        "definition_alignment_candidate_only": True,
        "aggregate_equivalence_truth": False,
        "independent_confirmation_allowed": False,
        "comparison_allowed": False,
        "measurement_invariance_truth": False,
        "cross_group_comparability_status": "R36_REQUIRED_BEFORE_GROUP_COMPARISON",
        "metric_value_output_allowed": False,
        "quality_truth_output_allowed": False,
        "claim_allowed": False,
        "active_match_evidence_pass": False,
        "single_match_validation_scope": "CURRENT_ACTIVE_MATCH_ONLY",
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "claim_boundary": (
            "aggregate_definition_candidate_only_provider_provenance_bound_no_value_"
            "no_equivalence_no_event_identity_no_independent_confirmation_no_group_comparison_no_claim"
        ),
    }


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_report(
    xlsx_path: str | Path,
    label_semantics_path: str | Path,
    reconciliation_path: str | Path,
    metric_policy_path: str | Path,
    registry_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    report = build_alignment(
        load_json(xlsx_path),
        load_json(label_semantics_path),
        load_json(reconciliation_path),
        load_json(metric_policy_path),
        load_json(registry_path),
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    report["outputs"] = {"json": str(destination)}
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report
