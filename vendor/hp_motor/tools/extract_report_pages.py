import json
import time
from pathlib import Path
from typing import Any, Dict

from PyPDF2 import PdfReader

from tools._shared import load_json, iter_report_records, get_report_id, get_pdf_path

INDEX_PATH = Path("artifacts/reports/index_reports.json")
OUT_DIR = Path("artifacts/reports/pages")

def page_text_safe(reader: PdfReader, page_index: int) -> str:
    # isolate slow/hanging pages with per-page try/except
    try:
        page = reader.pages[page_index]
        txt = page.extract_text() or ""
        # normalize line endings lightly
        return txt.replace("\r\n", "\n").replace("\r", "\n")
    except Exception as e:
        return f"__EXTRACT_ERR__:{type(e).__name__}:{e}"

def is_texty(sample: str) -> bool:
    # simple “text-based PDF?” probe
    s = sample.strip()
    if not s:
        return False
    # reject pages that are mostly extraction errors or whitespace
    if s.startswith("__EXTRACT_ERR__"):
        return False
    # heuristic: enough alpha chars
    alpha = sum(ch.isalpha() for ch in s)
    return alpha >= 40

def main() -> None:
    if not INDEX_PATH.exists():
        print(f"ERR: missing {INDEX_PATH}")
        raise SystemExit(2)

    index_obj: Any = load_json(INDEX_PATH)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total_reports = 0
    for i, rec in enumerate(iter_report_records(index_obj)):
        total_reports += 1
        report_id = get_report_id(rec, i)
        pdf_path = get_pdf_path(rec)

        if not pdf_path:
            print(f"ERR: {report_id} missing pdf_path/source_path/path/file_path")
            continue

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            # try relative to repo root
            pdf_file = Path(".") / pdf_path
        if not pdf_file.exists():
            print(f"ERR: {report_id} pdf not found: {pdf_path}")
            continue

        out_path = OUT_DIR / f"{report_id}.jsonl"

        t0 = time.time()
        try:
            reader = PdfReader(str(pdf_file))
            n_pages = len(reader.pages)
        except Exception as e:
            print(f"ERR: {report_id} open failed: {type(e).__name__}:{e}")
            continue

        chars_total = 0
        texty_pages = 0
        err_pages = 0

        # write jsonl with per-page flush
        with out_path.open("w", encoding="utf-8") as f:
            for p in range(n_pages):
                txt = page_text_safe(reader, p)
                if txt.startswith("__EXTRACT_ERR__"):
                    err_pages += 1
                else:
                    chars_total += len(txt)
                    if is_texty(txt):
                        texty_pages += 1

                row: Dict[str, Any] = {
                    "report_id": report_id,
                    "pdf_path": str(pdf_file),
                    "page_index": p,
                    "text": txt,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()

        dt = time.time() - t0
        # classify pdf mode quickly (not perfect, but operationally useful)
        mode = "text_based" if texty_pages >= max(1, int(0.2 * n_pages)) else "possibly_image_based"
        print(
            f"OK: {report_id} pages={n_pages} chars_total={chars_total} "
            f"texty_pages={texty_pages} err_pages={err_pages} mode={mode} dt={dt:.2f}s out={out_path}"
        )

    if total_reports == 0:
        print("ERR: no records found in index (iter_report_records returned empty)")
        raise SystemExit(3)

if __name__ == "__main__":
    main()
