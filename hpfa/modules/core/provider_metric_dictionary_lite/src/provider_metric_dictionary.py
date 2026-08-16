from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "provider_metric_dictionary_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
PRODUCTION_RELEASE = False

FINGERPRINT_FIELDS = (
    "provider_id", "provider_version", "source_role", "metric_id", "construct", "unit",
    "semantic_type", "numerator_definition", "denominator_definition", "eligibility_scope",
    "success_outcome_rule", "spatial_rule", "temporal_window", "aggregation_level",
    "missing_zero_denominator_policy", "derivation_lineage", "definition_source",
    "definition_evidence_status", "claim_ceiling",
)
OPERATIONAL_SEMANTIC_FIELDS = (
    "metric_family", "event_only_compatible", "comparison_allowed",
    "metric_value_output_allowed", "upstream_bindings",
)
DERIVATION_SEMANTIC_FIELDS = (
    "provider_id", "provider_version", "metric_id", "formula",
    "component_metric_ids", "derivation_status", "provider_definition_required",
    "upstream_denominator_policy_id",
)
ALLOWED_DEFINITION_STATUSES = {
    "REVIEWED_PROVIDER_DEFINITION", "USER_DEFINED_DOMAIN_CONTRACT",
    "DATA_CONFIRMED_CANDIDATE", "DATA_INFERRED_CANDIDATE",
    "PROVIDER_DEFINITION_REQUIRED", "REFERENCE_ONLY_REVIEWED_DEFINITION",
    "DATA_CONTRADICTED", "INSUFFICIENT_SAMPLE", "NOT_APPLICABLE",
}
PROVIDER_ADMISSIBLE_STATUS = "REVIEWED_PROVIDER_DEFINITION"
DOMAIN_ADMISSIBLE_STATUS = "USER_DEFINED_DOMAIN_CONTRACT"
UNVERIFIED_PROVIDER_VERSIONS = {
    "", "unknown", "unpublished", "provider_definition_unverified",
    "reference_definition_unversioned",
}
TRACKING_ONLY_TOKENS = {
    "pressure_truth", "pitch_control_truth", "body_orientation_truth",
    "off_ball_truth", "fatigue_truth", "tracking_truth",
}
AUTHORITATIVE_PROVIDER_SOURCE_ROLES = {
    "PROVIDER_OFFICIAL_DEFINITION", "PROVIDER_DOCUMENTATION", "REVIEWED_PROVIDER_DEFINITION",
}
ALLOWED_UPSTREAM_BINDING_KEYS = {
    "metric_policy_id", "aggregate_definition_id", "aggregate_definition_fingerprint_sha256",
}
AGGREGATE_SOURCE_ROLE_COMPATIBILITY = {
    "PROVIDER_SURFACE_CANDIDATE": {
        "PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE",
    },
    "PROVIDER_OFFICIAL_DEFINITION": {
        "PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE",
    },
    "PROVIDER_DOCUMENTATION": {
        "PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE",
    },
    "REVIEWED_PROVIDER_DEFINITION": {
        "PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE",
    },
}
EXPECTED_DICTIONARY_METRIC_FAMILY_BY_POLICY = {
    "pass_completion_rate_candidate": "pass",
}
EXPECTED_DENOMINATOR_POLICY_FINGERPRINTS = {
    "provider_bound_rate_v1": "44b23a6dbf3b11e70c0f5ccf04f0e965f9ee944d07532ec19590867871bd4426",
}
DOMAIN_OPERATIONAL_FIELDS = (
    "metric_family", "event_only_compatible", "comparison_allowed",
    "metric_value_output_allowed", "upstream_bindings",
)
EXPECTED_DOMAIN_OPERATIONAL_FINGERPRINTS = {
    "progressive_open_pass": "45ad4d8b97a3c9131bae2f75c0d061b8f944bcce59a0a33c8ded4e204e309999",
    "final_third_boundary_entry": "693bd04992c5d3ef6c5fd7790a188710ab5b80ee74e481c7c93890516f5a0ccc",
    "final_third_access_established": "693bd04992c5d3ef6c5fd7790a188710ab5b80ee74e481c7c93890516f5a0ccc",
    "chances": "346f8763fd76632578958ec59ef23675b5ded39d90e5ffe593d602a52ae8f199",
}
UPSTREAM_SHARED_SEMANTICS = (
    ("construct", "construct_target"),
    ("unit", "unit"),
    ("semantic_type", "value_type"),
    ("numerator_definition", "numerator_definition"),
    ("denominator_definition", "denominator_definition"),
    ("success_outcome_rule", "success_criteria"),
    ("temporal_window", "observation_window"),
    ("claim_ceiling", "claim_ceiling"),
    ("event_only_compatible", "event_only_compatible"),
    ("comparison_allowed", "comparison_allowed"),
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gap(gap_type: str, detail: str, severity: str = "FAIL_CLOSED") -> dict[str, str]:
    return {"gap_type": gap_type, "detail": detail, "severity": severity}


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fingerprint_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in FINGERPRINT_FIELDS}


def definition_fingerprint(row: dict[str, Any]) -> str:
    return _canonical_hash(_fingerprint_payload(row))


def derivation_semantic_fingerprint(row: dict[str, Any]) -> str:
    return _canonical_hash({field: row.get(field) for field in DERIVATION_SEMANTIC_FIELDS})


def _domain_operational_fingerprint(row: dict[str, Any]) -> str:
    payload = {}
    for field in DOMAIN_OPERATIONAL_FIELDS:
        value = row.get(field)
        if field == "upstream_bindings":
            value = value or {}
        payload[field] = value
    return _canonical_hash(payload)


def operational_semantic_fingerprint(
    row: dict[str, Any],
    *,
    metric_policy_row: dict[str, Any] | None = None,
    denominator_policy_row: dict[str, Any] | None = None,
    aggregate_definition_row: dict[str, Any] | None = None,
) -> str:
    payload = {
        "core_definition_fingerprint_sha256": definition_fingerprint(row),
        "operational_fields": {
            field: (row.get(field) or {} if field == "upstream_bindings" else row.get(field))
            for field in OPERATIONAL_SEMANTIC_FIELDS
        },
        "resolved_metric_policy": metric_policy_row,
        "resolved_denominator_policy": denominator_policy_row,
        "resolved_aggregate_definition": aggregate_definition_row,
    }
    return _canonical_hash(payload)


def _unique_index(
    rows: list[dict[str, Any]], field: str,
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    index: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for row in rows:
        raw = row.get(field)
        if raw in (None, ""):
            continue
        key = str(raw)
        if key in index:
            duplicates.add(key)
            continue
        index[key] = row
    for key in duplicates:
        index.pop(key, None)
    return index, duplicates


def _denominator_behavior_contract(policy_row: dict[str, Any]) -> str:
    zero = str(policy_row.get("zero_denominator_behavior") or "").upper()
    missing = str(policy_row.get("missing_denominator_behavior") or "").upper()
    if zero == "NOT_APPLICABLE" and missing == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    return f"{zero}_IF_VALIDATED_DENOMINATOR_ZERO;{missing}_IF_DENOMINATOR_UNKNOWN"


def build_dictionary_report(
    dictionary: dict[str, Any],
    aliases: dict[str, Any],
    derivations: dict[str, Any],
    conflicts: dict[str, Any],
    *,
    metric_policy: dict[str, Any] | None = None,
    denominator_policy: dict[str, Any] | None = None,
    aggregate_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hard: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    metrics = dictionary.get("metrics", [])
    if dictionary.get("dictionary_version") != "2.0.0":
        hard.append(_gap("dictionary_version_mismatch", str(dictionary.get("dictionary_version"))))
    if tuple(dictionary.get("fingerprint_fields", [])) != FINGERPRINT_FIELDS:
        hard.append(_gap("fingerprint_field_contract_mismatch", "dictionary fingerprint_fields differs from code contract"))
    if not isinstance(metrics, list) or not metrics:
        hard.append(_gap("metric_registry_empty", "metrics"))
        metrics = []

    policy_index, duplicate_policy_ids = _unique_index(
        (metric_policy or {}).get("metrics", []), "metric_id"
    )
    denominator_index, duplicate_denominator_ids = _unique_index(
        (denominator_policy or {}).get("policies", []), "denominator_policy_id"
    )
    aggregate_index, duplicate_aggregate_ids = _unique_index(
        (aggregate_registry or {}).get("definitions", []), "definition_id"
    )
    for identifier in sorted(duplicate_policy_ids):
        hard.append(_gap("duplicate_upstream_metric_policy_id", identifier))
    for identifier in sorted(duplicate_denominator_ids):
        hard.append(_gap("duplicate_upstream_denominator_policy_id", identifier))
    for identifier in sorted(duplicate_aggregate_ids):
        hard.append(_gap("duplicate_upstream_aggregate_definition_id", identifier))

    definition_index: dict[str, dict[str, Any]] = {}
    metric_ids: set[str] = set()
    duplicate_keys: set[str] = set()
    provider_ready_candidates: list[str] = []
    domain_ready_candidates: list[str] = []
    reference_only: list[str] = []
    candidate_only: list[str] = []
    upstream_binding_results: list[dict[str, str]] = []
    operational_fingerprints: dict[str, str] = {}

    for row in metrics:
        row_hard_start = len(hard)
        metric_id = str(row.get("metric_id") or "").strip()
        provider_id = str(row.get("provider_id") or "").strip()
        provider_version = str(row.get("provider_version") or "").strip()
        source_role = str(row.get("source_role") or "").strip()

        for field in sorted(field for field in FINGERPRINT_FIELDS if row.get(field) in (None, "")):
            hard.append(_gap("metric_fingerprint_field_missing", f"{metric_id or 'UNKNOWN'}:{field}"))
        for field in (
            "raw_labels", "metric_family", "event_only_compatible", "provider_binding_admitted",
            "domain_contract_admitted", "comparison_allowed", "metric_value_output_allowed",
        ):
            if field not in row:
                hard.append(_gap("metric_field_missing", f"{metric_id or 'UNKNOWN'}:{field}"))

        if row.get("event_only_compatible") is not True:
            hard.append(_gap("event_only_compatibility_required", metric_id or "UNKNOWN"))
        if not isinstance(row.get("metric_family"), str) or not row.get("metric_family"):
            hard.append(_gap("metric_family_missing_or_invalid", metric_id or "UNKNOWN"))
        if row.get("comparison_allowed") is not False:
            hard.append(_gap("row_comparison_permission_must_be_false", metric_id or "UNKNOWN"))
        if row.get("metric_value_output_allowed") is not False:
            hard.append(_gap("row_metric_value_permission_must_be_false", metric_id or "UNKNOWN"))

        upstream = row.get("upstream_bindings") or {}
        if not isinstance(upstream, dict):
            hard.append(_gap("upstream_bindings_invalid", metric_id or "UNKNOWN"))
            upstream = {}
        unknown_upstream_keys = sorted(set(upstream) - ALLOWED_UPSTREAM_BINDING_KEYS)
        if unknown_upstream_keys:
            hard.append(_gap("upstream_binding_key_unknown", f"{metric_id}:{','.join(unknown_upstream_keys)}"))

        if not metric_id:
            continue
        key = "::".join((provider_id, provider_version, metric_id))
        metric_ids.add(metric_id)
        if key in definition_index:
            duplicate_keys.add(key)
            hard.append(_gap("duplicate_provider_definition_key", key))
            continue
        definition_index[key] = row

        status = row.get("definition_evidence_status")
        if status not in ALLOWED_DEFINITION_STATUSES:
            hard.append(_gap("invalid_definition_evidence_status", f"{metric_id}:{status}"))
        stored_fp = str(row.get("definition_fingerprint_sha256") or "")
        if len(stored_fp) != 64 or stored_fp != definition_fingerprint(row):
            hard.append(_gap("definition_fingerprint_mismatch", metric_id))

        if row.get("semantic_type") in {"rate", "percentage"}:
            if not row.get("numerator_definition") or not row.get("denominator_definition"):
                hard.append(_gap("rate_without_explicit_fraction", metric_id))
            if row.get("missing_zero_denominator_policy") in (None, "", "NOT_APPLICABLE"):
                hard.append(_gap("rate_without_zero_denominator_policy", metric_id))

        leaked = sorted(set(row.get("produced_truths", [])) & TRACKING_ONLY_TOKENS)
        if leaked:
            hard.append(_gap("tracking_truth_leak", f"{metric_id}:{','.join(leaked)}"))

        provider_admitted = row.get("provider_binding_admitted") is True
        domain_admitted = row.get("domain_contract_admitted") is True
        if provider_admitted:
            if status != PROVIDER_ADMISSIBLE_STATUS:
                hard.append(_gap("provider_binding_admitted_without_reviewed_definition", metric_id))
            if provider_version.casefold() in UNVERIFIED_PROVIDER_VERSIONS:
                hard.append(_gap("provider_binding_admitted_without_version", metric_id))
            if provider_id == "hpfa":
                hard.append(_gap("provider_binding_admitted_for_hpfa_domain_namespace", metric_id))
            if source_role not in AUTHORITATIVE_PROVIDER_SOURCE_ROLES:
                hard.append(_gap("provider_binding_admitted_from_non_authoritative_source_role", f"{metric_id}:{source_role or 'EMPTY'}"))
        elif status == PROVIDER_ADMISSIBLE_STATUS:
            review.append(_gap("reviewed_provider_definition_not_runtime_admitted", metric_id, "REVIEW_REQUIRED"))

        if domain_admitted:
            if status != DOMAIN_ADMISSIBLE_STATUS or provider_id != "hpfa" or source_role != "HPFA_DOMAIN_CONTRACT":
                hard.append(_gap("invalid_domain_contract_admission", metric_id))
            expected_domain_fp = EXPECTED_DOMAIN_OPERATIONAL_FINGERPRINTS.get(metric_id)
            if expected_domain_fp is None:
                hard.append(_gap("domain_operational_fingerprint_not_registered", metric_id))
            elif _domain_operational_fingerprint(row) != expected_domain_fp:
                hard.append(_gap("domain_operational_fingerprint_mismatch", metric_id))
        elif status == DOMAIN_ADMISSIBLE_STATUS:
            hard.append(_gap("domain_contract_status_without_admission", metric_id))

        if status == "REFERENCE_ONLY_REVIEWED_DEFINITION":
            reference_only.append(key)
        elif not provider_admitted and not domain_admitted:
            candidate_only.append(key)

        policy_id = str(upstream.get("metric_policy_id") or "")
        aggregate_id = str(upstream.get("aggregate_definition_id") or "")
        policy_row: dict[str, Any] | None = None
        denominator_row: dict[str, Any] | None = None
        aggregate_row: dict[str, Any] | None = None

        if policy_id:
            binding_start = len(hard)
            if policy_id in duplicate_policy_ids:
                hard.append(_gap("upstream_metric_policy_identifier_ambiguous", f"{metric_id}:{policy_id}"))
            else:
                policy_row = policy_index.get(policy_id)
                if not policy_row:
                    hard.append(_gap("upstream_metric_policy_missing", f"{metric_id}:{policy_id}"))
                else:
                    for local_field, upstream_field in UPSTREAM_SHARED_SEMANTICS:
                        if row.get(local_field) != policy_row.get(upstream_field):
                            hard.append(_gap("upstream_metric_policy_semantic_mismatch", f"{metric_id}:{local_field}"))
                    expected_family = EXPECTED_DICTIONARY_METRIC_FAMILY_BY_POLICY.get(policy_id)
                    if expected_family and row.get("metric_family") != expected_family:
                        hard.append(_gap("upstream_metric_family_binding_mismatch", f"{metric_id}:{row.get('metric_family')}!={expected_family}"))
                    denominator_policy_id = str(policy_row.get("denominator_policy_id") or "")
                    if not denominator_policy_id:
                        hard.append(_gap("upstream_denominator_policy_id_missing", metric_id))
                    elif denominator_policy_id in duplicate_denominator_ids:
                        hard.append(_gap("upstream_denominator_policy_identifier_ambiguous", f"{metric_id}:{denominator_policy_id}"))
                    else:
                        denominator_row = denominator_index.get(denominator_policy_id)
                        if not denominator_row:
                            hard.append(_gap("upstream_denominator_policy_missing", f"{metric_id}:{denominator_policy_id}"))
                        else:
                            expected_denominator_fp = EXPECTED_DENOMINATOR_POLICY_FINGERPRINTS.get(denominator_policy_id)
                            if expected_denominator_fp is None or _canonical_hash(denominator_row) != expected_denominator_fp:
                                hard.append(_gap("upstream_denominator_policy_fingerprint_mismatch", f"{metric_id}:{denominator_policy_id}"))
                            if row.get("missing_zero_denominator_policy") != _denominator_behavior_contract(denominator_row):
                                hard.append(_gap("upstream_denominator_behavior_mismatch", metric_id))
            upstream_binding_results.append({
                "metric_id": metric_id,
                "binding": "metric_policy",
                "status": "BOUND" if len(hard) == binding_start else "INVALID",
            })

        if aggregate_id:
            binding_start = len(hard)
            if not policy_id:
                hard.append(_gap("upstream_aggregate_metric_policy_binding_required", metric_id))
            if aggregate_id in duplicate_aggregate_ids:
                hard.append(_gap("upstream_aggregate_definition_identifier_ambiguous", f"{metric_id}:{aggregate_id}"))
            else:
                aggregate_row = aggregate_index.get(aggregate_id)
                if not aggregate_row:
                    hard.append(_gap("upstream_aggregate_definition_missing", f"{metric_id}:{aggregate_id}"))
                else:
                    expected = str(upstream.get("aggregate_definition_fingerprint_sha256") or "")
                    actual = str(aggregate_row.get("metric_definition_fingerprint_sha256") or "")
                    if expected != actual or not expected:
                        hard.append(_gap("upstream_aggregate_fingerprint_mismatch", metric_id))
                    if row.get("numerator_definition") != aggregate_row.get("numerator_definition") or row.get("denominator_definition") != aggregate_row.get("denominator_definition"):
                        hard.append(_gap("upstream_aggregate_fraction_mismatch", metric_id))
                    if aggregate_row.get("provider_id") != provider_id:
                        hard.append(_gap("upstream_aggregate_provider_mismatch", metric_id))
                    if aggregate_row.get("provider_version") != provider_version:
                        hard.append(_gap("upstream_aggregate_provider_version_mismatch", metric_id))
                    if not policy_id or aggregate_row.get("metric_id") != policy_id:
                        hard.append(_gap("upstream_aggregate_metric_namespace_mismatch", f"{metric_id}:{aggregate_row.get('metric_id')}!={policy_id or 'MISSING'}"))
                    aggregate_roles = set(aggregate_row.get("source_roles", []))
                    allowed_roles = AGGREGATE_SOURCE_ROLE_COMPATIBILITY.get(source_role, set())
                    if not aggregate_roles or not aggregate_roles.issubset(allowed_roles):
                        hard.append(_gap("upstream_aggregate_source_role_mismatch", f"{metric_id}:{','.join(sorted(aggregate_roles)) or 'EMPTY'}"))
                    if policy_row is not None and "aggregate_candidate" not in set(policy_row.get("source_surface_roles", [])):
                        hard.append(_gap("upstream_metric_policy_aggregate_role_missing", metric_id))
            upstream_binding_results.append({
                "metric_id": metric_id,
                "binding": "aggregate_definition",
                "status": "BOUND" if len(hard) == binding_start else "INVALID",
            })

        operational_fp = operational_semantic_fingerprint(
            row,
            metric_policy_row=policy_row,
            denominator_policy_row=denominator_row,
            aggregate_definition_row=aggregate_row,
        )
        operational_fingerprints[key] = operational_fp
        stored_operational_fp = str(row.get("operational_semantic_fingerprint_sha256") or "")
        if stored_operational_fp and stored_operational_fp != operational_fp:
            hard.append(_gap("operational_semantic_fingerprint_mismatch", metric_id))
        if provider_admitted:
            if not stored_operational_fp:
                hard.append(_gap("provider_binding_missing_operational_semantic_fingerprint", metric_id))
            if len(hard) == row_hard_start:
                provider_ready_candidates.append(key)
        if domain_admitted and len(hard) == row_hard_start:
            domain_ready_candidates.append(key)

    provider_ready = sorted(key for key in provider_ready_candidates if key not in duplicate_keys)
    domain_ready = sorted(key for key in domain_ready_candidates if key not in duplicate_keys)
    provider_ready_set = set(provider_ready)
    domain_ready_set = set(domain_ready)

    alias_keys: set[tuple[str, str, str, str]] = set()
    alias_ready_count = 0
    for row in aliases.get("aliases", []):
        metric_id = str(row.get("metric_id") or "")
        if metric_id not in metric_ids:
            hard.append(_gap("alias_metric_unresolved", metric_id))
            continue
        alias_key = (
            str(row.get("provider_id") or ""), str(row.get("provider_version") or ""),
            str(row.get("surface_role") or ""), str(row.get("raw_label") or "").casefold(),
        )
        if alias_key in alias_keys:
            hard.append(_gap("duplicate_provider_version_role_alias", "|".join(alias_key)))
        alias_keys.add(alias_key)
        status = row.get("alias_status")
        provider_key = "::".join((str(row.get("provider_id") or ""), str(row.get("provider_version") or ""), metric_id))
        targets = [m for m in metrics if m.get("metric_id") == metric_id]
        if status == "ADMITTED":
            if provider_key not in provider_ready_set:
                hard.append(_gap("alias_admitted_without_provider_version_binding", metric_id))
            else:
                alias_ready_count += 1
        elif status == "CANDIDATE_ONLY":
            if any(
                "::".join((str(m.get("provider_id") or ""), str(m.get("provider_version") or ""), str(m.get("metric_id") or ""))) in domain_ready_set
                for m in targets if m.get("provider_id") == "hpfa"
            ):
                hard.append(_gap("candidate_provider_alias_targets_hpfa_domain_contract", metric_id))
        elif status != "REFERENCE_ONLY":
            hard.append(_gap("invalid_alias_status", f"{metric_id}:{status}"))

    for row in derivations.get("derivations", []):
        metric_id = str(row.get("metric_id") or "")
        components = [str(x) for x in row.get("component_metric_ids", [])]
        if metric_id not in metric_ids:
            hard.append(_gap("derivation_metric_unresolved", metric_id))
        for component in components:
            if component not in metric_ids:
                hard.append(_gap("derivation_component_unresolved", f"{metric_id}:{component}"))
        if row.get("derivation_status") != "CLEARED":
            continue

        formula = row.get("formula")
        if not isinstance(formula, str) or not formula.strip():
            hard.append(_gap("cleared_derivation_formula_missing", metric_id))
        stored_derivation_fp = str(row.get("derivation_semantic_fingerprint_sha256") or "")
        actual_derivation_fp = derivation_semantic_fingerprint(row)
        if len(stored_derivation_fp) != 64 or stored_derivation_fp != actual_derivation_fp:
            hard.append(_gap("cleared_derivation_semantic_fingerprint_mismatch", metric_id))

        namespace_provider = str(row.get("provider_id") or "").strip()
        namespace_version = str(row.get("provider_version") or "").strip()
        if not namespace_provider or not namespace_version:
            hard.append(_gap("derivation_namespace_required", metric_id))
            ready_targets = [
                key for key in provider_ready_set | domain_ready_set
                if key.endswith(f"::{metric_id}")
            ]
            if not ready_targets:
                hard.append(_gap("derivation_cleared_without_admitted_definition", metric_id))
            else:
                missing_details = []
                for target_key in ready_targets:
                    provider, version, _ = target_key.split("::", 2)
                    ready_set = provider_ready_set if target_key in provider_ready_set else domain_ready_set
                    missing = [c for c in components if f"{provider}::{version}::{c}" not in ready_set]
                    if missing:
                        missing_details.append(f"{provider}::{version}:{','.join(missing)}")
                if missing_details:
                    hard.append(_gap("derivation_components_not_admitted_same_namespace", f"{metric_id}:{'|'.join(missing_details)}"))
            continue

        target_key = f"{namespace_provider}::{namespace_version}::{metric_id}"
        if target_key in provider_ready_set:
            namespace_ready = provider_ready_set
        elif target_key in domain_ready_set:
            namespace_ready = domain_ready_set
        else:
            hard.append(_gap("derivation_cleared_without_admitted_definition", target_key))
            continue
        missing = [c for c in components if f"{namespace_provider}::{namespace_version}::{c}" not in namespace_ready]
        if missing:
            hard.append(_gap("derivation_components_not_admitted_same_namespace", f"{target_key}:{','.join(missing)}"))

    conflict_ids: set[str] = set()
    open_conflicts = 0
    for row in conflicts.get("conflicts", []):
        conflict_id = str(row.get("conflict_id") or "")
        if not conflict_id or conflict_id in conflict_ids:
            hard.append(_gap("invalid_or_duplicate_conflict_id", conflict_id or "EMPTY"))
        conflict_ids.add(conflict_id)
        for metric_id in row.get("metric_ids", []):
            if metric_id not in metric_ids:
                hard.append(_gap("conflict_metric_unresolved", f"{conflict_id}:{metric_id}"))
        if str(row.get("status") or "").startswith("OPEN_"):
            open_conflicts += 1

    if candidate_only:
        review.append(_gap("provider_definition_candidates_unresolved", str(len(candidate_only)), "REVIEW_REQUIRED"))
    if open_conflicts:
        review.append(_gap("metric_definition_conflicts_open", str(open_conflicts), "REVIEW_REQUIRED"))
    if not provider_ready:
        review.append(_gap("no_active_provider_definition_admitted", "provider definitions remain candidate/reference-only", "REVIEW_REQUIRED"))

    status = "FAIL_CLOSED" if hard else ("REVIEW_REQUIRED" if review else "SPEC_ONLY")
    status_counts = dict(Counter(str(row.get("definition_evidence_status")) for row in metrics))
    fp_errors = sum(1 for g in hard if g["gap_type"] == "definition_fingerprint_mismatch")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "spec_contract_valid": not hard,
        "dictionary_version": dictionary.get("dictionary_version"),
        "historical_donor_pr": dictionary.get("historical_donor_pr"),
        "historical_metric_record_count": dictionary.get("historical_metric_record_count"),
        "metric_record_count": len(definition_index),
        "definition_status_counts": status_counts,
        "definition_fingerprint_valid_count": len(definition_index) - fp_errors,
        "operational_semantic_fingerprints": operational_fingerprints,
        "provider_definition_ready_metric_ids": provider_ready,
        "provider_definition_ready_count": len(provider_ready),
        "hpfa_domain_contract_ready_metric_ids": domain_ready,
        "hpfa_domain_contract_ready_count": len(domain_ready),
        "reference_only_metric_ids": sorted(reference_only),
        "candidate_only_metric_ids": sorted(candidate_only),
        "provider_alias_ready_count": alias_ready_count,
        "open_conflict_count": open_conflicts,
        "upstream_binding_results": upstream_binding_results,
        "hard_block_hits": hard,
        "review_hits": review,
        "provider_candidate_is_validated_provider_identity": False,
        "same_label_is_same_definition": False,
        "arithmetic_reproduction_is_provider_definition_truth": False,
        "downstream_provider_definition_gate_open": bool(provider_ready) and not hard and not review,
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": PRODUCTION_RELEASE,
    }


def load_dictionary_pack(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    config_dir = root / "configs" / "metrics"
    aggregate_path = root / "hpfa" / "modules" / "core" / "aggregate_definition_alignment_lite" / "registry" / "sportsbase_aggregate_definition_candidates_v1.json"
    return build_dictionary_report(
        _load(config_dir / "provider_metric_dictionary_v1.json"),
        _load(config_dir / "provider_alias_registry_v1.json"),
        _load(config_dir / "metric_derivation_registry_v1.json"),
        _load(config_dir / "metric_conflict_queue_v1.json"),
        metric_policy=_load(config_dir / "metric_registry_v1.json"),
        denominator_policy=_load(config_dir / "metric_denominator_policy_v1.json"),
        aggregate_registry=_load(aggregate_path),
    )


def write_dictionary_report(repo_root: str | Path, output: str | Path) -> dict[str, Any]:
    report = load_dictionary_pack(repo_root)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
