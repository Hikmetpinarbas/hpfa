import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_definition_policy_lite" / "src"
CONFIG = ROOT / "configs" / "metrics"
sys.path.insert(0, str(SRC))

from metric_definition_policy import (  # noqa: E402
    build_metric_definition_policy,
    load_policy_pack,
    write_policy_report,
)


def _docs():
    names = [
        "metric_registry_v1.json",
        "metric_denominator_policy_v1.json",
        "metric_context_schema_v1.json",
        "metric_confidence_rules_v1.json",
        "metric_misuse_warnings_v1.json",
    ]
    return [json.loads((CONFIG / name).read_text(encoding="utf-8")) for name in names]


def test_seed_policy_pack_smoke_passes():
    report = load_policy_pack(CONFIG)
    assert report["status"] == "SMOKE_PASS"
    assert report["metric_definition_candidate_count"] == 2
    assert report["definition_status_counts"] == {"DEFINITION_CANDIDATE_READY": 2}


def test_every_metric_requires_unique_registry_entry():
    docs = _docs()
    docs[0]["metrics"].append(copy.deepcopy(docs[0]["metrics"][0]))
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "duplicate_metric_id" for gap in report["policy_gaps"])


def test_rate_and_percentage_require_denominator_definition():
    docs = _docs()
    docs[0]["metrics"][1]["denominator_definition"] = ""
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "rate_without_denominator" for gap in report["policy_gaps"])


def test_zero_denominator_must_be_handled():
    docs = _docs()
    docs[1]["policies"][1]["zero_denominator_behavior"] = ""
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "zero_denominator_unhandled" for gap in report["policy_gaps"])


def test_all_policy_references_resolve():
    docs = _docs()
    docs[0]["metrics"][0]["context_policy_id"] = "missing"
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "context_policy_unresolved" for gap in report["policy_gaps"])


def test_metric_requires_does_not_measure_and_forbidden_claims():
    for field in ("does_not_measure", "forbidden_claims"):
        docs = _docs()
        docs[0]["metrics"][0][field] = []
        report = build_metric_definition_policy(*docs)
        assert report["status"] == "FAIL_CLOSED"
        assert any(gap["gap_type"] == f"{field}_missing" for gap in report["policy_gaps"])


def test_comparison_is_blocked_without_definition_alignment():
    docs = _docs()
    docs[0]["metrics"][1]["comparison_allowed"] = True
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["metrics"][1]["comparison_allowed"] is False
    assert any(
        gap["gap_type"] == "comparison_allowed_without_definition_alignment"
        for gap in report["policy_gaps"]
    )


def test_policy_pack_never_emits_metric_quality_or_tactical_truth():
    report = load_policy_pack(CONFIG)
    assert report["metric_value_output_allowed"] is False
    assert report["quality_truth_output_allowed"] is False
    assert report["tactical_truth_output_allowed"] is False
    assert report["claim_output_allowed"] is False
    assert report["validated_metric_truth"] is False
    assert report["aggregate_equivalence_truth"] is False


def test_canonical_event_count_remains_unknown():
    report = load_policy_pack(CONFIG)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert all(metric["canonical_event_count"] == "UNKNOWN" for metric in report["metrics"])


def test_confidence_policy_requires_calibration_and_has_no_default_formula():
    report = load_policy_pack(CONFIG)
    assert report["status"] == "SMOKE_PASS"
    confidence = _docs()[3]["policies"][0]
    assert confidence["calibration_required"] is True
    assert confidence["sample_size_penalty"] == "CALIBRATION_REQUIRED_NO_DEFAULT_FORMULA"
    assert confidence["maximum_confidence"] == "UNSET_UNTIL_CALIBRATED"


def test_write_policy_report(tmp_path):
    report = write_policy_report(CONFIG, tmp_path)
    output = tmp_path / "metric_definition_policy_lite_v1.json"
    assert output.exists()
    assert report["outputs"]["json"] == str(output)


def test_no_sample_match_identity_leak():
    src = (SRC / "metric_definition_policy.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
