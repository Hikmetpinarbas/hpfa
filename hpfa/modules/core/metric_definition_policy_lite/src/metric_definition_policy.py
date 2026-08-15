from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "metric_definition_policy_lite_v1"
OUTPUT_JSON = "metric_definition_policy_lite_v1.json"
POLICY_VERSION = "1.0.0"

REQUIRED_METRIC_FIELDS = {
    "metric_id",
    "metric_name",
    "metric_family",
    "value_type",
    "unit",
    "numerator_definition",
    "observation_window",
    "entity_scope",
    "required_event_families",
    "required_context_fields",
    "event_only_compatible",
    "source_surface_roles",
    "derivation_dependency",
    "does_not_measure",
    "forbidden_claims",
    "claim_ceiling",
    "denominator_policy_id",
    "context_policy_id",
    "confidence_policy_id",
    "misuse_policy_ids",
}

RATE_TYPES = {"rate", "percentage", "ratio", "per_90"}
FAIL_CLOSED = "FAIL_CLOSED"
BLOCKED = "BLOCKED"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _non_empty(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return value is not None


def _gap(
    metric_id: str | None,
    code: str,
    *,
    severity: str = FAIL_CLOSED,
    detail: Any = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "metric_id": metric_id,
        "gap_type": code,
        "severity": severity,
    }
    if detail is not None:
        item["detail"] = detail
    return item


def _index_policy(
    records: Iterable[dict[str, Any]],
    id_field: str,
    family: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    index: dict[str, dict[str, Any]] = {}
    gaps: list[dict[str, Any]] = []
    for record in records:
        policy_id = str(record.get(id_field, "")).strip()
        if not policy_id:
            gaps.append(_gap(None, f"{family}_id_missing"))
            continue
        if policy_id in index:
            gaps.append(_gap(None, f"duplicate_{family}_id", detail=policy_id))
            continue
        index[policy_id] = dict(record)
    return index, gaps


def _validate_metric(
    record: dict[str, Any],
    seen: set[str],
    denominator_policies: dict[str, dict[str, Any]],
    context_policies: dict[str, dict[str, Any]],
    confidence_policies: dict[str, dict[str, Any]],
    misuse_policies: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    gaps: list[dict[str, Any]] = []
    metric_id = str(record.get("metric_id", "")).strip()
    if not metric_id:
        return None, [_gap(None, "metric_id_missing")]
    if metric_id in seen:
        return None, [_gap(metric_id, "duplicate_metric_id")]
    seen.add(metric_id)

    missing = sorted(field for field in REQUIRED_METRIC_FIELDS if not _non_empty(record.get(field)))
    for field in missing:
        gaps.append(_gap(metric_id, f"{field}_missing"))

    value_type = str(record.get("value_type", "")).strip().lower()
    denominator_definition = str(record.get("denominator_definition", "")).strip()
    denominator_policy_id = str(record.get("denominator_policy_id", "")).strip()
    context_policy_id = str(record.get("context_policy_id", "")).strip()
    confidence_policy_id = str(record.get("confidence_policy_id", "")).strip()
    misuse_policy_ids = [
        str(item).strip()
        for item in _as_list(record.get("misuse_policy_ids"))
        if str(item).strip()
    ]

    if value_type in RATE_TYPES and not denominator_definition:
        gaps.append(_gap(metric_id, "rate_without_denominator"))
    if denominator_policy_id not in denominator_policies:
        gaps.append(_gap(metric_id, "denominator_policy_unresolved", detail=denominator_policy_id))
    if context_policy_id not in context_policies:
        gaps.append(_gap(metric_id, "context_policy_unresolved", detail=context_policy_id))
    if confidence_policy_id not in confidence_policies:
        gaps.append(_gap(metric_id, "confidence_policy_unresolved", detail=confidence_policy_id))
    for policy_id in misuse_policy_ids:
        if policy_id not in misuse_policies:
            gaps.append(_gap(metric_id, "misuse_policy_unresolved", detail=policy_id))

    denominator_policy = denominator_policies.get(denominator_policy_id, {})
    if value_type in RATE_TYPES:
        if not _non_empty(denominator_policy.get("zero_denominator_behavior")):
            gaps.append(_gap(metric_id, "zero_denominator_unhandled"))
        if not _non_empty(denominator_policy.get("missing_denominator_behavior")):
            gaps.append(_gap(metric_id, "missing_denominator_unhandled"))

    normalized = dict(record)
    normalized.update(
        {
            "metric_id": metric_id,
            "definition_status": "BLOCKED" if gaps else "DEFINITION_CANDIDATE_READY",
            "comparison_allowed": bool(record.get("comparison_allowed", False))
            and str(record.get("aggregate_definition_status", "")).upper() == "ALIGNED",
            "validated_metric_truth": False,
            "aggregate_equivalence_truth": False,
            "metric_value_output_allowed": False,
            "claim_output_allowed": False,
            "canonical_event_count": "UNKNOWN",
        }
    )
    if record.get("comparison_allowed") and not normalized["comparison_allowed"]:
        gaps.append(
            _gap(
                metric_id,
                "comparison_allowed_without_definition_alignment",
                severity=BLOCKED,
            )
        )
        normalized["definition_status"] = "BLOCKED"
    return normalized, gaps


def build_metric_definition_policy(
    metric_registry: dict[str, Any],
    denominator_policy: dict[str, Any],
    context_schema: dict[str, Any],
    confidence_rules: dict[str, Any],
    misuse_warnings: dict[str, Any],
) -> dict[str, Any]:
    denominator_index, denominator_gaps = _index_policy(
        denominator_policy.get("policies", []),
        "denominator_policy_id",
        "denominator_policy",
    )
    context_index, context_gaps = _index_policy(
        context_schema.get("policies", []),
        "context_policy_id",
        "context_policy",
    )
    confidence_index, confidence_gaps = _index_policy(
        confidence_rules.get("policies", []),
        "confidence_policy_id",
        "confidence_policy",
    )
    misuse_index, misuse_gaps = _index_policy(
        misuse_warnings.get("policies", []),
        "misuse_policy_id",
        "misuse_policy",
    )

    gaps = denominator_gaps + context_gaps + confidence_gaps + misuse_gaps
    seen: set[str] = set()
    metrics: list[dict[str, Any]] = []
    for raw in metric_registry.get("metrics", []):
        if not isinstance(raw, dict):
            gaps.append(_gap(None, "metric_record_not_object"))
            continue
        normalized, metric_gaps = _validate_metric(
            raw,
            seen,
            denominator_index,
            context_index,
            confidence_index,
            misuse_index,
        )
        gaps.extend(metric_gaps)
        if normalized is not None:
            metrics.append(normalized)

    versions = {
        str(doc.get("policy_version", "")).strip()
        for doc in (
            metric_registry,
            denominator_policy,
            context_schema,
            confidence_rules,
            misuse_warnings,
        )
    }
    if versions != {POLICY_VERSION}:
        gaps.append(_gap(None, "policy_version_mismatch", detail=sorted(versions)))

    status = FAIL_CLOSED if any(gap["severity"] == FAIL_CLOSED for gap in gaps) else (
        "REVIEW_REQUIRED" if gaps else "SMOKE_PASS"
    )
    return {
        "module_id": MODULE_ID,
        "status": status,
        "policy_version": POLICY_VERSION,
        "metric_definition_candidate_count": len(metrics),
        "definition_status_counts": dict(
            sorted(Counter(metric["definition_status"] for metric in metrics).items())
        ),
        "policy_counts": {
            "denominator": len(denominator_index),
            "context": len(context_index),
            "confidence": len(confidence_index),
            "misuse": len(misuse_index),
        },
        "policy_gaps": gaps,
        "metrics": metrics,
        "metric_definition_candidate_only": True,
        "validated_metric_truth": False,
        "aggregate_equivalence_truth": False,
        "metric_value_output_allowed": False,
        "quality_truth_output_allowed": False,
        "tactical_truth_output_allowed": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "claim_boundary": (
            "definition_candidate_and_eligibility_only_no_metric_value_no_quality_"
            "no_tactical_truth_no_canonical_event_claim"
        ),
    }


def load_policy_pack(config_dir: str | Path) -> dict[str, Any]:
    root = Path(config_dir)

    def read(name: str) -> dict[str, Any]:
        return json.loads((root / name).read_text(encoding="utf-8"))

    return build_metric_definition_policy(
        read("metric_registry_v1.json"),
        read("metric_denominator_policy_v1.json"),
        read("metric_context_schema_v1.json"),
        read("metric_confidence_rules_v1.json"),
        read("metric_misuse_warnings_v1.json"),
    )


def write_policy_report(config_dir: str | Path, out_dir: str | Path) -> dict[str, Any]:
    report = load_policy_pack(config_dir)
    root = Path(out_dir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    output = root / OUTPUT_JSON
    report["outputs"] = {"json": str(output)}
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report
