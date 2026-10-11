#!/usr/bin/env python3
"""HPFA action-volume fidelity audit (read-only, stdlib only).

Compares the row-level ``eligible_action_family_candidate_counts`` written by
``context_action_semantics_rebind_lite`` with the provider's own entity-level
aggregate totals (XLSX). Optionally reports the bundle-level
``action_occurrence_candidate_count`` from ``action_occurrence_admission_lite``.

Why: the rebind count is a count of row-nucleus records whose label is an
ACTION_ANCHOR, i.e. facets x layers, while episode feature cards present it as
action volume. This tool measures how far that volume is from the provider's
aggregate universe and whether the gap differs by family (composition bias).

Claim ceiling: fidelity of row volume to the provider aggregate only. Provider
aggregates come from the same provider and are not football truth. The status
is never PASS.

Anchor sheets must be disjoint entity-level sheets (e.g. outfield players plus
goalkeepers). Do not add team-total sheets, or the anchor double counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hpfa.modules.core.xlsx_surface_reader_lite.src.native_ooxml import load_workbook  # noqa: E402

SCHEMA = "HPFA_ACTION_VOLUME_FIDELITY_AUDIT_V1"
CLAIM_CEILING = "ROW_VOLUME_VS_PROVIDER_AGGREGATE_FIDELITY_ONLY"

# Provider aggregate column -> HPFA action family. Exact reviewed headers only.
ANCHOR_COLUMNS: dict[str, tuple[str, ...]] = {
    "PASS": ("Passes",),
    "SHOT": ("Shots",),
    "TURNOVER": ("Lost balls",),
}
# Header variants seen in other exports. Reported, never summed: equivalence is a
# human semantic decision (provider label registry), not this tool's.
UNREVIEWED_ALIASES: dict[str, str] = {
    "Loss balls": "TURNOVER",
}
COMPOSITION_BIAS_TOLERANCE = 0.10
RUNTIME_AUTHORITY_MARKER = ("runtime", "active_single_match")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def _find_key(payload: Any, key: str, prefix: str = "") -> tuple[str, Any] | None:
    if isinstance(payload, dict):
        if key in payload:
            return (f"{prefix}{key}", payload[key])
        for name, value in payload.items():
            found = _find_key(value, key, f"{prefix}{name}.")
            if found:
                return found
    return None


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _read_anchor(path: Path) -> dict[str, Any]:
    wanted = {column for columns in ANCHOR_COLUMNS.values() for column in columns} | set(UNREVIEWED_ALIASES)
    record: dict[str, Any] = {"anchor": path.name, "path": str(path), "sha256": _sha256(path), "column_totals": {}}
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook[workbook.sheetnames[0]]
        record["sheet"] = sheet.title
        headers = {
            str(sheet.cell(row=1, column=col).value).strip(): col
            for col in range(1, sheet.max_column + 1)
            if sheet.cell(row=1, column=col).value is not None
        }
        for header in sorted(wanted & set(headers)):
            col = headers[header]
            values = (_number(sheet.cell(row=row, column=col).value) for row in range(2, sheet.max_row + 1))
            total = sum(v for v in values if v is not None)
            record["column_totals"][header] = int(total) if float(total).is_integer() else total
    finally:
        workbook.close()
    return record


def build_audit(
    *,
    rebind_path: Path,
    anchor_paths: Iterable[Path],
    occurrence_path: Path | None = None,
) -> dict[str, Any]:
    blocks: list[str] = []
    rebind = _read_json(Path(rebind_path))
    row_counts: dict[str, Any] = {}
    if rebind is None:
        blocks.append("REBIND_ARTEFACT_UNREADABLE")
    else:
        found = _find_key(rebind, "eligible_action_family_candidate_counts")
        if not found or not isinstance(found[1], dict):
            blocks.append("ROW_FAMILY_COUNTS_MISSING")
        else:
            row_counts = found[1]

    anchors = [_read_anchor(Path(p)) for p in anchor_paths]
    provider_totals: dict[str, float] = {}
    anchor_columns_used: dict[str, list[str]] = {}
    for family, columns in ANCHOR_COLUMNS.items():
        for anchor in anchors:
            for column in columns:
                if column in anchor["column_totals"]:
                    provider_totals[family] = provider_totals.get(family, 0) + anchor["column_totals"][column]
                    anchor_columns_used.setdefault(family, []).append(f"{anchor['anchor']}:{column}")

    unreviewed = [
        {"anchor": anchor["anchor"], "column": column, "candidate_family": family, "mapping_status": "UNREVIEWED_ALIAS_NOT_SUMMED"}
        for anchor in anchors
        for column, family in UNREVIEWED_ALIASES.items()
        if column in anchor["column_totals"]
    ]

    families = []
    for family in sorted(set(row_counts) | set(ANCHOR_COLUMNS)):
        rows = _number(row_counts.get(family))
        total = provider_totals.get(family)
        ratio = round(rows / total, 3) if rows is not None and total else None
        families.append({
            "family": family,
            "hpfa_row_count": int(rows) if rows is not None else None,
            "provider_anchor_total": total,
            "row_to_anchor_ratio": ratio,
            "anchor_columns": anchor_columns_used.get(family, []),
        })

    ratios = [row["row_to_anchor_ratio"] for row in families if row["row_to_anchor_ratio"] is not None]
    if not provider_totals:
        blocks.append("NO_ANCHOR_FAMILY_AVAILABLE")
    differential = {
        "family_count": len(ratios),
        "min_ratio": min(ratios) if ratios else None,
        "max_ratio": max(ratios) if ratios else None,
        "tolerance": COMPOSITION_BIAS_TOLERANCE,
        "composition_bias_suspected": bool(len(ratios) >= 2 and max(ratios) > min(ratios) * (1 + COMPOSITION_BIAS_TOLERANCE)),
        "meaning": "Row volume inflates families unequally relative to the provider aggregate; family shares built on row volume are biased.",
    }

    occurrence = _read_json(Path(occurrence_path)) if occurrence_path else None
    bundle: dict[str, Any] = {"available": occurrence is not None}
    if occurrence is not None:
        found = _find_key(occurrence, "action_occurrence_candidate_count")
        split = _find_key(occurrence, "action_occurrence_family_counts")
        bundle.update({
            "action_occurrence_candidate_count": found[1] if found else None,
            "json_path": found[0] if found else None,
            "family_split_available": bool(split),
        })

    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED" if blocks else "REVIEW_REQUIRED",
        "blocks": blocks,
        "inputs": {
            "rebind_path": str(rebind_path),
            "occurrence_path": str(occurrence_path) if occurrence_path else None,
            "anchors": anchors,
        },
        "families": families,
        "differential_inflation": differential,
        "occurrence_bundle": bundle,
        "unreviewed_alias_columns": unreviewed,
        "claim_ceiling": CLAIM_CEILING,
        "claim_boundary": {
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "provider_aggregate_is_football_truth": False,
            "provider_aggregate_is_independent_evidence": False,
            "production_release": False,
        },
    }


def _is_runtime_authority(path: Path) -> bool:
    parts = Path(path).resolve().parts
    return any(parts[i:i + 2] == RUNTIME_AUTHORITY_MARKER for i in range(len(parts) - 1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rebind", required=True, type=Path, help="context_action_semantics_rebind_lite_v1.json")
    parser.add_argument("--occurrence", type=Path, help="action_occurrence_admission_lite_v1.json (optional)")
    parser.add_argument("--anchor-xlsx", action="append", required=True, type=Path, help="disjoint entity-level provider aggregate sheet")
    parser.add_argument("--out", type=Path, help="write JSON here instead of stdout")
    args = parser.parse_args(argv)

    if args.out and _is_runtime_authority(args.out):
        print("refusing to write inside runtime/active_single_match authority", file=sys.stderr)
        return 2

    report = build_audit(rebind_path=args.rebind, anchor_paths=args.anchor_xlsx, occurrence_path=args.occurrence)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
