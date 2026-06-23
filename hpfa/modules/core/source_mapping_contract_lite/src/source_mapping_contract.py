from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "source_mapping_contract_lite_v1"
CLAIM_SAFETY = "SOURCE_MAPPING_CONTRACT_ONLY"
OUTPUT_CONTRACT_JSON = "source_mapping_contract_v1.json"
OUTPUT_AUDIT_JSON = "source_mapping_audit_v1.json"
OUTPUT_AUDIT_TXT = "source_mapping_audit_v1.txt"

CANONICAL_FIELDS = ["event_type", "team", "player", "minute", "second", "timestamp", "x", "y"]
REQUIRED_EVENT_SURFACE_FIELDS = ["event_type", "x", "y"]
BLOCKED_CLAIMS = [
    "canonical event count",
    "primary event truth",
    "validated event truth",
    "complete event stream",
    "deduplicated event count",
    "possession truth",
    "phase truth",
    "sequence truth",
    "tactical truth",
]


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_module_path(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_module_path(src)
    import spine_runner  # type: ignore

    return spine_runner


def canonical_event_lite_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "canonical_event_lite" / "src"
    ensure_module_path(src)
    import canonical_event_lite  # type: ignore

    return canonical_event_lite


def active_surfaces(active_match_path: Path, cel: Any) -> list[Path]:
    if not active_match_path.exists():
        return []
    return sorted(
        [p for p in active_match_path.iterdir() if p.is_file() and cel.source_format(p) in {"csv", "xml", "xlsx"}],
        key=lambda p: p.name.lower(),
    )


def is_aggregate_support_surface(path: Path, cel: Any) -> bool:
    """Aggregate support surfaces are mapped but not judged by event-like required fields."""
    return cel.source_format(path) == "xlsx"


def source_surface_kind(path: Path, cel: Any) -> str:
    return "aggregate_support" if is_aggregate_support_surface(path, cel) else "event_like_or_review"


def map_header(header: str, cel: Any) -> str | None:
    normalized = cel.normalize_header(header)
    return cel.SYNONYM_INDEX.get(normalized)


def source_mapping_records(source_file: Path, headers: list[str], cel: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    detected = cel.detect_columns(headers)
    required_sources = set()
    if not is_aggregate_support_surface(source_file, cel):
        required_sources = {detected.get(field) for field in REQUIRED_EVENT_SURFACE_FIELDS if detected.get(field)}
    for header in headers:
        canonical = map_header(header, cel)
        records.append({
            "source_file": source_file.name,
            "source_format": cel.source_format(source_file),
            "source_role": cel.source_role(source_file),
            "source_surface_kind": source_surface_kind(source_file, cel),
            "source_field": header,
            "normalized_source_field": cel.normalize_header(header),
            "canonical_field": canonical,
            "mapped": canonical is not None,
            "required": header in required_sources,
            "unmapped_policy": "preserve_in_extras" if canonical is None else "mapped_to_canonical_field",
            "claim_allowed": False,
        })
    return records


def sample_extras(rows: list[dict[str, Any]], unmapped_headers: list[str], max_rows: int = 3) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for idx, row in enumerate(rows[:max_rows], start=1):
        extras = {key: row.get(key) for key in unmapped_headers if key in row}
        samples.append({"source_row_index": idx, "extras": extras})
    return samples


def evaluate_source(path: Path, rows: list[dict[str, Any]], headers: list[str], cel: Any, strict_required: bool) -> dict[str, Any]:
    detected = cel.detect_columns(headers)
    aggregate_support = is_aggregate_support_surface(path, cel)
    missing_required = [] if aggregate_support else [field for field in REQUIRED_EVENT_SURFACE_FIELDS if detected.get(field) is None]
    unmapped_headers = [header for header in headers if map_header(header, cel) is None]
    mapped_headers = [header for header in headers if map_header(header, cel) is not None]

    if not rows or not headers:
        decision = "NO_ROWS_OR_NO_HEADERS"
    elif aggregate_support:
        decision = "AGGREGATE_SUPPORT_MAPPING_ONLY"
    elif missing_required and strict_required:
        decision = "FAIL_CLOSED_MISSING_REQUIRED"
    elif missing_required:
        decision = "DEGRADED_MISSING_REQUIRED"
    else:
        decision = "ACCEPT_MAPPING"

    return {
        "source_file": path.name,
        "source_format": cel.source_format(path),
        "source_role": cel.source_role(path),
        "source_surface_kind": source_surface_kind(path, cel),
        "rows_read": len(rows),
        "headers": headers,
        "detected_columns": detected,
        "mapped_column_count": len(mapped_headers),
        "unmapped_column_count": len(unmapped_headers),
        "unmapped_columns": unmapped_headers,
        "missing_required_fields": missing_required,
        "required_field_policy": "not_applicable_aggregate_support_surface" if aggregate_support else "event_like_surface_required_fields",
        "extras_preserved": bool(unmapped_headers),
        "extras_policy": "preserve_in_extras",
        "extras_sample": sample_extras(rows, unmapped_headers),
        "decision": decision,
        "claim_allowed": False,
    }


def build_contract(active_match_dir: str | Path, strict_required: bool = False, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    cel = canonical_event_lite_module(repo_root)
    active_match_path = Path(active_match_dir).expanduser().resolve(strict=False)

    sources: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []
    surfaces = active_surfaces(active_match_path, cel)
    status = "FAIL_CLOSED" if not surfaces else "PASS"
    overall_decision = "NO_SUPPORTED_SURFACES" if not surfaces else "SOURCES_EVALUATED"
    for path in surfaces:
        rows, headers = cel.read_surface(path)
        source = evaluate_source(path, rows, headers, cel, strict_required)
        sources.append(source)
        mappings.extend(source_mapping_records(path, headers, cel))
        if source["decision"] == "FAIL_CLOSED_MISSING_REQUIRED":
            status = "FAIL_CLOSED"
        elif source["decision"] in {"DEGRADED_MISSING_REQUIRED", "NO_ROWS_OR_NO_HEADERS"} and status != "FAIL_CLOSED":
            status = "REVIEW_REQUIRED"

    mapped_count = sum(1 for record in mappings if record["mapped"])
    unmapped_count = sum(1 for record in mappings if not record["mapped"])
    return {
        "module_id": MODULE_ID,
        "status": status,
        "overall_decision": overall_decision,
        "claim_safety": CLAIM_SAFETY,
        "active_match_dir": str(active_match_path),
        "strict_required": strict_required,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
        "production_binding_allowed": False,
        "source_count": len(sources),
        "mapping_record_count": len(mappings),
        "mapped_column_count": mapped_count,
        "unmapped_column_count": unmapped_count,
        "sources": sources,
        "mappings": mappings,
        "blocked_claims": BLOCKED_CLAIMS,
    }


def build_audit(contract: dict[str, Any]) -> dict[str, Any]:
    decisions: dict[str, int] = {}
    for source in contract.get("sources", []):
        decision = str(source.get("decision"))
        decisions[decision] = decisions.get(decision, 0) + 1
    if not decisions and contract.get("overall_decision") == "NO_SUPPORTED_SURFACES":
        decisions["NO_SUPPORTED_SURFACES"] = 1
    return {
        "module_id": MODULE_ID,
        "status": contract.get("status"),
        "overall_decision": contract.get("overall_decision"),
        "claim_safety": CLAIM_SAFETY,
        "active_match_dir": contract.get("active_match_dir"),
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
        "production_binding_allowed": False,
        "source_count": contract.get("source_count"),
        "mapping_record_count": contract.get("mapping_record_count"),
        "mapped_column_count": contract.get("mapped_column_count"),
        "unmapped_column_count": contract.get("unmapped_column_count"),
        "decision_counts": decisions,
        "sources_review": [
            {
                "source_file": source.get("source_file"),
                "source_format": source.get("source_format"),
                "source_role": source.get("source_role"),
                "source_surface_kind": source.get("source_surface_kind"),
                "rows_read": source.get("rows_read"),
                "mapped_column_count": source.get("mapped_column_count"),
                "unmapped_column_count": source.get("unmapped_column_count"),
                "missing_required_fields": source.get("missing_required_fields"),
                "required_field_policy": source.get("required_field_policy"),
                "decision": source.get("decision"),
                "extras_preserved": source.get("extras_preserved"),
            }
            for source in contract.get("sources", [])
        ],
        "blocked_claims": BLOCKED_CLAIMS,
    }


def render_audit_txt(audit: dict[str, Any]) -> str:
    lines = [
        "HPFA SOURCE MAPPING CONTRACT LITE V1 AUDIT",
        "===========================================",
        f"status={audit.get('status')}",
        f"overall_decision={audit.get('overall_decision')}",
        f"claim_safety={audit.get('claim_safety')}",
        f"active_match_dir={audit.get('active_match_dir')}",
        f"canonical_event_count={audit.get('canonical_event_count')}",
        f"deduplicated_event_count={audit.get('deduplicated_event_count')}",
        f"event_count_claim_allowed={audit.get('event_count_claim_allowed')}",
        f"production_binding_allowed={audit.get('production_binding_allowed')}",
        f"source_count={audit.get('source_count')}",
        f"mapping_record_count={audit.get('mapping_record_count')}",
        f"mapped_column_count={audit.get('mapped_column_count')}",
        f"unmapped_column_count={audit.get('unmapped_column_count')}",
        "",
        "[decision_counts]",
    ]
    for key, value in (audit.get("decision_counts") or {}).items():
        lines.append(f"{key}={value}")
    lines.extend(["", "[sources_review]"])
    for source in audit.get("sources_review", []):
        lines.append(
            f"{source.get('decision')} | {source.get('source_surface_kind')} | {source.get('source_role')} | "
            f"{source.get('source_format')} | rows={source.get('rows_read')} | mapped={source.get('mapped_column_count')} | "
            f"unmapped={source.get('unmapped_column_count')} | missing_required={source.get('missing_required_fields')} | "
            f"file={source.get('source_file')}"
        )
    lines.extend(["", "[blocked_claims]"])
    for claim in audit.get("blocked_claims", []):
        lines.append(f"- {claim}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(active_match_dir: str | Path, out_dir: str | Path, strict_required: bool = False, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    contract = build_contract(active_match_dir, strict_required=strict_required, root=repo_root)
    audit = build_audit(contract)

    contract_out = output_root / OUTPUT_CONTRACT_JSON
    audit_out = output_root / OUTPUT_AUDIT_JSON
    txt_out = output_root / OUTPUT_AUDIT_TXT
    contract["outputs"] = {"contract_json": str(contract_out), "audit_json": str(audit_out), "audit_txt": str(txt_out)}
    audit["outputs"] = contract["outputs"]

    contract_out.write_text(json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    audit_out.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_audit_txt(audit), encoding="utf-8")
    return audit
