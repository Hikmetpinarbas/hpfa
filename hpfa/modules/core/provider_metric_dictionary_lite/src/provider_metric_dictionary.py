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
OPERATIONAL_SEMANTIC_FIELDS = ("metric_family", "event_only_compatible", "upstream_bindings")

ALLOWED_DEFINITION_STATUSES = {
    "REVIEWED_PROVIDER_DEFINITION",
    "USER_DEFINED_DOMAIN_CONTRACT",
    "DATA_CONFIRMED_CANDIDATE",
    "DATA_INFERRED_CANDIDATE",
    "PROVIDER_DEFINITION_REQUIRED",
    "REFERENCE_ONLY_REVIEWED_DEFINITION",
    "DATA_CONTRADICTED",
    "INSUFFICIENT_SAMPLE",
    "NOT_APPLICABLE",
}
PROVIDER_ADMISSIBLE_STATUS = "REVIEWED_PROVIDER_DEFINITION"
DOMAIN_ADMISSIBLE_STATUS = "USER_DEFINED_DOMAIN_CONTRACT"
UNVERIFIED_PROVIDER_VERSIONS = {
    "", "UNKNOWN", "unpublished", "provider_definition_unverified",
    "reference_definition_unversioned",
}
TRACKING_ONLY_TOKENS = {
    "pressure_truth", "pitch_control_truth", "body_orientation_truth",
    "off_ball_truth", "fatigue_truth", "tracking_truth",
}
AUTHORITATIVE_PROVIDER_SOURCE_ROLES = {
    "PROVIDER_OFFICIAL_DEFINITION",
    "PROVIDER_DOCUMENTATION",
    "REVIEWED_PROVIDER_DEFINITION",
}
ALLOWED_UPSTREAM_BINDING_KEYS = {
    "metric_policy_id",
    "aggregate_definition_id",
    "aggregate_definition_fingerprint_sha256",
}
AGGREGATE_SOURCE_ROLE_COMPATIBILITY = {
    "PROVIDER_SURFACE_CANDIDATE": {
        "PLAYER_SURFACE_CANDIDATE",
        "TEAM_SURFACE_CANDIDATE",
        "GOALKEEPER_SURFACE_CANDIDATE",
    },
    "PROVIDER_OFFICIAL_DEFINITION": {
        "PLAYER_SURFACE_CANDIDATE",
        "TEAM_SURFACE_CANDIDATE",
        "GOALKEEPER_SURFACE_CANDIDATE",
    },
    "PROVIDER_DOCUMENTATION": {
        "PLAYER_SURFACE_CANDIDATE",
        "TEAM_SURFACE_CANDIDATE",
        "GOALKEEPER_SURFACE_CANDIDATE",
    },
    "REVIEWED_PROVIDER_DEFINITION": {
        "PLAYER_SURFACE_CANDIDATE",
        "TEAM_SURFACE_CANDIDATE",
        "GOALKEEPER_SURFACE_CANDIDATE",
    },
}
EXPECTED_DICTIONARY_METRIC_FAMILY_BY_POLICY = {
    "pass_completion_rate_candidate": "pass",
}
EXPECTED_DENOMINATOR_POLICY_FINGERPRINTS = {
    "provider_bound_rate_v1": "44b23a6dbf3b11e70c0f5ccf04f0e965f9ee944d07532ec19590867871bd4426",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gap(gap_type: str, detail: str, severity: str = "FAIL_CLOSED") -> dict[str, str]:
    return {"gap_type": gap_type, "detail": detail, "severity": severity}


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fingerprint_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in FINGERPRINT_FIELDS}


def definition_fingerprint(row: dict[str, Any]) -> str:
    return _canonical_hash(_fingerprint_payload(row))


def _metric_policy_index(metric_policy: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not metric_policy:
        return {}
    return {
        str(row.get("metric_id") or ""): row
        for row in metric_policy.get("metrics", [])
        if row.get("metric_id")
    }


def _denominator_policy_index(
    denominator_policy: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not denominator_policy:
        return {}
    return {
        str(row.get("denominator_policy_id") or ""): row
        for row in denominator_policy.get("policies", [])
        if row.get("denominator_policy_id")
    }


def _aggregate_index(
    aggregate_registry: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not aggregate_registry:
        return {}
    return {
        str(row.get("definition_id") or ""): row
        for row in aggregate_registry.get("definitions", [])
        if row.get("definition_id")
    }


def _denominator_behavior_contract(policy_row: dict[str, Any]) -> str:
    zero = str(policy_row.get("zero_denominator_behavior") or "").upper()
    missing = str(policy_row.get("missing_denominator_behavior") or "").upper()
    if zero == "NOT_APPLICABLE" and missing == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    return f"{zero}_IF_VALIDATED_DENOMINATOR_ZERO;{missing}_IF_DENOMINATOR_UNKNOWN"


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
            field: row.get(field) for field in OPERATIONAL_SEMANTIC_FIELDS
        },
        "resolved_metric_policy": metric_policy_row,
        "resolved_denominator_policy": denominator_policy_row,
        "resolved_aggregate_definition": aggregate_definition_row,
    }
    return _canonical_hash(payload)


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
        hard.append(_gap(
            "fingerprint_field_contract_mismatch",
            "dictionary fingerprint_fields differs from code contract",
        ))
    if not isinstance(metrics, list) or not metrics:
        hard.append(_gap("metric_registry_empty", "metrics"))
        metrics = []

    definition_index: dict[str, dict[str, Any]] = {}
    metric_ids: set[str] = set()
    provider_ready: list[str] = []
    domain_ready: list[str] = []
    reference_only: list[str] = []
    candidate_only: list[str] = []
    policy_index = _metric_policy_index(metric_policy)
    denominator_index = _denominator_policy_index(denominator_policy)
    aggregate_index = _aggregate_index(aggregate_registry)
    upstream_binding_results: list[dict[str, str]] = []
    operational_fingerprints: dict[str, str] = {}

    for row in metrics:
        row_hard_start = len(hard)
        metric_id = str(row.get("metric_id") or "").strip()
        provider_id = str(row.get("provider_id") or "").strip()
        provider_version = str(row.get("provider_version") or "").strip()
        source_role = str(row.get("source_role") or "").strip()

        missing = [
            field for field in FINGERPRINT_FIELDS
            if row.get(field) in (None, "")
        ]
        for field in sorted(missing):
            hard.append(_gap(
                "metric_fingerprint_field_missing",
                f"{metric_id or 'UNKNOWN'}:{field}",
            ))
        for field in (
            "raw_labels",
            "metric_family",
            "event_only_compatible",
            "provider_binding_admitted",
            "domain_contract_admitted",
        ):
            if field not in row:
                hard.append(_gap(
                    "metric_field_missing",
                    f"{metric_id or 'UNKNOWN'}:{field}",
                ))

        if row.get("event_only_compatible") is not True:
            hard.append(_gap("event_only_compatibility_required", metric_id or "UNKNOWN"))
        if not isinstance(row.get("metric_family"), str) or not row.get("metric_family"):
            hard.append(_gap("metric_family_missing_or_invalid", metric_id or "UNKNOWN"))

        upstream = row.get("upstream_bindings") or {}
        if not isinstance(upstream, dict):
            hard.append(_gap("upstream_bindings_invalid", metric_id or "UNKNOWN"))
            upstream = {}
        unknown_upstream_keys = sorted(set(upstream) - ALLOWED_UPSTREAM_BINDING_KEYS)
        if unknown_upstream_keys:
            hard.append(_gap(
                "upstream_binding_key_unknown",
                f"{metric_id}:{','.join(unknown_upstream_keys)}",
            ))

        if not metric_id:
            continue
        key = "::".join((provider_id, provider_version, metric_id))
        if key in definition_index:
            hard.append(_gap("duplicate_provider_definition_key", key))
            continue
        definition_index[key] = row
        metric_ids.add(metric_id)

        status = row.get("definition_evidence_status")
        if status not in ALLOWED_DEFINITION_STATUSES:
            hard.append(_gap(
                "invalid_definition_evidence_status",
                f"{metric_id}:{status}",
            ))

        stored_fp = str(row.get("definition_fingerprint_sha256") or "")
        computed_fp = definition_fingerprint(row)
        if len(stored_fp) != 64 or stored_fp != computed_fp:
            hard.append(_gap("definition_fingerprint_mismatch", metric_id))

        if row.get("semantic_type") in {"rate", "percentage"}:
            if not row.get("numerator_definition") or not row.get("denominator_definition"):
                hard.append(_gap("rate_without_explicit_fraction", metric_id))
            if row.get("missing_zero_denominator_policy") in (None, "", "NOT_APPLICABLE"):
                hard.append(_gap("rate_without_zero_denominator_policy", metric_id))

        produced = set(row.get("produced_truths", []))
        leaked = sorted(produced & TRACKING_ONLY_TOKENS)
        if leaked:
            hard.append(_gap(
                "tracking_truth_leak",
                f"{metric_id}:{','.join(leaked)}",
            ))

        provider_admitted = row.get("provider_binding_admitted") is True
        domain_admitted = row.get("domain_contract_admitted") is True

        if provider_admitted:
            if status != PROVIDER_ADMISSIBLE_STATUS:
                hard.append(_gap(
                    "provider_binding_admitted_without_reviewed_definition",
                    metric_id,
                ))
            if provider_version in UNVERIFIED_PROVIDER_VERSIONS:
                hard.append(_gap("provider_binding_admitted_without_version", metric_id))
            if provider_id == "hpfa":
                hard.append(_gap("provider_binding_admitted_for_hpfa_domain_namespace", metric_id))
            if source_role not in AUTHORITATIVE_PROVIDER_SOURCE_ROLES:
                hard.append(_gap(
                    "provider_binding_admitted_from_non_authoritative_source_role",
                    f"{metric_id}:{source_role or 'EMPTY'}",
                ))
        elif status == PROVIDER_ADMISSIBLE_STATUS:
            review.append(_gap(
                "reviewed_provider_definition_not_runtime_admitted",
                metric_id,
                "REVIEW_REQUIRED",
            ))

        if domain_admitted:
            if (
                status != DOMAIN_ADMISSIBLE_STATUS
                or provider_id != "hpfa"
                or source_role != "HPFA_DOMAIN_CONTRACT"
            ):
                hard.append(_gap("invalid_domain_contract_admission", metric_id))
            else:
                domain_ready.append(key)
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
            policy_row = policy_index.get(policy_id)
            if not policy_row:
                hard.append(_gap(
                    "upstream_metric_policy_missing",
                    f"{metric_id}:{policy_id}",
                ))
            else:
                for local_field, upstream_field in (
                    ("construct", "construct_target"),
                    ("unit", "unit"),
                    ("semantic_type", "value_type"),
                    ("numerator_definition", "numerator_definition"),
                    ("denominator_definition", "denominator_definition"),
                    ("claim_ceiling", "claim_ceiling"),
                ):
                    if row.get(local_field) != policy_row.get(upstream_field):
                        hard.append(_gap(
                            "upstream_metric_policy_semantic_mismatch",
                            f"{metric_id}:{local_field}",
                        ))

                expected_family = EXPECTED_DICTIONARY_METRIC_FAMILY_BY_POLICY.get(policy_id)
                if expected_family and row.get("metric_family") != expected_family:
                    hard.append(_gap(
                        "upstream_metric_family_binding_mismatch",
                        f"{metric_id}:{row.get('metric_family')}!={expected_family}",
                    ))
                if policy_row.get("event_only_compatible") is not True:
                    hard.append(_gap(
                        "upstream_metric_policy_not_event_only_compatible",
                        metric_id,
                    ))

                denominator_policy_id = str(policy_row.get("denominator_policy_id") or "")
                if not denominator_policy_id:
                    hard.append(_gap(
                        "upstream_denominator_policy_id_missing",
                        metric_id,
                    ))
                else:
                    denominator_row = denominator_index.get(denominator_policy_id)
                    if not denominator_row:
                        hard.append(_gap(
                            "upstream_denominator_policy_missing",
                            f"{metric_id}:{denominator_policy_id}",
                        ))
                    else:
                        expected_denominator_fp = EXPECTED_DENOMINATOR_POLICY_FINGERPRINTS.get(
                            denominator_policy_id
                        )
                        actual_denominator_fp = _canonical_hash(denominator_row)
                        if (
                            expected_denominator_fp is None
                            or actual_denominator_fp != expected_denominator_fp
                        ):
                            hard.append(_gap(
                                "upstream_denominator_policy_fingerprint_mismatch",
                                f"{metric_id}:{denominator_policy_id}",
                            ))
                        expected_behavior = _denominator_behavior_contract(denominator_row)
                        if row.get("missing_zero_denominator_policy") != expected_behavior:
                            hard.append(_gap(
                                "upstream_denominator_behavior_mismatch",
                                metric_id,
                            ))

            upstream_binding_results.append({
                "metric_id": metric_id,
                "binding": "metric_policy",
                "status": "BOUND" if len(hard) == binding_start else "INVALID",
            })

        if aggregate_id:
            binding_start = len(hard)
            aggregate_row = aggregate_index.get(aggregate_id)
            if not aggregate_row:
                hard.append(_gap(
                    "upstream_aggregate_definition_missing",
                    f"{metric_id}:{aggregate_id}",
                ))
            else:
                expected = str(
                    upstream.get("aggregate_definition_fingerprint_sha256") or ""
                )
                actual = str(
                    aggregate_row.get("metric_definition_fingerprint_sha256") or ""
                )
                if expected != actual or not expected:
                    hard.append(_gap(
                        "upstream_aggregate_fingerprint_mismatch",
                        metric_id,
                    ))
                if (
                    row.get("numerator_definition") != aggregate_row.get("numerator_definition")
                    or row.get("denominator_definition") != aggregate_row.get("denominator_definition")
                ):
                    hard.append(_gap(
                        "upstream_aggregate_fraction_mismatch",
                        metric_id,
                    ))
                if aggregate_row.get("provider_id") != provider_id:
                    hard.append(_gap(
                        "upstream_aggregate_provider_mismatch",
                        metric_id,
                    ))
                if aggregate_row.get("provider_version") != provider_version:
                    hard.append(_gap(
                        "upstream_aggregate_provider_version_mismatch",
                        metric_id,
                    ))
                if policy_id and aggregate_row.get("metric_id") != policy_id:
                    hard.append(_gap(
                        "upstream_aggregate_metric_namespace_mismatch",
                        f"{metric_id}:{aggregate_row.get('metric_id')}!={policy_id}",
                    ))

                aggregate_roles = set(aggregate_row.get("source_roles", []))
                allowed_roles = AGGREGATE_SOURCE_ROLE_COMPATIBILITY.get(source_role, set())
                if not aggregate_roles or not aggregate_roles.issubset(allowed_roles):
                    hard.append(_gap(
                        "upstream_aggregate_source_role_mismatch",
                        f"{metric_id}:{','.join(sorted(aggregate_roles)) or 'EMPTY'}",
                    ))

                if policy_row is not None:
                    policy_roles = set(policy_row.get("source_surface_roles", []))
                    if "aggregate_candidate" not in policy_roles:
                        hard.append(_gap(
                            "upstream_metric_policy_aggregate_role_missing",
                            metric_id,
                        ))

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

        stored_operational_fp = str(
            row.get("operational_semantic_fingerprint_sha256") or ""
        )
        if stored_operational_fp and stored_operational_fp != operational_fp:
            hard.append(_gap(
                "operational_semantic_fingerprint_mismatch",
                metric_id,
            ))
        if provider_admitted:
            if not stored_operational_fp:
                hard.append(_gap(
                    "provider_binding_missing_operational_semantic_fingerprint",
                    metric_id,
                ))
            if len(hard) == row_hard_start:
                provider_ready.append(key)

    provider_ready_set = set(provider_ready)
    domain_ready_set = set(domain_ready)

    alias_keys: set[tuple[str, str, str, str]] = set()
    alias_ready_count = 0
    for row in aliases.get("aliases", []):
        metric_id = str(row.get("metric_id") or "")
        if metric_id not in metric_ids:
            hard.append(_gap("alias_metric_unresolved", metric_id))
            continue
        key = (
            str(row.get("provider_id") or ""),
            str(row.get("provider_version") or ""),
            str(row.get("surface_role") or ""),
            str(row.get("raw_label") or "").casefold(),
        )
        if key in alias_keys:
            hard.append(_gap(
                "duplicate_provider_version_role_alias",
                "|".join(key),
            ))
        alias_keys.add(key)

        status = row.get("alias_status")
        provider_key = "::".join((
            str(row.get("provider_id") or ""),
            str(row.get("provider_version") or ""),
            metric_id,
        ))
        targets = [m for m in metrics if m.get("metric_id") == metric_id]

        if status == "ADMITTED":
            if provider_key not in provider_ready_set:
                hard.append(_gap(
                    "alias_admitted_without_provider_version_binding",
                    metric_id,
                ))
            else:
                alias_ready_count += 1
        elif status == "CANDIDATE_ONLY":
            if any(
                m.get("provider_id") == "hpfa"
                and "::".join((
                    str(m.get("provider_id") or ""),
                    str(m.get("provider_version") or ""),
                    str(m.get("metric_id") or ""),
                )) in domain_ready_set
                for m in targets
            ):
                hard.append(_gap(
                    "candidate_provider_alias_targets_hpfa_domain_contract",
                    metric_id,
                ))
        elif status != "REFERENCE_ONLY":
            hard.append(_gap(
                "invalid_alias_status",
                f"{metric_id}:{status}",
            ))

    for row in derivations.get("derivations", []):
        metric_id = str(row.get("metric_id") or "")
        if metric_id not in metric_ids:
            hard.append(_gap("derivation_metric_unresolved", metric_id))
        for component in row.get("component_metric_ids", []):
            if component not in metric_ids:
                hard.append(_gap(
                    "derivation_component_unresolved",
                    f"{metric_id}:{component}",
                ))
        if row.get("derivation_status") == "CLEARED":
            targets = [m for m in metrics if m.get("metric_id") == metric_id]
            admitted = False
            for target in targets:
                target_key = "::".join((
                    str(target.get("provider_id") or ""),
                    str(target.get("provider_version") or ""),
                    str(target.get("metric_id") or ""),
                ))
                if target_key in provider_ready_set or target_key in domain_ready_set:
                    admitted = True
                    break
            if not admitted:
                hard.append(_gap(
                    "derivation_cleared_without_admitted_definition",
                    metric_id,
                ))

    conflict_ids: set[str] = set()
    open_conflicts = 0
    for row in conflicts.get("conflicts", []):
        conflict_id = str(row.get("conflict_id") or "")
        if not conflict_id or conflict_id in conflict_ids:
            hard.append(_gap(
                "invalid_or_duplicate_conflict_id",
                conflict_id or "EMPTY",
            ))
        conflict_ids.add(conflict_id)
        for metric_id in row.get("metric_ids", []):
            if metric_id not in metric_ids:
                hard.append(_gap(
                    "conflict_metric_unresolved",
                    f"{conflict_id}:{metric_id}",
                ))
        if str(row.get("status") or "").startswith("OPEN_"):
            open_conflicts += 1

    if candidate_only:
        review.append(_gap(
            "provider_definition_candidates_unresolved",
            str(len(candidate_only)),
            "REVIEW_REQUIRED",
        ))
    if open_conflicts:
        review.append(_gap(
            "metric_definition_conflicts_open",
            str(open_conflicts),
            "REVIEW_REQUIRED",
        ))
    if not provider_ready:
        review.append(_gap(
            "no_active_provider_definition_admitted",
            "provider definitions remain candidate/reference-only",
            "REVIEW_REQUIRED",
        ))

    status = "FAIL_CLOSED" if hard else ("REVIEW_REQUIRED" if review else "SPEC_ONLY")
    status_counts = dict(
        Counter(str(row.get("definition_evidence_status")) for row in metrics)
    )
    definition_fp_errors = sum(
        1 for g in hard if g["gap_type"] == "definition_fingerprint_mismatch"
    )

    return {
        "module_id": MODULE_ID,
        "status": status,
        "spec_contract_valid": not hard,
        "dictionary_version": dictionary.get("dictionary_version"),
        "historical_donor_pr": dictionary.get("historical_donor_pr"),
        "historical_metric_record_count": dictionary.get("historical_metric_record_count"),
        "metric_record_count": len(definition_index),
        "definition_status_counts": status_counts,
        "definition_fingerprint_valid_count": len(definition_index) - definition_fp_errors,
        "operational_semantic_fingerprints": operational_fingerprints,
        "provider_definition_ready_metric_ids": sorted(provider_ready),
        "provider_definition_ready_count": len(provider_ready),
        "hpfa_domain_contract_ready_metric_ids": sorted(domain_ready),
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
        "downstream_provider_definition_gate_open": (
            bool(provider_ready) and not hard and not review
        ),
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": PRODUCTION_RELEASE,
    }


def load_dictionary_pack(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    config_dir = root / "configs" / "metrics"
    aggregate_path = (
        root
        / "hpfa"
        / "modules"
        / "core"
        / "aggregate_definition_alignment_lite"
        / "registry"
        / "sportsbase_aggregate_definition_candidates_v1.json"
    )
    return build_dictionary_report(
        _load(config_dir / "provider_metric_dictionary_v1.json"),
        _load(config_dir / "provider_alias_registry_v1.json"),
        _load(config_dir / "metric_derivation_registry_v1.json"),
        _load(config_dir / "metric_conflict_queue_v1.json"),
        metric_policy=_load(config_dir / "metric_registry_v1.json"),
        denominator_policy=_load(config_dir / "metric_denominator_policy_v1.json"),
        aggregate_registry=_load(aggregate_path),
    )


def write_dictionary_report(
    repo_root: str | Path,
    output: str | Path,
) -> dict[str, Any]:
    report = load_dictionary_pack(repo_root)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
