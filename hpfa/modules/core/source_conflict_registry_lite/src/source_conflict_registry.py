from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "source_conflict_registry_lite_v1"
CLAIM_SAFETY = "SOURCE_CONFLICT_EVIDENCE_ONLY"
OUTPUT_JSON = "source_conflict_registry_lite_v1.json"
OUTPUT_TXT = "source_conflict_registry_lite_v1.txt"

MAPPING_CONTRACT = "source_mapping_contract_v1.json"
MAPPING_AUDIT = "source_mapping_audit_v1.json"
PRIMARY_GATE = "primary_event_surface_gate_lite_v1.json"
PHYSICAL_AUDIT = "physical_cost_surface_audit_v1.json"
METRIC_REGISTRY = "metric_family_registry_lite_v1.json"

BLOCKED_CLAIMS = [
    "primary source truth",
    "canonical event count",
    "complete event stream",
    "validated event truth",
    "clean possession truth",
    "clean phase truth",
    "clean sequence truth",
    "tactical truth",
    "fitness truth",
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


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_mapping(input_dir: Path) -> tuple[dict[str, Any] | None, str | None]:
    for name in [MAPPING_CONTRACT, MAPPING_AUDIT]:
        payload = read_json(input_dir / name)
        if payload is not None:
            return payload, name
    return None, None


def conflict(kind: str, severity: str, summary: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"conflict_class": kind, "severity": severity, "summary": summary, "evidence": evidence, "claim_allowed": False}


def sources_from(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if "sources" in payload:
        return list(payload.get("sources") or [])
    if "sources_review" in payload:
        return list(payload.get("sources_review") or [])
    return []


def g(source: dict[str, Any], key: str, default: Any = None) -> Any:
    return source.get(key, default)


def detect_source_conflicts(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not sources:
        return [conflict("NO_SUPPORTED_SURFACES", "FAIL_CLOSED", "No supported source mapping surfaces were available.", {"source_count": 0})]

    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in sources:
        role = str(g(source, "source_role", "unknown"))
        by_role[role].append(source)
        kind = g(source, "source_surface_kind")
        decision = str(g(source, "decision", ""))
        mapped = int(g(source, "mapped_column_count", 0) or 0)
        missing = list(g(source, "missing_required_fields", []) or [])

        if kind == "event_like_or_review" and missing:
            out.append(conflict("UNMAPPED_EVENT_SURFACE", "REVIEW_REQUIRED", "Event-like surface has unmapped required event fields.", {
                "source_file": g(source, "source_file"), "source_role": role, "source_format": g(source, "source_format"),
                "mapped_column_count": mapped, "missing_required_fields": missing, "decision": decision,
            }))
        if kind == "aggregate_support":
            out.append(conflict("EVENT_LIKE_VS_AGGREGATE_SUPPORT", "INFO", "Aggregate support surface must not be treated as event truth.", {
                "source_file": g(source, "source_file"), "source_role": role, "source_format": g(source, "source_format"),
                "rows_read": g(source, "rows_read"), "decision": decision,
            }))
        if decision in {"DEGRADED_MISSING_REQUIRED", "NO_ROWS_OR_NO_HEADERS", "FAIL_CLOSED_MISSING_REQUIRED"}:
            out.append(conflict("REVIEW_REQUIRED_SOURCE", "REVIEW_REQUIRED", "Source mapping decision requires review before downstream use.", {
                "source_file": g(source, "source_file"), "source_role": role, "source_format": g(source, "source_format"), "decision": decision,
            }))
        if role in {"", "unknown", "UNKNOWN"}:
            out.append(conflict("SOURCE_ROLE_CONFLICT", "REVIEW_REQUIRED", "Source role is unknown.", {
                "source_file": g(source, "source_file"), "source_format": g(source, "source_format"), "source_role": role,
            }))

    for role, role_sources in by_role.items():
        event_like = [s for s in role_sources if g(s, "source_surface_kind") == "event_like_or_review"]
        if len(event_like) < 2:
            continue
        mapped_by_format = {str(g(s, "source_format")): int(g(s, "mapped_column_count", 0) or 0) for s in event_like}
        rows_by_format = {str(g(s, "source_format")): int(g(s, "rows_read", 0) or 0) for s in event_like}
        decisions = {str(g(s, "source_format")): str(g(s, "decision")) for s in event_like}
        if len(set(mapped_by_format.values())) > 1 or len(set(decisions.values())) > 1:
            out.append(conflict("SCHEMA_DIVERGENCE_BY_ROLE", "REVIEW_REQUIRED", "Same role has divergent mapping quality across event-like formats.", {
                "source_role": role, "mapped_counts_by_format": mapped_by_format, "decisions_by_format": decisions,
            }))
        positive_rows = [value for value in rows_by_format.values() if value > 0]
        if positive_rows and len(set(positive_rows)) > 1:
            out.append(conflict("ROW_COUNT_DISCREPANCY_BY_ROLE", "REVIEW_REQUIRED", "Same role has different visible row counts across event-like formats.", {
                "source_role": role, "rows_by_format": rows_by_format,
            }))
    return out


def detect_optional_conflicts(input_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    primary = read_json(input_dir / PRIMARY_GATE)
    if primary is not None and ("UNRESOLVED" in json.dumps(primary).upper() or "REVIEW_REQUIRED" in json.dumps(primary).upper()):
        out.append(conflict("PRIMARY_SURFACE_UNRESOLVED", "REVIEW_REQUIRED", "Primary event surface is unresolved or review-required.", {"input_file": PRIMARY_GATE}))
    for name in [PHYSICAL_AUDIT, METRIC_REGISTRY]:
        payload = read_json(input_dir / name)
        if payload is None:
            continue
        text = json.dumps(payload).lower()
        if any(token in text for token in ["count", "record_count", "family_counts"]) and "extracted_value" not in text:
            out.append(conflict("METRIC_FAMILY_COUNT_NOT_VALUE", "INFO", "Metric-family counts are present but are not physical values.", {"input_file": name}))
    return out


def summarize(conflicts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in conflicts:
        key = str(item.get("conflict_class"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_registry(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_path = Path(input_dir).expanduser().resolve(strict=False)
    mapping, mapping_source = load_mapping(input_path)
    if mapping is None:
        sources: list[dict[str, Any]] = []
        conflicts = [conflict("NO_SUPPORTED_SURFACES", "FAIL_CLOSED", "No source mapping JSON input was found.", {"expected": [MAPPING_CONTRACT, MAPPING_AUDIT]})]
    else:
        sources = sources_from(mapping)
        conflicts = detect_source_conflicts(sources) + detect_optional_conflicts(input_path)

    status = "PASS" if not conflicts else "REVIEW_REQUIRED"
    if any(item.get("severity") == "FAIL_CLOSED" for item in conflicts):
        status = "FAIL_CLOSED"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(input_path),
        "mapping_source": mapping_source,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
        "production_binding_allowed": False,
        "source_count": len(sources),
        "conflict_count": len(conflicts),
        "conflict_class_counts": summarize(conflicts),
        "sources_review": [{
            "source_file": g(s, "source_file"), "source_role": g(s, "source_role"), "source_format": g(s, "source_format"),
            "source_surface_kind": g(s, "source_surface_kind"), "rows_read": g(s, "rows_read"),
            "mapped_column_count": g(s, "mapped_column_count"), "unmapped_column_count": g(s, "unmapped_column_count"), "decision": g(s, "decision"),
        } for s in sources],
        "conflicts": conflicts,
        "blocked_claims": BLOCKED_CLAIMS,
        "repo_root": str(repo_root),
    }


def render_txt(registry: dict[str, Any]) -> str:
    lines = [
        "HPFA SOURCE CONFLICT REGISTRY LITE V1",
        "======================================",
        f"status={registry.get('status')}",
        f"claim_safety={registry.get('claim_safety')}",
        f"input_dir={registry.get('input_dir')}",
        f"mapping_source={registry.get('mapping_source')}",
        f"canonical_event_count={registry.get('canonical_event_count')}",
        f"deduplicated_event_count={registry.get('deduplicated_event_count')}",
        f"event_count_claim_allowed={registry.get('event_count_claim_allowed')}",
        f"production_binding_allowed={registry.get('production_binding_allowed')}",
        f"source_count={registry.get('source_count')}",
        f"conflict_count={registry.get('conflict_count')}",
        "",
        "[conflict_class_counts]",
    ]
    for key, value in (registry.get("conflict_class_counts") or {}).items():
        lines.append(f"{key}={value}")
    lines.extend(["", "[conflicts]"])
    for item in registry.get("conflicts", []):
        evidence = item.get("evidence") or {}
        label = evidence.get("source_file") or evidence.get("input_file") or evidence.get("source_role") or "n/a"
        lines.append(f"{item.get('severity')} | {item.get('conflict_class')} | {label} | {item.get('summary')}")
    lines.extend(["", "[blocked_claims]"])
    for claim in registry.get("blocked_claims", []):
        lines.append(f"- {claim}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    registry = build_registry(input_dir, root=repo_root)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    registry["outputs"] = {"registry_json": str(json_out), "registry_txt": str(txt_out)}
    json_out.write_text(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(registry), encoding="utf-8")
    return registry
