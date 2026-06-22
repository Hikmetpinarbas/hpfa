from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CLAIM_SAFETY = "EVIDENCE_ONLY"
RUNNER_ID = "active_match_spine_check_v1"


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def _ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _surface_manifest_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "canonical_ingest_surface_manifest" / "src"
    _ensure_module_path(src)
    import surface_manifest  # type: ignore

    return surface_manifest


def _boundary_scorer_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "composite_integration_office" / "src"
    _ensure_module_path(src)
    import boundary_analysis_scorer  # type: ignore

    return boundary_analysis_scorer


def summarize_bands(scores: list[dict[str, Any]]) -> dict[str, int]:
    bands: dict[str, int] = {}
    for row in scores:
        band = str(row.get("readiness_band"))
        bands[band] = bands.get(band, 0) + 1
    return bands


def run_spine_check(
    active_match_dir: str | Path,
    out_dir: str | Path,
    composite_registry: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    active_match_path = Path(active_match_dir).expanduser().resolve()
    output_root = Path(out_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    surface_out = output_root / "active_match_surface_manifest_v1.json"
    spine_json_out = output_root / "active_match_spine_check_v1.json"
    spine_txt_out = output_root / "active_match_spine_check_v1.txt"

    surface_manifest = _surface_manifest_module(repo_root)
    manifest = surface_manifest.write_manifest(str(active_match_path), str(surface_out))

    boundary_result: dict[str, Any] | None = None
    boundary_out: str | None = None
    if composite_registry is not None:
        boundary_out_path = output_root / "boundary_analysis_score_registry_v1.json"
        scorer = _boundary_scorer_module(repo_root)
        boundary_result = scorer.write_score_registry(composite_registry, boundary_out_path)
        boundary_out = str(boundary_out_path)

    status = "PASS" if manifest.get("status") == "PASS" else str(manifest.get("status", "UNKNOWN"))

    result = {
        "runner_id": RUNNER_ID,
        "status": status,
        "active_match_dir": str(active_match_path),
        "output_root": str(output_root),
        "surface_manifest": {
            "status": manifest.get("status"),
            "out": str(surface_out),
            "surface_file_count": manifest.get("surface_file_count"),
            "expected_surface_count": manifest.get("expected_surface_count"),
            "canonical_event_count": manifest.get("canonical_event_count"),
            "missing_expected_surfaces": manifest.get("missing_expected_surfaces"),
            "unexpected_surfaces": manifest.get("unexpected_surfaces"),
            "claim_safety": manifest.get("claim_safety"),
            "report_language_allowed": manifest.get("report_language_allowed"),
            "production_binding_allowed": manifest.get("production_binding_allowed"),
        },
        "boundary_scores": None,
        "claim_safety": CLAIM_SAFETY,
        "report_language_allowed": False,
        "production_binding_allowed": False,
    }

    if boundary_result is not None:
        result["boundary_scores"] = {
            "status": boundary_result.get("status"),
            "out": boundary_out,
            "score_count": boundary_result.get("score_count"),
            "claim_safety": boundary_result.get("claim_safety"),
            "active_match_validation_required": boundary_result.get("active_match_validation_required"),
            "bands": summarize_bands(boundary_result.get("scores", [])),
            "top_10": boundary_result.get("scores", [])[:10],
        }

    spine_json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    spine_txt_out.write_text(render_summary(result), encoding="utf-8")
    return result


def render_summary(result: dict[str, Any]) -> str:
    lines = [
        "HPFA ACTIVE_MATCH SPINE CHECK V1",
        "================================",
        f"status={result.get('status')}",
        f"active_match_dir={result.get('active_match_dir')}",
        f"claim_safety={result.get('claim_safety')}",
        f"report_language_allowed={result.get('report_language_allowed')}",
        f"production_binding_allowed={result.get('production_binding_allowed')}",
        "",
        "[surface_manifest]",
    ]
    surface = result.get("surface_manifest") or {}
    for key in [
        "status",
        "surface_file_count",
        "expected_surface_count",
        "canonical_event_count",
        "missing_expected_surfaces",
        "unexpected_surfaces",
        "claim_safety",
        "report_language_allowed",
        "production_binding_allowed",
        "out",
    ]:
        lines.append(f"{key}={surface.get(key)}")

    lines.append("")
    lines.append("[boundary_scores]")
    boundary = result.get("boundary_scores")
    if boundary is None:
        lines.append("status=SKIPPED")
    else:
        for key in ["status", "score_count", "claim_safety", "active_match_validation_required", "bands", "out"]:
            lines.append(f"{key}={boundary.get(key)}")
        lines.append("top_10=")
        for row in boundary.get("top_10", []):
            lines.append(
                f"{row.get('readiness_score')} {row.get('readiness_band')} "
                f"{row.get('recommended_action')} {row.get('composite_id')} {row.get('risk_flags')}"
            )
    lines.append("")
    return "\n".join(lines)
