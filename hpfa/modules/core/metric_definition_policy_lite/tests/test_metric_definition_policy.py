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
        "metric_exposure_policy_v1.json",
    ]
    return [json.loads((CONFIG / name).read_text(encoding="utf-8")) for name in names]


def test_seed_policy_pack_smoke_passes():
    report = load_policy_pack(CONFIG)
    assert report["status"] == "SMOKE_PASS"
    assert report["metric_definition_candidate_count"] == 2
    assert report["definition_status_counts"] == {"DEFINITION_CANDIDATE_READY": 2}
    assert report["policy_counts"]["exposure"] == 1


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


def test_definition_fingerprint_is_stable_and_definition_sensitive():
    first = load_policy_pack(CONFIG)
    second = load_policy_pack(CONFIG)
    fp1 = first["metrics"][1]["definition_fingerprint_sha256"]
    fp2 = second["metrics"][1]["definition_fingerprint_sha256"]
    assert fp1 == fp2
    assert len(fp1) == 64

    docs = _docs()
    docs[0]["metrics"][1]["numerator_definition"] += " changed"
    changed = build_metric_definition_policy(*docs)
    assert changed["metrics"][1]["definition_fingerprint_sha256"] != fp1


def test_definition_correctness_never_promotes_construct_validity():
    report = load_policy_pack(CONFIG)
    assert report["status"] == "SMOKE_PASS"
    assert report["construct_validity_truth"] is False
    assert all(metric["construct_validity_truth"] is False for metric in report["metrics"])
    assert all(metric["construct_validity_status"] == "UNVALIDATED_CONSTRUCT_CANDIDATE" for metric in report["metrics"])


def test_aggregation_class_is_required_and_validated():
    docs = _docs()
    docs[0]["metrics"][1]["aggregation_class"] = "MEAN_EVERYTHING"
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "aggregation_class_invalid" for gap in report["policy_gaps"])


def test_rate_with_unknown_denominator_closure_is_not_calculation_admitted():
    report = load_policy_pack(CONFIG)
    rate = report["metrics"][1]
    assert rate["denominator_closure_status"] == "UNKNOWN"
    assert rate["rate_calculation_admitted"] is False
    assert rate["metric_value_output_allowed"] is False


def test_denominator_subset_violation_fails_closed():
    docs = _docs()
    docs[1]["policies"][1]["numerator_subset_status"] = "VIOLATED"
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "denominator_numerator_subset_violated" for gap in report["policy_gaps"])


def test_per90_requires_explicit_exposure_policy():
    docs = _docs()
    metric = docs[0]["metrics"][1]
    metric["value_type"] = "per_90"
    metric["unit"] = "per_90"
    metric["denominator_policy_id"] = "validated_exposure_per90_v1"
    metric["exposure_policy_id"] = None
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "per90_exposure_policy_required" for gap in report["policy_gaps"])


def test_per90_stays_blocked_until_exposure_authority_is_validated():
    docs = _docs()
    metric = docs[0]["metrics"][1]
    metric["value_type"] = "per_90"
    metric["unit"] = "per_90"
    metric["denominator_policy_id"] = "validated_exposure_per90_v1"
    metric["exposure_policy_id"] = "player_on_pitch_exposure_candidate_v1"

    blocked = build_metric_definition_policy(*docs)
    assert blocked["status"] == "SMOKE_PASS"
    assert blocked["metrics"][1]["exposure_authority_status"] == "UNKNOWN"
    assert blocked["metrics"][1]["per90_calculation_admitted"] is False

    docs[5]["policies"][0]["exposure_authority_status"] = "VALIDATED"
    admitted = build_metric_definition_policy(*docs)
    assert admitted["status"] == "SMOKE_PASS"
    assert admitted["metrics"][1]["per90_calculation_admitted"] is True


def test_exposure_policy_rejects_physical_cost_semantics():
    docs = _docs()
    docs[5]["policies"][0]["physical_cost_semantics"] = True
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "exposure_misclassified_as_physical_cost" for gap in report["policy_gaps"])


def test_comparison_is_blocked_without_definition_and_construct_alignment():
    docs = _docs()
    docs[0]["metrics"][1]["comparison_allowed"] = True
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["metrics"][1]["comparison_allowed"] is False
    gap_types = {gap["gap_type"] for gap in report["policy_gaps"]}
    assert "comparison_allowed_without_definition_alignment" in gap_types
    assert "comparison_allowed_without_construct_validity" in gap_types


def test_policy_pack_never_emits_metric_quality_or_tactical_truth():
    report = load_policy_pack(CONFIG)
    assert report["metric_value_output_allowed"] is False
    assert report["quality_truth_output_allowed"] is False
    assert report["tactical_truth_output_allowed"] is False
    assert report["claim_output_allowed"] is False
    assert report["validated_metric_truth"] is False
    assert report["aggregate_equivalence_truth"] is False
    assert report["exposure_authority_truth"] is False


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
    content = (SRC / "metric_definition_policy.py").read_text(encoding="utf-8")
    content += (CONFIG / "metric_registry_v1.json").read_text(encoding="utf-8")
    content += (CONFIG / "metric_exposure_policy_v1.json").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026", "Sturm Graz", "Heart of Midlothian"]:
        assert token not in content
