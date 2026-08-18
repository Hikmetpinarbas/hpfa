from __future__ import annotations

import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

MODULE_ID = "triangulated_event_reflection_resolver_lite_v1"
CLAIM_SAFETY = "SERIALIZATION_EQUIVALENCE_EVIDENCE_ONLY"
OUTPUT_JSON = "triangulated_event_reflection_resolver_lite_v1.json"
OUTPUT_TXT = "triangulated_event_reflection_resolver_lite_v1.txt"
SUPPORTED_SUFFIXES = {".csv", ".tsv", ".xml"}
FINGERPRINT_FIELDS = ("provider_row_id", "start", "end", "code", "team", "action", "half", "pos_x", "pos_y")
BLOCKED_CLAIMS = [
    "true event count", "validated action count", "deduplicated event truth",
    "complete event stream", "physical action identity", "same upstream origin truth",
    "possession truth", "sequence truth",
]


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_module_path(src)
    import spine_runner  # type: ignore
    return spine_runner


def normalize_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    return " ".join(str(value).strip().casefold().split())


def normalize_number(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = str(value).strip().replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation:
        return normalize_text(value)
    normalized = format(number.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def lower_keys(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key).strip().casefold(): value for key, value in row.items()}


def source_role_from_name(path: Path) -> str:
    name = path.name.casefold()
    if "goalkeeper" in name:
        return "GOALKEEPER"
    if "player" in name:
        return "PLAYER"
    if "team" in name:
        return "TEAM"
    return "UNKNOWN"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    first_line = sample.splitlines()[0] if sample.splitlines() else ""
    if first_line.count(";") > first_line.count(",") and first_line.count(";") >= first_line.count("\t"):
        return ";"
    if first_line.count("\t") > first_line.count(","):
        return "\t"
    return ","


def canonical_row(raw: dict[str, Any], *, source_file: str, source_format: str, source_role: str, source_row_index: int) -> dict[str, Any]:
    row = lower_keys(raw)
    return {
        "provider_row_id": normalize_text(row.get("id", row.get("provider_row_id", ""))),
        "start": normalize_number(row.get("start", "")),
        "end": normalize_number(row.get("end", "")),
        "code": normalize_text(row.get("code", "")),
        "team": normalize_text(row.get("team", "")),
        "action": normalize_text(row.get("action", row.get("event_type", row.get("label", "")))),
        "half": normalize_text(row.get("half", row.get("period", ""))),
        "pos_x": normalize_number(row.get("pos_x", row.get("x", ""))),
        "pos_y": normalize_number(row.get("pos_y", row.get("y", ""))),
        "_source_file": source_file,
        "_source_format": source_format,
        "_source_role": source_role,
        "_source_row_index": source_row_index,
    }


def read_csv_or_tsv(path: Path, delimiter: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    delim = delimiter if delimiter is not None else detect_delimiter(path)
    role = source_role_from_name(path)
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delim)
        for idx, raw in enumerate(reader):
            rows.append(canonical_row(dict(raw), source_file=path.name, source_format=path.suffix.lower().lstrip("."), source_role=role, source_row_index=idx))
    return rows


def label_group_text(label: ET.Element) -> tuple[str, str] | None:
    group = ""
    text = ""
    for child in list(label):
        tag = child.tag.casefold()
        value = (child.text or "").strip()
        if tag == "group":
            group = value
        elif tag == "text":
            text = value
    if not group or not text:
        return None
    return normalize_text(group), text


def flatten_xml_instance(instance: ET.Element) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    labels: dict[str, str] = {}
    for child in list(instance):
        tag = child.tag.casefold()
        value = (child.text or "").strip()
        if tag == "label":
            pair = label_group_text(child)
            if pair is not None:
                labels.setdefault(pair[0], pair[1])
            continue
        if value:
            raw.setdefault(tag, value)
    for group, value in labels.items():
        raw.setdefault(group, value)
    return raw


def read_xml(path: Path) -> list[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    role = source_role_from_name(path)
    rows: list[dict[str, Any]] = []
    for idx, instance in enumerate(root.iter()):
        if instance.tag.casefold() != "instance":
            continue
        rows.append(canonical_row(flatten_xml_instance(instance), source_file=path.name, source_format="xml", source_role=role, source_row_index=idx))
    return rows


def discover_unique_surface_files(input_dir: str | Path) -> tuple[list[Path], list[dict[str, Any]]]:
    root = Path(input_dir).expanduser().resolve(strict=False)
    unique: list[Path] = []
    duplicates: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], Path] = {}
    for path in sorted(root.iterdir() if root.exists() else []):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        digest = file_sha256(path)
        key = (path.suffix.lower(), digest)
        if key in seen:
            duplicates.append({"source_file": path.name, "reflected_from_file": seen[key].name, "sha256": digest, "source_format": path.suffix.lower().lstrip(".")})
            continue
        seen[key] = path
        unique.append(path)
    return unique, duplicates


def read_surface(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        return read_csv_or_tsv(path)
    if path.suffix.lower() == ".tsv":
        return read_csv_or_tsv(path, "\t")
    if path.suffix.lower() == ".xml":
        return read_xml(path)
    return []


def row_fingerprint(row: dict[str, Any]) -> tuple[str, ...]:
    return (str(row.get("_source_role", "UNKNOWN")),) + tuple(str(row.get(field, "")) for field in FINGERPRINT_FIELDS)


def fingerprint_dict(fingerprint: tuple[str, ...]) -> dict[str, str]:
    return {"source_role": fingerprint[0], **{field: fingerprint[idx + 1] for idx, field in enumerate(FINGERPRINT_FIELDS)}}


def audit_role_pair(role: str, csv_paths: list[Path], xml_paths: list[Path]) -> dict[str, Any]:
    base = {
        "source_role": role,
        "csv_files": [path.name for path in csv_paths],
        "xml_files": [path.name for path in xml_paths],
        "equivalence_fields": list(FINGERPRINT_FIELDS),
        "physical_action_identity_truth": False,
        "same_upstream_origin_truth": False,
        "independent_source_vote_allowed": False,
    }
    if len(csv_paths) != 1 or len(xml_paths) != 1:
        return {**base, "state": "PAIRING_REVIEW_REQUIRED", "exact_visible_field_multiset_equivalent": False, "csv_surface_rows": None, "xml_surface_rows": None, "matched_surface_row_count": 0, "discrepancy_count": None, "csv_only_examples": [], "xml_only_examples": []}

    csv_rows = read_surface(csv_paths[0])
    xml_rows = read_surface(xml_paths[0])
    csv_counter = Counter(row_fingerprint(row) for row in csv_rows)
    xml_counter = Counter(row_fingerprint(row) for row in xml_rows)
    all_keys = set(csv_counter) | set(xml_counter)
    matched = sum(min(csv_counter[key], xml_counter[key]) for key in all_keys)
    discrepancy_count = sum(abs(csv_counter[key] - xml_counter[key]) for key in all_keys)
    exact = csv_counter == xml_counter and bool(csv_rows or xml_rows)

    csv_only: list[dict[str, Any]] = []
    xml_only: list[dict[str, Any]] = []
    for key in sorted(all_keys):
        delta = csv_counter[key] - xml_counter[key]
        if delta > 0 and len(csv_only) < 10:
            csv_only.append({"fingerprint": fingerprint_dict(key), "excess_row_count": delta})
        elif delta < 0 and len(xml_only) < 10:
            xml_only.append({"fingerprint": fingerprint_dict(key), "excess_row_count": -delta})

    return {
        **base,
        "state": "EXACT_VISIBLE_FIELD_MULTISET_EQUIVALENCE" if exact else "VISIBLE_FIELD_SERIALIZATION_DISCREPANCY",
        "exact_visible_field_multiset_equivalent": exact,
        "csv_surface_rows": len(csv_rows),
        "xml_surface_rows": len(xml_rows),
        "matched_surface_row_count": matched,
        "discrepancy_count": discrepancy_count,
        "csv_only_examples": csv_only,
        "xml_only_examples": xml_only,
    }


def build_report(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    unique_files, duplicate_files = discover_unique_surface_files(input_dir)
    rows = [row for path in unique_files for row in read_surface(path)]
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row_fingerprint(row)].append(row)
    multi_surface = sum(1 for members in groups.values() if len({str(item.get("_source_file")) for item in members}) > 1)

    by_role_format: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for path in unique_files:
        by_role_format[(source_role_from_name(path), path.suffix.lower().lstrip("."))].append(path)
    roles = sorted({role for role, fmt in by_role_format if role != "UNKNOWN" and fmt in {"csv", "xml"}})
    role_audits = [audit_role_pair(role, by_role_format.get((role, "csv"), []), by_role_format.get((role, "xml"), [])) for role in roles]
    exact_roles = sum(1 for item in role_audits if item["exact_visible_field_multiset_equivalent"])
    discrepancy_roles = sum(1 for item in role_audits if item["state"] == "VISIBLE_FIELD_SERIALIZATION_DISCREPANCY")
    review_roles = sum(1 for item in role_audits if item["state"] == "PAIRING_REVIEW_REQUIRED")
    if role_audits and exact_roles == len(role_audits):
        serialization_state = "EXACT_VISIBLE_FIELD_MULTISET_EQUIVALENCE"
    elif discrepancy_roles:
        serialization_state = "VISIBLE_FIELD_SERIALIZATION_DISCREPANCY"
    else:
        serialization_state = "PAIRING_REVIEW_REQUIRED"

    examples: list[dict[str, Any]] = []
    for key, members in groups.items():
        if len(examples) >= 25:
            break
        examples.append({"fingerprint": fingerprint_dict(key), "surface_row_count": len(members), "source_files": sorted({str(item.get("_source_file")) for item in members}), "claim_allowed": False})

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": serialization_state,
        "claim_safety": CLAIM_SAFETY,
        "surface_file_count": len(unique_files) + len(duplicate_files),
        "unique_surface_file_count": len(unique_files),
        "duplicate_surface_file_reflection_count": len(duplicate_files),
        "duplicate_surface_file_reflections": duplicate_files,
        "surface_row_count": len(rows),
        "reflection_group_count": len(groups),
        "single_surface_group_count": len(groups) - multi_surface,
        "multi_surface_group_count": multi_surface,
        "serialization_role_audit_count": len(role_audits),
        "serialization_exact_role_count": exact_roles,
        "serialization_discrepancy_role_count": discrepancy_roles,
        "serialization_pairing_review_role_count": review_roles,
        "serialization_role_audits": role_audits,
        "reflection_group_examples": examples,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "physical_action_identity_truth": False,
        "same_upstream_origin_truth": False,
        "reflection_group_truth": False,
        "action_count_claim_allowed": False,
        "independent_source_vote_allowed": False,
        "blocked_claims": BLOCKED_CLAIMS,
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA TRIANGULATED EVENT REFLECTION RESOLVER LITE V1",
        "====================================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"surface_file_count={report.get('surface_file_count')}",
        f"unique_surface_file_count={report.get('unique_surface_file_count')}",
        f"duplicate_surface_file_reflection_count={report.get('duplicate_surface_file_reflection_count')}",
        f"surface_row_count={report.get('surface_row_count')}",
        f"reflection_group_count={report.get('reflection_group_count')}",
        f"multi_surface_group_count={report.get('multi_surface_group_count')}",
        f"true_action_count={report.get('true_action_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        "", "[serialization_role_audits]",
    ]
    for item in report.get("serialization_role_audits", []):
        lines.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[reflection_group_examples]"])
    for item in report.get("reflection_group_examples", []):
        lines.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_claims]"])
    for item in report.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_report(input_dir, root=repo_root)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
