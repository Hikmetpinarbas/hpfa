#!/usr/bin/env python3
"""
HPFA Data Quality Gate V1

Purpose:
    Fail-closed / degraded / pass validation for event-only ACTIVE_MATCH surfaces.

Authority rules:
    - This tool does not create runtime truth.
    - This tool does not validate football claims.
    - This tool only decides whether an event surface is usable by downstream HPFA modules.
    - PDF/reference/archive/sample files must not be treated as event truth.

Input:
    CSV or JSONL event table.

Output:
    JSON gate report with PASS / DEGRADED / FAIL_CLOSED status.
    Optional short text summary with next allowed actions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

FAIL_CLOSED = "FAIL_CLOSED"
DEGRADED = "DEGRADED"
PASS = "PASS"

DEFAULT_REQUIRED_ANY = [
    ("event_id", "id"),
    ("event_type", "type", "action_type", "action"),
    ("team_id", "team", "team_name"),
    ("period", "half"),
]

TIME_COLUMNS = ("timestamp", "time", "game_clock", "game_clock_ms", "minute", "second")
X_COLUMNS = ("x", "start_x", "location_x")
Y_COLUMNS = ("y", "start_y", "location_y")
REFERENCE_MARKERS = ("pdf", "reference", "archive", "sample", "match_tests", "match001", "quarantine")


@dataclass
class GateFinding:
    gate_id: str
    status: str
    message: str
    evidence: Dict[str, Any]


def is_blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == "" or v.strip().lower() in {"none", "null", "nan"}
    return False


def clean_str(v: Any) -> str:
    return "" if is_blank(v) else str(v).strip()


def read_rows(path: Path) -> Tuple[List[Dict[str, Any]], str]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, start=1):
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict):
                        obj.setdefault("__row_lineage__", {"line_no": line_no})
                        rows.append(obj)
                    else:
                        rows.append({"__parse_error__": s, "__row_lineage__": {"line_no": line_no}})
                except json.JSONDecodeError:
                    rows.append({"__parse_error__": s, "__row_lineage__": {"line_no": line_no}})
        return rows, "jsonl"

    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            rows = []
            for line_no, row in enumerate(reader, start=2):
                row = dict(row)
                row.setdefault("__row_lineage__", {"line_no": line_no})
                rows.append(row)
        return rows, "csv"

    raise SystemExit(f"Unsupported input extension: {suffix}. Use .csv or .jsonl")


def norm_key_map(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    keys = set()
    for row in rows[:1000]:
        keys.update(str(k) for k in row.keys())
    return {k.lower().strip(): k for k in keys}


def first_present(key_map: Dict[str, str], aliases: Iterable[str]) -> Optional[str]:
    for a in aliases:
        if a.lower() in key_map:
            return key_map[a.lower()]
    return None


def to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(float(v)) else None
    s = str(v).strip().replace(",", ".")
    if not s:
        return None
    try:
        val = float(s)
        return val if math.isfinite(val) else None
    except ValueError:
        return None


def valid_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in rows if "__parse_error__" not in r]


def gate_reference_exclusion(path: Path) -> GateFinding:
    p = str(path).lower()
    markers = [m for m in REFERENCE_MARKERS if m in p]
    if markers:
        return GateFinding(
            "G09_REFERENCE_EXCLUSION",
            FAIL_CLOSED,
            "Input path contains reference/archive/sample marker; cannot be event truth.",
            {"markers": markers, "path": str(path)},
        )
    return GateFinding("G09_REFERENCE_EXCLUSION", PASS, "No reference marker detected in input path.", {"path": str(path)})


def gate_parse_errors(rows: List[Dict[str, Any]]) -> GateFinding:
    parse_errors = [r for r in rows if "__parse_error__" in r]
    if not parse_errors:
        return GateFinding("G00_PARSE", PASS, "No parse errors detected.", {"parse_error_count": 0})
    return GateFinding(
        "G00_PARSE",
        FAIL_CLOSED,
        "Parse errors detected in input rows.",
        {
            "parse_error_count": len(parse_errors),
            "line_sample": [r.get("__row_lineage__", {}) for r in parse_errors[:10]],
        },
    )


def gate_schema(rows: List[Dict[str, Any]]) -> GateFinding:
    rows = valid_rows(rows)
    if not rows:
        return GateFinding("G01_SCHEMA", FAIL_CLOSED, "No valid rows found.", {"row_count": 0})
    key_map = norm_key_map(rows)
    missing_groups = []
    selected = {}
    for group in DEFAULT_REQUIRED_ANY:
        found = first_present(key_map, group)
        if not found:
            missing_groups.append(list(group))
        else:
            selected[group[0]] = found
    if missing_groups:
        return GateFinding("G01_SCHEMA", FAIL_CLOSED, "Required semantic fields are missing.", {"missing_any_of": missing_groups, "selected": selected})
    return GateFinding("G01_SCHEMA", PASS, "Required semantic fields are present.", {"selected": selected, "row_count": len(rows)})


def gate_duplicate(rows: List[Dict[str, Any]]) -> GateFinding:
    rows = valid_rows(rows)
    key_map = norm_key_map(rows)
    event_col = first_present(key_map, ("event_id", "id"))
    if not event_col:
        return GateFinding("G02_DUPLICATE", DEGRADED, "No event id column; duplicate audit degraded.", {})
    vals = [clean_str(r.get(event_col, "")) for r in rows if clean_str(r.get(event_col, ""))]
    counts = Counter(vals)
    duplicate_ids = [k for k, v in counts.items() if v > 1]
    duplicate_rate = len(duplicate_ids) / max(len(counts), 1)
    status = FAIL_CLOSED if duplicate_rate > 0.01 else PASS
    return GateFinding("G02_DUPLICATE", status, "Duplicate event id audit completed.", {"event_col": event_col, "duplicate_id_count": len(duplicate_ids), "duplicate_rate": round(duplicate_rate, 6)})


def gate_coordinates(rows: List[Dict[str, Any]]) -> GateFinding:
    rows = valid_rows(rows)
    key_map = norm_key_map(rows)
    x_col = first_present(key_map, X_COLUMNS)
    y_col = first_present(key_map, Y_COLUMNS)
    if not x_col or not y_col:
        return GateFinding("G03_COORDINATE", DEGRADED, "Coordinate columns missing; spatial modules must degrade.", {"x_col": x_col, "y_col": y_col})
    checked = 0
    bad = 0
    for r in rows:
        x = to_float(r.get(x_col))
        y = to_float(r.get(y_col))
        if x is None or y is None:
            continue
        checked += 1
        metric_pitch = 0 <= x <= 105 and 0 <= y <= 68
        normalized_pitch = 0 <= x <= 100 and 0 <= y <= 100
        if not (metric_pitch or normalized_pitch):
            bad += 1
    if checked == 0:
        return GateFinding("G03_COORDINATE", DEGRADED, "Coordinates present but not numeric.", {"x_col": x_col, "y_col": y_col})
    bad_rate = bad / checked
    status = FAIL_CLOSED if bad_rate > 0.01 else PASS
    return GateFinding("G03_COORDINATE", status, "Coordinate bounds audit completed.", {"x_col": x_col, "y_col": y_col, "checked": checked, "bad": bad, "bad_rate": round(bad_rate, 6)})


def gate_temporal(rows: List[Dict[str, Any]]) -> GateFinding:
    rows = valid_rows(rows)
    key_map = norm_key_map(rows)
    time_col = first_present(key_map, TIME_COLUMNS)
    period_col = first_present(key_map, ("period", "half"))
    if not time_col:
        return GateFinding("G04_TEMPORAL", DEGRADED, "No usable time column; sequence timing must degrade.", {"time_col": None})
    prev: Dict[str, float] = {}
    jumps = 0
    checked = 0
    for r in rows:
        t = to_float(r.get(time_col))
        if t is None:
            continue
        p = clean_str(r.get(period_col, "unknown")) if period_col else "unknown"
        checked += 1
        if p in prev and t < prev[p]:
            jumps += 1
        prev[p] = t
    if checked == 0:
        return GateFinding("G04_TEMPORAL", DEGRADED, "Time column present but not numeric.", {"time_col": time_col})
    jump_rate = jumps / checked
    status = FAIL_CLOSED if jump_rate > 0.01 else PASS
    return GateFinding("G04_TEMPORAL", status, "Temporal monotonicity audit completed.", {"time_col": time_col, "period_col": period_col, "checked": checked, "backward_jumps": jumps, "jump_rate": round(jump_rate, 6)})


def gate_team_identity(rows: List[Dict[str, Any]]) -> GateFinding:
    rows = valid_rows(rows)
    key_map = norm_key_map(rows)
    team_col = first_present(key_map, ("team_id", "team", "team_name"))
    if not team_col:
        return GateFinding("G05_TEAM_IDENTITY", FAIL_CLOSED, "No team identity column.", {})
    missing_count = sum(1 for r in rows if not clean_str(r.get(team_col, "")))
    teams = sorted({clean_str(r.get(team_col, "")) for r in rows if clean_str(r.get(team_col, ""))})
    missing_rate = missing_count / max(len(rows), 1)
    if missing_count == len(rows) or missing_rate > 0.01:
        status = FAIL_CLOSED
    else:
        status = PASS if 1 <= len(teams) <= 4 else DEGRADED
    return GateFinding("G05_TEAM_IDENTITY", status, "Team identity audit completed.", {"team_col": team_col, "team_count": len(teams), "missing_count": missing_count, "missing_rate": round(missing_rate, 6), "teams_sample": teams[:8]})


def gate_period(rows: List[Dict[str, Any]]) -> GateFinding:
    rows = valid_rows(rows)
    key_map = norm_key_map(rows)
    period_col = first_present(key_map, ("period", "half"))
    if not period_col:
        return GateFinding("G07_PERIOD", FAIL_CLOSED, "No period/half column.", {})
    periods = sorted({clean_str(r.get(period_col, "")) for r in rows if clean_str(r.get(period_col, ""))})
    status = PASS if periods else FAIL_CLOSED
    return GateFinding("G07_PERIOD", status, "Period audit completed.", {"period_col": period_col, "periods": periods[:12]})


def summarize(findings: List[GateFinding]) -> str:
    statuses = [f.status for f in findings]
    if FAIL_CLOSED in statuses:
        return FAIL_CLOSED
    if DEGRADED in statuses:
        return DEGRADED
    return PASS


def next_action_for_status(status: str) -> Dict[str, Any]:
    if status == PASS:
        return {
            "phase_sequence_allowed": True,
            "metric_layer_allowed": True,
            "claim_layer_allowed": False,
            "reason": "Data quality gate passed. Downstream event-only context and metric layers may run. Claim layer remains blocked until claim gate and football audit.",
        }
    if status == DEGRADED:
        return {
            "phase_sequence_allowed": True,
            "metric_layer_allowed": "CONDITIONAL",
            "claim_layer_allowed": False,
            "reason": "Data quality is degraded. Downstream modules may run only in degraded mode and must preserve degraded flags. Claim layer remains blocked.",
        }
    return {
        "phase_sequence_allowed": False,
        "metric_layer_allowed": False,
        "claim_layer_allowed": False,
        "reason": "Data quality failed closed. No downstream analysis is allowed.",
    }


def write_summary(path: Path, report: Dict[str, Any]) -> None:
    findings = report.get("findings", [])
    failed = [f["gate_id"] for f in findings if f.get("status") == FAIL_CLOSED]
    degraded = [f["gate_id"] for f in findings if f.get("status") == DEGRADED]
    next_action = report["next_action"]
    lines = [
        f"tool={report['tool']}",
        f"status={report['status']}",
        f"input={report['input']}",
        f"input_format={report['input_format']}",
        f"row_count={report['row_count']}",
        f"valid_row_count={report['valid_row_count']}",
        f"failed_gates={','.join(failed) if failed else 'NONE'}",
        f"degraded_gates={','.join(degraded) if degraded else 'NONE'}",
        f"phase_sequence_allowed={next_action['phase_sequence_allowed']}",
        f"metric_layer_allowed={next_action['metric_layer_allowed']}",
        f"claim_layer_allowed={next_action['claim_layer_allowed']}",
        f"next_action_reason={next_action['reason']}",
        "claim_safety=NO_FOOTBALL_CLAIMS_EMITTED",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="HPFA event-table data quality gate v1")
    parser.add_argument("input", help="Input .csv or .jsonl event surface")
    parser.add_argument("--out", required=True, help="Output gate report JSON path")
    parser.add_argument("--summary-out", help="Optional output summary TXT path")
    args = parser.parse_args()

    input_path = Path(args.input)
    rows, input_format = read_rows(input_path)
    findings = [
        gate_reference_exclusion(input_path),
        gate_parse_errors(rows),
        gate_schema(rows),
        gate_duplicate(rows),
        gate_coordinates(rows),
        gate_temporal(rows),
        gate_team_identity(rows),
        gate_period(rows),
    ]
    final_status = summarize(findings)
    report = {
        "tool": "hpfa_data_quality_gate_v1",
        "status": final_status,
        "input": str(input_path),
        "input_format": input_format,
        "row_count": len(rows),
        "valid_row_count": len(valid_rows(rows)),
        "claim_safety": "NO_FOOTBALL_CLAIMS_EMITTED",
        "authority_note": "Runtime authority still requires Termux ACTIVE_MATCH execution.",
        "next_action": next_action_for_status(final_status),
        "findings": [asdict(f) for f in findings],
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.summary_out:
        write_summary(Path(args.summary_out), report)
    print(json.dumps({"status": final_status, "out": str(out_path), "row_count": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
