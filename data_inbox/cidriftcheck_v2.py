#!/usr/bin/env python3
"""
cidriftcheck_v2.py

Scope separation:
- ENUM_DRIFT: canonical_actions, possession_effects, allowed_states, fail_closed_defaults
- ALIAS_COLLISION: aliases only (normalized lower+strip)

Inputs:
  --canon-action-registry action_registry.yaml   (expects YAML with canonical_action + aliases)
  --code-enums code_enums.json                  (runtime/code side enums)

Outputs:
  --out-json drift_report.json
  --out-md   drift_report.md

Exit codes:
  0 = clean (no enum drift, no alias collisions)
  1 = drift/collision found
  2 = input/parse error
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Any, Tuple, Optional


# ---------------------------
# Minimal YAML for *this file*
# Supports:
# - key: value
# - key: [a,b,c]
# - key:
#     - item
#     + - item2
# Enough for action_registry_v1.0.1.yaml style blocks.
# ---------------------------

class ParseError(Exception):
    pass


def _strip_comment(line: str) -> str:
    if "#" in line:
        return line.split("#", 1)[0]
    return line


def _parse_inline_list(raw: str, line_no: int, line: str) -> List[str]:
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        raise ParseError(f"line {line_no}: inline list must be [..] :: {line!r}")
    inner = raw[1:-1].strip()
    if not inner:
        return []
    parts = [p.strip() for p in inner.split(",")]
    if any(p == "" for p in parts):
        raise ParseError(f"line {line_no}: empty item in inline list :: {line!r}")
    return parts


def _is_block_list_item(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("- ") or s.startswith("+ - ")


def _parse_block_list_item(line: str, line_no: int) -> str:
    s = line.lstrip()
    if s.startswith("+ - "):
        return s[len("+ - "):].strip()
    if s.startswith("- "):
        return s[len("- "):].strip()
    raise ParseError(f"line {line_no}: invalid block list item :: {line!r}")


def load_yaml_minimal(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise ParseError(f"file not found: {path}")

    out: Dict[str, Any] = {}
    lines = open(path, "r", encoding="utf-8").read().splitlines()

    current_key: Optional[str] = None
    current_list: Optional[List[str]] = None
    current_indent: Optional[int] = None

    for i, raw in enumerate(lines, start=1):
        line = _strip_comment(raw).rstrip("\r\n")
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))

        # if we are inside a block list
        if current_key is not None and current_list is not None:
            if indent <= (current_indent or 0):
                # close list context, re-process this line as a normal line
                out[current_key] = current_list
                current_key = None
                current_list = None
                current_indent = None
            else:
                if not _is_block_list_item(line):
                    raise ParseError(f"line {i}: expected list item under {current_key} :: {raw!r}")
                item = _parse_block_list_item(line, i)
                if item == "":
                    raise ParseError(f"line {i}: empty list item :: {raw!r}")
                current_list.append(item)
                continue

        # list item without header is forbidden
        if _is_block_list_item(line):
            raise ParseError(f"line {i}: list item outside block list :: {raw!r}")

        # key: rest
        if ":" not in line:
            raise ParseError(f"line {i}: missing ':' :: {raw!r}")
        key_part, rest = line.split(":", 1)
        key = key_part.strip()
        if not key:
            raise ParseError(f"line {i}: empty key :: {raw!r}")
        rest = rest.strip()

        if rest == "":
            # start block list
            current_key = key
            current_list = []
            current_indent = indent
            continue

        # scalar or inline list
        if rest.startswith("["):
            out[key] = _parse_inline_list(rest, i, raw)
        else:
            out[key] = rest

    if current_key is not None and current_list is not None:
        out[current_key] = current_list

    return out


# ---------------------------
# Action registry extraction
# ---------------------------

def parse_action_registry_yaml(path: str) -> Dict[str, Any]:
    """
    action_registry_v1.0.1.yaml format is a YAML list of blocks like:
      - canonical_action: GK_CATCH
        aliases: [a,b]
        possession_effect: START
        allowed_states: [CONTESTED, DEAD_BALL]
        fail_closed_default: UNVALIDATED

    Minimal parser approach:
    - We'll parse line-by-line with regex for the 5 fields.
    - aliases and allowed_states may be inline lists or block lists.
    Fail-closed if canonical_action missing.
    """
    text = open(path, "r", encoding="utf-8").read().splitlines()

    items: List[Dict[str, Any]] = []
    cur: Dict[str, Any] = {}

    def flush():
        nonlocal cur
        if cur:
            items.append(cur)
            cur = {}

    key_re = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*(.*)\s*$")
    dash_re = re.compile(r"^\s*-\s+([A-Za-z0-9_]+)\s*:\s*(.*)\s*$")

    # block list capture
    active_list_key: Optional[str] = None
    active_list_indent: Optional[int] = None
    active_list: Optional[List[str]] = None

    for idx, raw in enumerate(text, start=1):
        line = _strip_comment(raw).rstrip("\r\n")
        if not line.strip():
            continue

        # new item begins with "- canonical_action:"
        m = dash_re.match(line)
        if m:
            # close any pending list
            if active_list_key and active_list is not None:
                cur[active_list_key] = active_list
                active_list_key = None
                active_list = None
                active_list_indent = None

            # flush previous item
            flush()

            k = m.group(1)
            v = m.group(2).strip()
            if k != "canonical_action":
                raise ParseError(f"line {idx}: expected '- canonical_action:' got '- {k}:' :: {raw!r}")
            cur["canonical_action"] = v
            continue

        # handle active block list
        if active_list_key and active_list is not None:
            indent = len(line) - len(line.lstrip(" "))
            if indent <= (active_list_indent or 0):
                # list ended; finalize and fallthrough to parse current line normally
                cur[active_list_key] = active_list
                active_list_key = None
                active_list = None
                active_list_indent = None
            else:
                if not _is_block_list_item(line):
                    raise ParseError(f"line {idx}: expected list item for {active_list_key} :: {raw!r}")
                active_list.append(_parse_block_list_item(line, idx))
                continue

        m2 = key_re.match(line)
        if not m2:
            continue

        key = m2.group(1)
        rest = m2.group(2).strip()

        if rest == "":
            # start block list
            active_list_key = key
            active_list_indent = len(line) - len(line.lstrip(" "))
            active_list = []
            continue

        if rest.startswith("["):
            cur[key] = _parse_inline_list(rest, idx, raw)
        else:
            cur[key] = rest

    if active_list_key and active_list is not None:
        cur[active_list_key] = active_list

    flush()

    # build canonical maps
    actions: List[str] = []
    aliases: List[str] = []
    for it in items:
        ca = it.get("canonical_action")
        if not ca:
            raise ParseError("canonical_action missing in at least one block")
        actions.append(ca)
        al = it.get("aliases", [])
        if isinstance(al, list):
            aliases.extend(al)

    return {
        "canonical_actions": sorted(set(actions)),
        "aliases": aliases  # raw list; collision check will normalize
    }


# ---------------------------
# Checks
# ---------------------------

ENUM_KEYS = ["canonical_actions", "possession_effects", "allowed_states", "fail_closed_defaults"]

def check_enum_drift(canon_enums: Dict[str, List[str]], code_enums: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for k in ENUM_KEYS:
        c = canon_enums.get(k, [])
        r = code_enums.get(k, [])
        cset, rset = set(c), set(r)
        missing = sorted(cset - rset)
        extra = sorted(rset - cset)
        if missing:
            issues.append({"type": "ENUM_DRIFT", "key": k, "reason": "missing_values", "missing": missing, "severity": "HIGH"})
        if extra:
            issues.append({"type": "ENUM_DRIFT", "key": k, "reason": "extra_values", "extra": extra, "severity": "HIGH"})
    return issues


def normalize_alias(s: str) -> str:
    return s.strip().lower()


def check_alias_collision(alias_list: List[str]) -> List[Dict[str, Any]]:
    mp: Dict[str, List[str]] = {}
    for a in alias_list:
        n = normalize_alias(a)
        mp.setdefault(n, []).append(a)
    issues = []
    for n, group in mp.items():
        if len(group) > 1:
            issues.append({"type": "ALIAS_COLLISION", "normalized": n, "examples": group[:10], "count": len(group), "severity": "CRITICAL"})
    return issues


# ---------------------------
# Reporting
# ---------------------------

def write_json(obj: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def write_md(obj: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Drift Report (v2)\n\n")
        s = obj["summary"]
        f.write("## Summary\n")
        f.write(f"- enum_drift_count: {s['enum_drift_count']}\n")
        f.write(f"- alias_collision_count: {s['alias_collision_count']}\n\n")
        f.write("## Enum Drift Issues\n")
        for it in obj["enum_drift"]:
            f.write(f"- {it['key']} :: {it['reason']} :: {it.get('missing') or it.get('extra')}\n")
        f.write("\n## Alias Collisions\n")
        for it in obj["alias_collision"]:
            f.write(f"- normalized='{it['normalized']}' count={it['count']} examples={it['examples']}\n")


# ---------------------------
# CLI
# ---------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canon-action-registry", required=True)
    ap.add_argument("--code-enums", required=True)
    ap.add_argument("--out-json", default="drift_report.json")
    ap.add_argument("--out-md", default="drift_report.md")
    args = ap.parse_args()

    try:
        canon = parse_action_registry_yaml(args.canon_action_registry)
        code = json.load(open(args.code_enums, "r", encoding="utf-8"))

        # canon enums: use action_registry actions + code_enums for non-action enums (until canon_enums.yaml exists)
        canon_enums = {
            "canonical_actions": canon["canonical_actions"],
            "possession_effects": code.get("possession_effects", []),
            "allowed_states": code.get("allowed_states", []),
            "fail_closed_defaults": code.get("fail_closed_defaults", []),
        }

        enum_issues = check_enum_drift(canon_enums, code)
        alias_issues = check_alias_collision(canon["aliases"])

        report = {
            "summary": {
                "enum_drift_count": len(enum_issues),
                "alias_collision_count": len(alias_issues),
            },
            "enum_drift": enum_issues,
            "alias_collision": alias_issues,
        }

        write_json(report, args.out_json)
        write_md(report, args.out_md)

        if enum_issues or alias_issues:
            sys.exit(1)
        sys.exit(0)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
