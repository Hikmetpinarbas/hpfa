from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "triangulated_event_reflection_resolver_lite" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import triangulated_event_reflection_resolver as core
from hpfa.modules.core.content_source_role_resolver_lite.src import (
    content_source_role_resolver as role_resolver,
)

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
        short = CANDIDATE_TO_SHORT.get(candidate)
        if (
            relative
            and short
            and resolution.get("resolution_status") == "ROLE_CANDIDATE_ADMITTED"
        ):
            resolved[relative] = short
            resolved[Path(relative).name] = short
    return resolved


def runtime_source_role_from_name(path: Path) -> str:
    relative = str(path)
    return _ACTIVE_ROLE_INDEX.get(relative, _ACTIVE_ROLE_INDEX.get(path.name, "UNKNOWN"))


def _bridge_audit(report: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "module_id": "content_source_role_resolver_lite_v1",
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


def runtime_build_report(
    input_dir: str | Path,
    root: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else ROOT
    try:
        role_report = role_resolver.build_report(input_dir, root=repo_root)
    except Exception as exc:
        return {
            "module_id": core.MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "CONTENT_SOURCE_ROLE_RESOLUTION_FAILED",
            "hard_block_hits": ["content_source_role_resolution_bridge_failed"],
            "bridge_error_type": type(exc).__name__,
            "content_source_role_bridge": _bridge_audit({}, "FAIL_CLOSED"),
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "deduplicated_event_count": "UNKNOWN",
            "physical_action_identity_truth": False,
            "same_upstream_origin_truth": False,
            "independent_source_vote_allowed": False,
            "action_count_claim_allowed": False,
            "production_release": False,
        }

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
        return {
            "module_id": core.MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "CONTENT_SOURCE_ROLE_GATE_NOT_PASS",
            "hard_block_hits": ["content_source_role_resolution_gate_not_pass"],
            "content_source_role_bridge": _bridge_audit(role_report, "FAIL_CLOSED"),
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "deduplicated_event_count": "UNKNOWN",
            "physical_action_identity_truth": False,
            "same_upstream_origin_truth": False,
            "independent_source_vote_allowed": False,
            "action_count_claim_allowed": False,
            "production_release": False,
        }

    global _ACTIVE_ROLE_INDEX
    _ACTIVE_ROLE_INDEX = _role_resolution_index(role_report)
    previous = core.source_role_from_name
    core.source_role_from_name = runtime_source_role_from_name
    try:
        result = _CORE_BUILD_REPORT(input_dir, root=repo_root)
    finally:
        core.source_role_from_name = previous

    result["content_source_role_bridge"] = _bridge_audit(role_report, "PASS")
    result["filename_support_used_for_role_admission"] = False
    result["validated_team_identity"] = False
    result["validated_player_identity"] = False
    result["validated_event_identity"] = False
    result["canonical_event_count"] = "UNKNOWN"
    result["true_action_count"] = "UNKNOWN"
    result["deduplicated_event_count"] = "UNKNOWN"
    result["physical_action_identity_truth"] = False
    result["same_upstream_origin_truth"] = False
    result["independent_source_vote_allowed"] = False
    result["action_count_claim_allowed"] = False
    result["production_release"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current content-role-bound reflection resolver adapter"
    )
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = runtime_build_report(args.input_root, root=ROOT)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
