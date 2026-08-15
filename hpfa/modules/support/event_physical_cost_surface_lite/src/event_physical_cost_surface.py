from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "event_physical_cost_surface_lite_v1"
CLAIM_SAFETY = "PHYSICAL_COST_REPORT_AND_EXPOSURE_SURFACE_ONLY"
OUT_MANIFEST = "physical_cost_surface_manifest_v1.json"
OUT_TSV = "physical_cost_metric_extract_v1.tsv"
OUT_AUDIT_JSON = "physical_cost_surface_audit_v1.json"
OUT_AUDIT_TXT = "physical_cost_surface_audit_v1.txt"

PHYSICAL_PATTERNS = {
    "DISTANCE_TOTAL": [r"total distance", r"distance covered", r"\bdistance\b"],
    "DISTANCE_HIGH_INTENSITY": [r"high[- ]?intensity", r"high speed", r"\bhsr\b"],
    "DISTANCE_SPRINT": [r"sprint distance", r"sprinting distance", r"\bsprint\b", r"\bsprinting\b"],
    "SPEED_MAX": [r"max(?:imum)? speed", r"top speed"],
    "SPEED_AVERAGE": [r"average speed", r"avg speed"],
    "ACCELERATION": [r"\bacceleration\b", r"\baccelerations\b"],
    "DECELERATION": [r"\bdeceleration\b", r"\bdecelerations\b"],
    "METABOLIC_LOAD": [r"metabolic", r"metabolic power"],
    "PLAYER_LOAD": [r"player load"],
    "WORK_RATE": [r"work rate", r"workload"],
    "RECOVERY_TIME": [r"\brecovery\b"],
}
EXPOSURE_PATTERNS = {
    "MINUTES_PLAYED": [r"minutes played", r"playing time"],
}
REPORT_PATTERNS = {
    "FIFA_TECHNICAL_CONTEXT": [r"\bfifa\b", r"technical report", r"technical study"],
    "MATCH_REPORT_CONTEXT": [r"match report", r"match summary"],
    "FORM_REPORT_CONTEXT": [r"form report", r"form raporu"],
    "OFFICIAL_METRIC_CONTEXT": [r"official", r"metric", r"statistics"],
}
REPORT_NAME_TOKENS = ["fifa", "match report", "technical report", "technical study", "form report", "form raporu"]
PHYSICAL_NAME_TOKENS = ["fitness", "physical", "load", "player load", "gps", "gnss"]
BLOCKED_LANGUAGE_FAMILIES = [
    "physical_cost_as_event_count", "physical_cost_as_event_truth",
    "physical_cost_as_tactical_truth", "physical_cost_as_medical_truth",
    "minutes_played_as_physical_cost", "exposure_candidate_as_validated_playing_time",
    "report_surface_as_event_truth", "report_surface_overrides_active_match_evidence",
]


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_path(src)
    import spine_runner  # type: ignore
    return spine_runner


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                obj["jsonl_line"] = line_no
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def text_of(page: dict[str, Any]) -> str:
    for key in ("text", "page_text", "content", "extracted_text"):
        value = page.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def doc_of(page: dict[str, Any]) -> str:
    for key in ("document_name", "source_file", "file_name", "path", "title"):
        if page.get(key):
            return str(page[key])
    return "UNKNOWN_DOCUMENT"


def page_no(page: dict[str, Any]) -> str:
    for key in ("page_number", "page", "page_index"):
        if key in page:
            return str(page.get(key))
    return ""


def low(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def match_family(text: str, patterns: dict[str, list[str]], default: str | None = None) -> list[str]:
    t = low(text)
    found = [family for family, pats in patterns.items() if any(re.search(pat, t) for pat in pats)]
    if found:
        return found
    return [default] if default else []


def infer_surface_role(name: str, text: str) -> str:
    name_l = low(name); text_l = low(text[:2000])
    if any(token in name_l for token in REPORT_NAME_TOKENS):
        return "REPORT_METRIC_SURFACE"
    if any(token in name_l for token in PHYSICAL_NAME_TOKENS):
        return "PHYSICAL_COST_SURFACE"
    if any(token in text_l for token in ["fitness", "player load", "external load", "total distance", "sprint distance", "acceleration", "deceleration"]):
        return "PHYSICAL_COST_SURFACE"
    return "REPORT_METRIC_SURFACE"


def value_for_family(text: str, family: str) -> tuple[str, str]:
    patterns = PHYSICAL_PATTERNS.get(family, []) or EXPOSURE_PATTERNS.get(family, [])
    for pattern in patterns:
        m = re.search(rf"(?:{pattern})[^\d\n]{{0,40}}([-+]?\d+(?:[\.,]\d+)?)\s*(km/h|km|m|meters|metres|sprints?|acc|dec|min|minutes|au)?", text, flags=re.I)
        if m:
            return m.group(1), (m.group(2) or "")
        m = re.search(rf"([-+]?\d+(?:[\.,]\d+)?)\s*(km/h|km|m|meters|metres|sprints?|acc|dec|min|minutes|au)?[^\n]{{0,40}}(?:{pattern})", text, flags=re.I)
        if m:
            return m.group(1), (m.group(2) or "")
    return "", ""


def _record(idx: int, doc: str, page: dict[str, Any], family: str, role: str, text: str) -> dict[str, Any]:
    value_raw, unit_raw = value_for_family(text, family)
    if role == "PHYSICAL_COST_SURFACE":
        safety = "PHYSICAL_COST_ONLY"
    elif role == "EXPOSURE_NORMALIZATION_SURFACE":
        safety = "EXPOSURE_CANDIDATE_ONLY"
    else:
        safety = "REPORT_CONTEXT_ONLY"
    return {
        "record_id": f"PCR-{idx:06d}-{family}", "document_id": doc, "source_file": doc,
        "source_role": role, "page": page_no(page), "metric_family": family,
        "metric_name_raw": family, "metric_value_raw": value_raw, "unit_raw": unit_raw,
        "event_binding_status": "UNBOUND", "claim_safety": safety,
        "exposure_authority_status": "UNKNOWN" if role == "EXPOSURE_NORMALIZATION_SURFACE" else "NOT_APPLICABLE",
        "provenance": "reference_document_pages_v1.jsonl",
    }


def build_manifest(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve(strict=False)
    audit = read_json(root / "reference_document_extraction_audit_v1.json")
    fitness = read_json(root / "fitness_signal_pdf_index_v1.json")
    bridge = read_json(root / "fitness_tactical_bridge_lite_v1.json")
    pages = read_jsonl(root / "reference_document_pages_v1.jsonl")
    records: list[dict[str, Any]] = []
    surface_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    exposure_counts: Counter[str] = Counter()

    if pages:
        for idx, page in enumerate(pages, start=1):
            text = text_of(page); doc = doc_of(page); combined = doc + " " + text
            role = infer_surface_role(doc, text)
            families = match_family(combined, PHYSICAL_PATTERNS, "UNKNOWN_PHYSICAL") if role == "PHYSICAL_COST_SURFACE" else match_family(combined, REPORT_PATTERNS, "UNCLASSIFIED_REPORT_CONTEXT")
            for family in families:
                rec = _record(idx, doc, page, family, role, text)
                records.append(rec); surface_counts[role] += 1; family_counts[family] += 1
            for family in match_family(combined, EXPOSURE_PATTERNS):
                rec = _record(idx, doc, page, family, "EXPOSURE_NORMALIZATION_SURFACE", text)
                records.append(rec); surface_counts["EXPOSURE_NORMALIZATION_SURFACE"] += 1; exposure_counts[family] += 1
    else:
        pdf_count = audit.get("pdf_count") or fitness.get("pdf_count") or 0
        if pdf_count:
            records.append({
                "record_id": "PCR-AUDIT-000001", "document_id": "REFERENCE_AUDIT_SUMMARY",
                "source_file": "reference_document_extraction_audit_v1.json", "source_role": "REPORT_METRIC_SURFACE",
                "page": "", "metric_family": "UNCLASSIFIED_REPORT_CONTEXT", "metric_name_raw": "reference_document_available",
                "metric_value_raw": str(pdf_count), "unit_raw": "pdf_count", "event_binding_status": "UNBOUND",
                "claim_safety": "REPORT_CONTEXT_ONLY", "exposure_authority_status": "NOT_APPLICABLE",
                "provenance": "reference_document_extraction_audit_v1.json",
            })
            surface_counts["REPORT_METRIC_SURFACE"] += 1; family_counts["UNCLASSIFIED_REPORT_CONTEXT"] += 1

    return {
        "module_id": MODULE_ID, "status": "PASS" if records else "REVIEW_REQUIRED",
        "claim_safety": CLAIM_SAFETY, "runtime_event_truth": False,
        "event_count_claim_allowed": False, "metric_count_allowed": False,
        "surface_counts": dict(surface_counts),
        "metric_family_counts": dict(family_counts),
        "exposure_family_counts": dict(exposure_counts),
        "exposure_authority_truth": False,
        "record_count": len(records),
        "support_inputs": {
            "reference_audit_available": bool(audit), "reference_pdf_count": audit.get("pdf_count"),
            "reference_page_count": audit.get("page_count"), "reference_texty_pages": audit.get("texty_pages"),
            "reference_chars_total": audit.get("chars_total"), "fitness_index_available": bool(fitness),
            "fitness_pdf_count": fitness.get("pdf_count"), "bridge_available": bool(bridge),
        },
        "records": records, "blocked_language_families": BLOCKED_LANGUAGE_FAMILIES,
        "required_next_gates": ["claim router", "reference concept extractor", "ExposureAuthority", "postmatch physical cost context bridge"],
    }


def write_tsv(records: list[dict[str, Any]], path: Path) -> None:
    fields = ["record_id", "document_id", "source_file", "source_role", "page", "metric_family", "metric_name_raw", "metric_value_raw", "unit_raw", "event_binding_status", "claim_safety", "exposure_authority_status", "provenance"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t"); writer.writeheader()
        for row in records:
            writer.writerow({k: row.get(k, "") for k in fields})


def render_audit(report: dict[str, Any]) -> str:
    lines = [
        "HPFA EVENT PHYSICAL COST / EXPOSURE SURFACE LITE V1 AUDIT",
        "==========================================================", f"status={report.get('status')}",
        f"claim_safety={report.get('claim_safety')}", f"runtime_event_truth={report.get('runtime_event_truth')}",
        f"event_count_claim_allowed={report.get('event_count_claim_allowed')}", f"metric_count_allowed={report.get('metric_count_allowed')}",
        f"exposure_authority_truth={report.get('exposure_authority_truth')}", f"record_count={report.get('record_count')}", "", "[surface_counts]",
    ]
    lines += [f"{k}={v}" for k, v in report.get("surface_counts", {}).items()]
    lines += ["", "[metric_family_counts]"] + [f"{k}={v}" for k, v in report.get("metric_family_counts", {}).items()]
    lines += ["", "[exposure_family_counts]"] + [f"{k}={v}" for k, v in report.get("exposure_family_counts", {}).items()]
    lines += ["", "[support_inputs]", json.dumps(report.get("support_inputs", {}), ensure_ascii=False, sort_keys=True), "", "[blocked_language_families]"]
    lines += [f"- {item}" for item in report.get("blocked_language_families", [])]
    lines += ["", "[required_next_gates]"] + [f"- {item}" for item in report.get("required_next_gates", [])] + [""]
    return "\n".join(lines)


def write_outputs(out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = spine_runner_module(repo_root)
    out = spine_runner.validate_output_root(out_dir); out.mkdir(parents=True, exist_ok=True)
    report = build_manifest(out)
    manifest_out = out / OUT_MANIFEST; tsv_out = out / OUT_TSV; audit_json = out / OUT_AUDIT_JSON; audit_txt = out / OUT_AUDIT_TXT
    report["outputs"] = {"manifest_json": str(manifest_out), "metric_tsv": str(tsv_out), "audit_json": str(audit_json), "audit_txt": str(audit_txt)}
    manifest_out.write_text(json.dumps({k: v for k, v in report.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    write_tsv(report.get("records", []), tsv_out)
    audit_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    audit_txt.write_text(render_audit(report), encoding="utf-8")
    return report
