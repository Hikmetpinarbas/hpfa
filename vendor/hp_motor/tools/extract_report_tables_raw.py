import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

PAGES_DIR = Path("artifacts/reports/pages")
OUT_DIR = Path("artifacts/reports/tables")

RE_MULTI_SPACE = re.compile(r"[ \t]{2,}")
RE_NUM = re.compile(r"[-+]?\d+(?:[\.,]\d+)?%?")

RE_RANK_START = re.compile(r"^\s*\d+\s+")
RE_SCORE = re.compile(r"\d+\s*[:\-–]\s*\d+")  # 12:8 or 12-8


def classify_line(line: str) -> Tuple[bool, str]:
    """
    Returns (is_tableish, kind)
      kind: pipe | spaced | numeric | none
    """
    s = line.strip()
    if not s:
        return False, "none"

    # ignore obvious footers/headers (soft)
    if len(s) < 8:
        return False, "none"
    if s.lower().startswith(("page ", "sayfa ")):
        return False, "none"

    # pipe tables
    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
        nonempty = sum(1 for p in parts if p)
        if nonempty >= 3:
            return True, "pipe"

    # spaced columns
    if RE_MULTI_SPACE.search(s):
        # require multiple chunks to look like columns
        chunks = [c for c in RE_MULTI_SPACE.split(s) if c.strip()]
        if len(chunks) >= 3:
            return True, "spaced"

    # standings-like row (no header required)
    # rank TEAM ... many numbers; allow single-space separated PDFs
    if RE_RANK_START.match(s):
        nums = RE_NUM.findall(s)
        # reject lines that look like minutes distribution (0-15 etc.)
        if not re.search(r"\b0\s*[-–]\s*15\b", s) and len(nums) >= 8:
            return True, "standings_row"

    # numeric density hint
    nums = RE_NUM.findall(s)
    if len(nums) >= 3:
        return True, "numeric"

    return False, "none"

def extract_from_jsonl(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            obj = json.loads(raw)
            report_id = obj.get("report_id", "")
            page_index = obj.get("page_index", -1)
            text = obj.get("text", "") or ""
            if text.startswith("__EXTRACT_ERR__"):
                continue

            # split into lines and keep table-ish ones
            for li, line in enumerate(text.split("\n")):
                ok, kind = classify_line(line)
                if not ok:
                    continue
                rows.append(
                    {
                        "report_id": str(report_id),
                        "page_index": str(page_index),
                        "line_index": str(li),
                        "kind": kind,
                        "text": line.strip(),
                    }
                )
    return rows

def main() -> None:
    if not PAGES_DIR.exists():
        print(f"ERR: missing {PAGES_DIR} (run extract_report_pages.py first)")
        raise SystemExit(2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    jsonl_files = sorted(PAGES_DIR.glob("*.jsonl"))
    if not jsonl_files:
        print(f"ERR: no jsonl found in {PAGES_DIR}")
        raise SystemExit(3)

    for jf in jsonl_files:
        report_id = jf.stem
        rows = extract_from_jsonl(jf)
        out_csv = OUT_DIR / f"{report_id}__tables_raw.csv"

        with out_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["report_id", "page_index", "line_index", "kind", "text"])
            w.writeheader()
            for r in rows:
                w.writerow(r)

        print(f"OK: {report_id} rows={len(rows)} out={out_csv}")

if __name__ == "__main__":
    main()
