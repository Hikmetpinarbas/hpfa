from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "triplex_source_alignment_adapter_lite_v1"
CLAIM_SAFETY = "SOURCE_ALIGNMENT_EVIDENCE_ONLY"
OUTPUT_JSON = "triplex_source_alignment_adapter_lite_v1.json"
OUTPUT_TXT = "triplex_source_alignment_adapter_lite_v1.txt"
MAPPING_FILES = ["source_mapping_contract_v1.json", "source_mapping_audit_v1.json"]
CONFLICT_FILE = "source_conflict_registry_lite_v1.json"


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


def load_first(input_dir: Path, names: list[str]) -> tuple[dict[str, Any] | None, str | None]:
    for name in names:
        payload = read_json(input_dir / name)
        if payload is not None:
            return payload, name
    return None, None


def sources_from(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    return list(payload.get("sources") or payload.get("sources_review") or [])


def finding(kind: str, severity: str, summary: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_class": kind,
        "severity": severity,
        "summary": summary,
        "evidence": evidence,
        "fusion_admissible": False,
    }


def detect_alignment_findings(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not sources:
        return [finding("NO_SOURCE_SURFACES", "FAIL_CLOSED", "No source surfaces were available for Triplex alignment.", {"source_count": 0})]

    by_origin: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_independence_group: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for source in sources:
        source_file = source.get("source_file")
        surface_kind = source.get("source_surface_kind")
        origin_id = source.get("upstream_origin_id")
        independence_group = source.get("independence_group")
        lineage_role = str(source.get("lineage_role") or "").upper()

        if surface_kind == "event_like_or_review":
            if not origin_id:
                findings.append(finding("MISSING_UPSTREAM_ORIGIN_ID", "REVIEW_REQUIRED", "Event-like source has no upstream origin identifier.", {"source_file": source_file}))
            else:
                by_origin[str(origin_id)].append(source)

            if not independence_group:
                findings.append(finding("MISSING_INDEPENDENCE_GROUP", "REVIEW_REQUIRED", "Event-like source has no independence-group assignment.", {"source_file": source_file}))
            else:
                by_independence_group[str(independence_group)].append(source)

        if lineage_role in {"DERIVED", "DERIVED_OUTPUT", "DOWNSTREAM_OUTPUT"}:
            findings.append(finding("DERIVED_OUTPUT_AS_SOURCE", "FAIL_CLOSED", "Derived output cannot be admitted as an independent primary source.", {"source_file": source_file, "lineage_role": lineage_role}))

        if source.get("canonical_event_identity_compatible") is False:
            findings.append(finding("CANONICAL_EVENT_IDENTITY_INCOMPATIBLE", "REVIEW_REQUIRED", "Canonical event identity is explicitly incompatible.", {"source_file": source_file}))

        time_state = str(source.get("time_window_state") or "").upper()
        if time_state in {"AMBIGUOUS", "UNKNOWN", "MIXED"}:
            findings.append(finding("AMBIGUOUS_TIME_WINDOW", "REVIEW_REQUIRED", "Source time-window compatibility is unresolved.", {"source_file": source_file, "time_window_state": time_state}))

        for key, finding_class in [
            ("unit_compatibility", "UNIT_INCOMPATIBLE"),
            ("scope_compatibility", "SCOPE_INCOMPATIBLE"),
            ("denominator_compatibility", "DENOMINATOR_INCOMPATIBLE"),
        ]:
            state = str(source.get(key) or "").upper()
            if state in {"INCOMPATIBLE", "AMBIGUOUS", "UNKNOWN"}:
                findings.append(finding(finding_class, "REVIEW_REQUIRED", f"{key} is unresolved or incompatible.", {"source_file": source_file, key: state}))

    for origin_id, origin_sources in by_origin.items():
        files = sorted({str(item.get("source_file")) for item in origin_sources})
        if len(files) > 1:
            findings.append(finding("DUPLICATE_UPSTREAM_ORIGIN", "REVIEW_REQUIRED", "Multiple source surfaces share one upstream origin and must not be counted as independent evidence.", {"upstream_origin_id": origin_id, "source_files": files}))

    for group, group_sources in by_independence_group.items():
        origins = {str(item.get("upstream_origin_id")) for item in group_sources if item.get("upstream_origin_id")}
        if len(group_sources) > 1 and len(origins) <= 1:
            findings.append(finding("DEPENDENT_SOURCE_GROUP", "REVIEW_REQUIRED", "Independence group does not contain independently originated evidence.", {"independence_group": group, "source_files": sorted(str(item.get("source_file")) for item in group_sources)}))

    return findings


def summarize(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in findings:
        key = str(item.get("finding_class"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_alignment(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_path = Path(input_dir).expanduser().resolve(strict=False)
    mapping, mapping_source = load_first(input_path, MAPPING_FILES)
    conflict_registry = read_json(input_path / CONFLICT_FILE)
    sources = sources_from(mapping)
    findings = detect_alignment_findings(sources)

    inherited_conflict_count = int((conflict_registry or {}).get("conflict_count", 0) or 0)
    if conflict_registry is None:
        findings.append(finding("MISSING_SOURCE_CONFLICT_REGISTRY", "REVIEW_REQUIRED", "Existing source-conflict registry output was not available.", {"expected": CONFLICT_FILE}))

    status = "PASS" if not findings and inherited_conflict_count == 0 else "REVIEW_REQUIRED"
    if any(item.get("severity") == "FAIL_CLOSED" for item in findings):
        status = "FAIL_CLOSED"

    fusion_admissible = status == "PASS" and inherited_conflict_count == 0
    return {
        "module_id": MODULE_ID,
        "status": status,
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(input_path),
        "mapping_source": mapping_source,
        "conflict_registry_source": CONFLICT_FILE if conflict_registry is not None else None,
        "source_count": len(sources),
        "finding_count": len(findings),
        "finding_class_counts": summarize(findings),
        "inherited_conflict_count": inherited_conflict_count,
        "fusion_admissible": fusion_admissible,
        "claim_capacity": "SOURCE_ALIGNMENT_ONLY" if fusion_admissible else "BLOCKED_PENDING_REVIEW",
        "canonical_event_count": "UNKNOWN",
        "production_binding_allowed": False,
        "findings": findings,
        "repo_root": str(repo_root),
    }


def render_txt(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA TRIPLEX SOURCE ALIGNMENT ADAPTER LITE V1",
        "===============================================",
        f"status={payload.get('status')}",
        f"fusion_admissible={payload.get('fusion_admissible')}",
        f"claim_capacity={payload.get('claim_capacity')}",
        f"canonical_event_count={payload.get('canonical_event_count')}",
        f"production_binding_allowed={payload.get('production_binding_allowed')}",
        f"source_count={payload.get('source_count')}",
        f"finding_count={payload.get('finding_count')}",
        f"inherited_conflict_count={payload.get('inherited_conflict_count')}",
        "",
        "[findings]",
    ]
    for item in payload.get("findings", []):
        lines.append(f"{item.get('severity')} | {item.get('finding_class')} | {item.get('summary')}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    output_root = spine_runner_module(repo_root).validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_alignment(input_dir, root=repo_root)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    payload["outputs"] = {"alignment_json": str(json_out), "alignment_txt": str(txt_out)}
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(payload), encoding="utf-8")
    return payload
