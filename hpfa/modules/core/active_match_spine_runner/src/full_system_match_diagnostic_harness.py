from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _git_value(product_root: Path, *args: str) -> str:
    result = _run(["git", *args], cwd=product_root)
    if result["return_code"] != 0:
        return "UNKNOWN"
    return str(result["stdout"]).strip() or "UNKNOWN"


def _scan_core_modules(product_root: Path) -> list[dict[str, Any]]:
    core_root = product_root / "hpfa" / "modules" / "core"
    if not core_root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for module_dir in sorted((p for p in core_root.iterdir() if p.is_dir() and not p.name.startswith(".")), key=lambda p: p.name):
        tests = sorted((module_dir / "tests").glob("test_*.py")) if (module_dir / "tests").is_dir() else []
        sources = sorted((module_dir / "src").glob("*.py")) if (module_dir / "src").is_dir() else []
        rows.append({
            "module": module_dir.name,
            "source_file_count": len(sources),
            "test_file_count": len(tests),
            "test_files": [str(path.relative_to(product_root)) for path in tests],
        })
    return rows


def _module_from_test_file(test_file: str) -> str | None:
    match = re.search(r"(?:^|/)hpfa/modules/core/([^/]+)/tests/", str(test_file).replace("\\", "/"))
    return match.group(1) if match else None


def _module_states_from_fail_local(modules: list[dict[str, Any]], audit: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in audit.get("per_file_results") or []:
        if not isinstance(row, dict):
            continue
        module = _module_from_test_file(str(row.get("test_file") or ""))
        if module:
            grouped.setdefault(module, []).append(row)

    compile_pass = str(audit.get("product_compile_status") or "").upper() == "PASS"
    result: list[dict[str, Any]] = []
    for base in modules:
        module = str(base.get("module") or "")
        mapped = grouped.get(module, [])
        tests = sum(int(row.get("tests") or 0) for row in mapped)
        failures = sum(int(row.get("failures") or 0) for row in mapped)
        errors = sum(int(row.get("errors") or 0) for row in mapped)
        skipped = sum(int(row.get("skipped") or 0) for row in mapped)
        failed_files = sum(1 for row in mapped if int(row.get("returncode") or 0) != 0)
        passed = max(0, tests - failures - errors - skipped)
        expected_files = int(base.get("test_file_count") or 0)
        if not compile_pass:
            state = "UNKNOWN"
        elif expected_files == 0:
            state = "NO_TESTS"
        elif failures or errors or failed_files:
            state = "FAIL"
        elif len(mapped) != expected_files:
            state = "UNKNOWN"
        elif passed > 0:
            state = "PASS"
        else:
            state = "UNKNOWN"
        result.append({
            **base,
            "audited_test_file_count": len(mapped),
            "test_case_count": tests,
            "passed": passed,
            "failed": failures,
            "errors": errors,
            "skipped": skipped,
            "engineering_test_state": state,
        })
    return result


def run_engineering_checks(product_root: Path, out_dir: Path) -> dict[str, Any]:
    product_root = product_root.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    modules = _scan_core_modules(product_root)
    python_files = sum(1 for _ in (product_root / "hpfa").rglob("*.py")) if (product_root / "hpfa").is_dir() else 0
    core_test_files = sum(int(row.get("test_file_count") or 0) for row in modules)
    audit_dir = out_dir / "engineering_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"[HPFA_DIAG] engineering_audit START core_modules={len(modules)} core_test_files={core_test_files} python_files={python_files}",
        flush=True,
    )
    audit_run = _run([
        sys.executable,
        str(product_root / "repo_fail_local_product_test_audit_v1.py"),
        "--out-dir", str(audit_dir),
        "--timeout-seconds", "1800",
        "--per-file-timeout-seconds", "300",
    ], cwd=product_root)
    audit = _load_json(audit_dir / "HPFA_FAIL_LOCAL_PRODUCT_TEST_AUDIT.json")
    baseline = _load_json(audit_dir / "HPFA_FULL_REPO_HEALTH_AUDIT.json")
    module_states = _module_states_from_fail_local(modules, audit)
    state_counts = dict(Counter(str(row.get("engineering_test_state") or "UNKNOWN") for row in module_states))
    status = "PASS" if audit_run["return_code"] == 0 and str(audit.get("status") or "").upper() == "PASS" else "FAIL"

    print(
        "[HPFA_DIAG] engineering_audit END "
        f"rc={audit_run['return_code']} status={audit.get('status')} elapsed_seconds={audit_run['elapsed_seconds']} "
        f"isolated_test_files={audit.get('isolated_test_file_count')} isolated_tests={audit.get('isolated_tests')} "
        f"failures={audit.get('isolated_failures')} errors={audit.get('isolated_errors')} skipped={audit.get('isolated_skipped')} "
        f"monolithic={audit.get('monolithic_product_core_status')} contamination={audit.get('monolithic_state_contamination_classification')}",
        flush=True,
    )
    product_compile = baseline.get("product_compile") if isinstance(baseline.get("product_compile"), dict) else {}
    payload = {
        "module_id": "full_system_engineering_test_evidence_v1",
        "status": status,
        "authority": "REUSE_REPO_FAIL_LOCAL_PRODUCT_TEST_AUDIT_V1",
        "audit_return_code": audit_run["return_code"],
        "audit_elapsed_seconds": audit_run["elapsed_seconds"],
        "product_compile": {
            "status": audit.get("product_compile_status"),
            "return_code": audit.get("product_compile_returncode"),
            "elapsed_seconds": product_compile.get("elapsed_seconds"),
            "python_file_count": python_files,
        },
        "isolated_tests": {
            "status": audit.get("isolated_test_status"),
            "test_file_count": audit.get("isolated_test_file_count"),
            "tests": audit.get("isolated_tests"),
            "failures": audit.get("isolated_failures"),
            "errors": audit.get("isolated_errors"),
            "skipped": audit.get("isolated_skipped"),
            "elapsed_seconds": audit.get("isolated_elapsed_seconds"),
        },
        "monolithic_diagnostic": {
            "status": audit.get("monolithic_product_core_status"),
            "failures": audit.get("monolithic_pytest_failures"),
            "errors": audit.get("monolithic_pytest_errors"),
            "state_contamination_classification": audit.get("monolithic_state_contamination_classification"),
            "is_product_gate": audit.get("monolithic_run_is_product_gate"),
        },
        "whole_tree_status": audit.get("whole_tree_status"),
        "core_module_count": len(modules),
        "module_states": module_states,
        "engineering_test_state_counts": state_counts,
        "source_audit_json": str(audit_dir / "HPFA_FAIL_LOCAL_PRODUCT_TEST_AUDIT.json"),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    (out_dir / ENGINEERING_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _owner_candidates(component: dict[str, Any]) -> list[str]:
    component_id = str(component.get("component") or "")
    values = [C4_OWNER_MAP.get(component_id), component_id]
    artifact = str(component.get("output_artifact") or "")
    if artifact:
        stem = Path(artifact.split(":", 1)[0]).stem
        values.extend([stem, re.sub(r"_v\d+$", "", stem), re.sub(r"_projection_v\d+$", "", stem)])
    result: list[str] = []
    for value in values:
        if not value:
            continue
        for candidate in (value, value.replace("_projection", ""), value.replace("_candidate", "")):
            if candidate and candidate not in result:
                result.append(candidate)
    return result


def apply_engineering_states(diagnostic: dict[str, Any], engineering: dict[str, Any]) -> dict[str, Any]:
    states = {
        str(row.get("module")): str(row.get("engineering_test_state") or "UNKNOWN")
        for row in engineering.get("module_states") or [] if isinstance(row, dict)
    }
    names = sorted(states, key=len, reverse=True)
    for component in diagnostic.get("component_coverage") or []:
        if not isinstance(component, dict):
            continue
        owner = None
        for candidate in _owner_candidates(component):
            if candidate in states:
                owner = candidate
                break
            matches = [name for name in names if name.startswith(candidate) or candidate.startswith(name)]
            if len(matches) == 1:
                owner = matches[0]
                break
        component["engineering_owner_module"] = owner
        component["engineering_test_state"] = states.get(owner, "UNKNOWN") if owner else "UNKNOWN"
    diagnostic["engineering_test_evidence"] = engineering
    diagnostic["repository_module_engineering_matrix"] = engineering.get("module_states") or []
    diagnostic["engineering_test_state_counts"] = dict(Counter(
        str(row.get("engineering_test_state") or "UNKNOWN")
        for row in diagnostic.get("component_coverage") or [] if isinstance(row, dict)
    ))
    return diagnostic


def _human_answers(diagnostic: dict[str, Any]) -> list[tuple[str, str]]:
    football = diagnostic.get("match_football_intelligence") or {}
    occurrence = football.get("action_occurrence_structure") or {}
    seq = football.get("partial_order_sequences") or {}
    comp = football.get("comparison") or {}
    safe = football.get("safe_findings") or {}
    gaps = diagnostic.get("gap_report") or []
    top_gap = gaps[0] if gaps else {}
    emitted = safe.get("professional_finding_emitted_count") or 0
    return [
        ("1. Bu maçta HPFA ne gördü?", f"{occurrence.get('occurrence_candidates')} occurrence adayı, {seq.get('sequence_candidates')} partial-order sequence, {seq.get('branch_maps')} branch map, {comp.get('process_variant_families')} process-variant ailesi ve {comp.get('grammar_stable_mixed_outcome_families')} mixed-outcome ailesi."),
        ("2. Hangi oyun süreçlerini birbirine bağlayabildi?", "Occurrence → partial-order sequence → episode/process participation → visible consequence → matched success/failure variant → feature difference → finding admission zinciri kuruldu; yorum kapsamı source-bound match-process mekanizmasıdır."),
        ("3. Hangi başarılı ve başarısız varyantları ayırabildi?", f"Comparison-eligible outcome records={comp.get('eligible_outcome_records')}; aynı grammar içindeki success/failure varyantları review-locator ve branch-divergence düzeyinde ayrıldı."),
        ("4. Hangi tekrarlar gerçekten anlamlıydı?", "Match-local recurrence ve mixed-outcome aileleri inceleme locator'ı üretti; support authority dependency-resolved episode spread üzerinden taşınıyor."),
        ("5. Hangi karşı örnekler güçlü iddiaları engelledi?", f"Comparable counterevidence candidates={comp.get('comparable_counterevidence_candidates')}; safe-finding states={json.dumps(safe.get('status_counts') or {}, ensure_ascii=False, sort_keys=True)}; professional EMIT={emitted}."),
        ("6. Mevcut observation authority hangi futbol alanlarını kapsıyor?", "Current package temporal, spatial-event, actor/team, process, consequence ve aggregate context authority taşıyor; physical-state, intention ve causal construct aileleri kendi dedicated observation/evidence contractlarıyla çalışır."),
        ("7. Bugün analiste gerçekten hangi yeni bilgiyi kazandırdı?", f"Raw provider satırlarının tek başına vermediği {seq.get('branch_maps')} branch map, {seq.get('first_supported_divergence_candidates')} first-supported divergence adayı ve matched success/failure review locator'ları üretildi; bunlar match-local mekanizma incelemesini doğrudan zenginleştiriyor."),
        ("8. Bir sonraki en değerli geliştirme nedir?", str(top_gap.get("smallest_path") or "Evidence sufficiency/independence accounting ve current-run artifact ledger closure.")),
    ]


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
    lines.append("EN GUCLU SAVUNULABILIR REVIEW ADAYLARI")
    mechanisms = diagnostic.get("top_defensible_process_mechanism_candidates") or []
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
                f"failure={process.get('failure_visible_numerator')}/{process.get('failure_eligible_denominator')} tactical_truth=false causal_truth=false"
            )
    lines.extend(["", "END OF ANALYST DIAGNOSTIC"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA full-system match diagnostic with canonical ACTIVE_MATCH full spine and fail-local test authority.")
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
    full_spine = _run([
        sys.executable, str(runner), str(Path(args.active_match_dir).expanduser().resolve(strict=False)),
        "--out-dir", str(out_dir), "--full-spine", "--execution-root", str(product_root),
    ], cwd=product_root)
    print(f"[HPFA_DIAG] full_spine rc={full_spine['return_code']} elapsed_seconds={full_spine['elapsed_seconds']}", flush=True)

    src = product_root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import full_system_match_diagnostic as diagnostic_module

    diag_started = time.perf_counter()
    diagnostic = diagnostic_module.build_diagnostic(
        out_dir,
        repository="Hikmetpinarbas/hpfa",
        branch=_git_value(product_root, "branch", "--show-current"),
        pr=args.pr,
        head=_git_value(product_root, "rev-parse", "HEAD"),
    )
    apply_engineering_states(diagnostic, engineering)
    diag_seconds = round(time.perf_counter() - diag_started, 3)
    total_seconds = round(time.perf_counter() - started, 3)
    performance = {
        "module_id": "full_system_match_diagnostic_performance_v1",
        "engineering_audit_seconds": engineering.get("audit_elapsed_seconds"),
        "product_compile_seconds": (engineering.get("product_compile") or {}).get("elapsed_seconds"),
        "isolated_tests_seconds": (engineering.get("isolated_tests") or {}).get("elapsed_seconds"),
        "full_spine_seconds": full_spine["elapsed_seconds"],
        "diagnostic_seconds": diag_seconds,
        "total_seconds": total_seconds,
        "core_module_count": engineering.get("core_module_count"),
        "isolated_test_file_count": (engineering.get("isolated_tests") or {}).get("test_file_count"),
        "isolated_tests": (engineering.get("isolated_tests") or {}).get("tests"),
        "tests_failed": (engineering.get("isolated_tests") or {}).get("failures"),
        "test_errors": (engineering.get("isolated_tests") or {}).get("errors"),
        "tests_skipped": (engineering.get("isolated_tests") or {}).get("skipped"),
        "runtime_component_count": len(diagnostic.get("component_coverage") or []),
        "runtime_execution_state_counts": diagnostic.get("runtime_execution_state_counts") or {},
        "engineering_test_state_counts": diagnostic.get("engineering_test_state_counts") or {},
        "production_release": False,
    }
    diagnostic["performance"] = performance
    diagnostic["human_analyst_answer_pack"] = [{"question": q, "answer": a} for q, a in _human_answers(diagnostic)]
    diagnostic_module.write_outputs(out_dir, diagnostic)
    write_human_report(out_dir, diagnostic)
    (out_dir / PERFORMANCE_JSON).write_text(json.dumps(performance, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"[HPFA_DIAG] diagnostic status={diagnostic.get('status')} elapsed_seconds={diag_seconds} total_seconds={total_seconds} "
        f"components={performance['runtime_component_count']} execution_states={json.dumps(performance['runtime_execution_state_counts'], sort_keys=True)}",
        flush=True,
    )
    if engineering.get("status") != "PASS":
        return 2
    if full_spine["return_code"] != 0:
        return int(full_spine["return_code"])
    return 2 if str(diagnostic.get("status") or "").upper() == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
