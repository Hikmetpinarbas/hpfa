from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

MODULE_ID = "repo_full_health_audit_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _run(command: list[str], *, cwd: Path, timeout: int = 1800) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "stdout_tail": completed.stdout[-12000:],
            "stderr_tail": completed.stderr[-12000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "stdout_tail": str(exc.stdout or "")[-12000:],
            "stderr_tail": str(exc.stderr or "")[-12000:],
            "timed_out": True,
        }


def _git_head(root: Path) -> str | None:
    result = _run(["git", "rev-parse", "HEAD"], cwd=root, timeout=30)
    if result["returncode"] != 0:
        return None
    value = str(result["stdout_tail"]).strip().splitlines()
    return value[-1] if value else None


def _module_inventory(root: Path) -> dict[str, Any]:
    core = root / "hpfa" / "modules" / "core"
    module_dirs = sorted(
        [path for path in core.iterdir() if path.is_dir() and not path.name.startswith("__")]
        if core.is_dir()
        else [],
        key=lambda path: path.name,
    )
    rows: list[dict[str, Any]] = []
    for module in module_dirs:
        src = module / "src"
        tests = module / "tests"
        source_files = sorted(path for path in src.glob("*.py") if path.name != "__init__.py") if src.is_dir() else []
        test_files = sorted(tests.glob("test_*.py")) if tests.is_dir() else []
        rows.append(
            {
                "module": module.name,
                "source_file_count": len(source_files),
                "test_file_count": len(test_files),
                "has_source": bool(source_files),
                "has_tests": bool(test_files),
            }
        )
    return {
        "core_module_directory_count": len(rows),
        "modules_with_source_count": sum(row["has_source"] for row in rows),
        "modules_with_tests_count": sum(row["has_tests"] for row in rows),
        "core_source_file_count": sum(int(row["source_file_count"]) for row in rows),
        "core_test_file_count": sum(int(row["test_file_count"]) for row in rows),
        "modules_without_source": [row["module"] for row in rows if not row["has_source"]],
        "modules_without_tests": [row["module"] for row in rows if not row["has_tests"]],
        "modules": rows,
    }


def _repo_inventory(root: Path) -> dict[str, Any]:
    py_files = [path for path in root.rglob("*.py") if ".git" not in path.parts]
    test_files = [path for path in py_files if path.name.startswith("test_")]
    workflow_dir = root / ".github" / "workflows"
    workflows = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml")) if workflow_dir.is_dir() else []
    root_entrypoints = sorted(path.name for path in root.glob("*.py"))
    return {
        "repository_python_file_count": len(py_files),
        "repository_test_file_count": len(test_files),
        "workflow_file_count": len(workflows),
        "root_python_entrypoint_count": len(root_entrypoints),
        "root_python_entrypoints": root_entrypoints,
        "workflow_files": [path.name for path in workflows],
    }


def _parse_junit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "junit_present": False,
            "tests": None,
            "failures": None,
            "errors": None,
            "skipped": None,
            "time_seconds": None,
        }
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return {
            "junit_present": True,
            "tests": None,
            "failures": None,
            "errors": None,
            "skipped": None,
            "time_seconds": None,
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


def _write_text(path: Path, payload: dict[str, Any]) -> None:
    tests = payload.get("pytest_summary") or {}
    modules = payload.get("module_inventory") or {}
    repo = payload.get("repo_inventory") or {}
    lines = [
        "HPFA FULL REPOSITORY HEALTH AUDIT V1",
        "====================================",
        f"status={payload.get('status')}",
        f"git_head={payload.get('git_head')}",
        f"python={payload.get('python_version')}",
        f"repository_python_file_count={repo.get('repository_python_file_count')}",
        f"repository_test_file_count={repo.get('repository_test_file_count')}",
        f"workflow_file_count={repo.get('workflow_file_count')}",
        f"core_module_directory_count={modules.get('core_module_directory_count')}",
        f"modules_with_source_count={modules.get('modules_with_source_count')}",
        f"modules_with_tests_count={modules.get('modules_with_tests_count')}",
        f"core_source_file_count={modules.get('core_source_file_count')}",
        f"core_test_file_count={modules.get('core_test_file_count')}",
        f"compile_returncode={(payload.get('compile') or {}).get('returncode')}",
        f"compile_elapsed_seconds={(payload.get('compile') or {}).get('elapsed_seconds')}",
        f"collect_returncode={(payload.get('collect') or {}).get('returncode')}",
        f"collect_elapsed_seconds={(payload.get('collect') or {}).get('elapsed_seconds')}",
        f"pytest_returncode={(payload.get('pytest') or {}).get('returncode')}",
        f"pytest_elapsed_seconds={(payload.get('pytest') or {}).get('elapsed_seconds')}",
        f"pytest_tests={tests.get('tests')}",
        f"pytest_failures={tests.get('failures')}",
        f"pytest_errors={tests.get('errors')}",
        f"pytest_skipped={tests.get('skipped')}",
        "",
        "MODULES_WITHOUT_TESTS",
    ]
    lines.extend(f"- {name}" for name in modules.get("modules_without_tests") or [])
    lines.extend(["", "MODULES_WITHOUT_SOURCE"])
    lines.extend(f"- {name}" for name in modules.get("modules_without_source") or [])
    lines.extend([
        "",
        "CLAIM_LOCKS",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
        "NOTE",
        "This audit proves repository compile/test health only. It does not substitute for physical ACTIVE_MATCH evidence.",
        "A module directory is not automatically an independent runtime engine or an orphan capability.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile and test the full HPFA repository and write an inventory report.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    out = Path(args.out_dir).expanduser().resolve(strict=False)
    out.mkdir(parents=True, exist_ok=True)
    junit = out / "pytest-junit.xml"

    module_inventory = _module_inventory(root)
    repo_inventory = _repo_inventory(root)
    compile_result = _run([sys.executable, "-m", "compileall", "-q", str(root)], cwd=root, timeout=args.timeout_seconds)
    collect_result = _run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=root, timeout=args.timeout_seconds)
    pytest_result = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--durations=50",
            f"--junitxml={junit}",
        ],
        cwd=root,
        timeout=args.timeout_seconds,
    )
    pytest_summary = _parse_junit(junit)

    status = "PASS"
    if compile_result["returncode"] != 0 or collect_result["returncode"] != 0 or pytest_result["returncode"] != 0:
        status = "REVIEW_REQUIRED"

    payload = {
        "module_id": MODULE_ID,
        "status": status,
        "git_head": _git_head(root),
        "python_version": sys.version.replace("\n", " "),
        "module_inventory": module_inventory,
        "repo_inventory": repo_inventory,
        "compile": compile_result,
        "collect": collect_result,
        "pytest": pytest_result,
        "pytest_summary": pytest_summary,
        "physical_active_match_evaluated": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }
    json_path = out / "HPFA_FULL_REPO_HEALTH_AUDIT.json"
    txt_path = out / "HPFA_FULL_REPO_HEALTH_AUDIT.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_text(txt_path, payload)
    print(json.dumps({
        "status": status,
        "git_head": payload["git_head"],
        "core_module_directory_count": module_inventory["core_module_directory_count"],
        "modules_with_tests_count": module_inventory["modules_with_tests_count"],
        "pytest_tests": pytest_summary.get("tests"),
        "pytest_failures": pytest_summary.get("failures"),
        "pytest_errors": pytest_summary.get("errors"),
        "pytest_elapsed_seconds": pytest_result["elapsed_seconds"],
        "report": str(txt_path),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
