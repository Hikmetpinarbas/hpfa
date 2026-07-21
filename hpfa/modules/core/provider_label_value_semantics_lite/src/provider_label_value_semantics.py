from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "provider_label_value_semantics_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "PROVIDER_LABEL_VALUE_SEMANTICS_CANDIDATE_ONLY"
REGISTRY_VERSION = "sportsbase_label_semantics_reviewed_v2"
OUT = {
    "inventory": "provider_label_value_inventory_v1.json",
    "main": "provider_label_value_semantics_lite_v1.json",
    "unknown": "provider_label_unknown_report_v1.json",
    "conflict": "provider_label_conflict_report_v1.json",
    "analyst": "provider_label_value_semantics_analyst_audit_v1.txt",
}

SEMANTIC_FIELDS = (
    "semantic_role_candidate",
    "action_family_candidate",
    "outcome_candidate",
    "direction_candidate",
    "distance_candidate",
    "zone_candidate",
    "context_candidate",
    "relation_candidate",
    "restart_type_candidate",
    "shot_result_candidate",
    "action_subtype_candidate",
    "object_action_family_candidate",
    "progression_candidate",
    "key_action_candidate",
    "terminal_outcome_candidate",
    "card_type_candidate",
    "downstream_eligibility",
    "semantics_decision",
    "review_status",
)

REVIEW_MAPPING_STATUSES = {
    "TOKEN_FALLBACK_REVIEW_REQUIRED",
    "CONFLICT_REVIEW_REQUIRED",
    "UNKNOWN_UNREVIEWED",
}


def normalize_label(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = text.replace("%", " percent ")
    text = re.sub(r"\[\s*([^\]]+)\s*\]", r" \1 ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def validate_out(path: str | Path) -> Path:
    out = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in out.parts and out.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return out


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError("upstream_output_unreadable") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("upstream_output_malformed") from exc
    if not isinstance(payload, dict):
        raise ValueError("upstream_output_not_object")
    return payload


def _role_set(row: dict[str, Any]) -> set[str] | None:
    roles = row.get("source_roles")
    if roles is None:
        return None
    if not isinstance(roles, list) or not roles or not all(isinstance(value, str) and value for value in roles):
        raise ValueError("registry_invalid_source_roles")
    return set(roles)


def _roles_overlap(left: set[str] | None, right: set[str] | None) -> bool:
    return left is None or right is None or bool(left & right)


def load_registry(path: str | Path) -> dict[str, Any]:
    registry_path = Path(path)
    registry = load_json(registry_path)
    if registry.get("registry_id") != REGISTRY_VERSION:
        raise ValueError("registry_version_mismatch")

    exact_rules = registry.get("exact_rules")
    if exact_rules is None:
        exact_file = registry.get("exact_rules_file")
        if not isinstance(exact_file, str) or not exact_file:
            raise ValueError("registry_exact_rules_missing")
        exact_path = registry_path.parent / exact_file
        try:
            with exact_path.open(encoding="utf-8", newline="") as handle:
                exact_rules = []
                for raw in csv.DictReader(handle):
                    row = {key: value for key, value in raw.items() if value not in {None, ""}}
                    if "source_roles" in row:
                        row["source_roles"] = [value for value in row["source_roles"].split("|") if value]
                    exact_rules.append(row)
        except OSError as exc:
            raise ValueError("registry_exact_rules_unreadable") from exc
        registry["exact_rules"] = exact_rules

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in registry.get("exact_rules", []) or []:
        if not isinstance(row, dict):
            raise ValueError("registry_rule_not_object")
        normalized = normalize_label(row.get("label"))
        if not normalized:
            raise ValueError("registry_empty_label")
        if not row.get("semantic_role") or not row.get("rule_id"):
            raise ValueError("registry_rule_incomplete")
        _role_set(row)
        for prior in grouped[normalized]:
            if _roles_overlap(_role_set(prior), _role_set(row)):
                raise ValueError("registry_duplicate_conflict")
        grouped[normalized].append(row)
    return registry


def _upstream_guard(payloads: Iterable[dict[str, Any]]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    warnings: list[str] = []
    for payload in payloads:
        module = str(payload.get("module_id") or "UNKNOWN")
        status = str(payload.get("status") or "UNKNOWN")
        if payload.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
            blocks.append(f"canonical_event_count_claimed:{module}")
        if payload.get("production_release") is True:
            blocks.append(f"unexpected_production_claim:{module}")
        if status == "FAIL_CLOSED":
            blocks.append(f"upstream_fail_closed:{module}")
        elif status != "PASS":
            warnings.append(f"upstream_not_pass:{module}:{status}")
        for block in payload.get("hard_block_hits", []) or []:
            blocks.append(f"upstream_hard_block:{module}:{block}")
    return sorted(set(blocks)), sorted(set(warnings))


def _field_semantics_guard(payload: dict[str, Any]) -> list[str]:
    blocks: list[str] = []
    anchors = payload.get("required_anchor_audit") or {}
    for fmt in ("csv", "xml"):
        row = anchors.get(fmt) or {}
        if row.get("ready_for_candidate_reconciliation") is not True:
            blocks.append(f"required_field_path_semantics_missing:{fmt}")
    return blocks


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def _source_hash_guard(payloads: Iterable[dict[str, Any]]) -> list[str]:
    blocks: list[str] = []
    for payload in payloads:
        module = str(payload.get("module_id") or "UNKNOWN")
        for row in payload.get("files", []) or []:
            relative_path = str(row.get("relative_path") or row.get("file_name") or "UNKNOWN")
            if not _valid_sha256(row.get("sha256")):
                blocks.append(f"source_hash_missing_or_invalid:{module}:{relative_path}")
    return sorted(set(blocks))


def _token_present(label: str, token: str) -> bool:
    return re.search(rf"(^| ){re.escape(token)}( |$)", label) is not None


def _blank_classification() -> dict[str, Any]:
    return {
        "semantic_role_candidate": None,
        "action_family_candidate": None,
        "outcome_candidate": None,
        "direction_candidate": None,
        "distance_candidate": None,
        "zone_candidate": None,
        "context_candidate": None,
        "relation_candidate": None,
        "restart_type_candidate": None,
        "shot_result_candidate": None,
        "action_subtype_candidate": None,
        "object_action_family_candidate": None,
        "progression_candidate": None,
        "key_action_candidate": None,
        "terminal_outcome_candidate": None,
        "card_type_candidate": None,
        "downstream_eligibility": "BLOCKED_UNKNOWN",
        "semantics_decision": "UNRESOLVED",
        "review_status": "REVIEW_REQUIRED",
    }


def _row_to_classification(row: dict[str, Any], *, mapping_status: str, confidence: str) -> dict[str, Any]:
    result = _blank_classification()
    mapping = {
        "semantic_role_candidate": "semantic_role",
        "action_family_candidate": "action_family",
        "outcome_candidate": "outcome",
        "direction_candidate": "direction",
        "distance_candidate": "distance",
        "zone_candidate": "zone",
        "context_candidate": "context",
        "relation_candidate": "relation",
        "restart_type_candidate": "restart_type",
        "shot_result_candidate": "shot_result",
        "action_subtype_candidate": "action_subtype",
        "object_action_family_candidate": "object_action_family",
        "progression_candidate": "progression",
        "key_action_candidate": "key_action",
        "terminal_outcome_candidate": "terminal_outcome",
        "card_type_candidate": "card_type",
        "downstream_eligibility": "downstream_eligibility",
        "semantics_decision": "semantics_decision",
        "review_status": "review_status",
    }
    for output_key, input_key in mapping.items():
        if input_key in row:
            result[output_key] = row.get(input_key)
    result.update(
        {
            "mapping_status": mapping_status,
            "rule_id": row.get("rule_id"),
            "confidence_tier": confidence,
        }
    )
    return result


def _exact_matches(registry: dict[str, Any], normalized: str, source_role: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for row in registry.get("exact_rules", []) or []:
        if normalize_label(row.get("label")) != normalized:
            continue
        roles = _role_set(row)
        if roles is None or source_role in roles:
            matches.append(row)
    return matches


def _first_qualifier(normalized: str, registry: dict[str, Any], section: str) -> tuple[str | None, str | None]:
    for row in registry.get(section, []) or []:
        if any(_token_present(normalized, normalize_label(token)) for token in row.get("tokens", [])):
            return row["value"], row["rule_id"]
    return None, None


def classify_label(
    raw_label: str,
    *,
    source_format: str,
    registry: dict[str, Any],
    source_role: str = "UNKNOWN",
) -> dict[str, Any]:
    normalized = normalize_label(raw_label)
    if source_format == "xlsx":
        result = _blank_classification()
        result.update(
            {
                "semantic_role_candidate": "AGGREGATE_METRIC_LABEL",
                "downstream_eligibility": "AGGREGATE_ONLY",
                "semantics_decision": "XLSX_LABEL_PRESERVED_NO_EVENT_SEMANTICS",
                "review_status": "REVIEWED_CANDIDATE",
                "mapping_status": "XLSX_AGGREGATE_LABEL_CANDIDATE",
                "rule_id": "xlsx_metric_label_surface",
                "confidence_tier": "CANDIDATE_HIGH",
            }
        )
        return result

    exact = _exact_matches(registry, normalized, source_role)
    if len(exact) == 1:
        return _row_to_classification(exact[0], mapping_status="EXACT_REVIEWED_CANDIDATE", confidence="CANDIDATE_HIGH")
    if len(exact) > 1:
        result = _blank_classification()
        result.update(
            {
                "semantic_role_candidate": "UNKNOWN_UNREVIEWED",
                "action_family_candidate": "UNKNOWN",
                "mapping_status": "CONFLICT_REVIEW_REQUIRED",
                "rule_id": "+".join(sorted(str(row.get("rule_id")) for row in exact)),
                "confidence_tier": "CONFLICT",
                "semantics_decision": "EXACT_RULE_CONFLICT",
            }
        )
        return result

    for row in registry.get("prefix_rules", []) or []:
        prefix = normalize_label(row.get("prefix"))
        if prefix and normalized.startswith(prefix):
            result = _row_to_classification(row, mapping_status="PREFIX_RULE_REVIEWED_CANDIDATE", confidence="CANDIDATE_MEDIUM")
            if not result.get("context_candidate"):
                result["context_candidate"] = normalized.removeprefix(prefix).strip() or None
            result["semantics_decision"] = result.get("semantics_decision") or "PREFIX_CONTEXT_PRESERVED"
            result["review_status"] = "REVIEWED_CANDIDATE"
            return result

    family_hits: list[tuple[str, str]] = []
    for row in registry.get("anchor_tokens", []) or []:
        if any(_token_present(normalized, normalize_label(token)) for token in row.get("tokens", [])):
            family_hits.append((row["action_family"], row["rule_id"]))
    distinct_families = sorted({family for family, _ in family_hits})
    if len(distinct_families) > 1:
        result = _blank_classification()
        result.update(
            {
                "semantic_role_candidate": "UNKNOWN_UNREVIEWED",
                "action_family_candidate": "UNKNOWN",
                "mapping_status": "CONFLICT_REVIEW_REQUIRED",
                "rule_id": "+".join(sorted(rule for _, rule in family_hits)),
                "confidence_tier": "CONFLICT",
                "semantics_decision": "MULTI_ANCHOR_TOKEN_CONFLICT",
            }
        )
        return result
    if len(distinct_families) == 1:
        outcome, outcome_rule = _first_qualifier(normalized, registry, "outcome_tokens")
        direction, direction_rule = _first_qualifier(normalized, registry, "direction_tokens")
        distance, distance_rule = _first_qualifier(normalized, registry, "distance_tokens")
        zone, zone_rule = _first_qualifier(normalized, registry, "zone_tokens")
        family_rule = next(rule for family, rule in family_hits if family == distinct_families[0])
        rule_ids = [value for value in (family_rule, outcome_rule, direction_rule, distance_rule, zone_rule) if value]
        result = _blank_classification()
        result.update(
            {
                "semantic_role_candidate": "ACTION_ANCHOR",
                "action_family_candidate": distinct_families[0],
                "outcome_candidate": outcome,
                "direction_candidate": direction,
                "distance_candidate": distance,
                "zone_candidate": zone,
                "mapping_status": "TOKEN_FALLBACK_REVIEW_REQUIRED",
                "rule_id": "+".join(rule_ids),
                "confidence_tier": "CANDIDATE_LOW",
                "downstream_eligibility": "BLOCKED_PENDING_REVIEW",
                "semantics_decision": "TOKEN_SUGGESTION_NOT_ACCEPTED_SEMANTICS",
                "review_status": "REVIEW_REQUIRED",
            }
        )
        return result

    if normalized in {normalize_label(value) for value in registry.get("meta_labels", []) or []}:
        result = _blank_classification()
        result.update(
            {
                "semantic_role_candidate": "PERIOD_OR_META",
                "mapping_status": "EXACT_ALIAS_CANDIDATE",
                "rule_id": "period_meta_alias",
                "confidence_tier": "CANDIDATE_HIGH",
                "downstream_eligibility": "ADMIN_ONLY",
                "semantics_decision": "META_ALIAS_PRESERVED",
                "review_status": "REVIEWED_CANDIDATE",
            }
        )
        return result

    result = _blank_classification()
    result.update(
        {
            "semantic_role_candidate": "UNKNOWN_UNREVIEWED",
            "action_family_candidate": "UNKNOWN",
            "mapping_status": "UNKNOWN_UNREVIEWED",
            "rule_id": None,
            "confidence_tier": "UNKNOWN",
            "downstream_eligibility": "BLOCKED_UNKNOWN",
            "semantics_decision": "RAW_LABEL_PRESERVED_NO_GUESS",
            "review_status": "REVIEW_REQUIRED",
        }
    )
    return result


def _base_record(
    *,
    source_format: str,
    source_role: str,
    relative_path: str,
    source_sha256: str | None,
    raw_label: str,
    surface_row_volume: int | None,
    evidence_scope: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    classified = classify_label(
        raw_label,
        source_format=source_format,
        source_role=source_role,
        registry=registry,
    )
    normalized = normalize_label(raw_label)
    review_hits = []
    if classified["mapping_status"] in REVIEW_MAPPING_STATUSES:
        review_hits.append(classified["mapping_status"].casefold())
    return {
        "record_id": f"{source_format}:{source_role}:{relative_path}:{normalized}",
        "source_format": source_format,
        "source_role": source_role,
        "source_relative_path": relative_path,
        "source_sha256": source_sha256,
        "raw_label": raw_label,
        "normalized_label": normalized,
        "surface_row_volume": surface_row_volume,
        "evidence_scope": evidence_scope,
        **classified,
        "registry_version": REGISTRY_VERSION,
        "provenance_refs": [relative_path],
        "hard_block_hits": [],
        "review_hits": review_hits,
        "validated_semantics": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _is_duplicate_reflection(file_row: dict[str, Any], seen: set[tuple[str, str]]) -> bool:
    role = str(file_row.get("source_role") or "UNKNOWN")
    sha = str(file_row.get("sha256") or "")
    if not sha:
        return False
    key = (role, sha)
    if key in seen:
        return True
    seen.add(key)
    return False


def csv_label_records(payload: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_files: set[tuple[str, str]] = set()
    for file_row in payload.get("files", []) or []:
        if _is_duplicate_reflection(file_row, seen_files):
            continue
        source_role = str(file_row.get("source_role") or "UNKNOWN")
        relative_path = str(file_row.get("relative_path") or file_row.get("file_name") or "")
        sha256 = file_row.get("sha256")
        for row in file_row.get("action_taxonomy", []) or []:
            raw_type = str(row.get("raw_type") or "").strip()
            raw_subtype = str(row.get("raw_subtype") or "").strip()
            raw_label = " ".join(value for value in (raw_type, raw_subtype) if value).strip()
            if not raw_label:
                continue
            volume = row.get("surface_row_volume")
            records.append(
                _base_record(
                    source_format="csv",
                    source_role=source_role,
                    relative_path=relative_path,
                    source_sha256=str(sha256) if sha256 else None,
                    raw_label=raw_label,
                    surface_row_volume=int(volume) if isinstance(volume, int) else None,
                    evidence_scope="FULL_CSV_TAXONOMY_LABEL_VOLUME_NOT_ROW_IDENTITY",
                    registry=registry,
                )
            )
    return records


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def xml_label_records(payload: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_files: set[tuple[str, str]] = set()
    seen_labels: set[tuple[str, str, str]] = set()
    for file_row in payload.get("files", []) or []:
        if _is_duplicate_reflection(file_row, seen_files):
            continue
        source_role = str(file_row.get("source_role") or "UNKNOWN")
        relative_path = str(file_row.get("relative_path") or file_row.get("file_name") or "")
        sha256 = file_row.get("sha256")
        for example in file_row.get("example_rows", []) or []:
            group_key = next((key for key in example if key.casefold().endswith("label.group")), None)
            text_key = next((key for key in example if key.casefold().endswith("label.text")), None)
            if not group_key or not text_key:
                continue
            groups = _as_list(example.get(group_key))
            texts = _as_list(example.get(text_key))
            for group, text in zip(groups, texts):
                if normalize_label(group) != "action":
                    continue
                dedupe_key = (source_role, relative_path, normalize_label(text))
                if dedupe_key in seen_labels:
                    continue
                seen_labels.add(dedupe_key)
                records.append(
                    _base_record(
                        source_format="xml",
                        source_role=source_role,
                        relative_path=relative_path,
                        source_sha256=str(sha256) if sha256 else None,
                        raw_label=text,
                        surface_row_volume=None,
                        evidence_scope="XML_EXAMPLE_SUPPORT_ONLY_NOT_FULL_LABEL_INVENTORY",
                        registry=registry,
                    )
                )
    return records


def xlsx_label_records(payload: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_files: set[tuple[str, str]] = set()
    for file_row in payload.get("files", []) or []:
        if _is_duplicate_reflection(file_row, seen_files):
            continue
        relative_path = str(file_row.get("relative_path") or file_row.get("file_name") or "")
        sha256 = file_row.get("sha256")
        for sheet in file_row.get("sheets", []) or []:
            source_role = str(sheet.get("source_role") or file_row.get("source_role") or "UNKNOWN")
            for profile in sheet.get("column_profiles", []) or []:
                raw_label = str(profile.get("raw_column") or "").strip()
                if not raw_label:
                    continue
                records.append(
                    _base_record(
                        source_format="xlsx",
                        source_role=source_role,
                        relative_path=relative_path,
                        source_sha256=str(sha256) if sha256 else None,
                        raw_label=raw_label,
                        surface_row_volume=None,
                        evidence_scope="XLSX_AGGREGATE_LABEL_ONLY_NO_EVENT_SEMANTICS",
                        registry=registry,
                    )
                )
    return records


def _semantic_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in SEMANTIC_FIELDS)


def _cross_format_consistency(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row["source_format"] not in {"csv", "xml"}:
            continue
        grouped[(row["source_role"], row["normalized_label"])].append(row)
    comparable = 0
    conflicts: list[dict[str, Any]] = []
    for (role, label), rows in sorted(grouped.items()):
        formats = {row["source_format"] for row in rows}
        if formats != {"csv", "xml"}:
            continue
        comparable += 1
        signatures = {_semantic_signature(row) for row in rows}
        if len(signatures) > 1:
            conflicts.append(
                {
                    "source_role": role,
                    "normalized_label": label,
                    "signatures": [list(value) for value in sorted(signatures, key=str)],
                }
            )
    return {
        "comparable_label_count": comparable,
        "consistent_label_count": comparable - len(conflicts),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "validated_cross_format_equivalence": False,
        "evidence_scope": "LABEL_MAPPING_CONSISTENCY_ONLY",
    }


def _volume(records: list[dict[str, Any]], predicate) -> int:
    return sum(int(row.get("surface_row_volume") or 0) for row in records if predicate(row))


def _coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    csv_rows = [row for row in records if row["source_format"] == "csv"]
    total_volume = _volume(csv_rows, lambda row: True)
    exact_reviewed = _volume(csv_rows, lambda row: row["mapping_status"] == "EXACT_REVIEWED_CANDIDATE")
    prefix_reviewed = _volume(csv_rows, lambda row: row["mapping_status"] == "PREFIX_RULE_REVIEWED_CANDIDATE")
    token_review = _volume(csv_rows, lambda row: row["mapping_status"] == "TOKEN_FALLBACK_REVIEW_REQUIRED")
    unknown_unreviewed = _volume(csv_rows, lambda row: row["mapping_status"] == "UNKNOWN_UNREVIEWED")
    conflict_review = _volume(csv_rows, lambda row: row["mapping_status"] == "CONFLICT_REVIEW_REQUIRED")
    reviewed_preserved = _volume(csv_rows, lambda row: row["semantic_role_candidate"] == "UNKNOWN_REVIEWED_PRESERVED")
    reviewed_semantic = exact_reviewed + prefix_reviewed
    review_required = token_review + unknown_unreviewed + conflict_review
    action_volume = _volume(csv_rows, lambda row: row["semantic_role_candidate"] == "ACTION_ANCHOR")
    context_volume = _volume(csv_rows, lambda row: row["semantic_role_candidate"] in {"CONTEXT_INTERVAL", "PARTICIPATION_INTERVAL"})
    reference_volume = _volume(csv_rows, lambda row: row["semantic_role_candidate"] in {"OPPONENT_ACTION_REFERENCE", "RECEIVED_ACTION_REFERENCE", "DERIVED_CONSEQUENCE_CANDIDATE", "TERMINAL_OUTCOME_CANDIDATE"})
    admin_volume = _volume(csv_rows, lambda row: row["semantic_role_candidate"] in {"ADMINISTRATIVE_MARKER", "PERIOD_OR_META"})
    return {
        "csv_label_record_count": len(csv_rows),
        "csv_surface_row_volume": total_volume,
        "reviewed_semantic_surface_row_volume": reviewed_semantic,
        "reviewed_semantic_surface_row_volume_ratio": reviewed_semantic / total_volume if total_volume else 0.0,
        "exact_reviewed_surface_row_volume": exact_reviewed,
        "prefix_reviewed_surface_row_volume": prefix_reviewed,
        "token_fallback_review_surface_row_volume": token_review,
        "unknown_unreviewed_surface_row_volume": unknown_unreviewed,
        "unknown_reviewed_preserved_surface_row_volume": reviewed_preserved,
        "conflict_review_surface_row_volume": conflict_review,
        "review_required_surface_row_volume": review_required,
        "action_anchor_candidate_surface_row_volume": action_volume,
        "context_or_participation_surface_row_volume": context_volume,
        "reference_or_derived_surface_row_volume": reference_volume,
        "administrative_or_meta_surface_row_volume": admin_volume,
        "mapped_surface_row_volume": reviewed_semantic,
        "unknown_surface_row_volume": unknown_unreviewed,
        "mapped_surface_row_volume_ratio": reviewed_semantic / total_volume if total_volume else 0.0,
        "xml_example_support_label_count": sum(1 for row in records if row["source_format"] == "xml"),
        "xlsx_aggregate_label_count": sum(1 for row in records if row["source_format"] == "xlsx"),
        "coverage_scope": "CSV_LABEL_VOLUME_DECISION_COVERAGE_PLUS_XML_EXAMPLE_SUPPORT",
        "coverage_does_not_mean": [
            "semantic_truth",
            "physical_action_count",
            "canonical_event_count",
            "cross_format_independence",
        ],
    }


def build_semantics(
    csv_payload: dict[str, Any],
    xlsx_payload: dict[str, Any],
    xml_payload: dict[str, Any],
    field_semantics_payload: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    hard_blocks, warnings = _upstream_guard((csv_payload, xlsx_payload, xml_payload, field_semantics_payload))
    hard_blocks.extend(_field_semantics_guard(field_semantics_payload))
    hard_blocks.extend(_source_hash_guard((csv_payload, xlsx_payload, xml_payload)))

    records = (
        csv_label_records(csv_payload, registry)
        + xml_label_records(xml_payload, registry)
        + xlsx_label_records(xlsx_payload, registry)
    )
    if not records:
        hard_blocks.append("provider_label_inventory_empty")

    consistency = _cross_format_consistency(records)
    if consistency["conflict_count"]:
        warnings.append("paired_csv_xml_label_conflict")

    unknown_records = [row for row in records if row["mapping_status"] == "UNKNOWN_UNREVIEWED"]
    conflict_records = [row for row in records if row["mapping_status"] == "CONFLICT_REVIEW_REQUIRED"]
    token_fallback_records = [row for row in records if row["mapping_status"] == "TOKEN_FALLBACK_REVIEW_REQUIRED"]
    if unknown_records:
        warnings.append("unknown_unreviewed_provider_label_values_present")
    if conflict_records:
        warnings.append("conflicting_label_semantics_present")
    if token_fallback_records:
        warnings.append("token_fallback_semantics_review_required")

    coverage = _coverage(records)
    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if warnings else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "BLOCK_DOWNSTREAM" if hard_blocks else ("REVIEW_SEMANTICS" if warnings else "PASS_SEMANTICS_CANDIDATE"),
        "registry_version": REGISTRY_VERSION,
        "provider_label_record_count": len(records),
        "provider_label_records": records,
        "mapping_status_counts": dict(sorted(Counter(row["mapping_status"] for row in records).items())),
        "semantic_role_counts": dict(sorted(Counter(str(row["semantic_role_candidate"]) for row in records).items())),
        "action_family_counts": dict(sorted(Counter(str(row["action_family_candidate"]) for row in records if row["action_family_candidate"]).items())),
        "coverage": coverage,
        "cross_format_consistency": consistency,
        "unknown_provider_labels": [
            {
                "source_format": row["source_format"],
                "source_role": row["source_role"],
                "raw_label": row["raw_label"],
                "normalized_label": row["normalized_label"],
                "surface_row_volume": row["surface_row_volume"],
                "mapping_status": row["mapping_status"],
            }
            for row in unknown_records
        ],
        "token_fallback_review_records": [
            {
                "source_format": row["source_format"],
                "source_role": row["source_role"],
                "raw_label": row["raw_label"],
                "surface_row_volume": row["surface_row_volume"],
                "action_family_candidate": row["action_family_candidate"],
            }
            for row in token_fallback_records
        ],
        "conflict_records": consistency["conflicts"] + [
            {
                "source_format": row["source_format"],
                "source_role": row["source_role"],
                "raw_label": row["raw_label"],
                "surface_row_volume": row["surface_row_volume"],
                "semantics_decision": row["semantics_decision"],
            }
            for row in conflict_records
        ],
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(warnings)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "active_match_evidence_pass": False,
        "validated_provider_semantics": False,
        "validated_event_identity": False,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "donor_adaptation": {
            "accepted_idea": "reviewed exact label grammar, relation direction, qualifier separation and fail-closed fallback",
            "rejected_scope": [
                "donor_module_import",
                "broad_ontology_bundle",
                "parallel_semantic_framework",
                "probabilistic_or_llm_mapping",
                "tracking_dependent_truth",
            ],
        },
        "does_not_measure": [
            "canonical_event_truth",
            "physical_action_count",
            "validated_team_identity",
            "validated_player_identity",
            "validated_cross_format_equivalence",
            "aggregate_definition_truth",
            "sequence_truth",
            "phase_truth",
            "tactical_truth",
        ],
    }


def render_analyst(payload: dict[str, Any]) -> str:
    coverage = payload.get("coverage") or {}
    lines = [
        "HPFA PROVIDER LABEL VALUE SEMANTICS ANALYST AUDIT V2",
        f"status={payload.get('status')}",
        f"decision={payload.get('decision')}",
        f"registry_version={payload.get('registry_version')}",
        f"provider_label_record_count={payload.get('provider_label_record_count')}",
        f"csv_surface_row_volume={coverage.get('csv_surface_row_volume')}",
        f"reviewed_semantic_surface_row_volume={coverage.get('reviewed_semantic_surface_row_volume')}",
        f"reviewed_semantic_surface_row_volume_ratio={coverage.get('reviewed_semantic_surface_row_volume_ratio')}",
        f"action_anchor_candidate_surface_row_volume={coverage.get('action_anchor_candidate_surface_row_volume')}",
        f"context_or_participation_surface_row_volume={coverage.get('context_or_participation_surface_row_volume')}",
        f"reference_or_derived_surface_row_volume={coverage.get('reference_or_derived_surface_row_volume')}",
        f"administrative_or_meta_surface_row_volume={coverage.get('administrative_or_meta_surface_row_volume')}",
        f"review_required_surface_row_volume={coverage.get('review_required_surface_row_volume')}",
        f"unknown_unreviewed_surface_row_volume={coverage.get('unknown_unreviewed_surface_row_volume')}",
        f"xml_example_support_label_count={coverage.get('xml_example_support_label_count')}",
        f"cross_format_conflict_count={(payload.get('cross_format_consistency') or {}).get('conflict_count')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "analyst_evidence=visible provider-label volume is separated into physical-action candidates, context/participation, opponent or received references, derived/terminal markers and administrative/meta surfaces.",
        "safe_statement=label grammar decisions are complete for the reviewed ACTIVE_MATCH vocabulary; row identity, action nuclei, sequence and tactical truth remain downstream work.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(
    runtime_authority: str | Path,
    expected_runtime_authority: str | Path,
    csv_path: str | Path,
    xlsx_path: str | Path,
    xml_path: str | Path,
    field_semantics_path: str | Path,
    registry_path: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    output_root = validate_out(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    runtime = Path(runtime_authority).expanduser().resolve(strict=False)
    expected = Path(expected_runtime_authority).expanduser().resolve(strict=False)
    registry = load_registry(registry_path)
    payload = build_semantics(
        load_json(csv_path),
        load_json(xlsx_path),
        load_json(xml_path),
        load_json(field_semantics_path),
        registry,
    )
    if not runtime.is_dir():
        payload["hard_block_hits"] = sorted(set(payload["hard_block_hits"] + ["input_root_missing"]))
        payload["status"] = "FAIL_CLOSED"
        payload["decision"] = "BLOCK_DOWNSTREAM"
    if runtime != expected:
        payload["hard_block_hits"] = sorted(set(payload["hard_block_hits"] + ["runtime_authority_mismatch"]))
        payload["status"] = "FAIL_CLOSED"
        payload["decision"] = "BLOCK_DOWNSTREAM"
    payload["runtime_authority"] = str(runtime)
    payload["expected_runtime_authority"] = str(expected)
    payload["active_match_evidence_pass"] = (
        payload.get("status") == "PASS"
        and not payload.get("hard_block_hits")
        and runtime == expected
    )

    paths = {key: output_root / name for key, name in OUT.items()}
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    inventory_payload = {
        "module_id": MODULE_ID,
        "registry_version": REGISTRY_VERSION,
        "provider_label_record_count": payload["provider_label_record_count"],
        "provider_label_records": payload["provider_label_records"],
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }
    unknown_payload = {
        "module_id": MODULE_ID,
        "registry_version": REGISTRY_VERSION,
        "unknown_provider_labels": payload["unknown_provider_labels"],
        "unknown_unreviewed_surface_row_volume": payload["coverage"]["unknown_unreviewed_surface_row_volume"],
        "token_fallback_review_records": payload["token_fallback_review_records"],
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }
    conflict_payload = {
        "module_id": MODULE_ID,
        "registry_version": REGISTRY_VERSION,
        "conflict_records": payload["conflict_records"],
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }
    paths["inventory"].write_text(json.dumps(inventory_payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    paths["main"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    paths["unknown"].write_text(json.dumps(unknown_payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    paths["conflict"].write_text(json.dumps(conflict_payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    paths["analyst"].write_text(render_analyst(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-authority", required=True)
    parser.add_argument("--expected-runtime-authority", required=True)
    parser.add_argument("--csv-audit", required=True)
    parser.add_argument("--xlsx-audit", required=True)
    parser.add_argument("--xml-audit", required=True)
    parser.add_argument("--field-semantics", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = write_outputs(
        args.runtime_authority,
        args.expected_runtime_authority,
        args.csv_audit,
        args.xlsx_audit,
        args.xml_audit,
        args.field_semantics,
        args.registry,
        args.out,
    )
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "decision",
                    "registry_version",
                    "provider_label_record_count",
                    "coverage",
                    "hard_block_hits",
                    "review_hits",
                    "active_match_evidence_pass",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
