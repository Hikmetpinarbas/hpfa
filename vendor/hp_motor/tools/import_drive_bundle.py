#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

ARTIFACTS_DIR = Path("artifacts") / "import"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

RX_TR = str.maketrans({"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"})

def norm(s: str) -> str:
    x = (s or "").strip().lower().translate(RX_TR)
    x = re.sub(r"[^a-z0-9]+", "_", x).strip("_")
    return x

def sha256(p: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

@dataclass
class Route:
    bucket: str
    dest_dir: Path
    reason: str

def decide_route(p: Path) -> Route:
    name = p.name
    n = norm(name)
    ext = p.suffix.lower()

    # --- registry canonical candidates ---
    if ext in {".json", ".yaml", ".yml", ".csv", ".xlsx"}:
        if ("metric_encyclopedia" in n) or ("metric_dictionary" in n) or ("hp_metric" in n and "encyclopedia" in n):
            return Route("registry/canonical", Path("hp_motor/library/registry/inputs/canonical"), "metric encyclopedia/dictionary")
        if ("metric_registry" in n) or (("registry" in n) and ("metric" in n)) or ("sportsbase_metrics" in n):
            return Route("registry/vendor", Path("hp_motor/library/registry/inputs/vendor"), "vendor registry/metrics")
        if ("6faz" in n) or ("phase" in n) or ("map" in n) or ("index" in n):
            return Route("registry/maps", Path("hp_motor/library/registry/inputs/maps"), "phase/map/index")
        if ("guide" in n) or ("readme" in n) or ("integration" in n):
            return Route("registry/guides", Path("hp_motor/library/registry/inputs/guides"), "guide/readme")

    # --- docs / research ---
    if ext in {".docx", ".pdf", ".txt", ".md"}:
        # keep as docs, not in core
        return Route("docs", Path("hp_motor/library/inputs/drive_hp_proj_docs"), "documents/research")

    # --- packages ---
    if ext in {".zip", ".7z", ".rar"}:
        return Route("packages", Path("hp_motor/library/inputs/drive_hp_proj_packages"), "zip packages")

    return Route("other", Path("hp_motor/library/inputs/drive_hp_proj_other"), "uncategorized")

def safe_copy(src: Path, dest_dir: Path, dedupe_by_hash: Dict[str, str]) -> Tuple[str, str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    h = sha256(src)

    if h in dedupe_by_hash:
        return ("skipped_duplicate_hash", dedupe_by_hash[h])

    dest = dest_dir / src.name

    if dest.exists():
        try:
            if sha256(dest) == h:
                dedupe_by_hash[h] = str(dest)
                return ("skipped_duplicate_hash", str(dest))
        except Exception:
            pass

        stem = dest.stem
        suf = dest.suffix
        k = 2
        while True:
            cand = dest_dir / f"{stem}_dup{k}{suf}"
            if not cand.exists():
                dest = cand
                break
            k += 1

    shutil.copy2(src, dest)
    dedupe_by_hash[h] = str(dest)
    return ("copied", str(dest))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="hp_motor/library/inputs/drive_hp_proj", help="source folder")
    ap.add_argument("--apply", action="store_true", help="actually copy routed files (default: dry-run)")
    args = ap.parse_args()

    src_root = Path(args.src)
    if not src_root.exists():
        raise SystemExit(f"source not found: {src_root}")

    files = [p for p in src_root.rglob("*") if p.is_file()]
    files_sorted = sorted(files, key=lambda p: p.stat().st_size, reverse=True)

    report = {
        "src": str(src_root),
        "file_count": len(files),
        "apply": bool(args.apply),
        "routes": {},
        "actions": [],
        "top_largest": [],
        "errors": [],
        "warnings": [],
    }


    # --- inbox hygiene (dry-run warning only) ---
    # If docs are still in INBOX, the repo may grow silently.
    inbox_doc_ext = {".pdf", ".docx", ".txt", ".md"}
    inbox_docs = [p for p in files if p.suffix.lower() in inbox_doc_ext]
    if inbox_docs:
        total_bytes = sum(p.stat().st_size for p in inbox_docs)
        report["warnings"].append({
            "kind": "inbox_contains_docs",
            "doc_count": len(inbox_docs),
            "total_bytes": total_bytes,
            "note": "INBOX contains docs; prefer routing into drive_hp_proj_docs and keeping INBOX small."
        })
    for p in files_sorted[:30]:
        report["top_largest"].append({"size": p.stat().st_size, "path": str(p)})

    dedupe_by_hash: Dict[str, str] = {}

    for p in files_sorted:
        try:
            r = decide_route(p)
            report["routes"][r.bucket] = report["routes"].get(r.bucket, 0) + 1

            if args.apply:
                status, dest = safe_copy(p, r.dest_dir, dedupe_by_hash)
            else:
                status, dest = ("dry_run", str(r.dest_dir / p.name))

            report["actions"].append({
                "src": str(p),
                "bucket": r.bucket,
                "dest": dest,
                "status": status,
                "reason": r.reason,
            })
        except Exception as e:
            report["errors"].append({"src": str(p), "error": str(e)})

    out = ARTIFACTS_DIR / "drive_import_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK: import report ->", out)
    print("file_count:", report["file_count"])
    print("apply:", report["apply"])
    print("routes:", report["routes"])
    if report["errors"]:
        print("errors:", len(report["errors"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
