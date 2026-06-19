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
    ("event_type", "type", "action_type"),
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


def gate_schema(rows: List[Dict[str, Any]]) -> GateFinding:
    if not rows:
        return GateFinding("G01_SCHEMA", FAIL_CLOSED, "No rows found.", {"row_count": 0})
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
    key_map = norm_key_map(rows)
    event_col = first_present(key_map, ("event_id", "id"))
    if not event_col:
        return GateFinding("G02_DUPLICATE", DEGRADED, "No event id column; duplicate audit degraded.", {})
    vals = [str(r.get(event_col, "")).strip() for r in rows if str(r.get(event_col, "")).strip()]
    counts = Counter(vals)
    duplicate_ids = [k for k, v in counts.items() if v > 1]
    duplicate_rate = len(duplicate_ids) / max(len(counts), 1)
    status = FAIL_CLOSED if duplicate_rate > 0.01 else PASS
    return GateFinding("G02_DUPLICATE", status, "Duplicate event id audit completed.", {"event_col": event_col, "duplicate_id_count": len(duplicate_ids), "duplicate_rate": round(duplicate_rate, 6)})


def gate_coordinates(rows: List[Dict[str, Any]]) -> GateFinding:
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
        # Supports either metric pitch scale 0-105/0-68 or normalized 0-100/0-100.
        if not ((0 <= x <= 105 and 0 <= y <= 100) or (0 <= x <= 100 and 0 <= y <= 100)):
            bad += 1
    if checked == 0:
        return GateFinding("G03_COORDINATE", DEGRADED, "Coordinates present but not numeric.", {"x_col": x_col, "y_col": y_col})
    bad_rate = bad / checked
    status = FAIL_CLOSED if bad_rate > 0.01 else PASS
    return GateFinding("G03_COORDINATE", status, "Coordinate bounds audit completed.", {"x_col": x_col, "y_col": y_col, "checked": checked, "bad": bad, "bad_rate": round(bad_rate, 6)})


def gate_temporal(rows: List[Dict[str, Any]]) -> GateFinding:
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
        p = str(r.get(period_col, "unknown")) if period_col else "unknown"
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
    key_map = norm_key_map(rows)
    team_col = first_present(key_map, ("team_id", "team", "team_name"))
    if not team_col:
        return GateFinding("G05_TEAM_IDENTITY", FAIL_CLOSED, "No team identity column.", {})
    teams = sorted({str(r.get(team_col, "")).strip() for r in rows if str(r.get(team_col, "")).strip()})
    status = PASS if 1 <= len(teams) <= 4 else DEGRADED
    return GateFinding("G05_TEAM_IDENTITY", status, "Team identity audit completed.", {"team_col": team_col, "team_count": len(teams), "teams_sample": teams[:8]})


def gate_period(rows: List[Dict[str, Any]]) -> GateFinding:
    key_map = norm_key_map(rows)
    period_col = first_present(key_map, ("period", "half"))
    if not period_col:
        return GateFinding("G07_PERIOD", FAIL_CLOSED, "No period/half column.", {})
    periods = sorted({str(r.get(period_col, "")).strip() for r in rows if str(r.get(period_col, "")).strip()})
    status = PASS if periods else FAIL_CLOSED
    return GateFinding("G07_PERIOD", status, "Period audit completed.", {"period_col": period_col, "periods": periods[:12]})


def summarize(findings: List[GateFinding]) -> str:
    statuses = [f.status for f in findings]
    if FAIL_CLOSED in statuses:
        return FAIL_CLOSED
    if DEGRADED in statuses:
        return DEGRADED
    return PASS


def main() -> None:
    parser = argparse.ArgumentParser(description="HPFA event-table data quality gate v1")
    parser.add_argument("input", help="Input .csv or .jsonl event surface")
    parser.add_argument("--out", required=True, help="Output gate report JSON path")
    args = parser.parse_args()

    input_path = Path(args.input)
    rows, input_format = read_rows(input_path)
    findings = [
        gate_reference_exclusion(input_path),
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
        "claim_safety": "NO_FOOTBALL_CLAIMS_EMITTED",
        "authority_note": "Runtime authority still requires Termux ACTIVE_MATCH execution.",
        "findings": [asdict(f) for f in findings],
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": final_status, "out": str(out_path), "row_count": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
