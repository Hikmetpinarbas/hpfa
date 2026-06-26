from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

RUN_JSON = "active_match_full_run_lite_v1.json"
RUN_TXT = "active_match_full_run_lite_v1.txt"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def run_step(repo_root: Path, command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=repo_root, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "passed": completed.returncode == 0,
    }


def write_summary(out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    event_window = read_json(out_dir / "event_window_builder_lite_v1.json")
    time_scale = read_json(out_dir / "time_scale_router_lite_v1.json")
    axis = read_json(out_dir / "axis_integrity_tagger_lite_v1.json")
    report = {
        "module_id": "active_match_full_run_lite_v1",
        "status": "REVIEW_REQUIRED",
        "decision": "ACTIVE_MATCH_REPO_CHAIN_EXECUTED",
        "claim_safety": "RUNTIME_EVIDENCE_ONLY",
        "steps": steps,
        "engineering_evidence": {
            "all_steps_passed": all(step.get("passed") is True for step in steps),
            "event_window_output_exists": bool(event_window),
            "time_scale_output_exists": bool(time_scale),
            "axis_integrity_output_exists": bool(axis),
        },
        "analyst_evidence": {
            "input_context_count": event_window.get("input_context_count"),
            "minute_bearing_context_count": event_window.get("minute_bearing_context_count"),
            "event_window_count": event_window.get("event_window_count"),
            "routed_window_count": time_scale.get("routed_window_count"),
            "minute_axis_window_count": time_scale.get("minute_axis_window_count"),
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
        },
        "outputs": {
            "json": str(out_dir / RUN_JSON),
            "txt": str(out_dir / RUN_TXT),
        },
    }
    (out_dir / RUN_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA ACTIVE MATCH FULL RUN LITE V1",
        "===================================",
        f"status={report['status']}",
        f"decision={report['decision']}",
        f"claim_safety={report['claim_safety']}",
        "",
        "[engineering_evidence]",
        json.dumps(report["engineering_evidence"], ensure_ascii=False, sort_keys=True),
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
    parser.add_argument("--match-dir", default="runtime/active_single_match/current")
    parser.add_argument("--out-dir", default="runtime/outputs/active_match_current")
    args = parser.parse_args()

    match_dir = Path(args.match_dir)
    out_dir = Path(args.out_dir)
    if not match_dir.is_absolute():
        match_dir = repo_root / match_dir
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    steps = [
        run_step(repo_root, [sys.executable, "event_window_builder.py", "--input-dir", str(match_dir), "--raw-input-dir", str(match_dir), "--out-dir", str(out_dir)]),
        run_step(repo_root, [sys.executable, "time_scale_router.py", "--input-dir", str(out_dir), "--out-dir", str(out_dir)]),
        run_step(repo_root, [sys.executable, "axis_integrity_tagger.py", "--input-dir", str(out_dir), "--out-dir", str(out_dir)]),
    ]
    report = write_summary(out_dir, steps)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "engineering_evidence": report.get("engineering_evidence"),
        "analyst_evidence": report.get("analyst_evidence"),
        "claim_boundary": report.get("claim_boundary"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if all(step.get("passed") is True for step in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
