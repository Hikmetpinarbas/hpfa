#!/usr/bin/env python3
"""
cidriftcheck.py (Termux/CI friendly)

Canon (YAML) ile kod tarafı enum/state/action listelerini (JSON export) karşılaştırır.
Drift raporu üretir.

Exit codes:
  0 -> No drift (doc_only=0 and code_only=0)
  1 -> Drift detected (doc_only>0 or code_only>0)
  2 -> Input/parse error
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

def _strip_comments(line: str) -> str:
    # Minimal: quoted # korunmuyor; bu tool için yeterli
    return line.split("#", 1)[0]

def _unquote(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s

def _parse_scalar(v: str) -> Any:
    v = v.strip()
    if v == "":
        return ""
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip() for p in inner.split(",")]
        return [_unquote(p) for p in parts if p]
    return _unquote(v)

def load_yaml_minimal(path: str) -> Any:
    """Subset YAML: list-of-maps ve basit key:list destekler."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    lines: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = _strip_comments(raw.rstrip("\n"))
            if raw.strip():
                lines.append(raw)

    # list-of-maps: "- key: val"
    if any(re.match(r"^\s*-\s+\w+\s*:", ln) for ln in lines):
        items: List[Dict[str, Any]] = []
        current: Dict[str, Any] | None = None
        last_list_key: str | None = None

        for ln in lines:
            m = re.match(r"^\s*-\s+(\w+)\s*:\s*(.*)\s*$", ln)
            if m:
                if current is not None:
                    items.append(current)
                current = {m.group(1): _parse_scalar(m.group(2))}
                last_list_key = None
                continue

            m2 = re.match(r"^\s+(\w+)\s*:\s*(.*)\s*$", ln)
            if m2 and current is not None:
                k = m2.group(1)
                v = m2.group(2).strip()
                current[k] = _parse_scalar(v) if v else []
                last_list_key = k if v == "" else None
                continue

            m3 = re.match(r"^\s+-\s*(.+?)\s*$", ln)
            if m3 and current is not None and last_list_key and isinstance(current.get(last_list_key), list):
                current[last_list_key].append(_parse_scalar(m3.group(1)))
                continue

        if current is not None:
            items.append(current)
        return items

    # key: [a,b] or key:\n - a
    data: Dict[str, Any] = {}
    cur_key: str | None = None
    for ln in lines:
        m = re.match(r"^\s*(\w+)\s*:\s*(.*)\s*$", ln)
        if m:
            cur_key = m.group(1)
            rest = m.group(2).strip()
            data[cur_key] = _parse_scalar(rest) if rest else []
            continue
        m2 = re.match(r"^\s*-\s*(.+?)\s*$", ln)
        if m2 and cur_key is not None and isinstance(data.get(cur_key), list):
            data[cur_key].append(_parse_scalar(m2.group(1)))
            continue
    return data

def extract_canon_from_action_registry(obj: Any) -> Dict[str, List[str]]:
    """Your registry YAML -> lists for drift compare."""
    out: Dict[str, List[str]] = {
        "canonical_actions": [],
        "aliases": [],
        "possession_effects": [],
        "allowed_states": [],
        "fail_closed_defaults": [],
    }
    if not isinstance(obj, list):
        return out

    for item in obj:
        if not isinstance(item, dict):
            continue

        ca = item.get("canonical_action")
        if isinstance(ca, str):
            out["canonical_actions"].append(ca)

        al = item.get("aliases", [])
        if isinstance(al, list):
            out["aliases"].extend([a for a in al if isinstance(a, str)])

        pe = item.get("possession_effect")
        if isinstance(pe, str):
            out["possession_effects"].append(pe)

        st = item.get("allowed_states", [])
        if isinstance(st, list):
            out["allowed_states"].extend([s for s in st if isinstance(s, str)])

        fd = item.get("fail_closed_default")
        if isinstance(fd, str):
            out["fail_closed_defaults"].append(fd)

    for k in out:
        out[k] = sorted(set(out[k]))
    return out

def similar(a: str, b: str) -> bool:
    na = re.sub(r"[\s\-]+", "_", a.lower())
    nb = re.sub(r"[\s\-]+", "_", b.lower())
    ta = set(na.split("_"))
    tb = set(nb.split("_"))
    if not ta or not tb:
        return False
    overlap = len(ta & tb) / max(len(ta), len(tb))
    return overlap >= 0.6

def compare_lists(doc_list: List[str], code_list: List[str]) -> Tuple[List[str], List[str], List[Tuple[str, str]]]:
    docset = set(doc_list)
    codeset = set(code_list)

    doc_only = sorted(docset - codeset)
    code_only = sorted(codeset - docset)

    mismatches: List[Tuple[str, str]] = []
    for d in doc_only[:]:
        for c in code_only[:]:
            if similar(d, c):
                mismatches.append((d, c))
                doc_only.remove(d)
                code_only.remove(c)
                break

    return doc_only, code_only, mismatches

def build_report(canon: Dict[str, List[str]], code: Dict[str, List[str]]) -> Dict[str, Any]:
    report: Dict[str, Any] = {"summary": {}, "details": {}}
    keys = sorted(set(canon.keys()) | set(code.keys()))

    total_doc_only = 0
    total_code_only = 0
    total_warn = 0

    for k in keys:
        doc_list = canon.get(k, [])
        code_list = code.get(k, [])
        doc_only, code_only, mismatches = compare_lists(doc_list, code_list)
        report["details"][k] = {
            "doc_only": doc_only,
            "code_only": code_only,
            "mismatch": [{"doc": d, "code": c} for d, c in mismatches],
        }
        total_doc_only += len(doc_only)
        total_code_only += len(code_only)
        total_warn += len(mismatches)

    report["summary"] = {
        "doc_only_count": total_doc_only,
        "code_only_count": total_code_only,
        "mismatch_count": total_warn,
    }
    return report

def write_json(report: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

def write_markdown(report: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Drift Report\n\n")
        f.write("## Summary\n")
        f.write(f"- Doc-only: {report['summary']['doc_only_count']}\n")
        f.write(f"- Code-only: {report['summary']['code_only_count']}\n")
        f.write(f"- Mismatch (WARN): {report['summary']['mismatch_count']}\n\n")
        f.write("## Details\n\n")
        for key, block in report["details"].items():
            f.write(f"### {key}\n")
            f.write(f"- Doc-only: {block['doc_only']}\n")
            f.write(f"- Code-only: {block['code_only']}\n")
            f.write(f"- Mismatch: {block['mismatch']}\n\n")

def load_code_enums_json(path: str) -> Dict[str, List[str]]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    obj = json.load(open(path, "r", encoding="utf-8"))
    out: Dict[str, List[str]] = {}
    for k, v in obj.items():
        if isinstance(v, list):
            out[k] = [str(x) for x in v]
    return out

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canon-action-registry", required=True, help="Canonical action registry YAML")
    ap.add_argument("--code-enums", required=True, help="Code enums JSON export")
    ap.add_argument("--out-json", default="drift_report.json")
    ap.add_argument("--out-md", default="drift_report.md")
    args = ap.parse_args()

    try:
        canon_obj = load_yaml_minimal(args.canon_action_registry)
        canon = extract_canon_from_action_registry(canon_obj)
        code = load_code_enums_json(args.code_enums)

        report = build_report(canon, code)
        write_json(report, args.out_json)
        write_markdown(report, args.out_md)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    if report["summary"]["doc_only_count"] > 0 or report["summary"]["code_only_count"] > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
