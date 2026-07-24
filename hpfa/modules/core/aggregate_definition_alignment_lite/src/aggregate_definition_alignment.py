from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "aggregate_definition_alignment_lite_v1"
REGISTRY_VERSION = "1.0.0"
CANONICAL_EVENT_COUNT = "UNKNOWN"

REQUIRED_DEFINITION_FIELDS = {
    "definition_id",
    "provider_id",
    "provider_version",
    "source_roles",
    "aggregate_label",
    "metric_id",
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


def normalize_label(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("%", " percent ")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


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


def _upstream_guard(payload: dict[str, Any], expected_module_id: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if payload.get("module_id") != expected_module_id:
        hits.append(_fail("upstream_module_id_mismatch", expected_module_id))
    if payload.get("status") == "FAIL_CLOSED":
        hits.append(_fail("upstream_fail_closed", expected_module_id))
    if payload.get("canonical_event_count") not in (None, CANONICAL_EVENT_COUNT):
        hits.append(_fail("upstream_canonical_event_count_claimed", expected_module_id))
    if payload.get("production_release") is True:
        hits.append(_fail("upstream_production_release_claimed", expected_module_id))
    return hits


def _aggregate_labels(xlsx_payload: dict[str, Any]) -> set[tuple[str, str]]:
    labels: set[tuple[str, str]] = set()
    for file_row in xlsx_payload.get("files", []) or []:
        file_role = str(file_row.get("source_role") or "UNKNOWN")
        for sheet in file_row.get("sheets", []) or []:
            role = str(sheet.get("source_role") or file_role)
            for metric in sheet.get("metric_inventory", []) or []:
                label = normalize_label(
                    metric.get("normalized_metric_label")
                    or metric.get("raw_metric_label")
                )
                if label:
                    labels.add((role, label))
    return labels


def _semantic_records(label_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in label_payload.get("provider_label_records", []) or []
        if row.get("source_format") != "xlsx"
        and row.get("mapping_status") in ACCEPTED_SEMANTIC_STATUSES
    ]


def _semantic_match(row: dict[str, Any], required: dict[str, Any]) -> bool:
    for key, expected in required.items():
        if key == "source_formats":
            if row.get("source_format") not in {str(item) for item in _list(expected)}:
                return False
            continue
        if key == "source_roles":
            if row.get("source_role") not in {str(item) for item in _list(expected)}:
                return False
            continue
        if row.get(key) not in _list(expected):
            return False
    return True


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


def _validate_definition(
    row: dict[str, Any], seen: set[str]
) -> tuple[str | None, list[dict[str, Any]]]:
    definition_id = str(row.get("definition_id") or "").strip()
    hits: list[dict[str, Any]] = []
    if not definition_id:
        return None, [_fail("definition_id_missing")]
    if definition_id in seen:
        return None, [_fail("duplicate_definition_id", definition_id)]
    seen.add(definition_id)
    missing = sorted(
        field
        for field in REQUIRED_DEFINITION_FIELDS
        if row.get(field) in (None, "", [])
    )
    for field in missing:
        hits.append(_fail("definition_field_missing", f"{definition_id}:{field}"))
    if not isinstance(row.get("required_occurrence_semantics"), list):
        hits.append(_fail("required_occurrence_semantics_must_be_array", definition_id))
    return definition_id, hits


def build_alignment(
    xlsx_payload: dict[str, Any],
    label_semantics_payload: dict[str, Any],
    metric_policy_payload: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    hits = (
        _upstream_guard(xlsx_payload, "xlsx_surface_reader_lite_v1")
        + _upstream_guard(
            label_semantics_payload, "provider_label_value_semantics_lite_v1"
        )
        + _upstream_guard(
            metric_policy_payload, "metric_definition_policy_lite_v1"
        )
    )
    if registry.get("registry_version") != REGISTRY_VERSION:
        hits.append(_fail("registry_version_mismatch", registry.get("registry_version")))

    metric_index, metric_hits = _metric_index(metric_policy_payload)
    hits.extend(metric_hits)
    aggregate_labels = _aggregate_labels(xlsx_payload)
    semantic_records = _semantic_records(label_semantics_payload)
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
        aggregate_present = any((role, label) in aggregate_labels for role in roles)
        if not aggregate_present:
            row_hits.append(_review("aggregate_label_not_observed", label))

        metric = metric_index.get(str(raw.get("metric_id") or ""))
        if metric is None:
            row_hits.append(_fail("metric_definition_unresolved", raw.get("metric_id")))
        elif metric.get("definition_status") != "DEFINITION_CANDIDATE_READY":
            row_hits.append(_fail("metric_policy_not_ready", raw.get("metric_id")))

        semantic_support: list[dict[str, Any]] = []
        for requirement in raw.get("required_occurrence_semantics", []) or []:
            matches = [
                record
                for record in semantic_records
                if isinstance(requirement, dict)
                and _semantic_match(record, requirement)
            ]
            semantic_support.append(
                {
                    "requirement": requirement,
                    "match_count": len(matches),
                    "record_ids": [
                        str(record.get("record_id"))
                        for record in matches[:20]
                    ],
                }
            )
            if not matches:
                row_hits.append(
                    _review("required_occurrence_semantics_not_observed", requirement)
                )

        if raw.get("definition_evidence_status") != REVIEWED_DEFINITION_STATUS:
            row_hits.append(
                _review(
                    "provider_definition_evidence_unresolved",
                    raw.get("definition_evidence_status"),
                )
            )
        unresolved_dependencies = [
            item
            for item in _list(raw.get("derivation_dependency"))
            if str(item).upper().endswith(("UNRESOLVED", "UNKNOWN"))
        ]
        if unresolved_dependencies:
            row_hits.append(
                _review("derivation_dependency_unresolved", unresolved_dependencies)
            )

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
                "metric_id": raw.get("metric_id"),
                "provider_id": raw.get("provider_id"),
                "provider_version": raw.get("provider_version"),
                "source_roles": sorted(roles),
                "aggregate_label": raw.get("aggregate_label"),
                "normalized_aggregate_label": label,
                "aggregate_label_observed": aggregate_present,
                "semantic_support": semantic_support,
                "definition_evidence_status": raw.get("definition_evidence_status"),
                "derivation_dependency": raw.get("derivation_dependency"),
                "independence_status": raw.get("independence_status"),
                "alignment_decision": decision,
                "alignment_hits": row_hits,
                "comparison_allowed": False,
                "aggregate_equivalence_truth": False,
                "independent_confirmation_allowed": False,
                "metric_value_output_allowed": False,
                "claim_allowed": False,
                "claim_ceiling": raw.get("claim_ceiling"),
            }
        )

    if not registry.get("definitions"):
        hits.append(_fail("definition_registry_empty"))
    hits.extend(
        hit
        for row in rows
        for hit in row["alignment_hits"]
        if hit["severity"] == "FAIL_CLOSED"
    )
    hits = list(
        {
            json.dumps(hit, sort_keys=True, ensure_ascii=False): hit
            for hit in hits
        }.values()
    )
    status = (
        "FAIL_CLOSED"
        if any(hit["severity"] == "FAIL_CLOSED" for hit in hits)
        else (
            "REVIEW_REQUIRED"
            if any(
                row["alignment_decision"] == "REVIEW_REQUIRED_DEFINITION_ALIGNMENT"
                for row in rows
            )
            else "SMOKE_PASS"
        )
    )
    return {
        "module_id": MODULE_ID,
        "status": status,
        "registry_version": REGISTRY_VERSION,
        "definition_candidate_count": len(rows),
        "alignment_decision_counts": dict(
            sorted(Counter(row["alignment_decision"] for row in rows).items())
        ),
        "alignment_rows": rows,
        "hard_block_hits": [
            hit for hit in hits if hit["severity"] == "FAIL_CLOSED"
        ],
        "review_hits": [
            hit
            for row in rows
            for hit in row["alignment_hits"]
            if hit["severity"] == "REVIEW_REQUIRED"
        ],
        "definition_alignment_candidate_only": True,
        "aggregate_equivalence_truth": False,
        "independent_confirmation_allowed": False,
        "comparison_allowed": False,
        "metric_value_output_allowed": False,
        "quality_truth_output_allowed": False,
        "claim_allowed": False,
        "active_match_evidence_pass": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "claim_boundary": (
            "aggregate_definition_candidate_only_no_value_no_equivalence_"
            "no_independent_confirmation_no_claim"
        ),
    }


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_report(
    xlsx_path: str | Path,
    label_semantics_path: str | Path,
    metric_policy_path: str | Path,
    registry_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    report = build_alignment(
        load_json(xlsx_path),
        load_json(label_semantics_path),
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
