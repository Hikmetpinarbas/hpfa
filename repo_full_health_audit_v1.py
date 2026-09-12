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
LEGACY_ROOT_NAMES = {"hpfa-main", "vendor"}


def _run(command: list[str], *, cwd: Path, timeout: int = 1800, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "stdout_tail": completed.stdout[-16000:],
            "stderr_tail": completed.stderr[-16000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "stdout_tail": str(exc.stdout or "")[-16000:],
            "stderr_tail": str(exc.stderr or "")[-16000:],
            "timed_out": True,
        }


def _git_head(root: Path) -> str | None:
    result = _run(["git", "rev-parse", "HEAD"], cwd=root, timeout=30)
    if result["returncode"] != 0:
        return None
    lines = str(result["stdout_tail"]).strip().splitlines()
    return lines[-1] if lines else None


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
        root_tests = sorted(module.glob("test_*.py"))
        all_tests = [*test_files, *root_tests]
        rows.append({
            "module": module.name,
            "source_file_count": len(source_files),
            "test_file_count": len(all_tests),
            "has_source": bool(source_files),
            "has_tests": bool(all_tests),
        })
    return {
        "core_module_directory_count": len(rows),
        "modules_with_source_count": sum(bool(row["has_source"]) for row in rows),
        "modules_with_tests_count": sum(bool(row["has_tests"]) for row in rows),
        "core_source_file_count": sum(int(row["source_file_count"]) for row in rows),
        "core_test_file_count": sum(int(row["test_file_count"]) for row in rows),
        "modules_without_source": [row["module"] for row in rows if not row["has_source"]],
        "modules_without_tests": [row["module"] for row in rows if not row["has_tests"]],
        "modules": rows,
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
    if rel.parts[0] == "hpfa":
        return True
    return rel.parts[0] == "tests"


def _repo_inventory(root: Path) -> dict[str, Any]:
    all_py = [path for path in root.rglob("*.py") if ".git" not in path.parts]
    all_tests = [path for path in all_py if path.name.startswith("test_")]
    product_tests = [path for path in all_tests if _is_current_product_test(root, path)]
    legacy_tests = [path for path in all_tests if path not in product_tests]

    product_py = list(root.glob("*.py"))
    hpfa_root = root / "hpfa"
    if hpfa_root.is_dir():
        product_py.extend(path for path in hpfa_root.rglob("*.py") if ".git" not in path.parts)

    workflow_dir = root / ".github" / "workflows"
    workflows = []
    if workflow_dir.is_dir():
        workflows = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")])

    return {
        "repository_python_file_count": len(all_py),
        "repository_test_file_count": len(all_tests),
        "product_python_file_count": len(product_py),
        "product_test_file_count": len(product_tests),
        "legacy_or_imported_test_file_count": len(legacy_tests),
        "product_test_files": [str(path.relative_to(root)) for path in product_tests],
        "legacy_or_imported_test_files": [str(path.relative_to(root)) for path in legacy_tests],
        "product_python_files": [str(path.relative_to(root)) for path in product_py],
        "workflow_file_count": len(workflows),
        "root_python_entrypoint_count": len(list(root.glob("*.py"))),
        "root_python_entrypoints": sorted(path.name for path in root.glob("*.py")),
        "workflow_files": [path.name for path in workflows],
    }


def _parse_junit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"junit_present": False, "tests": None, "failures": None, "errors": None, "skipped": None, "time_seconds": None}
    try:
        xml_root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return {"junit_present": True, "tests": None, "failures": None, "errors": None, "skipped": None, "time_seconds": None}
    suites = [xml_root] if xml_root.tag == "testsuite" else list(xml_root.findall("testsuite"))

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
        f"product_core_status={payload.get('product_core_status')}",
        f"whole_tree_status={payload.get('whole_tree_status')}",
        f"git_head={payload.get('git_head')}",
        f"repository_python_file_count={repo.get('repository_python_file_count')}",
        f"repository_test_file_count={repo.get('repository_test_file_count')}",
        f"product_python_file_count={repo.get('product_python_file_count')}",
        f"product_test_file_count={repo.get('product_test_file_count')}",
        f"legacy_or_imported_test_file_count={repo.get('legacy_or_imported_test_file_count')}",
        f"workflow_file_count={repo.get('workflow_file_count')}",
        f"core_module_directory_count={modules.get('core_module_directory_count')}",
        f"modules_with_source_count={modules.get('modules_with_source_count')}",
        f"modules_with_tests_count={modules.get('modules_with_tests_count')}",
        f"core_source_file_count={modules.get('core_source_file_count')}",
        f"core_test_file_count={modules.get('core_test_file_count')}",
        f"product_compile_returncode={(payload.get('product_compile') or {}).get('returncode')}",
        f"whole_tree_compile_returncode={(payload.get('whole_tree_compile') or {}).get('returncode')}",
        f"collect_returncode={(payload.get('collect') or {}).get('returncode')}",
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
    lines.extend(["", "LEGACY_OR_IMPORTED_TEST_SURFACE"])
    lines.extend(f"- {name}" for name in repo.get("legacy_or_imported_test_files") or [])
    lines.extend([
        "",
        "WHOLE_TREE_COMPILE_DEBT",
        str((payload.get("whole_tree_compile") or {}).get("stdout_tail") or "NONE"),
        "",
        "CLAIM_LOCKS",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
        "NOTE",
        "Product core tests are explicit current tests under hpfa/ or root tests/, run with pytest --import-mode=importlib to avoid duplicate-basename collection collisions.",
        "hpfa-main/* is classified by repository governance as legacy_or_imported_structure and is reported separately rather than treated as current product authority.",
        "vendor/donor compile debt remains visible in whole_tree_status.",
        "This audit does not substitute for physical ACTIVE_MATCH evidence.",
        "A module directory is not automatically an independent runtime engine or an orphan capability.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile/test current HPFA product core and separately audit legacy/vendor tree debt.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    out = Path(args.out_dir).expanduser().resolve(strict=False)
    out.mkdir(parents=True, exist_ok=True)
    junit = out / "pytest-junit.xml"

    module_inventory = _module_inventory(root)
    repo_inventory = _repo_inventory(root)
    product_python_files = [str(root / value) for value in repo_inventory["product_python_files"]]
    product_test_files = list(repo_inventory["product_test_files"])

    product_compile = _run([sys.executable, "-m", "py_compile", *product_python_files], cwd=root, timeout=args.timeout_seconds)
    whole_tree_compile = _run([sys.executable, "-m", "compileall", "-q", str(root)], cwd=root, timeout=args.timeout_seconds)

    pytest_base = [sys.executable, "-m", "pytest", "--import-mode=importlib"]
    if product_test_files:
        collect_result = _run([*pytest_base, "--collect-only", "-q", *product_test_files], cwd=root, timeout=args.timeout_seconds)
        pytest_result = _run(
            [*pytest_base, "-q", "--durations=50", f"--junitxml={junit}", *product_test_files],
            cwd=root,
            timeout=args.timeout_seconds,
        )
    else:
        collect_result = {"returncode": 5, "elapsed_seconds": 0.0, "stdout_tail": "no_current_product_tests", "stderr_tail": "", "timed_out": False, "command": []}
        pytest_result = dict(collect_result)

    pytest_summary = _parse_junit(junit)
    product_core_status = "PASS" if all(result["returncode"] == 0 for result in (product_compile, collect_result, pytest_result)) else "REVIEW_REQUIRED"
    whole_tree_status = "PASS" if whole_tree_compile["returncode"] == 0 else "REVIEW_REQUIRED"
    status = "PASS" if product_core_status == "PASS" and whole_tree_status == "PASS" else "REVIEW_REQUIRED"

    payload = {
        "module_id": MODULE_ID,
        "status": status,
        "product_core_status": product_core_status,
        "whole_tree_status": whole_tree_status,
        "git_head": _git_head(root),
        "python_version": sys.version.replace("\n", " "),
        "module_inventory": module_inventory,
        "repo_inventory": repo_inventory,
        "product_compile": product_compile,
        "whole_tree_compile": whole_tree_compile,
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
        "product_core_status": product_core_status,
        "whole_tree_status": whole_tree_status,
        "git_head": payload["git_head"],
        "core_module_directory_count": module_inventory["core_module_directory_count"],
        "modules_with_tests_count": module_inventory["modules_with_tests_count"],
        "product_test_file_count": repo_inventory["product_test_file_count"],
        "pytest_tests": pytest_summary.get("tests"),
        "pytest_failures": pytest_summary.get("failures"),
        "pytest_errors": pytest_summary.get("errors"),
        "pytest_elapsed_seconds": pytest_result["elapsed_seconds"],
        "report": str(txt_path),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if product_core_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
