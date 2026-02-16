from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent.parent / "narrative_rules.yaml"


class GuardParseError(Exception):
    pass


@dataclass
class Hit:
    rule: str
    detail: str


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1].strip()
    return s


def _parse_inline_list(v: str) -> List[str]:
    v = v.strip()
    if not (v.startswith("[") and v.endswith("]")):
        raise GuardParseError("expected inline list [..]")
    inner = v[1:-1].strip()
    if inner == "":
        return []
    parts: List[str] = []
    buf = ""
    in_q: Optional[str] = None
    for ch in inner:
        if in_q:
            buf += ch
            if ch == in_q:
                in_q = None
        else:
            if ch in ("'", '"'):
                in_q = ch
                buf += ch
            elif ch == ",":
                if buf.strip():
                    parts.append(buf.strip())
                buf = ""
            else:
                buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return [_strip_quotes(p) for p in parts if p.strip() != ""]


def _parse_scalar(v: str) -> str:
    v = v.strip()
    return _strip_quotes(v)


def load_rules_yaml(path: Path = DEFAULT_RULES_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise GuardParseError(f"rules file not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()

    def clean(line: str) -> str:
        if "#" in line:
            pre = line.split("#", 1)[0]
            return pre.rstrip("\n")
        return line.rstrip("\n")

    lines = [clean(l).rstrip() for l in lines]
    lines = [l for l in lines if l.strip() != ""]

    if not lines or lines[0].strip() != "rules:":
        raise GuardParseError("YAML must start with 'rules:'")

    rules: Dict[str, Dict[str, Any]] = {}
    current_rule: Optional[str] = None

    for idx, line in enumerate(lines[1:], start=2):
        if line.startswith("  ") and not line.startswith("    "):
            if not line.strip().endswith(":"):
                raise GuardParseError(f"invalid rule header at line {idx}: {line}")
            rule_name = line.strip()[:-1].strip()
            if not rule_name:
                raise GuardParseError(f"empty rule name at line {idx}")
            rules[rule_name] = {}
            current_rule = rule_name
            continue

        if line.startswith("    "):
            if current_rule is None:
                raise GuardParseError(f"kv without rule at line {idx}: {line}")
            if ":" not in line:
                raise GuardParseError(f"invalid kv at line {idx}: {line}")
            k, v = line.strip().split(":", 1)
            k = k.strip()
            v = v.strip()
            if k == "terms":
                rules[current_rule][k] = _parse_inline_list(v)
            else:
                rules[current_rule][k] = _parse_scalar(v)
            continue

        raise GuardParseError(f"unexpected indentation at line {idx}: {line}")

    return {"rules": rules}


def _mask_quotes_per_line(line: str) -> Tuple[str, Optional[str]]:
    if '"' not in line:
        return line, None

    masked: List[str] = []
    in_q = False
    for ch in line:
        if ch == '"':
            in_q = not in_q
            masked.append('"')
        else:
            masked.append(" " if in_q else ch)

    if in_q:
        return line, "UNMATCHED_QUOTES"
    return "".join(masked), None


def _compile_regex_fail_closed(pat: str) -> re.Pattern:
    try:
        return re.compile(pat)
    except Exception as e:
        raise GuardParseError(f"bad regex: {e}")


def validate_narrative(text: str, state: str | None = None) -> dict:
    if not isinstance(text, str):
        return {"decision": "DENY", "canonical": None, "hits": [{"rule": "FAIL_CLOSED", "detail": "text_not_str"}]}

    try:
        cfg = load_rules_yaml()
        rules = cfg["rules"]
    except Exception as e:
        return {"decision": "DENY", "canonical": None, "hits": [{"rule": "FAIL_CLOSED", "detail": f"rules_load:{e}"}]}

    hits: List[Dict[str, str]] = []
    st = state.strip().upper() if isinstance(state, str) and state.strip() else None

    if st == "UNVALIDATED":
        allow_re = rules.get("unvalidated_gate", {}).get("allow_log_regex", "")
        try:
            allow_pat = _compile_regex_fail_closed(allow_re)
        except Exception as e:
            return {"decision": "DENY", "canonical": None, "hits": [{"rule": "FAIL_CLOSED", "detail": f"allow_log_regex:{e}"}]}
        if allow_pat.match(text.strip()):
            return {"decision": "PASS", "canonical": None, "hits": [{"rule": "UNVALIDATED_GATE", "detail": "allow_log_line"}]}
        return {"decision": "DENY", "canonical": None, "hits": [{"rule": "UNVALIDATED_GATE", "detail": "state_unvalidated_deny_all"}]}

    lines = text.splitlines() or [text]
    masked_lines: List[str] = []
    for ln in lines:
        if ln.lstrip().startswith(">"):
            masked_lines.append("")
            continue
        masked, err = _mask_quotes_per_line(ln)
        if err:
            return {"decision": "DENY", "canonical": None, "hits": [{"rule": "FAIL_CLOSED", "detail": err}]}
        masked_lines.append(masked)

    scan_text = "\n".join(masked_lines)

    deny_terms = rules.get("deny_uncertainty", {}).get("terms", [])
    if not isinstance(deny_terms, list):
        return {"decision": "DENY", "canonical": None, "hits": [{"rule": "FAIL_CLOSED", "detail": "deny_terms_not_list"}]}

    term_hits = []
    for t in deny_terms:
        if not isinstance(t, str) or t.strip() == "":
            continue
        tt = re.escape(t.strip())
        pat = rf"(?i)\b{tt}\b"
        if re.search(pat, scan_text):
            term_hits.append(t.strip())

    if term_hits:
        hits.append({"rule": "DENY_UNCERTAINTY", "detail": f"terms={term_hits}"})
        return {"decision": "DENY", "canonical": None, "hits": hits}

    if st == "CONTESTED":
        rr = rules.get("rewrite_contested_possession_claim", {})
        rex = rr.get("regex", "")
        canon = rr.get("canonical", "")
        try:
            pat = _compile_regex_fail_closed(rex)
        except Exception as e:
            return {"decision": "DENY", "canonical": None, "hits": [{"rule": "FAIL_CLOSED", "detail": f"rewrite_contested_regex:{e}"}]}
        if pat.search(scan_text):
            hits.append({"rule": "REWRITE_CONTESTED_POSSESSION", "detail": "matched"})
            return {"decision": "REWRITE", "canonical": canon, "hits": hits}

    if st == "DEAD_BALL":
        rr = rules.get("rewrite_dead_ball_in_play_claim", {})
        rex = rr.get("regex", "")
        canon = rr.get("canonical", "")
        try:
            pat = _compile_regex_fail_closed(rex)
        except Exception as e:
            return {"decision": "DENY", "canonical": None, "hits": [{"rule": "FAIL_CLOSED", "detail": f"rewrite_dead_ball_regex:{e}"}]}
        if pat.search(scan_text):
            hits.append({"rule": "REWRITE_DEAD_BALL_IN_PLAY", "detail": "matched"})
            return {"decision": "REWRITE", "canonical": canon, "hits": hits}

    return {"decision": "PASS", "canonical": None, "hits": hits}
