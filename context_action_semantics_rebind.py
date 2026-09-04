from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _append_projection_audit(report: dict[str, Any]) -> None:
    outputs = report.get("outputs") or {}
    summary_path = Path(str(outputs.get("summary") or ""))
    analyst_path = Path(str(outputs.get("analyst") or ""))
    lines = [
        "",
        "HPFA TEAM ATTRIBUTION RECOVERY V1",
        "=================================",
        f"projection_status={report.get('team_attribution_projection_status')}",
        f"eligible_action_candidate_count={report.get('action_occurrence_eligible_count')}",
        f"direct_known_team_eligible_count={report.get('direct_known_team_eligible_count')}",
        f"recovered_team_eligible_count={report.get('recovered_team_eligible_count')}",
        f"unresolved_team_eligible_count={report.get('unresolved_team_eligible_count')}",
        f"raw_known_team_coverage_candidate={report.get('raw_known_team_coverage_candidate')}",
        f"effective_known_team_coverage_candidate={report.get('effective_known_team_coverage_candidate')}",
        "team_attribution_is_validated_truth=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]
    text = "\n".join(lines)
    for path in (summary_path, analyst_path):
        if path.name and path.is_file():
            with path.open("a", encoding="utf-8") as handle:
                handle.write(text)


def _inherit_projection_status(report: dict[str, Any], projected: dict[str, Any]) -> None:
    status = projected.get("status")
    if status == "FAIL_CLOSED":
        report["status"] = "FAIL_CLOSED"
        report["decision"] = "CONTEXT_ACTION_SEMANTICS_TEAM_ATTRIBUTION_PROJECTION_REJECTED"
        report["hard_block_hits"] = sorted(set(
            list(report.get("hard_block_hits") or [])
            + [f"team_attribution:{item}" for item in (projected.get("hard_block_hits") or [])]
        ))
        return
    if status == "REVIEW_REQUIRED":
        if report.get("status") != "FAIL_CLOSED":
            report["status"] = "REVIEW_REQUIRED"
        review_hits = list(report.get("review_hits") or [])
        projection_hits = list(projected.get("review_hits") or [])
        if not projection_hits:
            projection_hits = ["team_attribution_projection_review_required"]
        report["review_hits"] = sorted(set(review_hits + [f"team_attribution:{item}" for item in projection_hits]))


def write_outputs(input_dir: str | Path, out_dir: str | Path, *, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "context_action_semantics_rebind_lite" / "src"
    core_path = src / "context_action_semantics_rebind.py"
    projection_path = src / "team_attribution_projection.py"
    core = _load_module_from_path("hpfa_context_action_semantics_rebind_core_v1", core_path)
    projection = _load_module_from_path("hpfa_team_attribution_projection_core_v1", projection_path)

    report = core.write_outputs(input_dir, out_dir, repo_root=root)
    source = Path(input_dir).expanduser().resolve(strict=False)
    evidence = _load_optional_json(source / "evidence_atom_inventory_lite_v1.json")
    identity = _load_optional_json(source / "match_local_identity_candidates_lite_v1.json")

    if evidence is None or identity is None:
        report["team_attribution_projection_status"] = "NOT_EVALUATED_IDENTITY_INPUTS_MISSING"
        report["direct_known_team_eligible_count"] = None
        report["recovered_team_eligible_count"] = None
        report["unresolved_team_eligible_count"] = None
        report["raw_known_team_coverage_candidate"] = None
        report["effective_known_team_coverage_candidate"] = None
        report["team_attribution_is_validated_truth"] = False
    else:
        projected = projection.project_team_attribution(report, evidence, identity)
        report["team_attribution_projection"] = {
            key: value
            for key, value in projected.items()
            if key != "context_action_semantic_records"
        }
        report["team_attribution_projection_status"] = projected.get("status")
        report["direct_known_team_eligible_count"] = projected.get("direct_known_team_eligible_count")
        report["recovered_team_eligible_count"] = projected.get("recovered_team_eligible_count")
        report["unresolved_team_eligible_count"] = projected.get("unresolved_team_eligible_count")
        report["raw_known_team_coverage_candidate"] = projected.get("raw_known_team_coverage_candidate")
        report["effective_known_team_coverage_candidate"] = projected.get("effective_known_team_coverage_candidate")
        report["team_attribution_is_validated_truth"] = False

        _inherit_projection_status(report, projected)
        if report.get("status") != "FAIL_CLOSED":
            projected_rows = projected.get("context_action_semantic_records")
            if isinstance(projected_rows, list) and len(projected_rows) == len(report.get("context_action_semantic_records") or []):
                report["context_action_semantic_records"] = projected_rows
            else:
                report["status"] = "FAIL_CLOSED"
                report["decision"] = "CONTEXT_ACTION_SEMANTICS_TEAM_ATTRIBUTION_PROJECTION_REJECTED"
                report["hard_block_hits"] = sorted(set(
                    list(report.get("hard_block_hits") or []) + ["team_attribution_projection_population_mismatch"]
                ))

    output_json = Path(str((report.get("outputs") or {}).get("json") or ""))
    if output_json.name:
        output_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    _append_projection_audit(report)
    return report


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir, repo_root=root)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "input_context_count": report.get("input_context_count"),
        "reviewed_provider_semantics_bound_count": report.get("reviewed_provider_semantics_bound_count"),
        "action_occurrence_eligible_count": report.get("action_occurrence_eligible_count"),
        "non_action_context_or_reference_count": report.get("non_action_context_or_reference_count"),
        "provider_semantics_unresolved_or_review_required_count": report.get("provider_semantics_unresolved_or_review_required_count"),
        "eligible_action_family_candidate_counts": report.get("eligible_action_family_candidate_counts"),
        "team_attribution_projection_status": report.get("team_attribution_projection_status"),
        "direct_known_team_eligible_count": report.get("direct_known_team_eligible_count"),
        "recovered_team_eligible_count": report.get("recovered_team_eligible_count"),
        "unresolved_team_eligible_count": report.get("unresolved_team_eligible_count"),
        "raw_known_team_coverage_candidate": report.get("raw_known_team_coverage_candidate"),
        "effective_known_team_coverage_candidate": report.get("effective_known_team_coverage_candidate"),
        "semantic_collision_audit": report.get("semantic_collision_audit"),
        "hard_block_hits": report.get("hard_block_hits"),
        "review_hits": report.get("review_hits"),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
