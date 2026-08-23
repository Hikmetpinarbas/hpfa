from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "provider_alias_field_semantics_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "FIELD_SEMANTICS_CANDIDATE_ONLY"
OUT = {
    "main": "provider_alias_field_semantics_lite_v1.json",
    "summary": "provider_alias_field_semantics_lite_v1.txt",
    "analyst": "provider_alias_field_semantics_analyst_audit_v1.txt",
}

EXACT_RULES: dict[tuple[str, str], tuple[str, str, str, str]] = {
    ("csv", "id"): ("event", "surface.row_id_candidate", "MEDIUM", "pafs_csv_001"),
    ("csv", "start"): ("time", "event.start_time_candidate", "HIGH", "pafs_csv_002"),
    ("csv", "end"): ("time", "event.end_time_candidate", "HIGH", "pafs_csv_003"),
    ("csv", "code"): ("support", "event.provider_code_candidate", "MEDIUM", "pafs_csv_004"),
    ("csv", "team"): ("actor", "event.team_candidate", "MEDIUM", "pafs_csv_005"),
    ("csv", "action"): ("action", "event.action_label_candidate", "HIGH", "pafs_csv_006"),
    ("csv", "half"): ("time", "event.period_candidate", "HIGH", "pafs_csv_007"),
    ("csv", "pos_x"): ("space", "event.start_x_candidate", "HIGH", "pafs_csv_008"),
    ("csv", "pos_y"): ("space", "event.start_y_candidate", "HIGH", "pafs_csv_009"),
    ("xml", "instance_id"): ("event", "surface.row_id_candidate", "MEDIUM", "pafs_xml_001"),
    ("xml", "instance_start"): ("time", "event.start_time_candidate", "HIGH", "pafs_xml_002"),
    ("xml", "instance_end"): ("time", "event.end_time_candidate", "HIGH", "pafs_xml_003"),
    ("xml", "instance_code"): ("support", "event.provider_code_candidate", "MEDIUM", "pafs_xml_004"),
    ("xml", "instance_label_group"): ("action", "event.action_group_candidate", "MEDIUM", "pafs_xml_005"),
    ("xml", "instance_label_text"): ("action", "event.action_label_candidate", "HIGH", "pafs_xml_006"),
}

REQUIRED_ANCHORS = {
    "csv": {"event.start_time_candidate", "event.end_time_candidate", "event.action_label_candidate", "event.period_candidate"},
    "xml": {"event.start_time_candidate", "event.end_time_candidate", "event.action_label_candidate"},
}


def norm(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = text.replace("%", " percent ")
    text = re.sub(r"\[\s*([^\]]+)\s*\]", r" \1 ", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


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


def _record(*, fmt: str, source_role: str, relative_path: str, raw_field: str, upstream: dict[str, Any]) -> dict[str, Any]:
    normalized = norm(raw_field)
    rule = EXACT_RULES.get((fmt, normalized))
    if rule:
        family, key, reliability, rule_id = rule
        status = "EXACT_RULE_CANDIDATE"
    elif fmt == "xlsx":
        role = upstream.get("identity_role_candidate")
        if role:
            family, key, reliability, rule_id = (
                "actor" if role in {"player", "team"} else "context",
                f"aggregate.{role}_candidate",
                "MEDIUM",
                f"pafs_xlsx_identity_{role}",
            )
            status = "UPSTREAM_IDENTITY_ROLE_CANDIDATE"
        else:
            family, key, reliability, rule_id = (
                "metric",
                "aggregate.metric_label_candidate",
                "LOW",
                "pafs_xlsx_metric_surface",
            )
            status = "AGGREGATE_METRIC_SURFACE_CANDIDATE"
    else:
        family = str(upstream.get("semantic_family_candidate") or upstream.get("semantic_role_candidate") or "unknown")
        key = upstream.get("canonical_key_candidate")
        reliability = "LOW" if key else "UNKNOWN"
        rule_id = "upstream_candidate_only" if key else None
        status = "UPSTREAM_CANDIDATE" if key else "UNKNOWN_PRESERVED"
    return {
        "format": fmt,
        "source_role": source_role,
        "relative_path": relative_path,
        "raw_field": raw_field,
        "normalized_field": normalized,
        "semantic_family_candidate": family,
        "canonical_key_candidate": key,
        "mapping_status": status,
        "alias_reliability": reliability,
        "rule_id": rule_id,
        "upstream_evidence": {
            "inferred_type": upstream.get("inferred_type"),
            "example_values": upstream.get("example_values", [])[:5],
            "row_coverage_ratio": upstream.get("row_coverage_ratio"),
            "percent_header_candidate": upstream.get("percent_header_candidate"),
            "identity_role_candidate": upstream.get("identity_role_candidate"),
        },
        "validated_semantics": False,
        "validated_identity": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def csv_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for file_row in payload.get("files", []) or []:
        for profile in file_row.get("column_profiles", []) or []:
            records.append(_record(fmt="csv", source_role=str(file_row.get("source_role") or "UNKNOWN"), relative_path=str(file_row.get("relative_path") or file_row.get("file_name") or ""), raw_field=str(profile.get("raw_column") or ""), upstream=profile))
    return records


def xlsx_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for file_row in payload.get("files", []) or []:
        for sheet in file_row.get("sheets", []) or []:
            for profile in sheet.get("column_profiles", []) or []:
                records.append(_record(fmt="xlsx", source_role=str(sheet.get("source_role") or file_row.get("source_role") or "UNKNOWN"), relative_path=str(file_row.get("relative_path") or file_row.get("file_name") or ""), raw_field=str(profile.get("raw_column") or ""), upstream=profile))
    return records


def xml_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for file_row in payload.get("files", []) or []:
        for field in file_row.get("field_inventory", []) or []:
            records.append(_record(fmt="xml", source_role=str(file_row.get("source_role") or "UNKNOWN"), relative_path=str(file_row.get("relative_path") or file_row.get("file_name") or ""), raw_field=str(field.get("raw_field_path") or ""), upstream=field))
    return records


def _upstream_status(payloads: Iterable[dict[str, Any]]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    warnings: list[str] = []
    for payload in payloads:
        module = str(payload.get("module_id") or "UNKNOWN")
        status = str(payload.get("status") or "UNKNOWN")
        if payload.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
            blocks.append(f"canonical_event_count_claimed:{module}")
        if status == "FAIL_CLOSED":
            blocks.append(f"upstream_fail_closed:{module}")
        elif status != "PASS":
            warnings.append(f"upstream_not_pass:{module}:{status}")
        for block in payload.get("hard_block_hits", []) or []:
            blocks.append(f"upstream_hard_block:{module}:{block}")
    return sorted(set(blocks)), sorted(set(warnings))


def _coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_format: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_format[row["format"]].append(row)
    result: dict[str, Any] = {}
    for fmt in ("csv", "xlsx", "xml"):
        rows = by_format.get(fmt, [])
        mapped = [row for row in rows if row.get("canonical_key_candidate")]
        exact = [row for row in rows if row.get("mapping_status") == "EXACT_RULE_CANDIDATE"]
        result[fmt] = {
            "field_count": len(rows),
            "candidate_mapped_count": len(mapped),
            "exact_rule_count": len(exact),
            "unknown_preserved_count": sum(1 for row in rows if row.get("mapping_status") == "UNKNOWN_PRESERVED"),
            "coverage_ratio": len(mapped) / len(rows) if rows else 0.0,
        }
    return result


def _anchor_audit(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_format: dict[str, set[str]] = defaultdict(set)
    for row in records:
        key = row.get("canonical_key_candidate")
        if key:
            by_format[row["format"]].add(str(key))
    result: dict[str, Any] = {}
    for fmt, required in REQUIRED_ANCHORS.items():
        present = by_format.get(fmt, set())
        missing = sorted(required - present)
        result[fmt] = {"required": sorted(required), "present": sorted(required & present), "missing": missing, "ready_for_candidate_reconciliation": not missing}
    return result


def _equivalence_groups(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        key = row.get("canonical_key_candidate")
        if key:
            grouped[str(key)].append(row)
    result: list[dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        formats = sorted({row["format"] for row in rows})
        result.append({
            "canonical_key_candidate": key,
            "formats": formats,
            "members": [{"format": row["format"], "relative_path": row["relative_path"], "raw_field": row["raw_field"], "rule_id": row.get("rule_id")} for row in rows],
            "cross_format_candidate": len(formats) > 1,
            "validated_equivalence": False,
        })
    return result


def build_semantics(csv_payload: dict[str, Any], xlsx_payload: dict[str, Any], xml_payload: dict[str, Any]) -> dict[str, Any]:
    hard_blocks, warnings = _upstream_status((csv_payload, xlsx_payload, xml_payload))
    records = csv_records(csv_payload) + xlsx_records(xlsx_payload) + xml_records(xml_payload)
    anchors = _anchor_audit(records)
    for fmt, row in anchors.items():
        if not row["ready_for_candidate_reconciliation"]:
            warnings.append(f"required_semantic_anchor_missing:{fmt}:{','.join(row['missing'])}")
    if not records:
        hard_blocks.append("no_field_records")
    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if warnings else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "field_record_count": len(records),
        "field_semantic_records": records,
        "mapping_coverage": _coverage(records),
        "required_anchor_audit": anchors,
        "candidate_equivalence_groups": _equivalence_groups(records),
        "mapping_status_counts": dict(sorted(Counter(row["mapping_status"] for row in records).items())),
        "hard_block_hits": sorted(set(hard_blocks)),
        "parse_warnings": sorted(set(warnings)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "active_match_evidence_pass": False,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "does_not_measure": ["validated_provider_semantics", "validated_cross_format_equivalence", "validated_team_identity", "validated_player_identity", "canonical_event_truth", "sequence_truth", "phase_truth", "tactical_truth"],
    }


def render_summary(payload: dict[str, Any]) -> str:
    return "\n".join(["HPFA PROVIDER ALIAS & FIELD SEMANTICS LITE V1", f"status={payload.get('status')}", f"field_record_count={payload.get('field_record_count')}", f"hard_block_hits={payload.get('hard_block_hits')}", f"parse_warnings={payload.get('parse_warnings')}", f"active_match_evidence_pass={payload.get('active_match_evidence_pass')}", "canonical_event_count=UNKNOWN", "production_release=false", ""])


def render_analyst(payload: dict[str, Any]) -> str:
    lines = ["HPFA PROVIDER ALIAS & FIELD SEMANTICS ANALYST AUDIT V1", f"status={payload.get('status')}", f"field_record_count={payload.get('field_record_count')}"]
    for fmt, row in (payload.get("mapping_coverage") or {}).items():
        lines.append(f"format={fmt} fields={row.get('field_count')} candidate_mapped={row.get('candidate_mapped_count')} exact_rules={row.get('exact_rule_count')} unknown_preserved={row.get('unknown_preserved_count')} coverage={row.get('coverage_ratio')}")
    for fmt, row in (payload.get("required_anchor_audit") or {}).items():
        lines.append(f"anchor_format={fmt} ready={row.get('ready_for_candidate_reconciliation')} missing={row.get('missing')}")
    lines += [f"cross_format_candidate_groups={sum(1 for row in payload.get('candidate_equivalence_groups', []) if row.get('cross_format_candidate'))}", "canonical_event_count=UNKNOWN", "production_release=false", "safe_statement=provider fields are mapped to candidate semantic roles; no validated identity, metric definition, event truth or tactical truth is produced.", ""]
    return "\n".join(lines)


def write_outputs(input_root: str | Path, csv_path: str | Path, xlsx_path: str | Path, xml_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    out = validate_out(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    try:
        payload = build_semantics(load_json(csv_path), load_json(xlsx_path), load_json(xml_path))
    except ValueError as exc:
        payload = {"module_id": MODULE_ID, "status": "FAIL_CLOSED", "field_record_count": 0, "hard_block_hits": [str(exc)], "parse_warnings": [], "canonical_event_count": CANONICAL_EVENT_COUNT, "active_match_evidence_pass": False, "production_release": False, "claim_ceiling": CLAIM_CEILING}
    payload["active_match_evidence_pass"] = (
        payload.get("status") in {"PASS", "REVIEW_REQUIRED"}
        and not payload.get("hard_block_hits")
        and root.parts[-2:] == ("active_single_match", "current")
        and all((payload.get("required_anchor_audit") or {}).get(fmt, {}).get("ready_for_candidate_reconciliation") for fmt in REQUIRED_ANCHORS)
    )
    paths = {key: out / name for key, name in OUT.items()}
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    paths["main"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    paths["summary"].write_text(render_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(render_analyst(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--csv-audit", required=True)
    parser.add_argument("--xlsx-audit", required=True)
    parser.add_argument("--xml-audit", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = write_outputs(args.input_root, args.csv_audit, args.xlsx_audit, args.xml_audit, args.out)
    print(json.dumps({key: payload.get(key) for key in ("status", "field_record_count", "hard_block_hits", "active_match_evidence_pass", "canonical_event_count", "production_release")}, ensure_ascii=False, indent=2))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
