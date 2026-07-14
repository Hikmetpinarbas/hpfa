from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "team_period_event_identity_discovery_lite_v1"
OUTPUT_JSON = "team_period_event_identity_discovery_lite_v1.json"
OUTPUT_TXT = "team_period_event_identity_discovery_lite_v1.txt"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _team(row: dict[str, Any]) -> str:
    return (_clean(row.get("team_normalized")) or _clean(row.get("team_raw")) or "UNKNOWN_TEAM").lower()


def _period(row: dict[str, Any]) -> str:
    return _clean(row.get("period_candidate")) or "UNKNOWN_PERIOD"


def _role(row: dict[str, Any]) -> str:
    return _clean(row.get("source_role")) or "UNKNOWN_ROLE"


def _event_id(row: dict[str, Any]) -> str:
    return _clean(row.get("source_event_id_raw"))


def _action(row: dict[str, Any]) -> str:
    return (_clean(row.get("event_type_raw")) or _clean(row.get("code_raw")) or _clean(row.get("event_family"))).lower()


def _time_key(row: dict[str, Any]) -> tuple[str, str]:
    return (_clean(row.get("start_raw")), _clean(row.get("end_raw")))


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("rows", payload) if isinstance(payload, dict) else payload
    return [row for row in rows if isinstance(row, dict)]


def build_report(canonical_json: str | Path) -> dict[str, Any]:
    rows = load_rows(canonical_json)
    eligible = [
        row for row in rows
        if row.get("row_surface_class") == "EVENT_LIKE_SOURCE_CANDIDATE"
        and row.get("source_format") in {"csv", "xml"}
    ]

    matrix: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: {"csv": [], "xml": []})
    for row in eligible:
        matrix[(_team(row), _period(row), _role(row))][str(row.get("source_format"))].append(row)

    partitions = []
    total_exact = total_temporal_action = total_csv = total_xml = 0
    ambiguous = unresolved = 0

    for (team, period, role), surfaces in sorted(matrix.items()):
        csv_rows = surfaces["csv"]
        xml_rows = surfaces["xml"]
        total_csv += len(csv_rows)
        total_xml += len(xml_rows)

        csv_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        xml_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in csv_rows:
            if _event_id(row):
                csv_by_id[_event_id(row)].append(row)
        for row in xml_rows:
            if _event_id(row):
                xml_by_id[_event_id(row)].append(row)

        exact = 0
        ambiguous_here = 0
        used_csv: set[int] = set()
        used_xml: set[int] = set()

        for event_id in sorted(set(csv_by_id) & set(xml_by_id)):
            cands_csv = csv_by_id[event_id]
            cands_xml = xml_by_id[event_id]
            if len(cands_csv) == 1 and len(cands_xml) == 1:
                c = cands_csv[0]
                x = cands_xml[0]
                if _time_key(c) == _time_key(x) and _action(c) == _action(x):
                    exact += 1
                    used_csv.add(id(c))
                    used_xml.add(id(x))
                else:
                    ambiguous_here += 1
            else:
                ambiguous_here += max(len(cands_csv), len(cands_xml))

        temporal_action = 0
        xml_index: dict[tuple[tuple[str, str], str], list[dict[str, Any]]] = defaultdict(list)
        for row in xml_rows:
            if id(row) not in used_xml:
                xml_index[(_time_key(row), _action(row))].append(row)

        for row in csv_rows:
            if id(row) in used_csv:
                continue
            candidates = xml_index.get((_time_key(row), _action(row)), [])
            candidates = [candidate for candidate in candidates if id(candidate) not in used_xml]
            if len(candidates) == 1:
                temporal_action += 1
                used_csv.add(id(row))
                used_xml.add(id(candidates[0]))
            elif len(candidates) > 1:
                ambiguous_here += 1

        unresolved_here = (len(csv_rows) - len(used_csv)) + (len(xml_rows) - len(used_xml))
        total_exact += exact
        total_temporal_action += temporal_action
        ambiguous += ambiguous_here
        unresolved += unresolved_here

        partitions.append({
            "team_entity_candidate": team,
            "period_candidate": period,
            "source_role": role,
            "csv_trace_count": len(csv_rows),
            "xml_trace_count": len(xml_rows),
            "provider_id_exact_pair_count": exact,
            "temporal_action_pair_count": temporal_action,
            "ambiguous_trace_count": ambiguous_here,
            "unresolved_trace_count": unresolved_here,
            "pair_coverage_ratio": round((2 * (exact + temporal_action)) / max(1, len(csv_rows) + len(xml_rows)), 6),
        })

    team_period_counts = Counter((_team(row), _period(row)) for row in eligible)
    cross_team_same_time = Counter()
    by_time: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in eligible:
        start, end = _time_key(row)
        if start or end:
            by_time[(start, end)].add(_team(row))
    for key, teams in by_time.items():
        if len(teams) > 1:
            cross_team_same_time[key] = len(teams)

    status = "DISCOVERY_PASS" if eligible and partitions else "FAIL_CLOSED"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "surface_trace_count": len(rows),
        "eligible_csv_xml_trace_count": len(eligible),
        "csv_trace_count": total_csv,
        "xml_trace_count": total_xml,
        "provider_id_exact_pair_count": total_exact,
        "temporal_action_pair_count": total_temporal_action,
        "assembled_same_role_pair_candidate_count": total_exact + total_temporal_action,
        "ambiguous_trace_count": ambiguous,
        "unresolved_trace_count": unresolved,
        "team_period_partition_count": len(team_period_counts),
        "cross_team_same_time_window_count": len(cross_team_same_time),
        "partitions": partitions,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "claim_boundary": "PAIRING_DISCOVERY_ONLY",
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA TEAM PERIOD EVENT IDENTITY DISCOVERY LITE V1",
        f"status={report['status']}",
        f"surface_trace_count={report['surface_trace_count']}",
        f"eligible_csv_xml_trace_count={report['eligible_csv_xml_trace_count']}",
        f"provider_id_exact_pair_count={report['provider_id_exact_pair_count']}",
        f"temporal_action_pair_count={report['temporal_action_pair_count']}",
        f"assembled_same_role_pair_candidate_count={report['assembled_same_role_pair_candidate_count']}",
        f"ambiguous_trace_count={report['ambiguous_trace_count']}",
        f"unresolved_trace_count={report['unresolved_trace_count']}",
        f"team_period_partition_count={report['team_period_partition_count']}",
        f"cross_team_same_time_window_count={report['cross_team_same_time_window_count']}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
        "[partitions]",
    ]
    lines.extend(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in report["partitions"])
    return "\n".join(lines) + "\n"


def write_outputs(canonical_json: str | Path, out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    if out.name != "HPFA" or out.parent.name != "Download":
        raise ValueError("nested_phone_output_directory_rejected")
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(canonical_json)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / OUTPUT_TXT).write_text(render_txt(report), encoding="utf-8")
    return report
