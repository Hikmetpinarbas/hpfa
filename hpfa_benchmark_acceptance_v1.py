from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

MODULE_ID = "hpfa_benchmark_acceptance_v1"
HEALTH_JSON = "HPFA_SYSTEM_HEALTH_AUDIT.json"
HEALTH_TXT = "HPFA_SYSTEM_HEALTH_AUDIT.txt"
COMBINED_TXT = "HPFA_ACCEPTANCE_COMBINED_REPORT.txt"
ANALYST_REPORT = "HPFA_ANALYST_REPORT.txt"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _module_dirs(repo_root: Path) -> list[Path]:
    root = repo_root / "hpfa" / "modules" / "core"
    if not root.is_dir():
        return []
    return sorted(
        [p for p in root.iterdir() if p.is_dir() and not p.name.startswith("__")],
        key=lambda p: p.name,
    )


def _test_files(module_dir: Path) -> list[Path]:
    tests = module_dir / "tests"
    if not tests.is_dir():
        return []
    return sorted(tests.glob("test_*.py"))


def _source_files(module_dir: Path) -> list[Path]:
    src = module_dir / "src"
    if not src.is_dir():
        return []
    return sorted(p for p in src.glob("*.py") if p.name != "__init__.py")


def _artifact_module_ids(out_dir: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for path in sorted(out_dir.glob("*.json")):
        payload = _load_json(path)
        module_id = str(payload.get("module_id") or "").strip()
        if module_id:
            result.setdefault(module_id, []).append(path.name)
    return result


def _normalize_module_id(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"_v\d+(?:\.\d+)*$", "", text)
    return text


def _runtime_observed_module_dirs(module_names: list[str], module_ids: list[str]) -> list[str]:
    normalized_ids = [_normalize_module_id(value) for value in module_ids]
    observed: list[str] = []
    for name in module_names:
        key = name.lower()
        if any(mid == key or mid.startswith(key + "_") or key.startswith(mid + "_") for mid in normalized_ids if mid):
            observed.append(name)
    return observed


def _report_delta(current: Path, previous: Path | None) -> dict[str, Any]:
    if previous is None or not previous.is_file() or not current.is_file():
        return {
            "comparison_state": "NOT_EVALUATED_PREVIOUS_REPORT_MISSING",
            "report_changed": None,
            "added_line_count": None,
            "removed_line_count": None,
            "changed_line_sample": [],
        }
    current_lines = current.read_text(encoding="utf-8", errors="replace").splitlines()
    previous_lines = previous.read_text(encoding="utf-8", errors="replace").splitlines()
    diff = list(difflib.unified_diff(previous_lines, current_lines, lineterm=""))
    added = [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]
    removed = [line[1:] for line in diff if line.startswith("-") and not line.startswith("---")]
    sample = [*[("+ " + line) for line in added[:10]], *[("- " + line) for line in removed[:10]]]
    return {
        "comparison_state": "EVALUATED",
        "report_changed": bool(diff),
        "added_line_count": len(added),
        "removed_line_count": len(removed),
        "changed_line_sample": sample,
    }


def _write_health_outputs(out_dir: Path, payload: dict[str, Any]) -> None:
    (out_dir / HEALTH_JSON).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "HPFA SYSTEM HEALTH AUDIT",
        "========================",
        f"status={payload.get('status')}",
        f"exact_head_elapsed_seconds={payload.get('exact_head_elapsed_seconds')}",
        f"core_module_directory_count={payload.get('core_module_directory_count')}",
        f"modules_with_source_count={payload.get('modules_with_source_count')}",
        f"modules_with_tests_count={payload.get('modules_with_tests_count')}",
        f"test_file_count={payload.get('test_file_count')}",
        f"fresh_json_artifact_count={payload.get('fresh_json_artifact_count')}",
        f"runtime_observed_module_id_count={payload.get('runtime_observed_module_id_count')}",
        f"runtime_observed_core_module_candidate_count={payload.get('runtime_observed_core_module_candidate_count')}",
        f"runtime_unobserved_core_module_candidate_count={payload.get('runtime_unobserved_core_module_candidate_count')}",
        f"module_runtime_timing_coverage={payload.get('module_runtime_timing_coverage')}",
        f"analyst_report_present={payload.get('analyst_report_present')}",
        f"analyst_report_delta_state={(payload.get('analyst_report_delta') or {}).get('comparison_state')}",
        "",
        "runtime_observed_core_module_candidates:",
    ]
    lines.extend(f"- {name}" for name in payload.get("runtime_observed_core_module_candidates") or [])
    lines.extend(["", "not_observed_as_independent_artifact_on_this_run:"])
    lines.extend(f"- {name}" for name in payload.get("runtime_unobserved_core_module_candidates") or [])
    lines.extend([
        "",
        "NOTES",
        "- runtime_unobserved does not prove orphan status; a module may be used as an imported library without emitting its own artifact.",
        "- per-module timing is not fabricated. Until producer-level timers are instrumented, only exact-head end-to-end elapsed time is authoritative.",
        "- canonical_event_count remains UNKNOWN; true_action_count remains UNKNOWN; production_release remains false.",
        "",
    ])
    (out_dir / HEALTH_TXT).write_text("\n".join(lines), encoding="utf-8")


def _write_combined_report(out_dir: Path, payload: dict[str, Any]) -> None:
    analyst_path = out_dir / ANALYST_REPORT
    analyst = analyst_path.read_text(encoding="utf-8", errors="replace") if analyst_path.is_file() else "HPFA_ANALYST_REPORT.txt mevcut degil.\n"
    delta = payload.get("analyst_report_delta") or {}
    health = (out_dir / HEALTH_TXT).read_text(encoding="utf-8", errors="replace")
    lines = [
        analyst.rstrip(),
        "",
        "",
        health.rstrip(),
        "",
        "ANALYST REPORT DELTA",
        "====================",
        f"comparison_state={delta.get('comparison_state')}",
        f"report_changed={delta.get('report_changed')}",
        f"added_line_count={delta.get('added_line_count')}",
        f"removed_line_count={delta.get('removed_line_count')}",
    ]
    for row in delta.get("changed_line_sample") or []:
        lines.append(str(row))
    lines.extend(["", "canonical_event_count=UNKNOWN", "true_action_count=UNKNOWN", "production_release=false", ""])
    (out_dir / COMBINED_TXT).write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exact-head ACTIVE_MATCH acceptance and write a non-production system-health benchmark.")
    parser.add_argument("--match-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--expected-product-commit", required=True)
    parser.add_argument("--previous-analyst-report")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    out_dir = Path(args.out_dir).expanduser().resolve(strict=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    exact_runner = repo_root / "active_match_exact_head_run_v1.py"

    command = [
        sys.executable,
        str(exact_runner),
        "--match-dir",
        str(Path(args.match_dir).expanduser().resolve(strict=False)),
        "--out-dir",
        str(out_dir),
        "--expected-product-commit",
        str(args.expected_product_commit),
    ]
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=repo_root, text=True, capture_output=True)
    elapsed = round(time.perf_counter() - started, 6)

    module_dirs = _module_dirs(repo_root)
    module_names = [path.name for path in module_dirs]
    source_counts = {path.name: len(_source_files(path)) for path in module_dirs}
    test_counts = {path.name: len(_test_files(path)) for path in module_dirs}
    artifact_module_ids = _artifact_module_ids(out_dir)
    observed_dirs = _runtime_observed_module_dirs(module_names, sorted(artifact_module_ids))
    observed_set = set(observed_dirs)
    unobserved_dirs = [name for name in module_names if name not in observed_set]

    analyst_path = out_dir / ANALYST_REPORT
    previous_path = Path(args.previous_analyst_report).expanduser().resolve(strict=False) if args.previous_analyst_report else None
    delta = _report_delta(analyst_path, previous_path)
    exact = _load_json(out_dir / "active_match_exact_head_run_v1.json")

    payload = {
        "module_id": MODULE_ID,
        "status": "PASS" if completed.returncode == 0 else "REVIEW_REQUIRED",
        "exact_head_returncode": completed.returncode,
        "exact_head_elapsed_seconds": elapsed,
        "exact_product_commit_verified": exact.get("exact_product_commit_verified") is True,
        "expected_product_commit": args.expected_product_commit,
        "product_code_commit": exact.get("product_code_commit"),
        "core_module_directory_count": len(module_dirs),
        "core_module_names": module_names,
        "modules_with_source_count": sum(1 for value in source_counts.values() if value > 0),
        "modules_with_tests_count": sum(1 for value in test_counts.values() if value > 0),
        "test_file_count": sum(test_counts.values()),
        "module_source_file_counts": source_counts,
        "module_test_file_counts": test_counts,
        "fresh_json_artifact_count": len(list(out_dir.glob("*.json"))),
        "runtime_observed_module_id_count": len(artifact_module_ids),
        "runtime_observed_module_ids": sorted(artifact_module_ids),
        "runtime_module_artifacts": artifact_module_ids,
        "runtime_observed_core_module_candidate_count": len(observed_dirs),
        "runtime_observed_core_module_candidates": observed_dirs,
        "runtime_unobserved_core_module_candidate_count": len(unobserved_dirs),
        "runtime_unobserved_core_module_candidates": unobserved_dirs,
        "runtime_unobserved_is_orphan_truth": False,
        "orphan_status": "NOT_PROVEN_BY_THIS_AUDIT",
        "module_runtime_timing_coverage": "END_TO_END_ONLY_PER_MODULE_TIMERS_NOT_YET_INSTRUMENTED",
        "per_module_runtime_seconds": {},
        "analyst_report_present": analyst_path.is_file(),
        "analyst_report_sha256": _sha256(analyst_path),
        "analyst_report_delta": delta,
        "exact_runner_stdout_tail": completed.stdout[-4000:],
        "exact_runner_stderr_tail": completed.stderr[-4000:],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    _write_health_outputs(out_dir, payload)
    _write_combined_report(out_dir, payload)
    print(json.dumps({
        "status": payload["status"],
        "exact_head_elapsed_seconds": elapsed,
        "core_module_directory_count": payload["core_module_directory_count"],
        "modules_with_tests_count": payload["modules_with_tests_count"],
        "runtime_observed_core_module_candidate_count": payload["runtime_observed_core_module_candidate_count"],
        "health_json": str(out_dir / HEALTH_JSON),
        "combined_report": str(out_dir / COMBINED_TXT),
    }, ensure_ascii=False, sort_keys=True))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
