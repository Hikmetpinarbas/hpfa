from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "fitness_tactical_bridge_lite_v1"
CLAIM_SAFETY = "SUPPORT_BRIDGE_ONLY_NO_CAUSALITY"
OUTPUT_JSON = "fitness_tactical_bridge_lite_v1.json"
OUTPUT_TXT = "fitness_tactical_bridge_lite_v1.txt"

BLOCKED_CLAIMS = [
    "fatigue truth",
    "load truth",
    "injury truth",
    "tactical causality",
    "coach intention",
    "dominance truth",
    "off-ball truth",
    "event truth override",
]


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def _ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    _ensure_module_path(src)
    import spine_runner  # type: ignore

    return spine_runner


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_missing": True, "path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}:{exc}", "path": str(path)}


def summarize_event_audit(event_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": not event_audit.get("_missing") and not event_audit.get("_error"),
        "status": event_audit.get("status"),
        "canonical_event_count": event_audit.get("canonical_event_count"),
        "canonical_lite_row_count": event_audit.get("canonical_lite_row_count"),
        "coverage": event_audit.get("coverage", {}),
        "top_event_families": dict(list((event_audit.get("event_family_volume") or {}).items())[:8]),
        "zone_distribution": event_audit.get("zone_distribution", {}),
        "channel_distribution": event_audit.get("channel_distribution", {}),
        "team_row_volume": event_audit.get("team_row_volume", {}),
    }


def summarize_pdf_index(pdf_index: dict[str, Any]) -> dict[str, Any]:
    pdfs = pdf_index.get("pdfs", []) if isinstance(pdf_index.get("pdfs"), list) else []
    return {
        "available": not pdf_index.get("_missing") and not pdf_index.get("_error"),
        "status": pdf_index.get("status"),
        "pdf_count": pdf_index.get("pdf_count", len(pdfs)),
        "runtime_event_truth": pdf_index.get("runtime_event_truth"),
        "support_signal_types": sorted({p.get("support_signal_type", "UNKNOWN") for p in pdfs}),
        "extraction_statuses": sorted({p.get("extraction_status", "UNKNOWN") for p in pdfs}),
    }


def summarize_reference_audit(ref_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": not ref_audit.get("_missing") and not ref_audit.get("_error"),
        "status": ref_audit.get("status"),
        "pdf_count": ref_audit.get("pdf_count"),
        "page_count": ref_audit.get("page_count"),
        "chars_total": ref_audit.get("chars_total"),
        "texty_pages": ref_audit.get("texty_pages"),
        "err_pages": ref_audit.get("err_pages"),
        "runtime_event_truth": ref_audit.get("runtime_event_truth"),
    }


def build_bridge(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve(strict=False)
    event_audit = read_json(root / "canonical_event_lite_audit_v1.json")
    pdf_index = read_json(root / "fitness_signal_pdf_index_v1.json")
    ref_audit = read_json(root / "reference_document_extraction_audit_v1.json")

    event_summary = summarize_event_audit(event_audit)
    pdf_summary = summarize_pdf_index(pdf_index)
    ref_summary = summarize_reference_audit(ref_audit)

    candidates: list[dict[str, Any]] = []
    if event_summary["available"] and pdf_summary["available"] and (pdf_summary.get("pdf_count") or 0) > 0:
        candidates.append({
            "candidate_id": "event_surface_plus_fitness_pdf_support",
            "safe_reading": "Visible event evidence and ACTIVE_MATCH-adjacent fitness PDF support evidence are both available for analyst review.",
            "claim_boundary": "cross_surface_review_candidate_only_no_fatigue_or_tactical_causality",
        })
    if event_summary["available"] and ref_summary["available"] and (ref_summary.get("texty_pages") or 0) > 0:
        candidates.append({
            "candidate_id": "event_surface_plus_reference_text_support",
            "safe_reading": "Visible event evidence and extracted reference-document text can be reviewed together by page-level provenance.",
            "claim_boundary": "reference_text_support_only_no_event_truth_override",
        })

    status = "PASS" if event_summary["available"] and pdf_summary["available"] else "REVIEW_REQUIRED"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "claim_safety": CLAIM_SAFETY,
        "output_root": str(root),
        "event_evidence_summary": event_summary,
        "fitness_pdf_support_summary": pdf_summary,
        "reference_document_summary": ref_summary,
        "cross_surface_review_candidates": candidates,
        "blocked_claims": BLOCKED_CLAIMS,
        "required_next_gates": [
            "claim router",
            "reference concept extractor",
            "team binding",
            "time/phase gate before temporal claims",
        ],
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA FITNESS-TACTICAL BRIDGE LITE V1",
        "======================================",
        f"status={report.get('status')}",
        f"claim_safety={report.get('claim_safety')}",
        f"output_root={report.get('output_root')}",
        "",
        "[event_evidence_summary]",
        json.dumps(report.get("event_evidence_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[fitness_pdf_support_summary]",
        json.dumps(report.get("fitness_pdf_support_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[reference_document_summary]",
        json.dumps(report.get("reference_document_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[cross_surface_review_candidates]",
    ]
    for row in report.get("cross_surface_review_candidates", []):
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_claims]"])
    for item in report.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.extend(["", "[required_next_gates]"])
    for item in report.get("required_next_gates", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_root: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    out = spine_runner.validate_output_root(output_root)
    out.mkdir(parents=True, exist_ok=True)
    report = build_bridge(out)
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
