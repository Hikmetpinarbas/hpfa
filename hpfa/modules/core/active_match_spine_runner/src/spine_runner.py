from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CLAIM_SAFETY = "EVIDENCE_ONLY"
RUNNER_ID = "active_match_spine_check_v1"
PHONE_OUTPUT_ROOTS = (
    Path("/sdcard/Download/HPFA"),
    Path("/storage/emulated/0/Download/HPFA"),
)
ALLOWED_RUNTIME_SURFACES = (
    Path("hpfa/modules/core/canonical_ingest_surface_manifest"),
    Path("hpfa/modules/core/composite_integration_office"),
)
FORBIDDEN_RUNTIME_PARTS = {
    "archive": "archive_surface_import_attempted",
    "archives": "archive_surface_import_attempted",
    "donor": "donor_surface_runtime_bound",
    "donors": "donor_surface_runtime_bound",
    "reference_only": "reference_only_surface_executed",
    "fixtures": "fixture_surface_used_as_active_match",
}


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def _ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def validate_active_match_authority(path: str | Path) -> Path:
    resolved = _resolve_path(Path(path))
    if tuple(part.lower() for part in resolved.parts[-3:]) != (
        "runtime",
        "active_single_match",
        "current",
    ):
        raise ValueError(f"runtime_authority_path_invalid:{resolved}")
    return resolved


def validate_runtime_surface(root: str | Path, path: str | Path) -> Path:
    repo_root = _resolve_path(Path(root))
    candidate = _resolve_path(Path(path))
    try:
        relative = candidate.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"runtime_surface_outside_product_repo:{candidate}") from exc

    lowered_parts = {part.lower() for part in relative.parts}
    for token, error_code in FORBIDDEN_RUNTIME_PARTS.items():
        if token in lowered_parts:
            raise ValueError(f"{error_code}:{relative.as_posix()}")

    for allowed in ALLOWED_RUNTIME_SURFACES:
        allowed_root = _resolve_path(repo_root / allowed)
        if candidate == allowed_root or allowed_root in candidate.parents:
            return candidate

    raise ValueError(f"unregistered_runtime_surface:{relative.as_posix()}")


def _surface_manifest_module(root: Path):
    src = validate_runtime_surface(
        root,
        root / "hpfa" / "modules" / "core" / "canonical_ingest_surface_manifest" / "src",
    )
    _ensure_module_path(src)
    import surface_manifest  # type: ignore

    return surface_manifest


def _boundary_scorer_module(root: Path):
    src = validate_runtime_surface(
        root,
        root / "hpfa" / "modules" / "core" / "composite_integration_office" / "src",
    )
    _ensure_module_path(src)
    import boundary_analysis_scorer  # type: ignore

    return boundary_analysis_scorer


def validate_output_root(out_dir: str | Path) -> Path:
    output_root = _resolve_path(Path(out_dir))
    for phone_root in PHONE_OUTPUT_ROOTS:
        resolved_phone_root = _resolve_path(phone_root)
        if output_root == resolved_phone_root:
            return output_root
        if resolved_phone_root in output_root.parents:
            raise ValueError(
                "nested_phone_output_directory_rejected: "
                f"use {resolved_phone_root} directly, not {output_root}"
            )
    return output_root


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
    active_match_path = validate_active_match_authority(active_match_dir)
    output_root = validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    surface_out = output_root / "active_match_surface_manifest_v1.json"
    spine_json_out = output_root / "active_match_spine_check_v1.json"
    spine_txt_out = output_root / "active_match_spine_check_v1.txt"

    executed_runtime_surfaces = [
        "hpfa/modules/core/canonical_ingest_surface_manifest",
    ]
    surface_manifest = _surface_manifest_module(repo_root)
    manifest = surface_manifest.write_manifest(str(active_match_path), str(surface_out))

    boundary_result: dict[str, Any] | None = None
    boundary_out: str | None = None
    if composite_registry is not None:
        boundary_out_path = output_root / "boundary_analysis_score_registry_v1.json"
        scorer = _boundary_scorer_module(repo_root)
        executed_runtime_surfaces.append("hpfa/modules/core/composite_integration_office")
        boundary_result = scorer.write_score_registry(composite_registry, boundary_out_path)
        boundary_out = str(boundary_out_path)

    status = "PASS" if manifest.get("status") == "PASS" else str(manifest.get("status", "UNKNOWN"))

    result = {
        "runner_id": RUNNER_ID,
        "status": status,
        "active_match_dir": str(active_match_path),
        "active_match_authority_validated": True,
        "output_root": str(output_root),
        "runtime_surface_policy": {
            "allowed_runtime_surfaces": [path.as_posix() for path in ALLOWED_RUNTIME_SURFACES],
            "executed_runtime_surfaces": executed_runtime_surfaces,
            "forbidden_archive_surfaces": ["archive", "archives"],
            "reference_only_surfaces": ["reference_only"],
            "fixture_surfaces": ["fixtures"],
            "unregistered_runtime_surface_allowed": False,
            "donor_runtime_binding_allowed": False,
        },
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
        f"active_match_authority_validated={result.get('active_match_authority_validated')}",
        f"claim_safety={result.get('claim_safety')}",
        f"report_language_allowed={result.get('report_language_allowed')}",
        f"production_binding_allowed={result.get('production_binding_allowed')}",
        "",
        "[runtime_surface_policy]",
    ]
    runtime_policy = result.get("runtime_surface_policy") or {}
    for key in [
        "allowed_runtime_surfaces",
        "executed_runtime_surfaces",
        "forbidden_archive_surfaces",
        "reference_only_surfaces",
        "fixture_surfaces",
        "unregistered_runtime_surface_allowed",
        "donor_runtime_binding_allowed",
    ]:
        lines.append(f"{key}={runtime_policy.get(key)}")

    lines.extend(["", "[surface_manifest]"])
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
