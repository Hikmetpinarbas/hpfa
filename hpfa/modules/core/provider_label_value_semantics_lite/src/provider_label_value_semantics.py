from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "provider_label_value_semantics_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "PROVIDER_LABEL_VALUE_SEMANTICS_CANDIDATE_ONLY"
REGISTRY_VERSION = "sportsbase_label_semantics_seed_v1"
OUT = {
    "inventory": "provider_label_value_inventory_v1.json",
    "main": "provider_label_value_semantics_lite_v1.json",
    "unknown": "provider_label_unknown_report_v1.json",
    "conflict": "provider_label_conflict_report_v1.json",
    "analyst": "provider_label_value_semantics_analyst_audit_v1.txt",
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


def load_registry(path: str | Path) -> dict[str, Any]:
    registry = load_json(path)
    if registry.get("registry_id") != REGISTRY_VERSION:
        raise ValueError("registry_version_mismatch")
    seen: set[str] = set()
    for row in registry.get("exact_rules", []) or []:
        normalized = normalize_label(row.get("label"))
        if not normalized:
            raise ValueError("registry_empty_label")
        if normalized in seen:
            raise ValueError("registry_duplicate_conflict")
        seen.add(normalized)
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


def _exact_rules(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        normalize_label(row.get("label")): row
        for row in registry.get("exact_rules", []) or []
    }


def _token_present(label: str, token: str) -> bool:
    return re.search(rf"(^| ){re.escape(token)}( |$)", label) is not None


def classify_label(
    raw_label: str,
    *,
    source_format: str,
    registry: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_label(raw_label)
    if source_format == "xlsx":
        return {
            "semantic_role_candidate": "AGGREGATE_METRIC_LABEL",
            "action_family_candidate": None,
            "outcome_candidate": None,
            "direction_candidate": None,
            "distance_candidate": None,
            "zone_candidate": None,
            "context_candidate": None,
            "mapping_status": "EXACT_REGISTRY_CANDIDATE",
            "rule_id": "xlsx_metric_label_surface",
            "confidence_tier": "CANDIDATE_HIGH",
        }

    exact = _exact_rules(registry).get(normalized)
    if exact:
        return {
            "semantic_role_candidate": exact["semantic_role"],
            "action_family_candidate": exact.get("action_family"),
            "outcome_candidate": exact.get("outcome"),
            "direction_candidate": exact.get("direction"),
            "distance_candidate": exact.get("distance"),
            "zone_candidate": exact.get("zone"),
            "context_candidate": exact.get("context"),
            "mapping_status": "EXACT_REGISTRY_CANDIDATE",
            "rule_id": exact["rule_id"],
            "confidence_tier": "CANDIDATE_HIGH",
        }

    for row in registry.get("prefix_rules", []) or []:
        prefix = normalize_label(row.get("prefix"))
        if prefix and normalized.startswith(prefix):
            return {
                "semantic_role_candidate": row["semantic_role"],
                "action_family_candidate": row.get("action_family"),
                "outcome_candidate": None,
                "direction_candidate": None,
                "distance_candidate": None,
                "zone_candidate": None,
                "context_candidate": row.get("context") or normalized.removeprefix(prefix).strip() or None,
                "mapping_status": "COMPOSITIONAL_RULE_CANDIDATE",
                "rule_id": row["rule_id"],
                "confidence_tier": "CANDIDATE_MEDIUM",
            }

    family: str | None = None
    family_rule: str | None = None
    for row in registry.get("anchor_tokens", []) or []:
        if any(_token_present(normalized, normalize_label(token)) for token in row.get("tokens", [])):
            family = row["action_family"]
            family_rule = row["rule_id"]
            break

    if not family:
        if normalized in set(map(normalize_label, registry.get("meta_labels", []) or [])):
            return {
                "semantic_role_candidate": "PERIOD_OR_META",
                "action_family_candidate": None,
                "outcome_candidate": None,
                "direction_candidate": None,
                "distance_candidate": None,
                "zone_candidate": None,
                "context_candidate": None,
                "mapping_status": "EXACT_ALIAS_CANDIDATE",
                "rule_id": "period_meta_alias",
                "confidence_tier": "CANDIDATE_HIGH",
            }
        return {
            "semantic_role_candidate": "UNKNOWN_PRESERVED",
            "action_family_candidate": "UNKNOWN",
            "outcome_candidate": None,
            "direction_candidate": None,
            "distance_candidate": None,
            "zone_candidate": None,
            "context_candidate": None,
            "mapping_status": "UNKNOWN_PRESERVED",
            "rule_id": None,
            "confidence_tier": "UNKNOWN",
        }

    def first_qualifier(section: str) -> tuple[str | None, str | None]:
        for row in registry.get(section, []) or []:
            if any(_token_present(normalized, normalize_label(token)) for token in row.get("tokens", [])):
                return row["value"], row["rule_id"]
        return None, None

    outcome, outcome_rule = first_qualifier("outcome_tokens")
    direction, direction_rule = first_qualifier("direction_tokens")
    distance, distance_rule = first_qualifier("distance_tokens")
    zone, zone_rule = first_qualifier("zone_tokens")
    rule_ids = [value for value in (family_rule, outcome_rule, direction_rule, distance_rule, zone_rule) if value]
    return {
        "semantic_role_candidate": "ACTION_ANCHOR",
        "action_family_candidate": family,
        "outcome_candidate": outcome,
        "direction_candidate": direction,
        "distance_candidate": distance,
        "zone_candidate": zone,
        "context_candidate": None,
        "mapping_status": "COMPOSITIONAL_RULE_CANDIDATE",
        "rule_id": "+".join(rule_ids),
        "confidence_tier": "CANDIDATE_MEDIUM",
    }


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
    classified = classify_label(raw_label, source_format=source_format, registry=registry)
    normalized = normalize_label(raw_label)
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
        "review_hits": [],
        "validated_semantics": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def csv_label_records(payload: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for file_row in payload.get("files", []) or []:
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
                    evidence_scope="FULL_CSV_TAXONOMY",
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
    seen: set[tuple[str, str, str]] = set()
    for file_row in payload.get("files", []) or []:
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
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                records.append(
                    _base_record(
                        source_format="xml",
                        source_role=source_role,
                        relative_path=relative_path,
                        source_sha256=str(sha256) if sha256 else None,
                        raw_label=text,
                        surface_row_volume=None,
                        evidence_scope="XML_EXAMPLE_SUPPORT_ONLY",
                        registry=registry,
                    )
                )
    return records


def xlsx_label_records(payload: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for file_row in payload.get("files", []) or []:
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
                        evidence_scope="XLSX_AGGREGATE_LABEL_ONLY",
                        registry=registry,
                    )
                )
    return records


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
        signatures = {
            (
                row["semantic_role_candidate"],
                row["action_family_candidate"],
                row["outcome_candidate"],
                row["direction_candidate"],
                row["distance_candidate"],
                row["zone_candidate"],
            )
            for row in rows
        }
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
    }


def _coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    csv_rows = [row for row in records if row["source_format"] == "csv"]
    total_volume = sum(int(row["surface_row_volume"] or 0) for row in csv_rows)
    unknown_volume = sum(
        int(row["surface_row_volume"] or 0)
        for row in csv_rows
        if row["mapping_status"] == "UNKNOWN_PRESERVED"
    )
    mapped_volume = total_volume - unknown_volume
    return {
        "csv_label_record_count": len(csv_rows),
        "csv_surface_row_volume": total_volume,
        "mapped_surface_row_volume": mapped_volume,
        "unknown_surface_row_volume": unknown_volume,
        "mapped_surface_row_volume_ratio": mapped_volume / total_volume if total_volume else 0.0,
        "xml_example_support_label_count": sum(1 for row in records if row["source_format"] == "xml"),
        "xlsx_aggregate_label_count": sum(1 for row in records if row["source_format"] == "xlsx"),
        "coverage_scope": "CSV_SURFACE_ROW_VOLUME_PLUS_XML_EXAMPLE_SUPPORT",
    }


def build_semantics(
    csv_payload: dict[str, Any],
    xlsx_payload: dict[str, Any],
    xml_payload: dict[str, Any],
    field_semantics_payload: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    hard_blocks, warnings = _upstream_guard(
        (csv_payload, xlsx_payload, xml_payload, field_semantics_payload)
    )
    hard_blocks.extend(_field_semantics_guard(field_semantics_payload))
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
    unknown_records = [row for row in records if row["mapping_status"] == "UNKNOWN_PRESERVED"]
    if unknown_records:
        warnings.append("unknown_provider_label_values_present")
    coverage = _coverage(records)
    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if warnings else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "BLOCK_DOWNSTREAM" if hard_blocks else ("REVIEW_SEMANTICS" if warnings else "PASS_SEMANTICS_CANDIDATE"),
        "provider_label_record_count": len(records),
        "provider_label_records": records,
        "mapping_status_counts": dict(sorted(Counter(row["mapping_status"] for row in records).items())),
        "semantic_role_counts": dict(sorted(Counter(row["semantic_role_candidate"] for row in records).items())),
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
            }
            for row in unknown_records
        ],
        "conflict_records": consistency["conflicts"],
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(warnings)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "active_match_evidence_pass": False,
        "validated_provider_semantics": False,
        "validated_event_identity": False,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "donor_adaptation": {
            "accepted_idea": "deterministic exact-or-compositional label mapping with preserved unknowns",
            "rejected_scope": [
                "donor_module_import",
                "broad_ontology_bundle",
                "parallel_semantic_framework",
                "probabilistic_or_llm_mapping",
            ],
        },
        "does_not_measure": [
            "canonical_event_truth",
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
        "HPFA PROVIDER LABEL VALUE SEMANTICS ANALYST AUDIT V1",
        f"status={payload.get('status')}",
        f"provider_label_record_count={payload.get('provider_label_record_count')}",
        f"csv_surface_row_volume={coverage.get('csv_surface_row_volume')}",
        f"mapped_surface_row_volume={coverage.get('mapped_surface_row_volume')}",
        f"unknown_surface_row_volume={coverage.get('unknown_surface_row_volume')}",
        f"mapped_surface_row_volume_ratio={coverage.get('mapped_surface_row_volume_ratio')}",
        f"xml_example_support_label_count={coverage.get('xml_example_support_label_count')}",
        f"cross_format_conflict_count={(payload.get('cross_format_consistency') or {}).get('conflict_count')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "safe_statement=visible provider labels were classified into claim-safe action, qualifier, context, meta, aggregate or unknown candidates; football event identity remains unresolved.",
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
        "provider_label_record_count": payload["provider_label_record_count"],
        "provider_label_records": payload["provider_label_records"],
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }
    unknown_payload = {
        "module_id": MODULE_ID,
        "unknown_provider_labels": payload["unknown_provider_labels"],
        "unknown_surface_row_volume": payload["coverage"]["unknown_surface_row_volume"],
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }
    conflict_payload = {
        "module_id": MODULE_ID,
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
