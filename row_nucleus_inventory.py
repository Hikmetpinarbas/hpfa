from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.content_source_role_resolver_lite.src import (
    content_source_role_resolver as role_resolver,
)
from hpfa.modules.core.row_nucleus_inventory_lite.src import (
    row_nucleus_inventory as core,
)

ROOT = Path(__file__).resolve().parent
_CORE_BUILD_REPORT = core.build_report
_ACTIVE_ROLE_INDEX: dict[str, str] = {}

CANDIDATE_TO_SHORT = {
    "PLAYER_SURFACE_CANDIDATE": "PLAYER",
    "TEAM_SURFACE_CANDIDATE": "TEAM",
    "GOALKEEPER_SURFACE_CANDIDATE": "GOALKEEPER",
}


def _role_resolution_index(report: dict[str, Any]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for record in report.get("files", []) or []:
        relative = str(record.get("relative_path") or "")
        resolution = record.get("resolution") or {}
        candidate = str(resolution.get("resolved_source_role") or "")
        short = str(resolution.get("resolved_short_role") or "") or CANDIDATE_TO_SHORT.get(candidate, "")
        if (
            relative
            and short in core.ROLE_PROJECTION
            and resolution.get("resolution_status") == "ROLE_CANDIDATE_ADMITTED"
        ):
            resolved[relative] = short
            resolved[Path(relative).name] = short
    return resolved


def runtime_source_role_from_name(path: Path) -> str:
    key = str(path)
    return _ACTIVE_ROLE_INDEX.get(key, _ACTIVE_ROLE_INDEX.get(path.name, "UNKNOWN"))


def _bridge_audit(report: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "module_id": role_resolver.MODULE_ID,
        "status": status,
        "role_resolution_applicable_file_count": report.get(
            "role_resolution_applicable_file_count"
        ),
        "role_candidate_admitted_file_count": report.get(
            "role_candidate_admitted_file_count"
        ),
        "unresolved_role_file_count": report.get("unresolved_role_file_count"),
        "resolved_role_counts": report.get("resolved_role_counts") or {},
        "filename_support_used_for_admission": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": "SOURCE_ROLE_CANDIDATE_ONLY",
    }


def _failure_report(
    decision: str,
    hard_block: str,
    role_report: dict[str, Any] | None = None,
    *,
    bridge_error_type: str | None = None,
) -> dict[str, Any]:
    role_report = role_report or {}
    rollup = {
        "status": "FAIL_CLOSED",
        "gates": [],
        "pass_count": 0,
        "review_required_count": 0,
        "fail_closed_count": 1,
        "not_applicable_count": 0,
    }
    report = {
        "module_id": core.MODULE_ID,
        "status": "FAIL_CLOSED",
        "module_status": "FAIL_CLOSED",
        "claim_safety": core.CLAIM_SAFETY,
        "decision": decision,
        "hard_block_hits": [hard_block],
        "content_source_role_bridge": _bridge_audit(role_report, "FAIL_CLOSED"),
        "content_source_role_bridge_status": "FAIL_CLOSED",
        "filename_support_used_for_role_admission": False,
        "filename_role_used_for_nucleus_grouping": False,
        "unique_surface_file_count": 0,
        "duplicate_surface_file_reflection_count": 0,
        "surface_row_count": 0,
        "missing_provider_id_surface_row_count": 0,
        "xlsx_file_count": 0,
        "xlsx_used_for_row_nucleus_identity": False,
        "row_nucleus_candidate_count": 0,
        "row_nucleus_pass_count": 0,
        "row_nucleus_review_required_count": 0,
        "source_role_candidate_counts": {},
        "serialization_relation_candidate_counts": {},
        "g01_g18_rollup": rollup,
        "row_nuclei": [],
        "blocked_claims": list(core.BLOCKED_CLAIMS),
        "provider_row_id_policy": "TEXT_CANDIDATE_NO_NUMERIC_CANONICALIZATION",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "row_nucleus_is_canonical_event": False,
        "physical_action_identity_truth": False,
        "same_upstream_origin_truth": False,
        "independent_source_vote_allowed": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "production_release": False,
    }
    if bridge_error_type:
        report["bridge_error_type"] = bridge_error_type
    return report


def runtime_build_report(
    input_dir: str | Path,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else ROOT
    try:
        role_report = role_resolver.build_report(input_dir, root=repo_root)
    except Exception as exc:
        return _failure_report(
            "CONTENT_SOURCE_ROLE_RESOLUTION_FAILED",
            "content_source_role_resolution_bridge_failed",
            bridge_error_type=type(exc).__name__,
        )

    applicable = int(role_report.get("role_resolution_applicable_file_count") or 0)
    admitted = int(role_report.get("role_candidate_admitted_file_count") or 0)
    unresolved = int(role_report.get("unresolved_role_file_count") or 0)
    bridge_pass = (
        role_report.get("status") == "PASS"
        and not (role_report.get("hard_block_hits") or [])
        and applicable > 0
        and admitted == applicable
        and unresolved == 0
    )
    if not bridge_pass:
        return _failure_report(
            "CONTENT_SOURCE_ROLE_GATE_NOT_PASS",
            "content_source_role_resolution_gate_not_pass",
            role_report,
        )

    role_index = _role_resolution_index(role_report)
    if not role_index:
        return _failure_report(
            "CONTENT_SOURCE_ROLE_MAP_EMPTY",
            "content_source_role_resolution_map_empty",
            role_report,
        )

    global _ACTIVE_ROLE_INDEX
    _ACTIVE_ROLE_INDEX = role_index
    previous = core.reflection.source_role_from_name
    core.reflection.source_role_from_name = runtime_source_role_from_name
    try:
        result = _CORE_BUILD_REPORT(input_dir)
    finally:
        core.reflection.source_role_from_name = previous

    result["content_source_role_bridge"] = _bridge_audit(role_report, "PASS")
    result["content_source_role_bridge_status"] = "PASS"
    result["filename_support_used_for_role_admission"] = False
    result["filename_role_used_for_nucleus_grouping"] = False
    result["validated_team_identity"] = False
    result["validated_player_identity"] = False
    result["validated_event_identity"] = False
    result["canonical_event_count"] = "UNKNOWN"
    result["true_action_count"] = "UNKNOWN"
    result["deduplicated_event_count"] = "UNKNOWN"
    result["physical_action_identity_truth"] = False
    result["same_upstream_origin_truth"] = False
    result["independent_source_vote_allowed"] = False
    result["comparison_allowed"] = False
    result["claim_allowed"] = False
    result["production_release"] = False
    return result


def runtime_write_outputs(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    output = core.validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = runtime_build_report(input_dir, root=root)
    report["outputs"] = {
        "json": str(output / core.OUTPUT_JSON),
        "summary": str(output / core.OUTPUT_TXT),
        "analyst": str(output / core.ANALYST_TXT),
        "rollup_json": str(output / core.ROLLUP_JSON),
        "rollup_txt": str(output / core.ROLLUP_TXT),
    }
    (output / core.OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / core.OUTPUT_TXT).write_text(core._summary_text(report), encoding="utf-8")
    (output / core.ANALYST_TXT).write_text(core._analyst_text(report), encoding="utf-8")
    rollup = report["g01_g18_rollup"]
    (output / core.ROLLUP_JSON).write_text(
        json.dumps(rollup, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / core.ROLLUP_TXT).write_text(core._rollup_text(rollup), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current content-role-bound Row Nucleus adapter"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report = runtime_write_outputs(args.input_dir, args.out_dir, root=ROOT)
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "content_source_role_bridge_status": report.get(
                    "content_source_role_bridge_status"
                ),
                "row_nucleus_candidate_count": report.get(
                    "row_nucleus_candidate_count", 0
                ),
                "row_nucleus_pass_count": report.get("row_nucleus_pass_count", 0),
                "row_nucleus_review_required_count": report.get(
                    "row_nucleus_review_required_count", 0
                ),
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
                "outputs": report.get("outputs") or {},
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
