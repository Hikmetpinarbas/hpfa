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

MODULE_ID = "row_nucleus_inventory_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "ROW_NUCLEUS_SURFACE_CANDIDATE_ONLY"
REQUIRED = ("start", "end", "period", "action")
SUPPORT = ("code", "team", "pos_x", "pos_y")
SIG_FIELDS = (*REQUIRED, *SUPPORT)
EVENT_SOURCE_ROLES = {
    "GOALKEEPER_SURFACE_CANDIDATE",
    "PLAYER_SURFACE_CANDIDATE",
    "TEAM_SURFACE_CANDIDATE",
}
REVIEW_MAPPING_STATUSES = {
    "TOKEN_FALLBACK_REVIEW_REQUIRED",
    "CONFLICT_REVIEW_REQUIRED",
    "UNKNOWN_UNREVIEWED",
}
ADMIN_SEMANTIC_ROLES = {"PERIOD_OR_META", "MATCH_BOUNDARY", "ADMINISTRATIVE"}
OUT = {
    "main": "row_nucleus_inventory_lite_v1.json",
    "summary": "row_nucleus_inventory_lite_v1.txt",
    "analyst": "row_nucleus_inventory_analyst_audit_v1.txt",
    "rollup": "g01_g18_data_quality_rollup_v1.json",
    "rollup_txt": "g01_g18_data_quality_rollup_v1.txt",
}


def norm_text(value: Any) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "").strip()).casefold()
    return None if not text or text in {"none", "null", "nan", "n/a", "na", "-"} else text


def norm_num(value: Any) -> str | None:
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
    return "0" if normalized in {"", "-0"} else normalized


def norm_field(key: str, value: Any) -> str | None:
    return norm_num(value) if key in {"id", "start", "end", "period", "pos_x", "pos_y"} else norm_text(value)


def norm_header(value: Any) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold())).strip("_")


def norm_label(value: Any) -> str:
    text = str(value or "").casefold().replace("%", " percent ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                value.update(chunk)
    except OSError as exc:
        raise ValueError("runtime_source_unreadable") from exc
    return value.hexdigest()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("upstream_output_unreadable_or_malformed") from exc
    if not isinstance(value, dict):
        raise ValueError("upstream_output_not_object")
    return value


def upstream_guard(items: Iterable[tuple[str, dict[str, Any]]]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    for name, payload in items:
        if payload.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
            blocks.append(f"canonical_event_count_claimed:{name}")
        if payload.get("production_release") is True:
            blocks.append(f"unexpected_production_claim:{name}")
        status = str(payload.get("module_status") or payload.get("status") or "UNKNOWN")
        if status == "FAIL_CLOSED":
            blocks.append(f"upstream_fail_closed:{name}")
        elif status not in {"PASS", "REVIEW_REQUIRED", "SPEC_ONLY", "SMOKE_PASS"}:
            reviews.append(f"upstream_status_review:{name}:{status}")
        blocks.extend(f"upstream_hard_block:{name}:{item}" for item in payload.get("hard_block_hits", []) or [])
    return sorted(set(blocks)), sorted(set(reviews))


def runtime_path(root: Path, row: dict[str, Any]) -> Path:
    relative = str(row.get("relative_path") or row.get("file_name") or "")
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("surface_path_outside_active_match") from exc
    return candidate


def inventory_sha_index(inventory: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for row in inventory.get("files", []) or []:
        relative = str(row.get("relative_path") or row.get("file_name") or "")
        sha = row.get("sha256")
        if relative and valid_sha256(sha):
            result[relative].add(str(sha).casefold())
    return dict(result)


def source_binding(
    root: Path,
    row: dict[str, Any],
    source_format: str,
    inventory_index: dict[str, set[str]],
) -> tuple[dict[str, Any], list[str]]:
    relative = str(row.get("relative_path") or row.get("file_name") or "")
    audit_sha = row.get("sha256")
    inventory_shas = sorted(inventory_index.get(relative, set()))
    blocks: list[str] = []
    runtime_sha: str | None = None
    if not relative or not valid_sha256(audit_sha) or not inventory_shas:
        blocks.append(f"source_sha_missing:{source_format}:{relative or 'UNKNOWN'}")
    else:
        try:
            runtime_sha = sha256_file(runtime_path(root, row))
        except ValueError:
            blocks.append(f"runtime_sha_mismatch:{source_format}:{relative}")
        expected = str(audit_sha).casefold()
        if runtime_sha != expected or expected not in inventory_shas:
            blocks.append(f"runtime_sha_mismatch:{source_format}:{relative}")
    return (
        {
            "source_format": source_format,
            "source_role": row.get("source_role"),
            "source_relative_path": relative,
            "audit_sha256": str(audit_sha).casefold() if valid_sha256(audit_sha) else None,
            "inventory_sha256_candidates": inventory_shas,
            "runtime_rehashed_sha256": runtime_sha,
            "audit_sha_match": bool(
                runtime_sha
                and valid_sha256(audit_sha)
                and runtime_sha == str(audit_sha).casefold()
                and runtime_sha in inventory_shas
            ),
        },
        blocks,
    )


def csv_rows(root: Path, audit: dict[str, Any]) -> list[dict[str, Any]]:
    headers = [str(item) for item in audit.get("raw_columns", []) or []]
    delimiter = audit.get("delimiter_candidate")
    if not headers or not delimiter:
        raise ValueError("csv_parse_contract_missing")
    try:
        text = runtime_path(root, audit).read_text(encoding=str(audit.get("encoding_candidate") or "utf-8"))
        parsed = list(csv.reader(io.StringIO(text, newline=""), delimiter=str(delimiter)))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError("csv_surface_unreadable_or_malformed") from exc
    normalized = [norm_header(item) for item in headers]
    header_index = next(
        (index for index, row in enumerate(parsed) if [norm_header(item) for item in row] == normalized),
        None,
    )
    if header_index is None:
        raise ValueError("csv_header_contract_mismatch")
    positions = {name: index for index, name in enumerate(normalized) if name}
    bundle = audit.get("field_bundle") or {}

    def index_for(key: str, fallback: str | None = None) -> int | None:
        raw = bundle.get(key)
        normalized_raw = norm_header(raw) if raw is not None else None
        if normalized_raw and normalized_raw in positions:
            return positions[normalized_raw]
        return positions.get(fallback or key)

    indexes = {
        "id": positions.get("id"),
        "start": index_for("start"),
        "end": index_for("end"),
        "period": index_for("period", "half"),
        "action": index_for("action"),
        "code": positions.get("code"),
        "team": index_for("team"),
        "pos_x": index_for("start_x", "pos_x"),
        "pos_y": index_for("start_y", "pos_y"),
    }
    if any(indexes[key] is None for key in ("id", *REQUIRED)):
        raise ValueError("csv_required_nucleus_field_missing")
    result: list[dict[str, Any]] = []
    for row in parsed[header_index + 1 :]:
        if len(row) != len(headers) or not any(str(item).strip() for item in row):
            continue
        if [norm_header(item) for item in row] == normalized:
            continue

        def value(key: str) -> str | None:
            index = indexes[key]
            return str(row[index]).strip() if index is not None else None

        action = value("action")
        code = value("code")
        team = value("team")
        if not team and code and action and code.endswith(f" - {action}"):
            team = code[: -len(f" - {action}")].strip() or None
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


def local_name(tag: Any) -> str:
    return str(tag).rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def descendant(elem: ET.Element, name: str) -> str | None:
    for node in elem.iter():
        if local_name(node.tag).casefold() == name.casefold() and str(node.text or "").strip():
            return str(node.text).strip()
    return None


def group_map(payload: dict[str, Any]) -> dict[str, str]:
    if payload.get("candidate_only") is not True or payload.get("validated_semantics") is not False:
        raise ValueError("xml_group_registry_not_candidate_only")
    result: dict[str, str] = {}
    for row in payload.get("exact_group_rules", []) or []:
        raw = norm_text(row.get("raw_group_label"))
        key = str(row.get("field_key_candidate") or "")
        if not raw or not key or not row.get("rule_id") or not row.get("source_ref"):
            raise ValueError("xml_group_registry_rule_incomplete")
        if raw in result and result[raw] != key:
            raise ValueError("xml_group_registry_conflict")
        result[raw] = key
    if not {"action", "period", "team", "pos_x", "pos_y"}.issubset(set(result.values())):
        raise ValueError("xml_group_registry_incomplete")
    return result


def xml_rows(root: Path, audit: dict[str, Any], mapping: dict[str, str]) -> list[dict[str, Any]]:
    guard = audit.get("security_guard") or {}
    if guard.get("status") != "PASS" or guard.get("dtd_or_entity_declaration_present") is True:
        raise ValueError("xml_security_contract_not_pass")
    selected = str(audit.get("selected_row_tag_candidate") or "")
    if not selected:
        raise ValueError("xml_row_container_candidate_missing")
    try:
        tree = ET.parse(runtime_path(root, audit)).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError("xml_surface_unreadable_or_malformed") from exc
    result: list[dict[str, Any]] = []
    for elem in tree.iter():
        if local_name(elem.tag) != selected:
            continue
        labels: dict[str, list[str]] = defaultdict(list)
        for label in elem.iter():
            if local_name(label.tag).casefold() != "label":
                continue
            group = descendant(label, "group")
            text = descendant(label, "text")
            key = mapping.get(norm_text(group) or "") if group and text else None
            if key:
                labels[key].append(text)

        def one(key: str) -> str | None:
            values = list(dict.fromkeys(labels.get(key, [])))
            return values[0] if len(values) == 1 else None

        action = one("action")
        code = descendant(elem, "code")
        team = one("team")
        if not team and code and action and code.endswith(f" - {action}"):
            team = code[: -len(f" - {action}")].strip() or None
        raw = {
            "id": descendant(elem, "ID"),
            "start": descendant(elem, "start"),
            "end": descendant(elem, "end"),
            "period": one("period"),
            "action": action,
            "code": code,
            "team": team,
            "pos_x": one("pos_x"),
            "pos_y": one("pos_y"),
        }
        result.append({key: norm_field(key, item) for key, item in raw.items()})
    return result


def unique_files(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for row in payload.get("files", []) or []:
        role = str(row.get("source_role") or "UNKNOWN")
        key = (role, str(row.get("sha256") or row.get("relative_path") or ""))
        if key in seen:
            continue
        seen.add(key)
        grouped[role].append(row)
    return dict(grouped)


def indexed(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int], int]:
    counts = Counter(str(row.get("id")) for row in rows if row.get("id") is not None)
    duplicates = {key: count for key, count in counts.items() if count > 1}
    values = {
        str(row["id"]): row
        for row in rows
        if row.get("id") is not None and counts[str(row["id"])] == 1
    }
    missing = sum(row.get("id") is None for row in rows)
    return values, duplicates, missing


def semantic_index(payload: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    result: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("provider_label_records", []) or []:
        key = (
            str(row.get("source_role") or "UNKNOWN"),
            norm_label(row.get("raw_label") or row.get("normalized_label")),
        )
        if key[1]:
            result[key].append(row)
    return dict(result)


def gate(gate_id: str, status: str, message: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"gate_id": gate_id, "status": status, "message": message, "evidence": evidence or {}}


def semantic_clearance(records: list[dict[str, Any]]) -> tuple[bool, list[str], list[str], list[str], list[str]]:
    statuses = sorted({str(row.get("mapping_status") or "UNKNOWN") for row in records})
    roles = sorted(
        {
            str(row.get("semantic_role_candidate"))
            for row in records
            if row.get("semantic_role_candidate")
        }
    )
    families = sorted(
        {
            str(row.get("action_family_candidate"))
            for row in records
            if row.get("action_family_candidate")
        }
    )
    eligibilities = sorted(
        {
            str(row.get("downstream_eligibility"))
            for row in records
            if row.get("downstream_eligibility")
        }
    )
    is_admin = (
        bool(roles)
        and set(roles).issubset(ADMIN_SEMANTIC_ROLES)
        and (not eligibilities or set(eligibilities) <= {"ADMIN_ONLY"})
    )
    cleared = (
        bool(records)
        and not any(status in REVIEW_MAPPING_STATUSES for status in statuses)
        and (len(families) == 1 or is_admin)
    )
    return cleared, statuses, roles, families, eligibilities


def build_inventory(
    root_path: str | Path,
    inventory: dict[str, Any],
    csv_payload: dict[str, Any],
    xml_payload: dict[str, Any],
    field_payload: dict[str, Any],
    label_payload: dict[str, Any],
    reconciliation: dict[str, Any],
    aggregate: dict[str, Any],
    dictionary: dict[str, Any],
    xml_registry: dict[str, Any],
) -> dict[str, Any]:
    root = Path(root_path).expanduser().resolve(strict=False)
    blocks, reviews = upstream_guard(
        [
            ("inventory", inventory),
            ("csv", csv_payload),
            ("xml", xml_payload),
            ("field_semantics", field_payload),
            ("label_semantics", label_payload),
            ("reconciliation", reconciliation),
            ("aggregate_alignment", aggregate),
            ("metric_dictionary", dictionary),
        ]
    )
    if not root.is_dir():
        blocks.append("input_root_missing")
    if not root.as_posix().rstrip("/").endswith("runtime/active_single_match/current"):
        blocks.append("runtime_authority_path_invalid")
    if reconciliation.get("module_id") != "cross_format_reconciliation_lite_v1":
        blocks.append("reconciliation_contract_mismatch")
    if label_payload.get("module_id") != "provider_label_value_semantics_lite_v1":
        blocks.append("label_semantics_contract_mismatch")
    if dictionary.get("module_id") != "provider_metric_dictionary_lite_v1":
        blocks.append("metric_dictionary_contract_mismatch")
    if (inventory.get("duplicate_report") or {}).get("exact_duplicate_reflection_count") is None:
        blocks.append("duplicate_reflection_lineage_missing")
    try:
        mapping = group_map(xml_registry)
    except ValueError as exc:
        mapping = {}
        blocks.append(str(exc))

    nuclei: list[dict[str, Any]] = []
    role_audits: list[dict[str, Any]] = []
    source_binding_audit: list[dict[str, Any]] = []
    semantics = semantic_index(label_payload)
    csv_roles = unique_files(csv_payload)
    xml_roles = unique_files(xml_payload)
    roles = sorted(set(csv_roles) | set(xml_roles))
    reference_roles = sorted(role for role in roles if role not in EVENT_SOURCE_ROLES)
    if reference_roles:
        blocks.extend(f"reference_or_unknown_source_role_rejected:{role}" for role in reference_roles)
    inv_index = inventory_sha_index(inventory)

    if not blocks:
        for role in roles:
            if len(csv_roles.get(role, [])) != 1 or len(xml_roles.get(role, [])) != 1:
                reviews.append(f"unpaired_or_ambiguous_role:{role}")
                continue
            csv_file = csv_roles[role][0]
            xml_file = xml_roles[role][0]
            csv_binding, csv_binding_blocks = source_binding(root, csv_file, "csv", inv_index)
            xml_binding, xml_binding_blocks = source_binding(root, xml_file, "xml", inv_index)
            source_binding_audit.extend([csv_binding, xml_binding])
            blocks.extend(csv_binding_blocks + xml_binding_blocks)
            if csv_binding_blocks or xml_binding_blocks:
                continue
            try:
                csv_records = csv_rows(root, csv_file)
                xml_records = xml_rows(root, xml_file, mapping)
            except ValueError as exc:
                blocks.append(f"row_surface_unreadable:{role}:{exc}")
                continue
            csv_index, csv_duplicates, csv_missing = indexed(csv_records)
            xml_index, xml_duplicates, xml_missing = indexed(xml_records)
            if csv_duplicates or xml_duplicates:
                blocks.append(f"duplicate_provider_row_id_candidate:{role}")
            if csv_missing or xml_missing:
                blocks.append(f"missing_provider_row_id_candidate:{role}")
            role_records: list[dict[str, Any]] = []
            signatures: dict[str, list[str]] = defaultdict(list)
            for row_id in sorted(set(csv_index) | set(xml_index), key=lambda value: (len(value), value)):
                csv_row = csv_index.get(row_id)
                xml_row = xml_index.get(row_id)
                representative = csv_row or xml_row or {}
                required_bad = [
                    field
                    for field in REQUIRED
                    if csv_row is None
                    or xml_row is None
                    or csv_row.get(field) is None
                    or csv_row.get(field) != xml_row.get(field)
                ]
                support_bad = [
                    field
                    for field in SUPPORT
                    if csv_row is not None
                    and xml_row is not None
                    and (csv_row.get(field) is not None or xml_row.get(field) is not None)
                    and csv_row.get(field) != xml_row.get(field)
                ]
                present_present = [
                    field
                    for field in SUPPORT
                    if csv_row is not None
                    and xml_row is not None
                    and csv_row.get(field) is not None
                    and csv_row.get(field) == xml_row.get(field)
                ]
                both_missing = [
                    field
                    for field in SUPPORT
                    if csv_row is not None
                    and xml_row is not None
                    and csv_row.get(field) is None
                    and xml_row.get(field) is None
                ]
                one_missing = [
                    field
                    for field in SUPPORT
                    if csv_row is not None
                    and xml_row is not None
                    and ((csv_row.get(field) is None) != (xml_row.get(field) is None))
                ]
                signature_without_id = digest(*(representative.get(field) for field in SIG_FIELDS))
                signature_with_id = digest(row_id, *(representative.get(field) for field in SIG_FIELDS))
                signatures[signature_without_id].append(row_id)
                semantic_records = semantics.get((role, norm_label(representative.get("action"))), [])
                (
                    semantic_is_clear,
                    mapping_statuses,
                    semantic_roles,
                    families,
                    downstream_eligibilities,
                ) = semantic_clearance(semantic_records)
                reasons: list[str] = []
                if csv_row is None or xml_row is None:
                    reasons.append("one_sided_visible_surface")
                if required_bad:
                    reasons.append("required_field_mismatch")
                if support_bad or one_missing:
                    reasons.append("supporting_field_mismatch_or_one_missing")
                if not semantic_is_clear:
                    reasons.append("semantic_mapping_not_cleared")
                if required_bad or support_bad or one_missing or csv_row is None or xml_row is None:
                    support_status = "REVIEW_REQUIRED_SURFACE_SUPPORT"
                elif both_missing:
                    support_status = "CSV_XML_REQUIRED_ALIGNED_PARTIAL_SUPPORT"
                else:
                    support_status = "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT"
                role_records.append(
                    {
                        "nucleus_id": "rn_"
                        + digest(
                            role,
                            row_id,
                            signature_with_id,
                            csv_file.get("sha256"),
                            xml_file.get("sha256"),
                        )[:24],
                        "source_role": role,
                        "provider_row_id_candidate": row_id,
                        "source_relative_paths": [
                            csv_binding["source_relative_path"],
                            xml_binding["source_relative_path"],
                        ],
                        "source_sha256_lineage": [
                            csv_binding["audit_sha256"],
                            xml_binding["audit_sha256"],
                        ],
                        "runtime_rehashed_sha256": {
                            "csv": csv_binding["runtime_rehashed_sha256"],
                            "xml": xml_binding["runtime_rehashed_sha256"],
                        },
                        "csv_surface_ref": bool(csv_row),
                        "xml_surface_ref": bool(xml_row),
                        "candidate_signature_without_id": signature_without_id,
                        "candidate_signature_with_id": signature_with_id,
                        "start_candidate": representative.get("start"),
                        "end_candidate": representative.get("end"),
                        "period_candidate": representative.get("period"),
                        "action_raw": representative.get("action"),
                        "code_raw": representative.get("code"),
                        "team_raw_candidate": representative.get("team"),
                        "pos_x_candidate": representative.get("pos_x"),
                        "pos_y_candidate": representative.get("pos_y"),
                        "semantic_role_candidates": semantic_roles,
                        "action_family_candidates": families,
                        "outcome_candidates": sorted(
                            {
                                str(row.get("outcome_candidate"))
                                for row in semantic_records
                                if row.get("outcome_candidate")
                            }
                        ),
                        "downstream_eligibility_candidates": downstream_eligibilities,
                        "mapping_statuses": mapping_statuses,
                        "mapping_rule_ids": sorted(
                            {
                                str(row.get("rule_id"))
                                for row in semantic_records
                                if row.get("rule_id")
                            }
                        ),
                        "cross_format_support_status": support_status,
                        "present_present_support_fields": present_present,
                        "both_missing_support_fields": both_missing,
                        "one_missing_support_fields": one_missing,
                        "required_mismatch_fields": required_bad,
                        "supporting_mismatch_fields": support_bad,
                        "cross_id_collision_status": "NOT_EVALUATED",
                        "duplicate_reflection_status": "LINEAGE_PRESERVED_NOT_RECOUNTED",
                        "aggregate_definition_dependency": "DERIVATION_DEPENDENCY_UNRESOLVED",
                        "ambiguity_reasons": sorted(set(reasons)),
                        "hard_block_hits": [],
                        "review_hits": sorted(set(reasons)),
                        "nucleus_status": "REVIEW_REQUIRED" if reasons else "PASS",
                        "validated_event_identity": False,
                        "canonical_event_count": CANONICAL_EVENT_COUNT,
                        "claim_ceiling": CLAIM_CEILING,
                    }
                )
            collisions = {signature: ids for signature, ids in signatures.items() if len(ids) > 1}
            for record in role_records:
                if record["candidate_signature_without_id"] in collisions:
                    record["cross_id_collision_status"] = "CROSS_ID_COLLISION_CANDIDATE"
                    record["review_hits"] = sorted(
                        set(record["review_hits"] + ["cross_id_signature_collision_candidate"])
                    )
                    record["ambiguity_reasons"] = record["review_hits"]
                    record["nucleus_status"] = "REVIEW_REQUIRED"
                else:
                    record["cross_id_collision_status"] = "NO_COLLISION_OBSERVED"
            nuclei.extend(role_records)
            role_audits.append(
                {
                    "source_role": role,
                    "csv_row_candidate_count": len(csv_records),
                    "xml_row_candidate_count": len(xml_records),
                    "nucleus_candidate_count": len(role_records),
                    "cross_id_collision_candidate_count": sum(
                        len(ids) - 1 for ids in collisions.values()
                    ),
                    "review_required_nucleus_count": sum(
                        record["nucleus_status"] == "REVIEW_REQUIRED" for record in role_records
                    ),
                    "source_sha_binding_pass": (
                        csv_binding["audit_sha_match"] and xml_binding["audit_sha_match"]
                    ),
                }
            )

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    review_count = sum(record.get("nucleus_status") == "REVIEW_REQUIRED" for record in nuclei)
    semantic_review_count = sum(
        "semantic_mapping_not_cleared" in (record.get("review_hits") or [])
        for record in nuclei
    )
    collision_count = sum(
        record.get("cross_id_collision_status") == "CROSS_ID_COLLISION_CANDIDATE"
        for record in nuclei
    )
    coordinate_missing_count = sum(
        record.get("pos_x_candidate") is None or record.get("pos_y_candidate") is None
        for record in nuclei
    )
    surface_review_count = sum(
        record.get("cross_format_support_status") == "REVIEW_REQUIRED_SURFACE_SUPPORT"
        for record in nuclei
    )
    reflection_count = int(
        (inventory.get("duplicate_report") or {}).get("exact_duplicate_reflection_count") or 0
    )
    binding_failures = [row for row in source_binding_audit if not row.get("audit_sha_match")]
    gates = [
        gate(
            "G01",
            "FAIL_CLOSED" if blocks else "PASS",
            "Upstream contracts checked.",
            {"hard_block_hits": blocks},
        ),
        gate(
            "G02",
            "FAIL_CLOSED"
            if "runtime_authority_path_invalid" in blocks
            or binding_failures
            or any(
                "runtime_sha_mismatch" in block or "source_sha_missing" in block
                for block in blocks
            )
            else "PASS",
            "Runtime authority and SHA binding checked.",
            {
                "input_root": str(root),
                "source_binding_record_count": len(source_binding_audit),
                "binding_failure_count": len(binding_failures),
            },
        ),
        gate(
            "G03",
            "FAIL_CLOSED" if reference_roles else "PASS",
            "Source-role and reference separation checked.",
            {"source_roles": roles, "rejected_roles": reference_roles},
        ),
        gate(
            "G04",
            "FAIL_CLOSED" if any("contract_mismatch" in block for block in blocks) else "PASS",
            "Field and label semantics dependencies checked.",
        ),
        gate(
            "G05",
            "FAIL_CLOSED"
            if any("required_nucleus_field_missing" in block for block in blocks)
            else "PASS",
            "Required row fields checked.",
        ),
        gate(
            "G06",
            "REVIEW_REQUIRED"
            if any(
                "required_field_mismatch" in (record.get("review_hits") or [])
                for record in nuclei
            )
            else "PASS",
            "Temporal surface checked.",
        ),
        gate(
            "G07",
            "REVIEW_REQUIRED" if coordinate_missing_count else "PASS",
            "Coordinate surface checked.",
            {"coordinate_missing_nucleus_count": coordinate_missing_count},
        ),
        gate(
            "G08",
            "FAIL_CLOSED"
            if any("provider_row_id_candidate" in block for block in blocks)
            else "PASS",
            "Provider row-id surface checked.",
        ),
        gate(
            "G09",
            "REVIEW_REQUIRED" if surface_review_count else "PASS",
            "Same-role reconciliation checked.",
            {"surface_review_nucleus_count": surface_review_count},
        ),
        gate(
            "G10",
            "PASS",
            "Duplicate reflections remain lineage.",
            {"exact_duplicate_reflection_count": reflection_count},
        ),
        gate(
            "G11",
            "REVIEW_REQUIRED" if collision_count else "PASS",
            "Cross-ID collisions checked.",
            {"collision_nucleus_count": collision_count},
        ),
        gate(
            "G12",
            "REVIEW_REQUIRED" if semantic_review_count else "PASS",
            "Label semantic readiness checked.",
            {"semantic_review_nucleus_count": semantic_review_count},
        ),
        gate(
            "G13",
            "REVIEW_REQUIRED" if semantic_review_count else "PASS",
            "Action-family or administrative semantic routing checked.",
        ),
        gate("G14", "PASS", "Identity remains candidate-only."),
        gate("G15", "PASS", "Missing and zero remain distinct."),
        gate(
            "G16",
            "REVIEW_REQUIRED" if aggregate.get("definition_alignment_cleared") is not True else "PASS",
            "Aggregate derivation dependency checked.",
        ),
        gate("G17", "PASS", "Claim layer remains closed.", {"claim_allowed": False}),
        gate(
            "G18",
            "PASS",
            "Traceability and release invariants preserved.",
            {"canonical_event_count": CANONICAL_EVENT_COUNT, "production_release": False},
        ),
    ]
    gate_states = [row["status"] for row in gates]
    rollup_status = (
        "FAIL_CLOSED"
        if "FAIL_CLOSED" in gate_states
        else ("REVIEW_REQUIRED" if "REVIEW_REQUIRED" in gate_states else "PASS")
    )
    status = (
        "FAIL_CLOSED"
        if blocks
        else (
            "REVIEW_REQUIRED"
            if reviews or review_count or rollup_status == "REVIEW_REQUIRED"
            else "PASS"
        )
    )
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "input_root": str(root),
        "source_binding_audit": source_binding_audit,
        "row_nuclei": nuclei,
        "row_nucleus_candidate_count": len(nuclei),
        "row_nucleus_pass_count": sum(
            record["nucleus_status"] == "PASS" for record in nuclei
        ),
        "row_nucleus_review_required_count": review_count,
        "source_role_count": len(role_audits),
        "role_audits": role_audits,
        "g01_g18_rollup": {
            "status": rollup_status,
            "gates": gates,
            "pass_count": gate_states.count("PASS"),
            "review_required_count": gate_states.count("REVIEW_REQUIRED"),
            "fail_closed_count": gate_states.count("FAIL_CLOSED"),
            "not_applicable_count": gate_states.count("NOT_APPLICABLE"),
        },
        "duplicate_reflection_count": reflection_count,
        "cross_id_collision_nucleus_count": collision_count,
        "semantic_review_nucleus_count": semantic_review_count,
        "surface_review_nucleus_count": surface_review_count,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "active_match_evidence_pass": False,
        "row_nucleus_is_canonical_event": False,
        "base_event_admission_allowed": False,
        "validated_event_identity": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_cross_role_equivalence": False,
        "aggregate_definition_truth": False,
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "analyst_evidence": {
            "safe_statement": (
                "Visible same-role CSV/XML row candidates were assembled into row-nucleus "
                "candidates with runtime SHA lineage, cross-format support and semantic-review "
                "status. They are not canonical events, validated identities or tactical truth."
            )
        },
    }


def render_summary(payload: dict[str, Any]) -> str:
    rollup = payload.get("g01_g18_rollup") or {}
    return "\n".join(
        [
            "HPFA ROW NUCLEUS INVENTORY LITE V1",
            f"status={payload.get('status')}",
            f"row_nucleus_candidate_count={payload.get('row_nucleus_candidate_count')}",
            f"row_nucleus_review_required_count={payload.get('row_nucleus_review_required_count')}",
            f"source_binding_record_count={len(payload.get('source_binding_audit') or [])}",
            f"g01_g18_status={rollup.get('status')}",
            f"hard_block_hits={payload.get('hard_block_hits')}",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "",
        ]
    )


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> None:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    rollup = payload.get("g01_g18_rollup") or {}
    (output / OUT["main"]).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / OUT["summary"]).write_text(render_summary(payload), encoding="utf-8")
    (output / OUT["analyst"]).write_text(
        (payload.get("analyst_evidence") or {}).get("safe_statement", "")
        + "\ncanonical_event_count=UNKNOWN\nproduction_release=false\n",
        encoding="utf-8",
    )
    (output / OUT["rollup"]).write_text(
        json.dumps(rollup, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / OUT["rollup_txt"]).write_text(
        "\n".join(
            [
                "HPFA G01-G18 DATA QUALITY ROLLUP V1",
                f"status={rollup.get('status')}",
                *(
                    f"{row.get('gate_id')}={row.get('status')}"
                    for row in rollup.get("gates", []) or []
                ),
                "canonical_event_count=UNKNOWN",
                "production_release=false",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "input-root",
        "inventory",
        "csv-audit",
        "xml-audit",
        "field-semantics",
        "label-semantics",
        "reconciliation",
        "aggregate-alignment",
        "metric-dictionary",
        "xml-group-registry",
        "out",
    ):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args()
    payload = build_inventory(
        args.input_root,
        load_json(args.inventory),
        load_json(args.csv_audit),
        load_json(args.xml_audit),
        load_json(args.field_semantics),
        load_json(args.label_semantics),
        load_json(args.reconciliation),
        load_json(args.aggregate_alignment),
        load_json(args.metric_dictionary),
        load_json(args.xml_group_registry),
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "row_nucleus_candidate_count",
                    "row_nucleus_review_required_count",
                    "cross_id_collision_nucleus_count",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
