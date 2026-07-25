from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "provider_metric_dictionary_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
PRODUCTION_RELEASE = False

ALLOWED_STATUSES = {
    "REVIEWED_PROVIDER_DEFINITION",
    "USER_DEFINED_DOMAIN_CONTRACT",
    "DATA_CONFIRMED_CANDIDATE",
    "DATA_INFERRED_CANDIDATE",
    "DATA_CONTRADICTED",
    "PROVIDER_DEFINITION_REQUIRED",
    "INSUFFICIENT_SAMPLE",
    "NOT_APPLICABLE",
}
PROMOTABLE_STATUSES = {
    "REVIEWED_PROVIDER_DEFINITION",
    "USER_DEFINED_DOMAIN_CONTRACT",
}
REQUIRED_METRIC_FIELDS = {
    "metric_id",
    "provider_id",
    "provider_version",
    "raw_labels",
    "metric_family",
    "semantic_type",
    "definition_evidence_status",
    "event_only_compatible",
    "claim_ceiling",
}
TRACKING_ONLY_TOKENS = {
    "pressure_truth",
    "pitch_control_truth",
    "body_orientation_truth",
    "off_ball_truth",
    "fatigue_truth",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_dictionary_pack(config_dir: str | Path) -> dict[str, Any]:
    root = Path(config_dir)
    return build_dictionary_report(
        _load(root / "provider_metric_dictionary_v1.json"),
        _load(root / "provider_alias_registry_v1.json"),
        _load(root / "metric_derivation_registry_v1.json"),
        _load(root / "metric_conflict_queue_v1.json"),
    )


def _gap(gap_type: str, detail: str, severity: str = "FAIL_CLOSED") -> dict[str, str]:
    return {"gap_type": gap_type, "detail": detail, "severity": severity}


def build_dictionary_report(
    dictionary: dict[str, Any],
    aliases: dict[str, Any],
    derivations: dict[str, Any],
    conflicts: dict[str, Any],
) -> dict[str, Any]:
    gaps: list[dict[str, str]] = []
    metrics = dictionary.get("metrics", [])
    definition_index: dict[str, dict[str, Any]] = {}
    semantic_metric_ids: set[str] = set()

    if dictionary.get("dictionary_version") != "1.0.0":
        gaps.append(_gap("dictionary_version_mismatch", str(dictionary.get("dictionary_version"))))
    if not isinstance(metrics, list) or not metrics:
        gaps.append(_gap("metric_registry_empty", "metrics"))
        metrics = []

    for row in metrics:
        metric_id = str(row.get("metric_id") or "").strip()
        missing = sorted(field for field in REQUIRED_METRIC_FIELDS if row.get(field) in (None, "", []))
        for field in missing:
            gaps.append(_gap("metric_field_missing", f"{metric_id or 'UNKNOWN'}:{field}"))
        if not metric_id:
            continue
        definition_key = "::".join(
            [
                str(row.get("provider_id") or "").strip(),
                str(row.get("provider_version") or "").strip(),
                metric_id,
            ]
        )
        if definition_key in definition_index:
            gaps.append(_gap("duplicate_provider_definition_key", definition_key))
            continue
        definition_index[definition_key] = row
        semantic_metric_ids.add(metric_id)

        status = row.get("definition_evidence_status")
        if status not in ALLOWED_STATUSES:
            gaps.append(_gap("invalid_definition_evidence_status", f"{metric_id}:{status}"))
        if status in PROMOTABLE_STATUSES and not row.get("source_reference"):
            gaps.append(_gap("promoted_definition_without_source", metric_id))
        if row.get("semantic_type") in {"rate", "percentage"}:
            if not row.get("numerator_definition") or not row.get("denominator_definition"):
                gaps.append(_gap("rate_without_explicit_fraction", metric_id))
            if not row.get("zero_denominator_rule"):
                gaps.append(_gap("zero_denominator_unhandled", metric_id))
        produced = set(row.get("produced_truths", []))
        leaked = sorted(produced & TRACKING_ONLY_TOKENS)
        if leaked and row.get("event_only_compatible") is True:
            gaps.append(_gap("tracking_truth_leak", f"{metric_id}:{','.join(leaked)}"))

    alias_keys: set[tuple[str, str, str]] = set()
    for row in aliases.get("aliases", []):
        metric_id = str(row.get("metric_id") or "")
        if metric_id not in semantic_metric_ids:
            gaps.append(_gap("alias_metric_unresolved", metric_id))
        key = (
            str(row.get("provider_id") or ""),
            str(row.get("surface_role") or ""),
            str(row.get("raw_label") or "").casefold(),
        )
        if key in alias_keys:
            gaps.append(_gap("duplicate_provider_role_alias", "|".join(key)))
        alias_keys.add(key)

    for row in derivations.get("derivations", []):
        metric_id = str(row.get("metric_id") or "")
        if metric_id not in semantic_metric_ids:
            gaps.append(_gap("derivation_metric_unresolved", metric_id))
        for component in row.get("component_metric_ids", []):
            if component not in semantic_metric_ids:
                gaps.append(_gap("derivation_component_unresolved", f"{metric_id}:{component}"))
        matching_statuses = {
            item.get("definition_evidence_status")
            for item in metrics
            if item.get("metric_id") == metric_id
        }
        if row.get("derivation_status") == "CLEARED" and not (
            matching_statuses & PROMOTABLE_STATUSES
        ):
            gaps.append(_gap("derivation_cleared_without_definition", metric_id))

    conflict_ids: set[str] = set()
    for row in conflicts.get("conflicts", []):
        conflict_id = str(row.get("conflict_id") or "")
        if not conflict_id or conflict_id in conflict_ids:
            gaps.append(_gap("invalid_or_duplicate_conflict_id", conflict_id or "EMPTY"))
        conflict_ids.add(conflict_id)
        for metric_id in row.get("metric_ids", []):
            if metric_id not in semantic_metric_ids:
                gaps.append(_gap("conflict_metric_unresolved", f"{conflict_id}:{metric_id}"))

    hard = [gap for gap in gaps if gap["severity"] == "FAIL_CLOSED"]
    review = [gap for gap in gaps if gap["severity"] == "REVIEW_REQUIRED"]
    status = "FAIL_CLOSED" if hard else ("REVIEW_REQUIRED" if review else "SPEC_ONLY")
    status_counts = dict(Counter(row.get("definition_evidence_status") for row in metrics))
    ready_ids = sorted(
        definition_key
        for definition_key, row in definition_index.items()
        if row.get("definition_evidence_status") in PROMOTABLE_STATUSES
    )

    return {
        "module_id": MODULE_ID,
        "status": status,
        "dictionary_version": dictionary.get("dictionary_version"),
        "metric_record_count": len(definition_index),
        "definition_status_counts": status_counts,
        "runtime_contract_ready_metric_ids": ready_ids,
        "runtime_contract_ready_count": len(ready_ids),
        "unresolved_conflict_count": len(conflict_ids),
        "policy_gaps": gaps,
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": PRODUCTION_RELEASE,
    }


def write_dictionary_report(config_dir: str | Path, output: str | Path) -> dict[str, Any]:
    report = load_dictionary_pack(config_dir)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report
