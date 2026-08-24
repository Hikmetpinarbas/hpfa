from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

RUN_JSON = "active_match_full_run_lite_v1.json"
RUN_TXT = "active_match_full_run_lite_v1.txt"
SURFACE_SUFFIXES = {".csv", ".xml", ".xlsx"}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def safe_int(value: Any) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return 0


def ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def spine_runner_module(repo_root: Path):
    src = repo_root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_module_path(src)
    import spine_runner  # type: ignore
    return spine_runner


def provider_time_module(repo_root: Path):
    src = (
        repo_root
        / "hpfa"
        / "modules"
        / "core"
        / "provider_alias_field_semantics_lite"
        / "src"
    )
    ensure_module_path(src)
    import provider_time_semantic_admission  # type: ignore
    return provider_time_semantic_admission


def readable_surface_files(match_dir: Path) -> list[Path]:
    if not match_dir.exists() or not match_dir.is_dir():
        return []
    return [
        p
        for p in match_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SURFACE_SUFFIXES
    ]


def run_step(repo_root: Path, command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "passed": completed.returncode == 0,
    }


def run_provider_time_context_step(
    repo_root: Path,
    match_dir: Path,
    out_dir: Path,
) -> dict[str, Any]:
    try:
        module = provider_time_module(repo_root)
        report = module.write_minimum_context_with_provider_time(
            match_dir,
            out_dir,
            repo_root,
        )
    except Exception as exc:
        return {
            "command": ["internal:provider_time_semantic_admission_lite_v1"],
            "returncode": 1,
            "stdout": "",
            "stderr": f"{type(exc).__name__}:{exc}",
            "passed": False,
        }
    admission = report.get("provider_time_semantic_admission") or {}
    return {
        "command": ["internal:provider_time_semantic_admission_lite_v1"],
        "returncode": 0,
        "stdout": json.dumps(
            {
                "status": admission.get("status"),
                "unit_candidate": admission.get("unit_candidate"),
                "time_basis_candidate": admission.get("time_basis_candidate"),
                "review_reasons": admission.get("review_reasons"),
                "context_candidate_count": report.get("context_candidate_count"),
                "time_admission_status": report.get("time_admission_status"),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        "stderr": "",
        "passed": True,
    }


def write_summary(
    out_dir: Path,
    steps: list[dict[str, Any]],
    input_status: dict[str, Any],
) -> dict[str, Any]:
    minimum_context = read_json(out_dir / "minimum_viable_context_lite_v1.json")
    event_window = read_json(out_dir / "event_window_builder_lite_v1.json")
    time_scale = read_json(out_dir / "time_scale_router_lite_v1.json")
    axis = read_json(out_dir / "axis_integrity_tagger_lite_v1.json")
    provider_time = minimum_context.get("provider_time_semantic_admission") or {}

    evidence_nonzero = (
        safe_int(event_window.get("input_context_count")) > 0
        and safe_int(event_window.get("event_window_count")) > 0
    )
    all_steps_passed = all(step.get("passed") is True for step in steps)
    valid_run = (
        bool(input_status.get("input_surface_ready"))
        and all_steps_passed
        and evidence_nonzero
    )
    report = {
        "module_id": "active_match_full_run_lite_v1",
        "status": "REVIEW_REQUIRED" if valid_run else "FAIL_CLOSED",
        "decision": (
            "ACTIVE_MATCH_REPO_CHAIN_EXECUTED"
            if valid_run
            else "ACTIVE_MATCH_INPUT_OR_EVIDENCE_REJECTED"
        ),
        "claim_safety": "RUNTIME_EVIDENCE_ONLY",
        "input_status": input_status,
        "steps": steps,
        "engineering_evidence": {
            "all_steps_passed": all_steps_passed,
            "evidence_nonzero": evidence_nonzero,
            "valid_run": valid_run,
            "minimum_context_output_exists": bool(minimum_context),
            "provider_time_admission_status": provider_time.get("status"),
            "provider_time_unit_candidate": provider_time.get("unit_candidate"),
            "provider_time_basis_candidate": provider_time.get(
                "time_basis_candidate"
            ),
            "event_window_output_exists": bool(event_window),
            "time_scale_output_exists": bool(time_scale),
            "axis_integrity_output_exists": bool(axis),
        },
        "analyst_evidence": {
            "input_context_count": event_window.get("input_context_count"),
            "minute_bearing_context_count": event_window.get(
                "minute_bearing_context_count"
            ),
            "event_window_count": event_window.get("event_window_count"),
            "routed_window_count": time_scale.get("routed_window_count"),
            "minute_axis_window_count": time_scale.get(
                "minute_axis_window_count"
            ),
            "provider_time_runtime_checks": provider_time.get("runtime_checks"),
            "time_admission_status": event_window.get("time_admission_status"),
            "ordering_status": event_window.get("ordering_status"),
            "axis_integrity_score": axis.get("axis_integrity_score"),
            "axis_status": axis.get("axis_status"),
            "downstream_permissions": axis.get("downstream_permissions"),
        },
        "claim_boundary": {
            "canonical_event_count": "UNKNOWN",
            "deduplicated_event_count": "UNKNOWN",
            "phase_truth": False,
            "possession_truth": False,
            "sequence_truth": False,
            "rhythm_truth": False,
            "tactical_truth": False,
            "dominance_truth": False,
            "production_release": False,
        },
        "outputs": {
            "json": str(out_dir / RUN_JSON),
            "txt": str(out_dir / RUN_TXT),
        },
    }
    (out_dir / RUN_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "HPFA ACTIVE MATCH FULL RUN LITE V1",
        "===================================",
        f"status={report['status']}",
        f"decision={report['decision']}",
        f"claim_safety={report['claim_safety']}",
        "",
        "[input_status]",
        json.dumps(report["input_status"], ensure_ascii=False, sort_keys=True),
        "",
        "[engineering_evidence]",
        json.dumps(
            report["engineering_evidence"],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "",
        "[analyst_evidence]",
        json.dumps(report["analyst_evidence"], ensure_ascii=False, sort_keys=True),
        "",
        "[claim_boundary]",
        json.dumps(report["claim_boundary"], ensure_ascii=False, sort_keys=True),
        "",
    ]
    (out_dir / RUN_TXT).write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--match-dir",
        default="runtime/active_single_match/current",
    )
    parser.add_argument(
        "--out-dir",
        default="runtime/outputs/active_match_current",
    )
    args = parser.parse_args()

    match_dir = Path(args.match_dir)
    out_dir = Path(args.out_dir)
    if not match_dir.is_absolute():
        match_dir = repo_root / match_dir
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir

    spine = spine_runner_module(repo_root)
    out_dir = spine.validate_output_root(out_dir)
    surfaces = readable_surface_files(match_dir)
    input_status = {
        "match_dir": str(match_dir),
        "surface_file_count": len(surfaces),
        "input_surface_ready": len(surfaces) > 0,
    }
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_status["input_surface_ready"]:
        report = write_summary(out_dir, [], input_status)
        print(
            json.dumps(
                {
                    "status": report.get("status"),
                    "decision": report.get("decision"),
                    "input_status": report.get("input_status"),
                    "engineering_evidence": report.get("engineering_evidence"),
                    "outputs": report.get("outputs"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1

    steps = [
        run_provider_time_context_step(repo_root, match_dir, out_dir),
        run_step(
            repo_root,
            [
                sys.executable,
                "event_window_builder.py",
                "--input-dir",
                str(out_dir),
                "--raw-input-dir",
                str(match_dir),
                "--out-dir",
                str(out_dir),
            ],
        ),
        run_step(
            repo_root,
            [
                sys.executable,
                "time_scale_router.py",
                "--input-dir",
                str(out_dir),
                "--out-dir",
                str(out_dir),
            ],
        ),
        run_step(
            repo_root,
            [
                sys.executable,
                "axis_integrity_tagger.py",
                "--input-dir",
                str(out_dir),
                "--out-dir",
                str(out_dir),
            ],
        ),
    ]
    report = write_summary(out_dir, steps, input_status)
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "decision": report.get("decision"),
                "input_status": report.get("input_status"),
                "engineering_evidence": report.get("engineering_evidence"),
                "analyst_evidence": report.get("analyst_evidence"),
                "claim_boundary": report.get("claim_boundary"),
                "outputs": report.get("outputs"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report.get("engineering_evidence", {}).get("valid_run") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
