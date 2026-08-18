from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from hpfa.modules.core.row_nucleus_content_role_bridge_lite.src import (
    row_nucleus_content_role_bridge as bridge,
)
from hpfa.modules.core.row_nucleus_inventory_lite.src import (
    row_nucleus_inventory as nucleus,
)

MODULE_ID = "statistical_spatial_evidence_lite_v1"
CLAIM_SAFETY = "ROW_NUCLEUS_SPATIAL_DISTRIBUTION_CANDIDATE_ONLY"
OUTPUT_JSON = "statistical_spatial_evidence_lite_v1.json"
OUTPUT_TXT = "statistical_spatial_evidence_lite_v1.txt"
ANALYST_TXT = "statistical_spatial_evidence_analyst_audit_v1.txt"
GRID_SPECS = ((12, 8), (16, 12))

METHOD_ADMISSION_REGISTRY = [
    {
        "method": "SPATIAL_GRID_SHANNON_ENTROPY",
        "status": "IMPLEMENTED_CANDIDATE_ONLY",
        "prerequisite": "content-resolved row nuclei + explicit coordinate-frame dimensions",
        "claim_boundary": "row-nucleus coordinate distribution, not event unpredictability or tactical truth",
    },
    {
        "method": "SPATIAL_GRID_CONCENTRATION_HHI",
        "status": "IMPLEMENTED_CANDIDATE_ONLY",
        "prerequisite": "same as spatial entropy",
        "claim_boundary": "coordinate concentration evidence only",
    },
    {
        "method": "RAW_X_THIRD_DISTRIBUTION",
        "status": "IMPLEMENTED_CANDIDATE_ONLY",
        "prerequisite": "explicit pitch length",
        "claim_boundary": "raw x-axis thirds; not team-relative first/middle/final third without attack-direction admission",
    },
    {
        "method": "KDE_2D",
        "status": "DEFERRED",
        "prerequisite": "independent point-process unit + bandwidth policy + boundary correction",
        "claim_boundary": "multi-label row nuclei cannot silently become physical event points",
    },
    {
        "method": "RIPLEY_K",
        "status": "DEFERRED",
        "prerequisite": "point independence + edge correction + null-process contract",
        "claim_boundary": "no clustering significance claim from dependent row reflections",
    },
    {
        "method": "MANN_WHITNEY_OR_RATE_TESTS",
        "status": "DEFERRED",
        "prerequisite": "independent observation-unit contract + multiplicity policy",
        "claim_boundary": "single-match pseudo-replication cannot be promoted to tactical causality",
    },
    {
        "method": "BIVARIATE_POISSON_DIXON_COLES",
        "status": "DEFERRED",
        "prerequisite": "multi-match team-strength model + validated scoring/xG construct inputs",
        "claim_boundary": "single-match xG means do not prove deserved outcome or goalkeeper causality",
    },
    {
        "method": "KAPLAN_MEIER_COX",
        "status": "DEFERRED",
        "prerequisite": "admitted sequence/possession candidate unit + censoring/event definition",
        "claim_boundary": "source start/end intervals are not physical possession survival durations",
    },
    {
        "method": "PCA_FACTOR_ANALYSIS",
        "status": "DEFERRED",
        "prerequisite": "multi-match sample size + measurement invariance + scaling policy",
        "claim_boundary": "single-match player rows do not establish stable latent tactical factors",
    },
    {
        "method": "BETA_BINOMIAL_BAYESIAN_SHRINKAGE",
        "status": "DEFERRED",
        "prerequisite": "validated prior population + eligible denominator/exposure authority",
        "claim_boundary": "posterior ability is not available from arbitrary match counts",
    },
]


def _fnum(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _validate_frame(pitch_length: float, pitch_width: float) -> None:
    if not math.isfinite(pitch_length) or not math.isfinite(pitch_width):
        raise ValueError("invalid_coordinate_frame_dimensions")
    if pitch_length <= 0 or pitch_width <= 0:
        raise ValueError("invalid_coordinate_frame_dimensions")


def _grid_cell(
    x: float,
    y: float,
    *,
    pitch_length: float,
    pitch_width: float,
    columns: int,
    rows: int,
) -> tuple[int, int]:
    if not (0.0 <= x <= pitch_length and 0.0 <= y <= pitch_width):
        raise ValueError("coordinate_out_of_frame")
    col = min(columns - 1, int((x / pitch_length) * columns))
    row = min(rows - 1, int((y / pitch_width) * rows))
    return col, row


def _raw_x_third(x: float, pitch_length: float) -> str:
    first = pitch_length / 3.0
    second = 2.0 * pitch_length / 3.0
    if x < first:
        return "RAW_X_THIRD_1"
    if x < second:
        return "RAW_X_THIRD_2"
    return "RAW_X_THIRD_3"


def _team_candidate(
    source_role: str,
    fields: dict[str, Any],
) -> tuple[str | None, str]:
    direct = str(fields.get("team") or "").strip()
    if direct:
        return direct, "DIRECT_VISIBLE_TEAM_FIELD_CANDIDATE"

    # TEAM surfaces in the current provider family may encode team context as
    # '<team candidate> - <action label>' inside code. Preserve it only when
    # the resolved action label is an exact visible suffix. This is candidate
    # extraction, not validated team identity.
    if source_role == "TEAM":
        code = str(fields.get("code") or "").strip()
        action = str(fields.get("action") or "").strip()
        suffix = f" - {action}"
        if code and action and code.casefold().endswith(suffix.casefold()):
            prefix = code[: -len(suffix)].strip()
            if prefix:
                return prefix, "TEAM_CODE_PREFIX_CANDIDATE"

    return None, "TEAM_CANDIDATE_UNRESOLVED"


def _entropy_from_counts(counts: Iterable[int]) -> float:
    values = [int(value) for value in counts if int(value) > 0]
    total = sum(values)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in values:
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def _grid_distribution(
    points: list[tuple[float, float]],
    *,
    pitch_length: float,
    pitch_width: float,
    columns: int,
    rows: int,
) -> dict[str, Any]:
    counts: Counter[tuple[int, int]] = Counter(
        _grid_cell(
            x,
            y,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            columns=columns,
            rows=rows,
        )
        for x, y in points
    )
    total = len(points)
    entropy = _entropy_from_counts(counts.values())
    max_entropy = math.log2(columns * rows) if columns * rows > 1 else 0.0
    normalized = entropy / max_entropy if max_entropy > 0 else 0.0
    hhi = sum((count / total) ** 2 for count in counts.values()) if total else 0.0
    top_cells = [
        {
            "cell_x": cell[0],
            "cell_y": cell[1],
            "row_nucleus_count": count,
            "share": round(count / total, 6) if total else 0.0,
        }
        for cell, count in counts.most_common(10)
    ]
    return {
        "grid_columns": columns,
        "grid_rows": rows,
        "eligible_coordinate_nucleus_count": total,
        "occupied_cell_count": len(counts),
        "shannon_entropy_bits": round(entropy, 6),
        "normalized_grid_entropy": round(normalized, 6),
        "effective_cell_count": round(2.0**entropy, 6) if total else 0.0,
        "concentration_hhi": round(hhi, 6),
        "top_cells": top_cells,
        "grid_entropy_is_tactical_unpredictability_truth": False,
        "row_nucleus_is_physical_event_point": False,
    }


def _group_metrics(
    points: list[tuple[float, float]],
    *,
    source_role: str,
    team_candidate: str,
    team_candidate_sources: Counter[str],
    pitch_length: float,
    pitch_width: float,
) -> dict[str, Any]:
    thirds = Counter(_raw_x_third(x, pitch_length) for x, _ in points)
    total = len(points)
    mean_x = sum(x for x, _ in points) / total if total else 0.0
    mean_y = sum(y for _, y in points) / total if total else 0.0
    var_x = sum((x - mean_x) ** 2 for x, _ in points) / total if total else 0.0
    var_y = sum((y - mean_y) ** 2 for _, y in points) / total if total else 0.0
    return {
        "source_role": source_role,
        "team_candidate": team_candidate,
        "team_candidate_derivation_counts": dict(sorted(team_candidate_sources.items())),
        "validated_team_identity": False,
        "eligible_coordinate_nucleus_count": total,
        "coordinate_centroid_candidate": {
            "x": round(mean_x, 6),
            "y": round(mean_y, 6),
            "team_shape_truth": False,
        },
        "coordinate_dispersion_candidate": {
            "std_x": round(math.sqrt(var_x), 6),
            "std_y": round(math.sqrt(var_y), 6),
            "team_width_or_length_truth": False,
        },
        "raw_x_third_distribution": {
            key: {
                "row_nucleus_count": thirds.get(key, 0),
                "share": round(thirds.get(key, 0) / total, 6) if total else 0.0,
            }
            for key in ("RAW_X_THIRD_1", "RAW_X_THIRD_2", "RAW_X_THIRD_3")
        },
        "raw_x_thirds_are_team_relative": False,
        "grids": {
            f"{columns}x{rows}": _grid_distribution(
                points,
                pitch_length=pitch_length,
                pitch_width=pitch_width,
                columns=columns,
                rows=rows,
            )
            for columns, rows in GRID_SPECS
        },
    }


def build_from_bridge_report(
    bridge_report: dict[str, Any],
    *,
    pitch_length: float,
    pitch_width: float,
    frame_provenance: str,
) -> dict[str, Any]:
    _validate_frame(pitch_length, pitch_width)
    if bridge_report.get("status") == "FAIL_CLOSED":
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["upstream_row_nucleus_bridge_fail_closed"],
            "method_admission_registry": METHOD_ADMISSION_REGISTRY,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }
    if bridge_report.get("content_role_resolution_status") != "PASS":
        return {
            "module_id": MODULE_ID,
            "status": "REVIEW_REQUIRED",
            "review_hits": ["content_source_role_resolution_not_pass"],
            "method_admission_registry": METHOD_ADMISSION_REGISTRY,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }
    if not str(frame_provenance or "").strip():
        return {
            "module_id": MODULE_ID,
            "status": "REVIEW_REQUIRED",
            "review_hits": ["coordinate_frame_provenance_required"],
            "method_admission_registry": METHOD_ADMISSION_REGISTRY,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    excluded_review = 0
    excluded_missing = 0
    excluded_out_of_frame = 0
    excluded_missing_team = 0
    eligible = 0

    for item in bridge_report.get("row_nuclei", []) or []:
        if item.get("status") != "PASS":
            excluded_review += 1
            continue
        fields = item.get("resolved_visible_fields") or {}
        x = _fnum(fields.get("pos_x"))
        y = _fnum(fields.get("pos_y"))
        if x is None or y is None:
            excluded_missing += 1
            continue
        if not (0.0 <= x <= pitch_length and 0.0 <= y <= pitch_width):
            excluded_out_of_frame += 1
            continue
        source_role = str(item.get("source_role") or "UNKNOWN")
        if source_role not in nucleus.ROLE_PROJECTION:
            excluded_review += 1
            continue
        team_candidate, team_source = _team_candidate(source_role, fields)
        if not team_candidate:
            excluded_missing_team += 1
            continue

        key = (source_role, team_candidate)
        if key not in grouped:
            grouped[key] = {"points": [], "team_sources": Counter()}
        grouped[key]["points"].append((x, y))
        grouped[key]["team_sources"][team_source] += 1
        eligible += 1

    groups = [
        _group_metrics(
            payload["points"],
            source_role=source_role,
            team_candidate=team_candidate,
            team_candidate_sources=payload["team_sources"],
            pitch_length=pitch_length,
            pitch_width=pitch_width,
        )
        for (source_role, team_candidate), payload in sorted(grouped.items())
    ]
    review_hits: list[str] = []
    if bridge_report.get("status") == "REVIEW_REQUIRED":
        review_hits.append("upstream_row_nucleus_review_preserved")
    if excluded_out_of_frame:
        review_hits.append("coordinate_out_of_frame_nuclei_excluded")
    if excluded_missing_team:
        review_hits.append("team_candidate_unresolved_nuclei_excluded")
    if not groups:
        review_hits.append("no_eligible_coordinate_nuclei")
    status = "REVIEW_REQUIRED" if review_hits else "PASS"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "claim_safety": CLAIM_SAFETY,
        "upstream_module_id": bridge_report.get("module_id"),
        "upstream_status": bridge_report.get("status"),
        "content_role_resolution_status": bridge_report.get(
            "content_role_resolution_status"
        ),
        "coordinate_frame_candidate": {
            "pitch_length": pitch_length,
            "pitch_width": pitch_width,
            "provenance": frame_provenance,
            "validated_provider_coordinate_frame_truth": False,
            "attack_direction_truth": False,
        },
        "eligible_coordinate_nucleus_count": eligible,
        "excluded_review_required_nucleus_count": excluded_review,
        "excluded_missing_coordinate_nucleus_count": excluded_missing,
        "excluded_out_of_frame_nucleus_count": excluded_out_of_frame,
        "excluded_missing_team_candidate_nucleus_count": excluded_missing_team,
        "spatial_distribution_candidate_group_count": len(groups),
        "spatial_distribution_candidates": groups,
        "method_admission_registry": METHOD_ADMISSION_REGISTRY,
        "review_hits": review_hits,
        "hard_block_hits": [],
        "team_candidate_is_validated_identity": False,
        "spatial_point_is_canonical_event": False,
        "row_nucleus_is_physical_action": False,
        "team_shape_truth": False,
        "pitch_control_truth": False,
        "dominance_truth": False,
        "tactical_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def build_report(
    input_dir: str | Path,
    *,
    pitch_length: float,
    pitch_width: float,
    frame_provenance: str,
    root: str | Path | None = None,
) -> dict[str, Any]:
    bridge_report = bridge.build_report(input_dir, root=root)
    return build_from_bridge_report(
        bridge_report,
        pitch_length=pitch_length,
        pitch_width=pitch_width,
        frame_provenance=frame_provenance,
    )


def write_outputs(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    pitch_length: float,
    pitch_width: float,
    frame_provenance: str,
    root: str | Path | None = None,
) -> dict[str, Any]:
    output = nucleus.validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    bridge_report = bridge.write_outputs(input_dir, output, root=root)
    report = build_from_bridge_report(
        bridge_report,
        pitch_length=pitch_length,
        pitch_width=pitch_width,
        frame_provenance=frame_provenance,
    )
    report["outputs"] = {
        "json": str(output / OUTPUT_JSON),
        "summary": str(output / OUTPUT_TXT),
        "analyst": str(output / ANALYST_TXT),
    }
    (output / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = [
        "HPFA STATISTICAL SPATIAL EVIDENCE LITE V1",
        f"status={report.get('status')}",
        f"eligible_coordinate_nucleus_count={report.get('eligible_coordinate_nucleus_count', 0)}",
        f"spatial_distribution_candidate_group_count={report.get('spatial_distribution_candidate_group_count', 0)}",
        f"excluded_review_required_nucleus_count={report.get('excluded_review_required_nucleus_count', 0)}",
        f"excluded_missing_coordinate_nucleus_count={report.get('excluded_missing_coordinate_nucleus_count', 0)}",
        f"excluded_out_of_frame_nucleus_count={report.get('excluded_out_of_frame_nucleus_count', 0)}",
        f"excluded_missing_team_candidate_nucleus_count={report.get('excluded_missing_team_candidate_nucleus_count', 0)}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ]
    (output / OUTPUT_TXT).write_text("\n".join(summary) + "\n", encoding="utf-8")
    analyst = [
        "HPFA STATISTICAL SPATIAL ANALYST AUDIT V1",
        f"status={report.get('status')}",
        "Implemented: grid occupancy, Shannon entropy, effective-cell count, HHI concentration and raw x-third distribution.",
        "The unit is an eligible row-nucleus coordinate candidate, not a canonical event or physical action.",
        "TEAM context may expose a team candidate only through exact '<team> - <action>' visible code suffix structure; this remains candidate-only identity evidence.",
        "Unresolved team candidates are excluded rather than pooled across teams.",
        "Centroid/dispersion are coordinate-evidence summaries, not team shape, compactness or pitch-control truth.",
        "Raw x-thirds are not own/middle/final thirds until attack direction is separately admitted.",
        "Deferred methods and prerequisites are disclosed in method_admission_registry.",
        "canonical_event_count=UNKNOWN",
    ]
    (output / ANALYST_TXT).write_text("\n".join(analyst) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--pitch-length", required=True, type=float)
    parser.add_argument("--pitch-width", required=True, type=float)
    parser.add_argument("--frame-provenance", required=True)
    args = parser.parse_args()
    report = write_outputs(
        args.input_dir,
        args.out_dir,
        pitch_length=args.pitch_length,
        pitch_width=args.pitch_width,
        frame_provenance=args.frame_provenance,
    )
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "eligible_coordinate_nucleus_count": report.get(
                    "eligible_coordinate_nucleus_count", 0
                ),
                "spatial_distribution_candidate_group_count": report.get(
                    "spatial_distribution_candidate_group_count", 0
                ),
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
