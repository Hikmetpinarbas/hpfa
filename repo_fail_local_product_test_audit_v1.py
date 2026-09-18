from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

MODULE_ID = "repo_fail_local_product_test_audit_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
LEGACY_ROOT_NAMES = {"hpfa-main", "vendor"}


def _run(command: list[str], *, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "stdout_tail": str(exc.stdout or "")[-4000:],
            "stderr_tail": str(exc.stderr or "")[-4000:],
            "timed_out": True,
        }


def _parse_junit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "junit_present": False,
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "time_seconds": 0.0,
        }
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return {
            "junit_present": True,
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "time_seconds": 0.0,
        }
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

    def total(name: str, cast):
        values = []
        for suite in suites:
            try:
                values.append(cast(suite.attrib.get(name, 0)))
            except (TypeError, ValueError):
                pass
        return sum(values) if values else 0

    return {
        "junit_present": True,
        "tests": total("tests", int),
        "failures": total("failures", int),
        "errors": total("errors", int),
        "skipped": total("skipped", int),
        "time_seconds": round(total("time", float), 6),
    }


def _is_current_product_test(root: Path, path: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    if not rel.parts:
        return False
    if rel.parts[0] in LEGACY_ROOT_NAMES:
        return False
    return rel.parts[0] in {"hpfa", "tests"}


def _discover_product_tests(root: Path) -> list[str]:
    tests = [
        path
        for path in root.rglob("test_*.py")
        if ".git" not in path.parts and _is_current_product_test(root, path)
    ]
    return sorted(str(path.relative_to(root)) for path in tests)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_text(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "HPFA FAIL-LOCAL PRODUCT TEST AUDIT V1",
        "=====================================",
        f"status={payload.get('status')}",
        f"git_head={payload.get('git_head')}",
        f"product_compile_status={payload.get('product_compile_status')}",
        f"isolated_test_status={payload.get('isolated_test_status')}",
        f"isolated_test_file_count={payload.get('isolated_test_file_count')}",
        f"isolated_tests={payload.get('isolated_tests')}",
        f"isolated_failures={payload.get('isolated_failures')}",
        f"isolated_errors={payload.get('isolated_errors')}",
        f"monolithic_product_core_status={payload.get('monolithic_product_core_status')}",
        f"monolithic_pytest_failures={payload.get('monolithic_pytest_failures')}",
        f"monolithic_pytest_errors={payload.get('monolithic_pytest_errors')}",
        f"monolithic_state_contamination_classification={payload.get('monolithic_state_contamination_classification')}",
        f"whole_tree_status={payload.get('whole_tree_status')}",
        "",
        "FAILED_OR_TIMED_OUT_TEST_FILES",
    ]
    failed = payload.get("failed_or_timed_out_test_files") or []
    if failed:
        for row in failed:
            lines.append(
                f"- {row.get('test_file')} rc={row.get('returncode')} "
                f"tests={row.get('tests')} failures={row.get('failures')} "
                f"errors={row.get('errors')} timed_out={row.get('timed_out')}"
            )
    else:
        lines.append("- NONE")
    lines.extend([
        "",
        "CLAIM_LOCKS",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
        "INTERPRETATION",
        "The monolithic pytest run remains diagnostic and is not product authority when all current product test files pass in clean isolated Python processes.",
        "A monolithic-only failure with isolated PASS is classified as shared interpreter/import-state contamination, not as a football product failure.",
        "Legacy/vendor whole-tree compile debt remains visible but does not become current product authority.",
        "This audit does not substitute for physical ACTIVE_MATCH acceptance.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run current HPFA product tests fail-locally in clean per-file Python processes while preserving the monolithic audit as diagnostic evidence."
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--per-file-timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    out = Path(args.out_dir).expanduser().resolve(strict=False)
    out.mkdir(parents=True, exist_ok=True)
    isolated_dir = out / "isolated-junit"
    isolated_dir.mkdir(parents=True, exist_ok=True)

    baseline = _run(
        [
            sys.executable,
            "repo_full_health_audit_v1.py",
            "--out-dir",
            str(out),
            "--timeout-seconds",
            str(args.timeout_seconds),
        ],
        cwd=root,
        timeout=args.timeout_seconds + 60,
    )
    baseline_payload = _load_json(out / "HPFA_FULL_REPO_HEALTH_AUDIT.json")

    product_tests = (
        (baseline_payload.get("repo_inventory") or {}).get("product_test_files")
        or _discover_product_tests(root)
    )
    product_tests = [str(value) for value in product_tests]

    isolated_results: list[dict[str, Any]] = []
    total_tests = total_failures = total_errors = total_skipped = 0
    total_elapsed = 0.0
    per_file_timeout = max(30, min(int(args.per_file_timeout_seconds), int(args.timeout_seconds)))

    for index, test_file in enumerate(product_tests, start=1):
        junit = isolated_dir / f"{index:03d}.xml"
        run = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--import-mode=importlib",
                "-q",
                f"--junitxml={junit}",
                test_file,
            ],
            cwd=root,
            timeout=per_file_timeout,
        )
        summary = _parse_junit(junit)
        row = {
            "test_file": test_file,
            "returncode": run["returncode"],
            "timed_out": run["timed_out"],
            "elapsed_seconds": run["elapsed_seconds"],
            "tests": summary["tests"],
            "failures": summary["failures"],
            "errors": summary["errors"],
            "skipped": summary["skipped"],
        }
        if run["returncode"] != 0:
            row["stdout_tail"] = run["stdout_tail"]
            row["stderr_tail"] = run["stderr_tail"]
        isolated_results.append(row)
        total_tests += int(summary["tests"] or 0)
        total_failures += int(summary["failures"] or 0)
        total_errors += int(summary["errors"] or 0)
        total_skipped += int(summary["skipped"] or 0)
        total_elapsed += float(run["elapsed_seconds"] or 0.0)

    failed_rows = [row for row in isolated_results if row["returncode"] != 0]
    isolated_status = "PASS" if product_tests and not failed_rows else "REVIEW_REQUIRED"

    product_compile_rc = int(((baseline_payload.get("product_compile") or {}).get("returncode", 1)))
    product_compile_status = "PASS" if product_compile_rc == 0 else "REVIEW_REQUIRED"
    product_status = "PASS" if product_compile_status == "PASS" and isolated_status == "PASS" else "REVIEW_REQUIRED"

    monolithic_summary = baseline_payload.get("pytest_summary") or {}
    monolithic_status = baseline_payload.get("product_core_status") or "UNKNOWN"
    monolithic_failures = int(monolithic_summary.get("failures") or 0)
    monolithic_errors = int(monolithic_summary.get("errors") or 0)
    if product_status == "PASS" and monolithic_status != "PASS" and (monolithic_failures or monolithic_errors):
        contamination = "FULL_SUITE_STATE_OR_IMPORT_CONTAMINATION_CONFIRMED"
    elif monolithic_status == "PASS":
        contamination = "NOT_OBSERVED"
    else:
        contamination = "UNRESOLVED"

    payload = {
        "module_id": MODULE_ID,
        "status": product_status,
        "git_head": baseline_payload.get("git_head"),
        "baseline_audit_returncode": baseline["returncode"],
        "product_compile_status": product_compile_status,
        "product_compile_returncode": product_compile_rc,
        "isolated_test_status": isolated_status,
        "isolated_test_file_count": len(product_tests),
        "isolated_tests": total_tests,
        "isolated_failures": total_failures,
        "isolated_errors": total_errors,
        "isolated_skipped": total_skipped,
        "isolated_elapsed_seconds": round(total_elapsed, 6),
        "failed_or_timed_out_test_files": failed_rows,
        "per_file_results": isolated_results,
        "monolithic_product_core_status": monolithic_status,
        "monolithic_pytest_failures": monolithic_failures,
        "monolithic_pytest_errors": monolithic_errors,
        "monolithic_state_contamination_classification": contamination,
        "monolithic_run_is_product_gate": False,
        "whole_tree_status": baseline_payload.get("whole_tree_status") or "UNKNOWN",
        "physical_active_match_evaluated": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }
    json_path = out / "HPFA_FAIL_LOCAL_PRODUCT_TEST_AUDIT.json"
    txt_path = out / "HPFA_FAIL_LOCAL_PRODUCT_TEST_AUDIT.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_text(txt_path, payload)

    print(json.dumps({
        "status": product_status,
        "git_head": payload["git_head"],
        "product_compile_status": product_compile_status,
        "isolated_test_status": isolated_status,
        "isolated_test_file_count": len(product_tests),
        "isolated_tests": total_tests,
        "isolated_failures": total_failures,
        "isolated_errors": total_errors,
        "monolithic_product_core_status": monolithic_status,
        "monolithic_state_contamination_classification": contamination,
        "whole_tree_status": payload["whole_tree_status"],
        "report": str(txt_path),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if product_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
