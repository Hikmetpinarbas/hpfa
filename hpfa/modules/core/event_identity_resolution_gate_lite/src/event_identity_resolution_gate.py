from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "event_identity_resolution_gate_lite_v1"
CLAIM_SAFETY = "DUPLICATE_RISK_CANDIDATES_ONLY"
OUTPUT_JSON = "event_identity_resolution_gate_lite_v1.json"
OUTPUT_TXT = "event_identity_resolution_gate_lite_v1.txt"

STRATEGY_VERSIONS = [
    "V0_EXACT_FINGERPRINT",
    "V1_BUCKETED_SPATIOTEMPORAL_FINGERPRINT",
    "V2_PROVENANCE_CLUSTER_REVIEW",
    "V3_FAIL_CLOSED_UNRESOLVED",
]


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


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return [r for r in data["rows"] if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def bucket_number(value: Any, size: float) -> str:
    number = to_float(value)
    if number is None:
        return "UNKNOWN"
    return str(int(math.floor(number / size)))


def normalized_team(value: Any) -> str:
    raw = clean(value)
    raw = re.sub(r"\s*\([^()]*\)\s*$", "", raw)
    return raw.lower() or "UNKNOWN"


def normalized_player(value: Any) -> str:
    raw = clean(value).lower()
    return raw or "UNKNOWN"


def row_provenance(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_file": row.get("source_file"),
        "source_role": row.get("source_role"),
        "source_format": row.get("source_format"),
        "source_row_index": row.get("source_row_index"),
        "event_family": row.get("event_family"),
        "team_normalized": row.get("team_normalized"),
        "player_raw": row.get("player_raw"),
        "x_meters": row.get("x_meters"),
        "y_meters": row.get("y_meters"),
        "minute_raw": row.get("minute_raw"),
        "timestamp_raw": row.get("timestamp_raw"),
    }


def stable_hash(parts: list[str]) -> str:
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def v0_exact_fingerprint(row: dict[str, Any]) -> str | None:
    event = clean(row.get("event_family"))
    x = clean(row.get("x_meters"))
    y = clean(row.get("y_meters"))
    if not event or event == "UNKNOWN_OR_OTHER" or not x or not y:
        return None
    parts = [
        "V0",
        event,
        normalized_team(row.get("team_normalized")),
        normalized_player(row.get("player_raw")),
        x,
        y,
        clean(row.get("minute_raw")) or "NO_MINUTE",
        clean(row.get("timestamp_raw")) or "NO_TIME",
    ]
    return stable_hash(parts)


def v1_bucketed_fingerprint(row: dict[str, Any]) -> str | None:
    event = clean(row.get("event_family"))
    xb = bucket_number(row.get("x_meters"), 5.0)
    yb = bucket_number(row.get("y_meters"), 5.0)
    if not event or event == "UNKNOWN_OR_OTHER" or xb == "UNKNOWN" or yb == "UNKNOWN":
        return None
    parts = [
        "V1",
        event,
        normalized_team(row.get("team_normalized")),
        normalized_player(row.get("player_raw")),
        f"x{xb}",
        f"y{yb}",
        clean(row.get("minute_raw")) or "NO_MINUTE",
        clean(row.get("timestamp_raw")) or "NO_TIME",
    ]
    return stable_hash(parts)


def source_roles(rows: list[dict[str, Any]]) -> set[str]:
    return {clean(r.get("source_role")) for r in rows if clean(r.get("source_role"))}


def cluster_from_group(strategy: str, fingerprint: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(rows) < 2:
        return None
    roles = source_roles(rows)
    cross_surface = len(roles) > 1
    if not cross_surface:
        return None
    has_time = any(clean(r.get("minute_raw")) or clean(r.get("timestamp_raw")) for r in rows)
    confidence = "MEDIUM" if has_time else "LOW"
    return {
        "cluster_id": stable_hash([strategy, fingerprint]),
        "strategy": strategy,
        "fingerprint": fingerprint,
        "duplicate_risk_level": confidence,
        "cross_surface": True,
        "source_roles": sorted(roles),
        "source_row_count": len(rows),
        "deduplicated_event_truth": False,
        "metric_count_allowed": False,
        "provenance": [row_provenance(r) for r in rows],
        "review_reason": "cross_surface_rows_share_candidate_fingerprint",
    }


def build_gate(canonical_event_lite_json: str | Path) -> dict[str, Any]:
    rows = load_rows(canonical_event_lite_json)
    v0_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    v1_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved = []

    for idx, row in enumerate(rows, start=1):
        fp0 = v0_exact_fingerprint(row)
        fp1 = v1_bucketed_fingerprint(row)
        if fp0:
            v0_groups[fp0].append(row)
        if fp1:
            v1_groups[fp1].append(row)
        if not fp0 and not fp1:
            unresolved.append({"row_index": idx, "reason": "insufficient_fingerprint_fields", "provenance": row_provenance(row)})

    clusters = []
    seen = set()
    for strategy, groups in [("V0_EXACT_FINGERPRINT", v0_groups), ("V1_BUCKETED_SPATIOTEMPORAL_FINGERPRINT", v1_groups)]:
        for fp, group_rows in groups.items():
            cluster = cluster_from_group(strategy, fp, group_rows)
            if cluster and cluster["cluster_id"] not in seen:
                seen.add(cluster["cluster_id"])
                clusters.append(cluster)

    status = "PASS" if rows else "REVIEW_REQUIRED"
    decision = "DUPLICATE_RISK_CANDIDATES_FOUND" if clusters else "UNRESOLVED_INSUFFICIENT_FIELDS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": decision,
        "claim_safety": CLAIM_SAFETY,
        "strategy_versions": STRATEGY_VERSIONS,
        "surface_row_inventory_total": len(rows),
        "candidate_cluster_count": len(clusters),
        "duplicate_risk_candidate_count": sum(c.get("source_row_count", 0) for c in clusters),
        "unresolved_candidate_count": len(unresolved),
        "duplicate_cluster_candidates": clusters[:200],
        "unresolved_sample": unresolved[:100],
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
        "metric_count_allowed": False,
        "primary_event_surface_candidate": "UNRESOLVED",
        "blocked_claims": [
            "confirmed duplicate event",
            "deduplicated event truth",
            "validated event count",
            "metric count allowed",
            "primary event stream",
        ],
        "required_next_gates": [
            "primary event surface gate",
            "time/phase lite",
            "possession boundary lite",
            "sequence candidate gate",
            "claim router",
        ],
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA EVENT IDENTITY RESOLUTION GATE LITE V1",
        "=============================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"surface_row_inventory_total={report.get('surface_row_inventory_total')}",
        f"candidate_cluster_count={report.get('candidate_cluster_count')}",
        f"duplicate_risk_candidate_count={report.get('duplicate_risk_candidate_count')}",
        f"unresolved_candidate_count={report.get('unresolved_candidate_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"deduplicated_event_count={report.get('deduplicated_event_count')}",
        f"event_count_claim_allowed={report.get('event_count_claim_allowed')}",
        f"metric_count_allowed={report.get('metric_count_allowed')}",
        "",
        "[strategy_versions]",
    ]
    for item in report.get("strategy_versions", []):
        lines.append(f"- {item}")
    lines.extend(["", "[duplicate_cluster_candidates]"])
    for row in report.get("duplicate_cluster_candidates", [])[:50]:
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_claims]"])
    for item in report.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.extend(["", "[required_next_gates]"])
    for item in report.get("required_next_gates", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(canonical_event_lite_json: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    out = spine_runner.validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_gate(canonical_event_lite_json)
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
