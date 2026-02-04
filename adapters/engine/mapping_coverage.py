import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now_iso_z(now: Optional[datetime] = None) -> str:
    dt = now if now is not None else datetime.now(timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_mapping_coverage_report(
    *,
    provider: str,
    mappings_path: Path,
    unmapped_report_path: Path,
    output_path: Path,
    now: Optional[datetime] = None,
) -> Path:
    """
    Writes deterministic mapping_coverage.json (except generated_at_utc).
    Type-level coverage: mapped_types / (mapped_types + unmapped_types)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    action_map = _read_json(mappings_path)
    if not isinstance(action_map, dict):
        raise ValueError("engine_action_map.json must be an object/dict")

    mapped_types = len(action_map)

    unmapped = _read_json(unmapped_report_path)
    unmapped_rows = unmapped.get("unmapped_actions", []) or []
    if not isinstance(unmapped_rows, list):
        raise ValueError("unmapped_actions.json unmapped_actions must be a list")

    unmapped_types = len(unmapped_rows)

    top: List[Tuple[str, int]] = []
    for row in unmapped_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("provider_action", "")).strip()
        try:
            count = int(row.get("count", 0))
        except Exception:
            count = 0
        if name:
            top.append((name, count))

    top.sort(key=lambda t: (-t[1], t[0]))
    top_unmapped = [{"provider_action": n, "count": c} for (n, c) in top[:10]]

    denom = mapped_types + unmapped_types
    coverage_ratio = (mapped_types / denom) if denom > 0 else 1.0

    report: Dict[str, Any] = {
        "provider": provider,
        "generated_at_utc": _utc_now_iso_z(now),
        "mapping": {
            "mapped_actions": mapped_types,
            "unmapped_actions": unmapped_types,
            "total_observed_actions": denom,
            "coverage_ratio": coverage_ratio,
        },
        "top_unmapped": top_unmapped,
    }

    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def maybe_write_mapping_coverage_report(provider: str) -> Optional[Path]:
    """
    Side-effect gated by HPFA_REPORTS_DIR, consistent with A4.2.
    Reads mappings from repo, unmapped report from reports dir.
    """
    reports_dir_s = os.environ.get("HPFA_REPORTS_DIR", "").strip()
    if not reports_dir_s:
        return None

    reports_dir = Path(reports_dir_s)
    mappings_path = Path("mappings") / "engine_action_map.json"
    unmapped_report_path = reports_dir / "unmapped_actions.json"
    output_path = reports_dir / "mapping_coverage.json"

    if not mappings_path.exists():
        return None
    if not unmapped_report_path.exists():
        return None

    return generate_mapping_coverage_report(
        provider=provider,
        mappings_path=mappings_path,
        unmapped_report_path=unmapped_report_path,
        output_path=output_path,
        now=None,
    )
