from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "reference_document_ingest_lite_v1"
CLAIM_SAFETY = "REFERENCE_ONLY_SUPPORT_SIGNAL"

MANIFEST_JSON = "reference_document_manifest_v1.json"
PAGES_JSONL = "reference_document_pages_v1.jsonl"
AUDIT_JSON = "reference_document_extraction_audit_v1.json"
AUDIT_TXT = "reference_document_extraction_audit_v1.txt"


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_id(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "document"


def support_type_from_name(name: str) -> str:
    text = name.lower()
    if "gps" in text:
        return "GPS_SUPPORT_PDF"
    if "hrv" in text:
        return "HRV_SUPPORT_PDF"
    if "wellness" in text:
        return "WELLNESS_SUPPORT_PDF"
    if "rpe" in text:
        return "RPE_SUPPORT_PDF"
    if "load" in text or "fitness" in text or "physical" in text:
        return "LOAD_FITNESS_SUPPORT_PDF"
    if "report" in text:
        return "REFERENCE_REPORT_PDF"
    return "REFERENCE_SUPPORT_PDF"


def pdf_reader_class():
    try:
        from pypdf import PdfReader  # type: ignore
        return PdfReader, "pypdf"
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader  # type: ignore
        return PdfReader, "PyPDF2"
    except Exception:
        return None, "PDF_EXTRACTION_DEPENDENCY_MISSING"


def is_texty(text: str) -> bool:
    sample = text.strip()
    if not sample:
        return False
    if sample.startswith("__EXTRACT_ERR__"):
        return False
    alpha = sum(ch.isalpha() for ch in sample)
    return alpha >= 40


def page_text_safe(reader: Any, page_index: int) -> tuple[str, str]:
    try:
        page = reader.pages[page_index]
        text = page.extract_text() or ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text, "OK"
    except Exception as exc:
        return f"__EXTRACT_ERR__:{type(exc).__name__}:{exc}", "ERROR"


def discover_pdfs(input_dir: str | Path) -> list[Path]:
    root = Path(input_dir).expanduser().resolve(strict=False)
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("*.pdf") if p.is_file()], key=lambda p: str(p).lower())


def build_manifest_and_pages(input_dir: str | Path, active_match_mode: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    root = Path(input_dir).expanduser().resolve(strict=False)
    pdfs = discover_pdfs(root)
    reader_cls, reader_dependency = pdf_reader_class()

    manifest: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    page_count = 0
    chars_total = 0
    texty_pages = 0
    err_pages = 0
    text_based_count = 0
    possibly_image_based_count = 0

    for idx, pdf in enumerate(pdfs, start=1):
        rel = str(pdf.relative_to(root)) if root.exists() else pdf.name
        document_id = f"{idx:04d}_{safe_id(pdf.stem)}"
        sha = sha256_file(pdf)
        source_role = "ACTIVE_MATCH_ADJACENT_SUPPORT_DOCUMENT" if active_match_mode else "REFERENCE_DOCUMENT"
        row = {
            "document_id": document_id,
            "source_file": pdf.name,
            "relative_path": rel,
            "size_bytes": pdf.stat().st_size,
            "sha256": sha,
            "source_role": source_role,
            "support_signal_type": support_type_from_name(pdf.name),
            "runtime_event_truth": False,
            "claim_boundary": "reference_only_support_signal_no_event_truth_override",
            "reader_dependency": reader_dependency,
        }

        if reader_cls is None:
            row["extraction_status"] = "PDF_EXTRACTION_DEPENDENCY_MISSING"
            row["page_count"] = 0
            manifest.append(row)
            continue

        try:
            reader = reader_cls(str(pdf))
            n_pages = len(reader.pages)
            row["page_count"] = n_pages
            doc_texty = 0
            doc_err = 0
            doc_chars = 0
            for page_index in range(n_pages):
                text, status = page_text_safe(reader, page_index)
                if status == "ERROR":
                    err_pages += 1
                    doc_err += 1
                else:
                    chars_total += len(text)
                    doc_chars += len(text)
                    if is_texty(text):
                        texty_pages += 1
                        doc_texty += 1
                page_count += 1
                pages.append({
                    "document_id": document_id,
                    "source_file": pdf.name,
                    "page_index": page_index,
                    "text": text,
                    "char_count": len(text),
                    "extraction_status": status,
                    "claim_safety": CLAIM_SAFETY,
                })
            mode = "text_based" if doc_texty >= max(1, int(0.2 * max(1, n_pages))) else "possibly_image_based"
            if mode == "text_based":
                text_based_count += 1
            else:
                possibly_image_based_count += 1
            row.update({
                "extraction_status": "PDF_EXTRACTION_PASS",
                "text_mode": mode,
                "chars_total": doc_chars,
                "texty_pages": doc_texty,
                "err_pages": doc_err,
            })
        except Exception as exc:
            row.update({
                "extraction_status": "PDF_EXTRACTION_FAIL_CLOSED",
                "page_count": 0,
                "error": f"{type(exc).__name__}:{exc}",
            })
        manifest.append(row)

    audit = {
        "module_id": MODULE_ID,
        "status": "REFERENCE_DOCUMENT_INGEST_PASS" if manifest else "NO_REFERENCE_PDF_FOUND",
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(root),
        "active_match_mode": active_match_mode,
        "pdf_count": len(manifest),
        "page_count": page_count,
        "chars_total": chars_total,
        "texty_pages": texty_pages,
        "err_pages": err_pages,
        "text_based_count": text_based_count,
        "possibly_image_based_count": possibly_image_based_count,
        "runtime_event_truth": False,
        "blocked_claims": [
            "fatigue truth",
            "load truth",
            "injury truth",
            "tactical truth",
            "dominance truth",
            "event truth override",
        ],
    }
    return manifest, pages, audit


def write_jsonl(rows: list[dict[str, Any]], out: Path) -> None:
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def render_audit_txt(audit: dict[str, Any], manifest: list[dict[str, Any]]) -> str:
    lines = [
        "HPFA REFERENCE DOCUMENT INGEST LITE V1",
        "=======================================",
        f"status={audit.get('status')}",
        f"claim_safety={audit.get('claim_safety')}",
        f"input_dir={audit.get('input_dir')}",
        f"active_match_mode={audit.get('active_match_mode')}",
        f"pdf_count={audit.get('pdf_count')}",
        f"page_count={audit.get('page_count')}",
        f"chars_total={audit.get('chars_total')}",
        f"texty_pages={audit.get('texty_pages')}",
        f"err_pages={audit.get('err_pages')}",
        f"runtime_event_truth={audit.get('runtime_event_truth')}",
        "",
        "[documents]",
    ]
    for row in manifest:
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_claims]"])
    for item in audit.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path, active_match_mode: bool = False, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    output_root = spine_runner.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    manifest, pages, audit = build_manifest_and_pages(input_dir, active_match_mode=active_match_mode)
    manifest_out = output_root / MANIFEST_JSON
    pages_out = output_root / PAGES_JSONL
    audit_json_out = output_root / AUDIT_JSON
    audit_txt_out = output_root / AUDIT_TXT

    audit["output_root"] = str(output_root)
    audit["outputs"] = {
        "manifest_json": str(manifest_out),
        "pages_jsonl": str(pages_out),
        "audit_json": str(audit_json_out),
        "audit_txt": str(audit_txt_out),
    }

    manifest_out.write_text(json.dumps({"documents": manifest}, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    write_jsonl(pages, pages_out)
    audit_json_out.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    audit_txt_out.write_text(render_audit_txt(audit, manifest), encoding="utf-8")
    return audit
