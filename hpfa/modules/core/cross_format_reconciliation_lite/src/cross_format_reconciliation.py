from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "cross_format_reconciliation_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "CROSS_FORMAT_SURFACE_RECONCILIATION_CANDIDATE_ONLY"
OUT = {
    "main": "cross_format_reconciliation_lite_v1.json",
    "summary": "cross_format_reconciliation_lite_v1.txt",
    "analyst": "cross_format_reconciliation_analyst_audit_v1.txt",
}

REQUIRED_FIELDS = ("start", "end", "period", "action")
SUPPORT_FIELDS = ("code", "team", "pos_x", "pos_y")
SIGNATURE_FIELDS_WITHOUT_ID = (*REQUIRED_FIELDS, *SUPPORT_FIELDS)
SIGNATURE_FIELDS_WITH_ID = ("id", *SIGNATURE_FIELDS_WITHOUT_ID)
REVIEW_MAPPING_STATUSES = {
    "TOKEN_FALLBACK_REVIEW_REQUIRED",
    "CONFLICT_REVIEW_REQUIRED",
    "UNKNOWN_UNREVIEWED",
}
ROLE_ORDER = {
    "GOALKEEPER_SURFACE_CANDIDATE": 0,
    "PLAYER_SURFACE_CANDIDATE": 1,
    "TEAM_SURFACE_CANDIDATE": 2,
}


def norm_text(value: Any) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "").strip()).casefold()
    if not text or text in {"none", "null", "nan", "n/a", "na", "-"}:
        return None
    return text


def norm_number(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text or text.casefold() in {"none", "null", "nan", "n/a", "na", "-"}:
        return None
    if "," in text and "." not in text:
        text = text.replace(" ", "").replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation:
        return norm_text(text)
    if not number.is_finite():
        return None
    normalized = format(number.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return "0" if normalized in {"-0", ""} else normalized


def norm_period(value: Any) -> str | None:
    return norm_number(value)


def norm_field(field: str, value: Any) -> str | None:
    if field in {"start", "end", "pos_x", "pos_y", "id"}:
        return norm_number(value)
    if field == "period":
        return norm_period(value)
    return norm_text(value)


def norm_header(value: Any) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().casefold())).strip("_")


def validate_out(path: str | Path) -> Path:
    out = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in out.parts and out.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return out


def is_active(path: Path) -> bool:
    return path.as_posix().rstrip("/").endswith("runtime/active_single_match/current")


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


def _stable_digest(values: Iterable[str | None]) -> str:
    text = json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValueError("runtime_source_unreadable") from exc
    return digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def _safe_candidate_value(value: Any) -> str | None:
    normalized = norm_text(value)
    return normalized[:160] if normalized is not None else None


def _source_binding_audit(
    root: Path,
    inventory: dict[str, Any],
    payloads: Iterable[tuple[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[str]]:
    inventory_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in inventory.get("files", []) or []:
        relative = str(row.get("relative_path") or row.get("file_name") or "")
        if relative:
            inventory_by_path[relative].append(row)

    records: list[dict[str, Any]] = []
    blocks: list[str] = []
    for source_format, payload in payloads:
        for row in payload.get("files", []) or []:
            relative = str(row.get("relative_path") or row.get("file_name") or "")
            audit_sha = row.get("sha256")
            inventory_rows = inventory_by_path.get(relative, [])
            inventory_shas = sorted(
                {
                    str(item.get("sha256")).casefold()
                    for item in inventory_rows
                    if _valid_sha256(item.get("sha256"))
                }
            )
            runtime_sha: str | None = None
            if not relative or not _valid_sha256(audit_sha) or not inventory_shas:
                blocks.append(f"source_sha_missing:{source_format}:{relative or 'UNKNOWN'}")
            else:
                try:
                    runtime_sha = _sha256_file(_path(root, row))
                except ValueError:
                    blocks.append(f"runtime_sha_mismatch:{source_format}:{relative}")
                expected = str(audit_sha).casefold()
                if runtime_sha != expected or expected not in inventory_shas:
                    blocks.append(f"runtime_sha_mismatch:{source_format}:{relative}")
            records.append(
                {
                    "source_format": source_format,
                    "source_role": row.get("source_role"),
                    "source_relative_path": relative,
                    "audit_sha256": str(audit_sha).casefold() if _valid_sha256(audit_sha) else None,
                    "inventory_sha256_candidates": inventory_shas,
                    "runtime_rehashed_sha256": runtime_sha,
                    "audit_sha_match": bool(
                        runtime_sha
                        and _valid_sha256(audit_sha)
                        and runtime_sha == str(audit_sha).casefold()
                        and runtime_sha in inventory_shas
                    ),
                }
            )
    return records, sorted(set(blocks))


def _semantic_provenance_guard(payload: dict[str, Any]) -> list[str]:
    blocks: list[str] = []
    if payload.get("module_id") != "provider_label_value_semantics_lite_v1":
        return ["field_path_semantics_used_as_value_semantics"]
    for row in payload.get("provider_label_records", []) or []:
        relative = str(row.get("source_relative_path") or "UNKNOWN")
        if not _valid_sha256(row.get("source_sha256")):
            blocks.append(f"source_sha_missing:label_semantics:{relative}")
        rule_id = row.get("rule_id")
        provenance_refs = row.get("provenance_refs") or []
        if rule_id and not provenance_refs:
            blocks.append(f"semantic_rule_without_source_ref:{row.get('record_id') or relative}")
        mapping_status = str(row.get("mapping_status") or "")
        downstream = str(row.get("downstream_eligibility") or "")
        if mapping_status == "TOKEN_FALLBACK_REVIEW_REQUIRED" and not downstream.startswith("BLOCKED"):
            blocks.append(f"token_fallback_promoted_without_review:{row.get('record_id') or relative}")
        if mapping_status == "CONFLICT_REVIEW_REQUIRED" and not downstream.startswith("BLOCKED"):
            blocks.append(f"multi_anchor_conflict_resolved_fail_open:{row.get('record_id') or relative}")
        if mapping_status in REVIEW_MAPPING_STATUSES and row.get("review_status") == "REVIEWED_CANDIDATE":
            blocks.append(f"review_mapping_promoted_without_resolution:{row.get('record_id') or relative}")
    return sorted(set(blocks))


def _provider_semantic_provenance_records(
    label_payload: dict[str, Any],
    source_payloads: Iterable[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    source_index: dict[tuple[str, str], dict[str, Any]] = {}
    for source_format, payload in source_payloads:
        for row in payload.get("files", []) or []:
            relative = str(row.get("relative_path") or row.get("file_name") or "")
            source_index[(source_format, relative)] = row

    records: list[dict[str, Any]] = []
    for row in label_payload.get("provider_label_records", []) or []:
        source_format = str(row.get("source_format") or "UNKNOWN")
        relative = str(row.get("source_relative_path") or "")
        source = source_index.get((source_format, relative), {})
        mapping_status = str(row.get("mapping_status") or "UNKNOWN")
        rule_id = row.get("rule_id")
        ambiguity_reasons = list(row.get("review_hits") or [])
        raw_field_path = None
        if raw_field_path is None:
            ambiguity_reasons.append("raw_field_path_not_proven_by_label_value_record")
        conflicting_rule_ids = (
            sorted(str(rule).strip() for rule in str(rule_id).split("+") if str(rule).strip())
            if mapping_status == "CONFLICT_REVIEW_REQUIRED"
            else []
        )
        records.append(
            {
                "source_file_id": source.get("file_id"),
                "source_sha256": row.get("source_sha256"),
                "source_role": row.get("source_role"),
                "provider_candidate": "SPORTSBASE_PROVIDER_CANDIDATE",
                "raw_field_path": raw_field_path,
                "raw_label": row.get("raw_label"),
                "normalized_label": row.get("normalized_label"),
                "exact_label_rule_id": (
                    rule_id
                    if mapping_status
                    in {"EXACT_REVIEWED_CANDIDATE", "EXACT_ALIAS_CANDIDATE"}
                    else None
                ),
                "fallback_rule_id": (
                    rule_id if mapping_status == "TOKEN_FALLBACK_REVIEW_REQUIRED" else None
                ),
                "semantic_role_candidate": row.get("semantic_role_candidate"),
                "action_family_candidate": row.get("action_family_candidate"),
                "context_family_candidate": row.get("context_candidate"),
                "derivation_dependency": (
                    "DERIVATION_DEPENDENCY_UNRESOLVED"
                    if source_format == "xlsx"
                    else "SOURCE_INDEPENDENCE_NOT_ESTABLISHED"
                ),
                "independence_group": "SPORTSBASE_VISIBLE_SURFACE_GROUP",
                "mapping_confidence": row.get("confidence_tier"),
                "ambiguity_reasons": sorted(set(str(value) for value in ambiguity_reasons)),
                "conflicting_rule_ids": conflicting_rule_ids,
                "source_row_refs": list(row.get("provenance_refs") or []),
                "claim_ceiling": row.get("claim_ceiling"),
                "status": mapping_status,
                "decision": row.get("semantics_decision"),
            }
        )
    return records


def _load_xml_group_registry(payload: dict[str, Any]) -> dict[str, str]:
    if payload.get("candidate_only") is not True or payload.get("validated_semantics") is not False:
        raise ValueError("xml_label_priority_used_without_authority_contract")
    if not payload.get("source_refs"):
        raise ValueError("semantic_rule_without_source_ref:xml_group_registry")
    mapping: dict[str, str] = {}
    for row in payload.get("exact_group_rules", []) or []:
        raw_group = norm_text(row.get("raw_group_label"))
        candidate = str(row.get("field_key_candidate") or "")
        if not raw_group or not candidate or not row.get("rule_id") or not row.get("source_ref"):
            raise ValueError("semantic_rule_without_source_ref:xml_group_registry_rule")
        if raw_group in mapping and mapping[raw_group] != candidate:
            raise ValueError("xml_group_registry_conflict")
        mapping[raw_group] = candidate
    required = {"action", "period", "team", "pos_x", "pos_y"}
    if not required.issubset(set(mapping.values())):
        raise ValueError("xml_group_authority_contract_incomplete")
    return mapping


def _dedupe_reflections(files: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    reflections = 0
    for row in files:
        key = str(row.get("sha256") or row.get("relative_path") or row.get("file_name") or "")
        if key and key in seen:
            reflections += 1
            continue
        seen.add(key)
        result.append(row)
    return result, reflections


def _files_by_role(payload: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], int]:
    unique, reflections = _dedupe_reflections(list(payload.get("files", []) or []))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in unique:
        grouped[str(row.get("source_role") or "UNKNOWN")].append(row)
    return dict(grouped), reflections


def _path(root: Path, row: dict[str, Any]) -> Path:
    relative = str(row.get("relative_path") or row.get("file_name") or "")
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("surface_path_outside_active_match") from exc
    return candidate


def _csv_rows(root: Path, audit: dict[str, Any]) -> list[dict[str, Any]]:
    path = _path(root, audit)
    encoding = str(audit.get("encoding_candidate") or "utf-8")
    delimiter = audit.get("delimiter_candidate")
    headers = [str(value) for value in audit.get("raw_columns", []) or []]
    if not delimiter or not headers:
        raise ValueError("csv_parse_contract_missing")
    try:
        text = path.read_text(encoding=encoding)
    except (OSError, UnicodeError) as exc:
        raise ValueError("csv_surface_unreadable") from exc
    try:
        parsed = list(csv.reader(io.StringIO(text, newline=""), delimiter=str(delimiter)))
    except csv.Error as exc:
        raise ValueError("csv_surface_malformed") from exc
    normalized_headers = [norm_header(value) for value in headers]
    header_index = next(
        (index for index, row in enumerate(parsed) if [norm_header(value) for value in row] == normalized_headers),
        None,
    )
    if header_index is None:
        raise ValueError("csv_header_contract_mismatch")
    index_by_name = {name: index for index, name in enumerate(normalized_headers) if name}
    bundle = audit.get("field_bundle") or {}

    def idx(bundle_key: str, fallback: str | None = None) -> int | None:
        raw = bundle.get(bundle_key)
        if raw is not None:
            normalized = norm_header(raw)
            if normalized in index_by_name:
                return index_by_name[normalized]
        return index_by_name.get(fallback or bundle_key)

    indexes = {
        "id": index_by_name.get("id"),
        "start": idx("start"),
        "end": idx("end"),
        "period": idx("period", "half"),
        "action": idx("action"),
        "code": index_by_name.get("code"),
        "team": idx("team"),
        "pos_x": idx("start_x", "pos_x"),
        "pos_y": idx("start_y", "pos_y"),
    }
    if any(indexes[key] is None for key in ("id", *REQUIRED_FIELDS)):
        raise ValueError("csv_required_reconciliation_field_missing")

    result: list[dict[str, Any]] = []
    width = len(headers)
    for row in parsed[header_index + 1 :]:
        if not any(str(value).strip() for value in row):
            continue
        if len(row) != width:
            continue
        if [norm_header(value) for value in row] == normalized_headers:
            continue

        def value(key: str) -> str | None:
            index = indexes.get(key)
            return str(row[index]).strip() if index is not None else None

        action = value("action")
        code = value("code")
        team = value("team")
        if not team and code and action:
            suffix = f" - {action}"
            if code.endswith(suffix):
                team = code[: -len(suffix)].strip() or None
        raw = {
            "id": value("id"),
            "start": value("start"),
            "end": value("end"),
            "period": value("period"),
            "action": action,
            "code": code,
            "team": team,
            "pos_x": value("pos_x"),
            "pos_y": value("pos_y"),
        }
        result.append({key: norm_field(key, item) for key, item in raw.items()})
    return result


def _local_name(tag: Any) -> str:
    return str(tag).rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def _first_descendant_text(elem: ET.Element, name: str) -> str | None:
    for node in elem.iter():
        if _local_name(node.tag).casefold() == name.casefold():
            text = str(node.text or "").strip()
            if text:
                return text
    return None


def _xml_rows(
    root: Path,
    audit: dict[str, Any],
    xml_group_mapping: dict[str, str],
) -> list[dict[str, Any]]:
    path = _path(root, audit)
    guard = audit.get("security_guard") or {}
    if guard.get("status") != "PASS" or guard.get("dtd_or_entity_declaration_present") is True:
        raise ValueError("xml_security_contract_not_pass")
    selected = str(audit.get("selected_row_tag_candidate") or "")
    if not selected:
        raise ValueError("xml_row_container_candidate_missing")
    try:
        tree_root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError("xml_surface_unreadable_or_malformed") from exc

    result: list[dict[str, Any]] = []
    for elem in tree_root.iter():
        if _local_name(elem.tag) != selected:
            continue
        labels: dict[str, list[str]] = defaultdict(list)
        for label in elem.iter():
            if _local_name(label.tag).casefold() != "label":
                continue
            group = _first_descendant_text(label, "group")
            text = _first_descendant_text(label, "text")
            if group and text:
                semantic_key = xml_group_mapping.get(norm_text(group) or "")
                if semantic_key:
                    labels[semantic_key].append(text)

        def label_value(field_key: str) -> str | None:
            values = list(dict.fromkeys(labels.get(field_key, [])))
            return values[0] if len(values) == 1 else None

        action = label_value("action")
        code = _first_descendant_text(elem, "code")
        team = label_value("team")
        if not team and code and action:
            suffix = f" - {action}"
            if code.endswith(suffix):
                team = code[: -len(suffix)].strip() or None
        raw = {
            "id": _first_descendant_text(elem, "ID"),
            "start": _first_descendant_text(elem, "start"),
            "end": _first_descendant_text(elem, "end"),
            "period": label_value("period"),
            "action": action,
            "code": code,
            "team": team,
            "pos_x": label_value("pos_x"),
            "pos_y": label_value("pos_y"),
        }
        result.append({key: norm_field(key, item) for key, item in raw.items()})
    return result


def _index(records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int], int]:
    counts = Counter(str(row.get("id")) for row in records if row.get("id") is not None)
    duplicates = {key: count for key, count in counts.items() if count > 1}
    indexed = {
        str(row["id"]): row
        for row in records
        if row.get("id") is not None and counts[str(row["id"])] == 1
    }
    missing = sum(1 for row in records if row.get("id") is None)
    return indexed, duplicates, missing


def _role_pair(
    role: str,
    root: Path,
    csv_audit: dict[str, Any],
    xml_audit: dict[str, Any],
    xlsx_rows: list[dict[str, Any]],
    xml_group_mapping: dict[str, str],
    source_bindings: dict[tuple[str, str], dict[str, Any]],
    field_semantics_version: str,
    label_semantics_version: str,
) -> dict[str, Any]:
    csv_rows = _csv_rows(root, csv_audit)
    xml_rows = _xml_rows(root, xml_audit, xml_group_mapping)
    csv_index, csv_duplicates, csv_missing_ids = _index(csv_rows)
    xml_index, xml_duplicates, xml_missing_ids = _index(xml_rows)
    hard_blocks: list[str] = []
    warnings: list[str] = []
    if csv_duplicates or xml_duplicates:
        hard_blocks.append("duplicate_surface_row_id_candidate")
    if csv_missing_ids or xml_missing_ids:
        hard_blocks.append("surface_row_id_candidate_missing")

    common = sorted(set(csv_index) & set(xml_index), key=lambda value: (len(value), value))
    csv_only = sorted(set(csv_index) - set(xml_index), key=lambda value: (len(value), value))
    xml_only = sorted(set(xml_index) - set(csv_index), key=lambda value: (len(value), value))
    required_aligned = 0
    exact_aligned = 0
    required_mismatch = 0
    supporting_mismatch = 0
    present_present_support_count = 0
    present_present_support_match_count = 0
    both_missing_support_count = 0
    one_missing_support_count = 0
    mismatch_examples: list[dict[str, Any]] = []
    signatures_without_id: dict[str, set[str]] = defaultdict(set)
    signatures_with_id: Counter[str] = Counter()

    for row_id in common:
        csv_row = csv_index[row_id]
        xml_row = xml_index[row_id]
        required_bad = [field for field in REQUIRED_FIELDS if csv_row.get(field) != xml_row.get(field) or csv_row.get(field) is None]
        support_bad = [
            field
            for field in SUPPORT_FIELDS
            if (csv_row.get(field) is not None or xml_row.get(field) is not None)
            and csv_row.get(field) != xml_row.get(field)
        ]
        for field in SUPPORT_FIELDS:
            csv_value = csv_row.get(field)
            xml_value = xml_row.get(field)
            if csv_value is None and xml_value is None:
                both_missing_support_count += 1
            elif csv_value is None or xml_value is None:
                one_missing_support_count += 1
            else:
                present_present_support_count += 1
                if csv_value == xml_value:
                    present_present_support_match_count += 1
        if not required_bad:
            required_aligned += 1
        else:
            required_mismatch += 1
        all_support_present = all(
            csv_row.get(field) is not None and xml_row.get(field) is not None
            for field in SUPPORT_FIELDS
        )
        if not required_bad and not support_bad and all_support_present:
            exact_aligned += 1
        elif support_bad:
            supporting_mismatch += 1
        signature_without_id = _stable_digest(
            [csv_row.get(field) for field in SIGNATURE_FIELDS_WITHOUT_ID]
        )
        signature_with_id = _stable_digest(
            [csv_row.get(field) for field in SIGNATURE_FIELDS_WITH_ID]
        )
        signatures_without_id[signature_without_id].add(row_id)
        signatures_with_id[signature_with_id] += 1
        if (required_bad or support_bad) and len(mismatch_examples) < 20:
            mismatched_fields = sorted(set(required_bad + support_bad))
            mismatch_examples.append(
                {
                    "surface_row_id_candidate": row_id,
                    "required_mismatch_fields": required_bad,
                    "supporting_mismatch_fields": support_bad,
                    "candidate_safe_values": {
                        field: {
                            "csv": _safe_candidate_value(csv_row.get(field)),
                            "xml": _safe_candidate_value(xml_row.get(field)),
                        }
                        for field in mismatched_fields
                    },
                }
            )

    if csv_only or xml_only:
        warnings.append("unmatched_surface_row_id_candidates")
    if required_mismatch:
        warnings.append("required_field_mismatch_candidates")
    if supporting_mismatch:
        warnings.append("supporting_field_mismatch_candidates")
    if len(csv_rows) == len(xml_rows) and (csv_only or xml_only or required_mismatch):
        warnings.append("equal_row_count_does_not_prove_alignment")
    cross_id_collision_count = sum(
        len(row_ids) - 1
        for row_ids in signatures_without_id.values()
        if len(row_ids) > 1
    )
    local_duplicate_candidate_count = sum(
        count - 1 for count in signatures_with_id.values() if count > 1
    )
    if cross_id_collision_count:
        warnings.append("cross_id_signature_collision_candidates")
    if local_duplicate_candidate_count:
        hard_blocks.append("local_duplicate_candidate_detected")

    if hard_blocks:
        decision = "BLOCK_FUSION"
    elif warnings:
        decision = "PASS_WITH_WARNINGS"
    else:
        decision = "PASS_ALIGNMENT_CANDIDATE"

    xlsx_formula_cells = sum(
        int((sheet.get("formula_audit") or {}).get("formula_cell_count") or 0)
        for file_row in xlsx_rows
        for sheet in file_row.get("sheets", []) or []
    )
    xlsx_profiled_rows = sum(
        int(sheet.get("profiled_row_count") or 0)
        for file_row in xlsx_rows
        for sheet in file_row.get("sheets", []) or []
    )
    denominator = max(len(csv_index), len(xml_index), 1)
    common_denominator = max(len(common), 1)
    csv_relative = str(csv_audit.get("relative_path") or "")
    xml_relative = str(xml_audit.get("relative_path") or "")
    csv_binding = source_bindings.get(("csv", csv_relative), {})
    xml_binding = source_bindings.get(("xml", xml_relative), {})
    xlsx_bindings = [
        source_bindings.get(("xlsx", str(row.get("relative_path") or "")), {})
        for row in xlsx_rows
    ]
    audit_sha_match = bool(
        csv_binding.get("audit_sha_match")
        and xml_binding.get("audit_sha_match")
        and all(row.get("audit_sha_match") for row in xlsx_bindings)
    )
    return {
        "reconciliation_id": "recon_" + _stable_digest([role, csv_relative, xml_relative])[:24],
        "source_role": role,
        "csv_relative_path": csv_relative,
        "xml_relative_path": xml_relative,
        "csv_sha256": csv_audit.get("sha256"),
        "xml_sha256": xml_audit.get("sha256"),
        "xlsx_source_sha": [row.get("sha256") for row in xlsx_rows],
        "runtime_rehashed_sha": {
            "csv": csv_binding.get("runtime_rehashed_sha256"),
            "xml": xml_binding.get("runtime_rehashed_sha256"),
            "xlsx": [row.get("runtime_rehashed_sha256") for row in xlsx_bindings],
        },
        "audit_sha_match": audit_sha_match,
        "source_independence_status": "SAME_PROVIDER_SURFACES_INDEPENDENCE_NOT_ESTABLISHED",
        "derivation_dependency_status": "DERIVATION_DEPENDENCY_UNRESOLVED",
        "candidate_signature_without_id": {
            "fields": list(SIGNATURE_FIELDS_WITHOUT_ID),
            "signature_set_sha256": _stable_digest(sorted(signatures_without_id)),
        },
        "candidate_signature_with_id": {
            "fields": list(SIGNATURE_FIELDS_WITH_ID),
            "signature_set_sha256": _stable_digest(sorted(signatures_with_id)),
        },
        "cross_id_collision_count": cross_id_collision_count,
        "local_duplicate_candidate_count": local_duplicate_candidate_count,
        "upstream_duplicate_reflection_count": 0,
        "csv_profiled_row_count": len(csv_rows),
        "xml_row_candidate_count": len(xml_rows),
        "row_count_equal_signal": len(csv_rows) == len(xml_rows),
        "csv_unique_id_candidate_count": len(csv_index),
        "xml_unique_id_candidate_count": len(xml_index),
        "csv_duplicate_id_candidates": csv_duplicates,
        "xml_duplicate_id_candidates": xml_duplicates,
        "csv_missing_id_candidate_count": csv_missing_ids,
        "xml_missing_id_candidate_count": xml_missing_ids,
        "shared_id_candidate_count": len(common),
        "csv_only_id_candidate_count": len(csv_only),
        "xml_only_id_candidate_count": len(xml_only),
        "required_field_aligned_count": required_aligned,
        "exact_surface_alignment_candidate_count": exact_aligned,
        "required_field_mismatch_candidate_count": required_mismatch,
        "supporting_field_mismatch_candidate_count": supporting_mismatch,
        "present_present_support_count": present_present_support_count,
        "present_present_support_match_count": present_present_support_match_count,
        "both_missing_support_count": both_missing_support_count,
        "one_missing_support_count": one_missing_support_count,
        "id_candidate_coverage_ratio": len(common) / denominator,
        "required_field_alignment_ratio": required_aligned / common_denominator if common else 0.0,
        "exact_surface_alignment_ratio": exact_aligned / common_denominator if common else 0.0,
        "csv_only_id_examples": csv_only[:20],
        "xml_only_id_examples": xml_only[:20],
        "mismatch_examples": mismatch_examples,
        "candidate_signature_collision_count": cross_id_collision_count,
        "xlsx_support": {
            "surface_count": len(xlsx_rows),
            "profiled_row_count": xlsx_profiled_rows,
            "formula_cell_count": xlsx_formula_cells,
            "source_dependency_status": "DERIVATION_DEPENDENCY_UNRESOLVED",
            "independent_confirmation_allowed": False,
            "aggregate_definition_truth": False,
        },
        "decision": decision,
        "reconciliation_status": decision,
        "field_semantics_version": field_semantics_version,
        "label_semantics_version": label_semantics_version,
        "active_match_evidence_pass": False,
        "hard_block_hits": hard_blocks,
        "parse_warnings": warnings,
        "validated_cross_format_equivalence": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_reconciliation(
    input_root: str | Path,
    inventory: dict[str, Any],
    csv_payload: dict[str, Any],
    xlsx_payload: dict[str, Any],
    xml_payload: dict[str, Any],
    field_semantics_payload: dict[str, Any],
    label_semantics_payload: dict[str, Any],
    xml_group_registry: dict[str, Any],
) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    hard_blocks, warnings = _upstream_guard(
        (
            inventory,
            csv_payload,
            xlsx_payload,
            xml_payload,
            field_semantics_payload,
            label_semantics_payload,
        )
    )
    if not root.is_dir():
        hard_blocks.append("input_root_missing")
    anchors = field_semantics_payload.get("required_anchor_audit") or {}
    for fmt in ("csv", "xml"):
        if not (anchors.get(fmt) or {}).get("ready_for_candidate_reconciliation"):
            hard_blocks.append(f"required_semantic_anchor_missing:{fmt}")
    if any(
        row.get("validated_equivalence") is True
        for row in field_semantics_payload.get("candidate_equivalence_groups", []) or []
    ):
        hard_blocks.append("unexpected_validated_equivalence_claim")
    if "id" in SIGNATURE_FIELDS_WITHOUT_ID:
        hard_blocks.append("candidate_signature_includes_identity_only")
    if not SIGNATURE_FIELDS_WITHOUT_ID:
        hard_blocks.append("cross_id_collision_check_disabled")
    hard_blocks.extend(_semantic_provenance_guard(label_semantics_payload))
    if any(
        row.get("independent_confirmation_allowed") is True
        for row in xlsx_payload.get("files", []) or []
    ) or xlsx_payload.get("independent_confirmation_allowed") is True:
        hard_blocks.append("derived_xlsx_surface_used_as_independent_confirmation")
    duplicate_report = inventory.get("duplicate_report")
    if not isinstance(duplicate_report, dict) or "exact_duplicate_reflection_count" not in duplicate_report:
        hard_blocks.append("upstream_duplicate_lineage_lost")

    try:
        xml_group_mapping = _load_xml_group_registry(xml_group_registry)
    except ValueError as exc:
        xml_group_mapping = {}
        hard_blocks.append(str(exc))

    source_binding_records, source_binding_blocks = _source_binding_audit(
        root,
        inventory,
        (
            ("csv", csv_payload),
            ("xlsx", xlsx_payload),
            ("xml", xml_payload),
        ),
    )
    hard_blocks.extend(source_binding_blocks)
    source_bindings = {
        (str(row.get("source_format")), str(row.get("source_relative_path"))): row
        for row in source_binding_records
    }
    field_semantics_version = str(
        field_semantics_payload.get("module_id") or "FIELD_SEMANTICS_VERSION_UNKNOWN"
    )
    label_semantics_version = str(
        label_semantics_payload.get("registry_version")
        or label_semantics_payload.get("module_id")
        or "LABEL_SEMANTICS_VERSION_UNKNOWN"
    )
    provider_semantic_records = _provider_semantic_provenance_records(
        label_semantics_payload,
        (
            ("csv", csv_payload),
            ("xlsx", xlsx_payload),
            ("xml", xml_payload),
        ),
    )

    csv_by_role, csv_reflections = _files_by_role(csv_payload)
    xml_by_role, xml_reflections = _files_by_role(xml_payload)
    xlsx_by_role, xlsx_reflections = _files_by_role(xlsx_payload)
    roles = sorted(set(csv_by_role) | set(xml_by_role), key=lambda role: (ROLE_ORDER.get(role, 99), role))
    pair_reports: list[dict[str, Any]] = []
    unpaired_roles: list[dict[str, Any]] = []

    if not hard_blocks:
        for role in roles:
            csv_rows = csv_by_role.get(role, [])
            xml_rows = xml_by_role.get(role, [])
            if len(csv_rows) != 1 or len(xml_rows) != 1:
                unpaired_roles.append(
                    {
                        "source_role": role,
                        "csv_surface_count": len(csv_rows),
                        "xml_surface_count": len(xml_rows),
                        "decision": "DOWNGRADE_TO_SINGLE_SURFACE" if csv_rows or xml_rows else "BLOCK_FUSION",
                    }
                )
                warnings.append(f"unpaired_or_ambiguous_surface_role:{role}")
                continue
            try:
                report = _role_pair(
                    role,
                    root,
                    csv_rows[0],
                    xml_rows[0],
                    xlsx_by_role.get(role, []),
                    xml_group_mapping,
                    source_bindings,
                    field_semantics_version,
                    label_semantics_version,
                )
            except ValueError as exc:
                hard_blocks.append(f"role_reconciliation_unreadable:{role}:{exc}")
                continue
            pair_reports.append(report)
            hard_blocks.extend(f"{role}:{value}" for value in report.get("hard_block_hits", []))
            warnings.extend(f"{role}:{value}" for value in report.get("parse_warnings", []))

    if not roles:
        hard_blocks.append("no_csv_or_xml_event_surface")
    if not pair_reports and not hard_blocks:
        hard_blocks.append("no_comparable_csv_xml_role_pair")

    hard_blocks = sorted(set(hard_blocks))
    warnings = sorted(set(warnings))
    if hard_blocks:
        status = "FAIL_CLOSED"
        fusion_admissibility = "BLOCKED"
    elif warnings:
        status = "REVIEW_REQUIRED"
        fusion_admissibility = "CANDIDATE_ONLY_WITH_WARNINGS"
    else:
        status = "PASS"
        fusion_admissibility = "CANDIDATE_ONLY"

    total_shared = sum(int(row.get("shared_id_candidate_count") or 0) for row in pair_reports)
    total_exact = sum(int(row.get("exact_surface_alignment_candidate_count") or 0) for row in pair_reports)
    total_required_mismatch = sum(int(row.get("required_field_mismatch_candidate_count") or 0) for row in pair_reports)
    total_unmatched = sum(
        int(row.get("csv_only_id_candidate_count") or 0) + int(row.get("xml_only_id_candidate_count") or 0)
        for row in pair_reports
    )
    total_present_present = sum(
        int(row.get("present_present_support_count") or 0) for row in pair_reports
    )
    total_both_missing = sum(
        int(row.get("both_missing_support_count") or 0) for row in pair_reports
    )
    total_cross_id_collisions = sum(
        int(row.get("cross_id_collision_count") or 0) for row in pair_reports
    )
    upstream_duplicate_reflection_count = int(
        (inventory.get("duplicate_report") or {}).get(
            "exact_duplicate_reflection_count"
        )
        or 0
    )
    for row in pair_reports:
        row["upstream_duplicate_reflection_count"] = upstream_duplicate_reflection_count
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "input_root": str(root),
        "pair_reports": pair_reports,
        "unpaired_roles": unpaired_roles,
        "role_pair_count": len(pair_reports),
        "duplicate_reflection_audit": {
            "upstream_duplicate_reflection_count": upstream_duplicate_reflection_count,
            "csv_duplicate_reflections_not_recounted": csv_reflections,
            "xml_duplicate_reflections_not_recounted": xml_reflections,
            "xlsx_duplicate_reflections_not_recounted": xlsx_reflections,
            "local_duplicate_candidate_count": sum(
                int(row.get("local_duplicate_candidate_count") or 0)
                for row in pair_reports
            ),
        },
        "source_binding_audit": source_binding_records,
        "provider_semantic_provenance_records": provider_semantic_records,
        "field_semantics_version": field_semantics_version,
        "label_semantics_version": label_semantics_version,
        "xml_group_semantics_registry_version": xml_group_registry.get("registry_id"),
        "reconciliation_totals": {
            "shared_id_candidate_count": total_shared,
            "exact_surface_alignment_candidate_count": total_exact,
            "required_field_mismatch_candidate_count": total_required_mismatch,
            "unmatched_id_candidate_count": total_unmatched,
            "present_present_support_count": total_present_present,
            "both_missing_support_count": total_both_missing,
            "cross_id_collision_count": total_cross_id_collisions,
        },
        "fusion_admissibility": fusion_admissibility,
        "hard_block_hits": hard_blocks,
        "parse_warnings": warnings,
        "active_match_evidence_pass": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "validated_cross_format_equivalence": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "aggregate_definition_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "does_not_measure": [
            "canonical_event_truth",
            "provider_independence_truth",
            "aggregate_definition_truth",
            "sequence_truth",
            "phase_truth",
            "tactical_truth",
        ],
        "analyst_evidence": {
            "provider_label_mapping_status_counts": label_semantics_payload.get(
                "mapping_status_counts"
            )
            or {},
            "exact_rule_label_examples": [
                row.get("raw_label")
                for row in label_semantics_payload.get("provider_label_records", []) or []
                if row.get("mapping_status")
                in {"EXACT_REVIEWED_CANDIDATE", "EXACT_ALIAS_CANDIDATE"}
            ][:20],
            "fallback_or_conflict_label_examples": [
                row.get("raw_label")
                for row in label_semantics_payload.get("provider_label_records", []) or []
                if row.get("mapping_status") in REVIEW_MAPPING_STATUSES
            ][:20],
            "non_independent_source_surfaces": sorted(
                {
                    str(row.get("source_relative_path"))
                    for row in provider_semantic_records
                    if row.get("derivation_dependency")
                    in {
                        "DERIVATION_DEPENDENCY_UNRESOLVED",
                        "SOURCE_INDEPENDENCE_NOT_ESTABLISHED",
                    }
                }
            ),
            "downstream_blocking_ambiguities": sorted(
                set(hard_blocks + warnings)
            ),
            "safe_statement": (
                "Visible provider-label surfaces were bound to semantic candidates; source lineage "
                "and cross-format surface alignment were recorded. This output does not establish "
                "canonical events, validated identity or tactical truth."
            )
        },
    }


def render_summary(payload: dict[str, Any]) -> str:
    totals = payload.get("reconciliation_totals") or {}
    return "\n".join(
        [
            "HPFA CROSS-FORMAT RECONCILIATION LITE V1",
            f"status={payload.get('status')}",
            f"module_status={payload.get('module_status')}",
            f"runtime_evidence_status={payload.get('runtime_evidence_status')}",
            f"release_status={payload.get('release_status')}",
            f"role_pair_count={payload.get('role_pair_count')}",
            f"shared_id_candidate_count={totals.get('shared_id_candidate_count')}",
            f"exact_surface_alignment_candidate_count={totals.get('exact_surface_alignment_candidate_count')}",
            f"required_field_mismatch_candidate_count={totals.get('required_field_mismatch_candidate_count')}",
            f"unmatched_id_candidate_count={totals.get('unmatched_id_candidate_count')}",
            f"present_present_support_count={totals.get('present_present_support_count')}",
            f"both_missing_support_count={totals.get('both_missing_support_count')}",
            f"cross_id_collision_count={totals.get('cross_id_collision_count')}",
            f"fusion_admissibility={payload.get('fusion_admissibility')}",
            f"hard_block_hits={payload.get('hard_block_hits')}",
            f"parse_warnings={payload.get('parse_warnings')}",
            f"active_match_evidence_pass={payload.get('active_match_evidence_pass')}",
            "validated_cross_format_equivalence=false",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "",
        ]
    )


def render_analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA CROSS-FORMAT RECONCILIATION ANALYST AUDIT V1",
        f"status={payload.get('status')}",
        f"module_status={payload.get('module_status')}",
        f"runtime_evidence_status={payload.get('runtime_evidence_status')}",
        f"release_status={payload.get('release_status')}",
        f"fusion_admissibility={payload.get('fusion_admissibility')}",
    ]
    for row in payload.get("pair_reports", []) or []:
        lines += [
            "",
            f"source_role={row.get('source_role')}",
            f"csv_surface={row.get('csv_relative_path')}",
            f"xml_surface={row.get('xml_relative_path')}",
            f"csv_rows={row.get('csv_profiled_row_count')}",
            f"xml_rows={row.get('xml_row_candidate_count')}",
            f"row_count_equal_signal={row.get('row_count_equal_signal')}",
            f"shared_id_candidates={row.get('shared_id_candidate_count')}",
            f"required_aligned={row.get('required_field_aligned_count')}",
            f"exact_surface_alignment_candidates={row.get('exact_surface_alignment_candidate_count')}",
            f"required_mismatches={row.get('required_field_mismatch_candidate_count')}",
            f"supporting_mismatches={row.get('supporting_field_mismatch_candidate_count')}",
            f"present_present_support={row.get('present_present_support_count')}",
            f"both_missing_support={row.get('both_missing_support_count')}",
            f"cross_id_collisions={row.get('cross_id_collision_count')}",
            f"audit_sha_match={row.get('audit_sha_match')}",
            f"csv_only_ids={row.get('csv_only_id_candidate_count')}",
            f"xml_only_ids={row.get('xml_only_id_candidate_count')}",
            f"decision={row.get('decision')}",
            f"xlsx_dependency_status={(row.get('xlsx_support') or {}).get('source_dependency_status')}",
        ]
    lines += [
        "",
        "validated_cross_format_equivalence=false",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "safe_statement=Visible provider-label surfaces were bound to semantic candidates; source lineage and cross-format alignment were recorded. This does not create canonical event, validated identity or tactical truth.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(
    input_root: str | Path,
    expected_runtime_authority: str | Path,
    inventory_path: str | Path,
    csv_path: str | Path,
    xlsx_path: str | Path,
    xml_path: str | Path,
    field_semantics_path: str | Path,
    label_semantics_path: str | Path,
    xml_group_registry_path: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    out = validate_out(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = build_reconciliation(
        input_root,
        load_json(inventory_path),
        load_json(csv_path),
        load_json(xlsx_path),
        load_json(xml_path),
        load_json(field_semantics_path),
        load_json(label_semantics_path),
        load_json(xml_group_registry_path),
    )
    input_resolved = Path(input_root).expanduser().resolve(strict=False)
    expected_resolved = (
        Path(expected_runtime_authority).expanduser().resolve(strict=False)
    )
    authority_equal = input_resolved == expected_resolved and is_active(expected_resolved)
    if not authority_equal:
        payload["hard_block_hits"] = sorted(
            set((payload.get("hard_block_hits") or []) + ["runtime_authority_mismatch"])
        )
        payload["status"] = "FAIL_CLOSED"
        payload["module_status"] = "FAIL_CLOSED"
        payload["fusion_admissibility"] = "BLOCKED"
    payload["active_match_evidence_pass"] = (
        payload.get("status") == "PASS"
        and not payload.get("hard_block_hits")
        and not payload.get("parse_warnings")
        and authority_equal
    )
    payload["runtime_evidence_status"] = (
        "ACTIVE_MATCH_EVIDENCE_PASS"
        if payload["active_match_evidence_pass"]
        else "ACTIVE_MATCH_EVIDENCE_NOT_GRANTED"
    )
    payload["release_status"] = "NOT_PRODUCTION"
    paths = {key: out / name for key, name in OUT.items()}
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    paths["main"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    paths["summary"].write_text(render_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(render_analyst(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--expected-runtime-authority", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--csv-audit", required=True)
    parser.add_argument("--xlsx-audit", required=True)
    parser.add_argument("--xml-audit", required=True)
    parser.add_argument("--field-semantics", required=True)
    parser.add_argument("--label-semantics", required=True)
    parser.add_argument("--xml-group-registry", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        payload = write_outputs(
            args.input_root,
            args.expected_runtime_authority,
            args.inventory,
            args.csv_audit,
            args.xlsx_audit,
            args.xml_audit,
            args.field_semantics,
            args.label_semantics,
            args.xml_group_registry,
            args.out,
        )
    except ValueError as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "hard_block_hits": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "role_pair_count",
                    "fusion_admissibility",
                    "hard_block_hits",
                    "parse_warnings",
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
