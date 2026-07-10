from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "discipline_lens_registry.py"
SPEC = importlib.util.spec_from_file_location("discipline_lens_registry", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_statistics_request() -> dict:
    return {
        "request_id": "lens_001",
        "discipline": "statistics",
        "diagnostic_primitive": "distribution_summary",
        "inputs": {"observations": [1, 2, 3], "sample_size": 3},
        "canonical_event_count": "UNKNOWN",
        "claim_output_allowed": False,
        "report_language_allowed": False,
    }


def test_registry_contains_initial_disciplines() -> None:
    assert set(MODULE.DISCIPLINE_REGISTRY) == {"statistics", "entropy", "graph_theory", "geometry", "bayes", "game_theory"}


def test_valid_registered_lens_is_candidate() -> None:
    result = MODULE.evaluate_lens_request(valid_statistics_request())
    assert result["status"] == "SMOKE_PASS"
    assert result["decision"] == "INCLUDE_DISCIPLINE_LENS_CANDIDATE"


def test_unregistered_discipline_routes_to_review() -> None:
    request = valid_statistics_request()
    request["discipline"] = "metaphor"
    result = MODULE.evaluate_lens_request(request)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "unregistered_discipline" in result["review_hits"]


def test_disallowed_primitive_routes_to_review() -> None:
    request = valid_statistics_request()
    request["diagnostic_primitive"] = "tactical_truth"
    result = MODULE.evaluate_lens_request(request)
    assert "primitive_not_allowed_for_discipline" in result["review_hits"]


def test_missing_required_inputs_routes_to_review() -> None:
    request = valid_statistics_request()
    request["inputs"] = {"observations": [1, 2, 3]}
    result = MODULE.evaluate_lens_request(request)
    assert result["missing_inputs"] == ["sample_size"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_top_level_forbidden_field_fails_closed() -> None:
    request = valid_statistics_request()
    request["claim_text"] = "forbidden"
    result = MODULE.evaluate_lens_request(request)
    assert result["status"] == "FAIL_CLOSED"
    assert "claim_text" in result["forbidden_upstream_hits"]


def test_nested_forbidden_field_fails_closed() -> None:
    request = valid_statistics_request()
    request["inputs"]["payload"] = {"tactical_truth": True}
    result = MODULE.evaluate_lens_request(request)
    assert result["status"] == "FAIL_CLOSED"
    assert "inputs.payload.tactical_truth" in result["forbidden_upstream_hits"]


def test_empty_forbidden_value_does_not_trigger() -> None:
    request = valid_statistics_request()
    request["claim_text"] = ""
    result = MODULE.evaluate_lens_request(request)
    assert result["status"] == "SMOKE_PASS"


def test_upstream_fail_closed_propagates() -> None:
    request = valid_statistics_request()
    request["status"] = "FAIL_CLOSED"
    result = MODULE.evaluate_lens_request(request)
    assert "upstream_request_failed_closed" in result["hard_block_hits"]


def test_canonical_event_count_claim_rejected() -> None:
    request = valid_statistics_request()
    request["canonical_event_count"] = 100
    result = MODULE.evaluate_lens_request(request)
    assert "canonical_event_count_claim_rejected" in result["hard_block_hits"]


def test_claim_and_report_flags_rejected() -> None:
    request = valid_statistics_request()
    request["claim_output_allowed"] = True
    request["report_language_allowed"] = True
    result = MODULE.evaluate_lens_request(request)
    assert "claim_output_not_allowed" in result["hard_block_hits"]
    assert "report_language_not_allowed" in result["hard_block_hits"]


def test_output_never_emits_truth_or_claim_permission() -> None:
    result = MODULE.evaluate_lens_request(valid_statistics_request())
    assert result["claim_output_allowed"] is False
    assert result["report_language_allowed"] is False
    assert result["tactical_truth"] is False
    assert result["causal_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_report_counts_include_review_block() -> None:
    review_request = valid_statistics_request()
    review_request["discipline"] = "unknown"
    blocked_request = valid_statistics_request()
    blocked_request["claim_text"] = "blocked"
    report = MODULE.build_registry_report([valid_statistics_request(), review_request, blocked_request])
    assert report["decision_counts"] == {
        "INCLUDE_DISCIPLINE_LENS_CANDIDATE": 1,
        "ROUTE_DISCIPLINE_LENS_TO_REVIEW": 1,
        "BLOCK_DISCIPLINE_LENS": 1,
    }
    assert report["status"] == "FAIL_CLOSED"


def test_write_outputs_rejects_nested_phone_output(tmp_path: Path) -> None:
    nested = tmp_path / "phone" / "nested"
    try:
        MODULE.write_outputs([valid_statistics_request()], nested)
    except Exception as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output must fail")


def test_no_sample_match_identity_leak() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    for token in ["galatasaray", "fenerbahce", "besiktas", "trabzonspor", "france", "morocco"]:
        assert token not in source
