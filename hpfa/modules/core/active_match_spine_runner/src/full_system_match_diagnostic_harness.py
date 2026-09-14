from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "active_match_full_system_match_diagnostic_harness_v1"
ENGINEERING_JSON = "full_system_engineering_test_evidence_v1.json"
PERFORMANCE_JSON = "full_system_match_diagnostic_performance_v1.json"
HUMAN_REPORT_TR = "HPFA_FULL_SYSTEM_MATCH_DIAGNOSTIC_TR.txt"

C4_OWNER_MAP = {
    "c4_fusion": "multi_signal_evidence_fusion_lite",
    "c4_argument": "composite_argument_builder_lite",
    "c4_route": "defeasible_argument_router_lite",
    "c4_graph": "evidence_graph_engine_lite",
    "c4_lens": "evidence_lens_matrix_lite",
    "c4_safe_sentence": "safe_argument_router_tr_lite",
    "c4_report_block": "analyst_report_block_composer_lite",
    "c4_output_contract": "report_output_contract_lite",
    "c4_assembly": "final_report_assembly_gate_lite",
}


def _run(command: list[str], *, cwd: Path) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "return_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def _git_value(product_root: Path, *args: str) -> str:
    result = _run(["git", *args], cwd=product_root)
    if result["return_code"] != 0:
        return "UNKNOWN"
    value = str(result["stdout"]).strip()
    return value or "UNKNOWN"


def _parse_pytest_summary(text: str) -> dict[str, int]:
    result = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    patterns = {
        "passed": r"(\d+) passed",
        "failed": r"(\d+) failed",
        "skipped": r"(\d+) skipped",
        "errors": r"(\d+) errors?",
    }
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            result[key] = int(matches[-1])
    return result


def _scan_core_modules(product_root: Path) -> list[dict[str, Any]]:
    core_root = product_root / "hpfa" / "modules" / "core"
    rows: list[dict[str, Any]] = []
    if not core_root.is_dir():
        return rows
    for module_dir in sorted((p for p in core_root.iterdir() if p.is_dir() and not p.name.startswith(".")), key=lambda p: p.name):
        test_files = sorted((module_dir / "tests").glob("test_*.py")) if (module_dir / "tests").is_dir() else []
        source_files = sorted((module_dir / "src").glob("*.py")) if (module_dir / "src").is_dir() else []
        rows.append({
            "module": module_dir.name,
            "source_file_count": len(source_files),
            "test_file_count": len(test_files),
            "test_files": [str(p.relative_to(product_root)) for p in test_files],
        })
    return rows


def _module_from_testcase(testcase: ET.Element) -> str | None:
    file_value = str(testcase.attrib.get("file") or "").replace("\\", "/")
    match = re.search(r"(?:^|/)hpfa/modules/core/([^/]+)/tests/", file_value)
    if match:
        return match.group(1)
    classname = str(testcase.attrib.get("classname") or "")
    match = re.search(r"(?:^|\.)hpfa\.modules\.core\.([^.]+)\.tests(?:\.|$)", classname)
    return match.group(1) if match else None


def _junit_module_execution(junit_path: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = {}
    try:
        root = ET.parse(junit_path).getroot()
    except (OSError, ET.ParseError):
        return {}
    for testcase in root.iter("testcase"):
        module = _module_from_testcase(testcase)
        if not module:
            continue
        counter = counts.setdefault(module, Counter())
        counter["test_case_count"] += 1
        if testcase.find("failure") is not None:
            counter["failed"] += 1
        elif testcase.find("error") is not None:
            counter["errors"] += 1
        elif testcase.find("skipped") is not None:
            counter["skipped"] += 1
        else:
            counter["passed"] += 1
    return {module: dict(counter) for module, counter in counts.items()}


def run_engineering_checks(product_root: Path, out_dir: Path) -> dict[str, Any]:
    product_root = product_root.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    modules = _scan_core_modules(product_root)
    python_file_count = sum(1 for _ in (product_root / "hpfa").rglob("*.py")) if (product_root / "hpfa").is_dir() else 0
    test_file_count = sum(row["test_file_count"] for row in modules)

    compile_result = _run([sys.executable, "-m", "compileall", "-q", str(product_root / "hpfa")], cwd=product_root)
    print(
        f"[HPFA_DIAG] compile rc={compile_result['return_code']} elapsed_seconds={compile_result['elapsed_seconds']} python_files={python_file_count}",
        flush=True,
    )

    junit_path = out_dir / "full_system_core_tests_junit_v1.xml"
    test_result = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(product_root / "hpfa" / "modules" / "core"),
            f"--junitxml={junit_path}",
        ],
        cwd=product_root,
    )
    summary = _parse_pytest_summary(str(test_result["stdout"]) + "\n" + str(test_result["stderr"]))
    module_execution = _junit_module_execution(junit_path)
    print(
        "[HPFA_DIAG] core_tests "
        f"rc={test_result['return_code']} elapsed_seconds={test_result['elapsed_seconds']} "
        f"passed={summary['passed']} failed={summary['failed']} errors={summary['errors']} skipped={summary['skipped']} "
        f"test_files={test_file_count} modules_with_executed_tests={len(module_execution)}",
        flush=True,
    )

    compile_pass = compile_result["return_code"] == 0
    tests_pass = test_result["return_code"] == 0
    module_states: list[dict[str, Any]] = []
    for row in modules:
        execution = module_execution.get(str(row["module"]), {})
        if not compile_pass:
            state = "UNKNOWN"
        elif row["test_file_count"] == 0:
            state = "NO_TESTS"
        elif int(execution.get("failed") or 0) > 0 or int(execution.get("errors") or 0) > 0:
            state = "FAIL"
        elif int(execution.get("passed") or 0) > 0:
            state = "PASS"
        else:
            state = "UNKNOWN"
        module_states.append({**row, **execution, "engineering_test_state": state})

    status = "PASS" if compile_pass and tests_pass else "FAIL"
    payload = {
        "module_id": "full_system_engineering_test_evidence_v1",
        "status": status,
        "compile": {
            "return_code": compile_result["return_code"],
            "elapsed_seconds": compile_result["elapsed_seconds"],
            "python_file_count": python_file_count,
        },
        "core_tests": {
            "return_code": test_result["return_code"],
            "elapsed_seconds": test_result["elapsed_seconds"],
            "test_file_count": test_file_count,
            "junit_artifact": str(junit_path) if junit_path.is_file() else None,
            "modules_with_executed_tests": len(module_execution),
            **summary,
        },
        "core_module_count": len(modules),
        "module_states": module_states,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    (out_dir / ENGINEERING_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _owner_candidates(component: dict[str, Any]) -> list[str]:
    component_id = str(component.get("component") or "")
    candidates = [component_id]
    if component_id in C4_OWNER_MAP:
        candidates.insert(0, C4_OWNER_MAP[component_id])
    artifact = str(component.get("output_artifact") or "")
    if artifact:
        stem = Path(artifact.split(":", 1)[0]).stem
        candidates.extend([
            stem,
            re.sub(r"_v\d+$", "", stem),
            re.sub(r"_projection_v\d+$", "", stem),
            re.sub(r"_candidates?_lite_v\d+$", "", stem),
        ])
    expanded: list[str] = []
    for value in candidates:
        if not value:
            continue
        expanded.append(value)
        expanded.append(value.replace("_projection", ""))
        expanded.append(value.replace("_candidate", ""))
    return list(dict.fromkeys(expanded))


def apply_engineering_states(diagnostic: dict[str, Any], engineering: dict[str, Any]) -> dict[str, Any]:
    module_states = {
        str(row.get("module")): str(row.get("engineering_test_state") or "UNKNOWN")
        for row in (engineering.get("module_states") or [])
        if isinstance(row, dict)
    }
    module_names = sorted(module_states, key=len, reverse=True)

    for component in diagnostic.get("component_coverage") or []:
        if not isinstance(component, dict):
            continue
        owner = None
        for candidate in _owner_candidates(component):
            if candidate in module_states:
                owner = candidate
                break
            matches = [name for name in module_names if candidate and (name.startswith(candidate) or candidate.startswith(name))]
            if len(matches) == 1:
                owner = matches[0]
                break
        component["engineering_owner_module"] = owner
        component["engineering_test_state"] = module_states.get(owner, "UNKNOWN") if owner else "UNKNOWN"

    diagnostic["engineering_test_evidence"] = engineering
    diagnostic["repository_module_engineering_matrix"] = engineering.get("module_states") or []
    diagnostic["engineering_test_state_counts"] = dict(
        Counter(str(c.get("engineering_test_state") or "UNKNOWN") for c in diagnostic.get("component_coverage") or [] if isinstance(c, dict))
    )
    return diagnostic


def _human_answers(diagnostic: dict[str, Any]) -> list[tuple[str, str]]:
    mi = diagnostic.get("match_football_intelligence") or {}
    seq = mi.get("partial_order_sequences") or {}
    comp = mi.get("comparison") or {}
    safe = mi.get("safe_findings") or {}
    mechanisms = diagnostic.get("top_defensible_process_mechanism_candidates") or []
    gaps = diagnostic.get("gap_report") or []
    top_gap = gaps[0] if gaps else {}
    status_counts = safe.get("status_counts") or {}
    emitted = safe.get("professional_finding_emitted_count") or 0
    answers = [
        (
            "1. Bu maçta HPFA ne gördü?",
            f"{(mi.get('action_occurrence_structure') or {}).get('occurrence_candidates')} action-occurrence adayı; "
            f"{seq.get('sequence_candidates')} partial-order sequence adayı; {seq.get('branch_maps')} branch map; "
            f"{comp.get('process_variant_families')} observable process-variant ailesi ve {comp.get('grammar_stable_mixed_outcome_families')} grammar-stable mixed-outcome ailesi görünür oldu.",
        ),
        (
            "2. Hangi oyun süreçlerini birbirine bağlayabildi?",
            "Occurrence → partial-order sequence → episode/process participation → visible consequence → matched success/failure variant → feature difference → challenge/finding admission zinciri kurulabildi; bu bağların hiçbiri coach intention veya causal truth olarak yükseltilmedi.",
        ),
        (
            "3. Hangi başarılı ve başarısız varyantları ayırabildi?",
            f"Comparison-eligible outcome records={comp.get('eligible_outcome_records')}; process-variant families={comp.get('process_variant_families')}; en büyük review aileleri success/failure varyantlarını aynı grammar içinde tutuyor. Güçlü publishable mekanizma yerine review-locator üretildi.",
        ),
        (
            "4. Hangi tekrarlar gerçekten anlamlıydı?",
            "Match-local recurrence ve mixed-outcome aileleri analist incelemesi için anlamlı locator üretti; ancak dependency/statistical independence kanıtlanmadığı için tekrar sayısı profesyonel finding gücüne çevrilmedi.",
        ),
        (
            "5. Hangi karşı örnekler güçlü iddiaları engelledi?",
            f"Comparable counterevidence candidates={comp.get('comparable_counterevidence_candidates')}; safe-finding state={json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}; professional EMIT={emitted}. Failure/deviant varyantların aynı grammar ailelerinde kalması güçlü claim'i aşağı çekti.",
        ),
        (
            "6. Sistem hangi noktalarda kör kaldı?",
            "Tracking/video yok; true shape, compactness, off-ball geometry, body orientation, pressure geometry, coach intention ve causality doğrudan kanıtlanamaz. External context ve independence admission da mevcut run'da sınırlı/eksik olabilir.",
        ),
        (
            "7. Bugün analiste gerçekten hangi yeni bilgiyi kazandırdı?",
            f"Raw provider satırlarının tek başına söylemediği {seq.get('branch_maps')} branch map, {seq.get('first_supported_divergence_candidates')} first-supported divergence adayı, matched success/failure varyant karşılaştırmaları ve claim-bounded review locator'ları üretti. Bunlar video/maç incelemesini hedefli hale getirir; publishable tactical truth değildir.",
        ),
        (
            "8. Bir sonraki en değerli geliştirme nedir?",
            str(top_gap.get("smallest_path") or "Evidence sufficiency/independence accounting ve current-run artifact ledger closure."),
        ),
    ]
    return answers


def write_human_report(root: Path, diagnostic: dict[str, Any]) -> Path:
    path = root / HUMAN_REPORT_TR
    lines = [
        "HPFA FULL SYSTEM MATCH DIAGNOSTIC — ANALIST RAPORU",
        "=================================================",
        f"runtime_status={diagnostic.get('status')}",
        "claim_ceiling=ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY",
        "diagnostic_creates_new_evidence=false",
        "",
    ]
    for question, answer in _human_answers(diagnostic):
        lines.extend([question, answer, ""])
    mechanisms = diagnostic.get("top_defensible_process_mechanism_candidates") or []
    lines.append("EN GUCLU SAVUNULABILIR REVIEW ADAYLARI")
    if not mechanisms:
        lines.append("- Yeterli current-run candidate yok; kota doldurulmadı.")
    for index, row in enumerate(mechanisms[:5], 1):
        lines.append(
            f"- C{index}: resolved={row.get('resolved_variant_count')} success={row.get('success_variant_count')} failure={row.get('failure_variant_count')} "
            f"claim_ceiling={row.get('claim_ceiling')} independence={str(row.get('dependency_independence_proven') is True).lower()}"
        )
        process = row.get("best_provider_reviewed_process_context_difference")
        if isinstance(process, dict):
            lines.append(
                f"  provider_reviewed_context={process.get('feature_token')} "
                f"success={process.get('success_visible_numerator')}/{process.get('success_eligible_denominator')} "
                f"failure={process.get('failure_visible_numerator')}/{process.get('failure_eligible_denominator')} "
                "tactical_truth=false causal_truth=false"
            )
    lines.extend(["", "END OF ANALYST DIAGNOSTIC"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA full-system match diagnostic using the canonical ACTIVE_MATCH full-spine runner.")
    parser.add_argument("active_match_dir")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--product-root", default=str(Path(__file__).resolve().parents[5]))
    parser.add_argument("--pr", default="359")
    args = parser.parse_args()

    started = time.perf_counter()
    product_root = Path(args.product_root).expanduser().resolve(strict=False)
    out_dir = Path(args.out_dir).expanduser().resolve(strict=False)
    out_dir.mkdir(parents=True, exist_ok=True)

    engineering = run_engineering_checks(product_root, out_dir)

    runner = product_root / "active_match_spine_runner.py"
    full_spine_result = _run(
        [
            sys.executable,
            str(runner),
            str(Path(args.active_match_dir).expanduser().resolve(strict=False)),
            "--out-dir",
            str(out_dir),
            "--full-spine",
            "--execution-root",
            str(product_root),
        ],
        cwd=product_root,
    )
    print(
        f"[HPFA_DIAG] full_spine rc={full_spine_result['return_code']} elapsed_seconds={full_spine_result['elapsed_seconds']}",
        flush=True,
    )

    src = product_root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import full_system_match_diagnostic as diagnostic_module

    diagnostic_started = time.perf_counter()
    head = _git_value(product_root, "rev-parse", "HEAD")
    branch = _git_value(product_root, "branch", "--show-current")
    diagnostic = diagnostic_module.build_diagnostic(
        out_dir,
        repository="Hikmetpinarbas/hpfa",
        branch=branch,
        pr=args.pr,
        head=head,
    )
    apply_engineering_states(diagnostic, engineering)
    diagnostic_seconds = round(time.perf_counter() - diagnostic_started, 3)
    total_seconds = round(time.perf_counter() - started, 3)
    performance = {
        "module_id": "full_system_match_diagnostic_performance_v1",
        "compile_seconds": engineering.get("compile", {}).get("elapsed_seconds"),
        "core_tests_seconds": engineering.get("core_tests", {}).get("elapsed_seconds"),
        "full_spine_seconds": full_spine_result["elapsed_seconds"],
        "diagnostic_seconds": diagnostic_seconds,
        "total_seconds": total_seconds,
        "core_module_count": engineering.get("core_module_count"),
        "core_test_file_count": engineering.get("core_tests", {}).get("test_file_count"),
        "tests_passed": engineering.get("core_tests", {}).get("passed"),
        "tests_failed": engineering.get("core_tests", {}).get("failed"),
        "tests_skipped": engineering.get("core_tests", {}).get("skipped"),
        "runtime_component_count": len(diagnostic.get("component_coverage") or []),
        "runtime_execution_state_counts": diagnostic.get("runtime_execution_state_counts") or {},
        "engineering_test_state_counts": diagnostic.get("engineering_test_state_counts") or {},
        "production_release": False,
    }
    diagnostic["performance"] = performance
    diagnostic["human_analyst_answer_pack"] = [
        {"question": q, "answer": a} for q, a in _human_answers(diagnostic)
    ]
    diagnostic_module.write_outputs(out_dir, diagnostic)
    write_human_report(out_dir, diagnostic)
    (out_dir / PERFORMANCE_JSON).write_text(json.dumps(performance, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        "[HPFA_DIAG] diagnostic "
        f"status={diagnostic.get('status')} elapsed_seconds={diagnostic_seconds} total_seconds={total_seconds} "
        f"components={performance['runtime_component_count']} execution_states={json.dumps(performance['runtime_execution_state_counts'], sort_keys=True)}",
        flush=True,
    )

    if engineering.get("status") != "PASS":
        return 2
    if full_spine_result["return_code"] != 0:
        return full_spine_result["return_code"]
    return 2 if str(diagnostic.get("status") or "").upper() == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
