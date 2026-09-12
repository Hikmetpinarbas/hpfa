from pathlib import Path

import hpfa_benchmark_acceptance_v1 as benchmark


def test_runtime_observed_mapping_does_not_promote_unseen_modules() -> None:
    modules = ["alpha_lite", "beta_lite", "gamma_lite"]
    observed = benchmark._runtime_observed_module_dirs(
        modules,
        ["alpha_lite_v1", "beta_lite_extra_v1"],
    )
    assert observed == ["alpha_lite", "beta_lite"]
    assert "gamma_lite" not in observed


def test_report_delta_fails_open_when_previous_report_missing(tmp_path: Path) -> None:
    current = tmp_path / "current.txt"
    current.write_text("A\nB\n", encoding="utf-8")
    result = benchmark._report_delta(current, None)
    assert result["comparison_state"] == "NOT_EVALUATED_PREVIOUS_REPORT_MISSING"
    assert result["report_changed"] is None


def test_report_delta_reports_added_and_removed_lines(tmp_path: Path) -> None:
    current = tmp_path / "current.txt"
    previous = tmp_path / "previous.txt"
    current.write_text("A\nC\n", encoding="utf-8")
    previous.write_text("A\nB\n", encoding="utf-8")
    result = benchmark._report_delta(current, previous)
    assert result["comparison_state"] == "EVALUATED"
    assert result["report_changed"] is True
    assert result["added_line_count"] == 1
    assert result["removed_line_count"] == 1


def test_health_output_never_claims_unobserved_equals_orphan(tmp_path: Path) -> None:
    payload = {
        "status": "PASS",
        "exact_head_elapsed_seconds": 1.0,
        "core_module_directory_count": 2,
        "modules_with_source_count": 2,
        "modules_with_tests_count": 2,
        "test_file_count": 2,
        "fresh_json_artifact_count": 1,
        "runtime_observed_module_id_count": 1,
        "runtime_observed_core_module_candidate_count": 1,
        "runtime_unobserved_core_module_candidate_count": 1,
        "module_runtime_timing_coverage": "END_TO_END_ONLY_PER_MODULE_TIMERS_NOT_YET_INSTRUMENTED",
        "analyst_report_present": False,
        "analyst_report_delta": {"comparison_state": "NOT_EVALUATED_PREVIOUS_REPORT_MISSING"},
        "runtime_observed_core_module_candidates": ["alpha_lite"],
        "runtime_unobserved_core_module_candidates": ["beta_lite"],
    }
    benchmark._write_health_outputs(tmp_path, payload)
    text = (tmp_path / benchmark.HEALTH_TXT).read_text(encoding="utf-8")
    assert "runtime_unobserved does not prove orphan status" in text
    assert "per-module timing is not fabricated" in text
