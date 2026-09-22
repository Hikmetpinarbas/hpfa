import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_definition_policy_lite" / "src"
CONFIG = ROOT / "configs" / "metrics"
sys.path.insert(0, str(SRC))

from metric_definition_policy import build_metric_definition_policy, load_policy_pack, write_policy_report


def _docs():
    names = [
        "metric_registry_v1.json", "metric_denominator_policy_v1.json",
        "metric_context_schema_v1.json", "metric_confidence_rules_v1.json",
        "metric_misuse_warnings_v1.json", "metric_exposure_policy_v1.json",
    ]
    return [json.loads((CONFIG / name).read_text(encoding="utf-8")) for name in names]


def test_seed_policy_pack_smoke_passes():
    report = load_policy_pack(CONFIG)
    registered_metric_count = len(_docs()[0]["metrics"])
    assert report["status"] == "SMOKE_PASS"
    assert report["metric_definition_candidate_count"] == registered_metric_count
    assert report["definition_status_counts"] == {"DEFINITION_CANDIDATE_READY": registered_metric_count}
    assert report["policy_counts"]["exposure"] == 1


def test_every_metric_requires_unique_registry_entry():
    docs = _docs(); docs[0]["metrics"].append(copy.deepcopy(docs[0]["metrics"][0]))
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "duplicate_metric_id" for g in report["policy_gaps"])


def test_rate_and_percentage_require_denominator_definition():
    docs = _docs(); docs[0]["metrics"][1]["denominator_definition"] = ""
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "rate_without_denominator" for g in report["policy_gaps"])


def test_zero_denominator_must_be_handled():
    docs = _docs(); docs[1]["policies"][1]["zero_denominator_behavior"] = ""
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "zero_denominator_unhandled" for g in report["policy_gaps"])


def test_all_policy_references_resolve():
    docs = _docs(); docs[0]["metrics"][0]["context_policy_id"] = "missing"
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "context_policy_unresolved" for g in report["policy_gaps"])


def test_metric_requires_does_not_measure_and_forbidden_claims():
    for field in ("does_not_measure", "forbidden_claims"):
        docs = _docs(); docs[0]["metrics"][0][field] = []
        report = build_metric_definition_policy(*docs)
        assert report["status"] == "FAIL_CLOSED"
        assert any(g["gap_type"] == f"{field}_missing" for g in report["policy_gaps"])


def test_definition_fingerprint_is_stable_and_semantically_sensitive():
    baseline = load_policy_pack(CONFIG)
    fp = baseline["metrics"][1]["definition_fingerprint_sha256"]
    assert fp == load_policy_pack(CONFIG)["metrics"][1]["definition_fingerprint_sha256"]
    assert len(fp) == 64
    for mutator in (
        lambda d: d[0]["metrics"][1].__setitem__("numerator_definition", "changed numerator"),
        lambda d: d[0]["metrics"][1].__setitem__("construct_target", "changed construct"),
        lambda d: d[0]["metrics"][1].__setitem__("aggregation_class", "STANDARDIZATION_REQUIRED"),
        lambda d: d[1]["policies"][1].__setitem__("review_reason", "changed policy semantics"),
    ):
        docs = _docs(); mutator(docs)
        changed = build_metric_definition_policy(*docs)
        assert changed["metrics"][1]["definition_fingerprint_sha256"] != fp


def test_definition_correctness_never_promotes_construct_validity():
    report = load_policy_pack(CONFIG)
    assert report["construct_validity_truth"] is False
    assert all(m["construct_validity_truth"] is False for m in report["metrics"])


def test_aggregation_class_is_required_and_validated():
    docs = _docs(); docs[0]["metrics"][1]["aggregation_class"] = "MEAN_EVERYTHING"
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "aggregation_class_invalid" for g in report["policy_gaps"])


def test_rate_cannot_use_summable_count_algebra():
    docs = _docs(); docs[0]["metrics"][1]["aggregation_class"] = "SUMMABLE_COUNT"
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "aggregation_class_incompatible_with_value_type" for g in report["policy_gaps"])


def test_rate_with_unknown_denominator_closure_is_not_calculation_admitted():
    rate = load_policy_pack(CONFIG)["metrics"][1]
    assert rate["denominator_closure_status"] == "UNKNOWN"
    assert rate["rate_calculation_admitted"] is False
    assert rate["metric_value_output_allowed"] is False


def test_subset_proven_alone_does_not_close_denominator():
    docs = _docs(); policy = docs[1]["policies"][1]
    policy["numerator_subset_status"] = "PROVEN"
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "SMOKE_PASS"
    assert report["metrics"][1]["denominator_closure_status"] == "UNKNOWN"
    assert report["metrics"][1]["rate_calculation_admitted"] is False


def test_denominator_closes_only_when_all_set_relations_are_admitted():
    docs = _docs(); policy = docs[1]["policies"][1]
    policy.update({
        "numerator_subset_status": "PROVEN", "component_relation": "PARTITION",
        "mutual_exclusivity_status": "PROVEN", "collective_exhaustiveness_status": "PROVEN",
        "uncovered_opportunity_status": "NONE", "denominator_nucleus_count": 10,
    })
    report = build_metric_definition_policy(*docs)
    assert report["metrics"][1]["denominator_closure_status"] == "CLOSED"
    assert report["metrics"][1]["rate_calculation_admitted"] is True


def test_denominator_subset_violation_fails_closed():
    docs = _docs(); docs[1]["policies"][1]["numerator_subset_status"] = "VIOLATED"
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "denominator_numerator_subset_violated" for g in report["policy_gaps"])


def test_per90_requires_explicit_exposure_policy():
    docs = _docs(); metric = docs[0]["metrics"][1]
    metric.update({"value_type": "per_90", "unit": "per_90", "denominator_policy_id": "validated_exposure_per90_v1", "exposure_policy_id": None})
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "per90_exposure_policy_required" for g in report["policy_gaps"])


def test_per90_requires_both_exposure_authority_and_denominator_closure():
    docs = _docs(); metric = docs[0]["metrics"][1]
    metric.update({"value_type": "per_90", "unit": "per_90", "denominator_policy_id": "validated_exposure_per90_v1", "exposure_policy_id": "player_on_pitch_exposure_candidate_v1"})
    blocked = build_metric_definition_policy(*docs)
    assert blocked["metrics"][1]["per90_calculation_admitted"] is False
    docs[5]["policies"][0]["exposure_authority_status"] = "VALIDATED"
    still_blocked = build_metric_definition_policy(*docs)
    assert still_blocked["metrics"][1]["exposure_authority_status"] == "VALIDATED"
    assert still_blocked["metrics"][1]["denominator_closure_status"] == "UNKNOWN"
    assert still_blocked["metrics"][1]["per90_calculation_admitted"] is False
    policy = docs[1]["policies"][2]
    policy.update({"component_relation": "PARTITION", "mutual_exclusivity_status": "PROVEN", "collective_exhaustiveness_status": "PROVEN", "uncovered_opportunity_status": "NONE", "denominator_nucleus_count": 90})
    admitted = build_metric_definition_policy(*docs)
    assert admitted["metrics"][1]["denominator_closure_status"] == "CLOSED"
    assert admitted["metrics"][1]["per90_calculation_admitted"] is True


def test_exposure_policy_rejects_physical_cost_semantics():
    docs = _docs(); docs[5]["policies"][0]["physical_cost_semantics"] = True
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(g["gap_type"] == "exposure_misclassified_as_physical_cost" for g in report["policy_gaps"])


def test_comparison_is_blocked_without_definition_and_construct_alignment():
    docs = _docs(); docs[0]["metrics"][1]["comparison_allowed"] = True
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["metrics"][1]["comparison_allowed"] is False
    gaps = {g["gap_type"] for g in report["policy_gaps"]}
    assert "comparison_allowed_without_definition_alignment" in gaps
    assert "comparison_allowed_without_construct_validity" in gaps


def test_policy_pack_never_emits_metric_quality_or_tactical_truth():
    report = load_policy_pack(CONFIG)
    for key in ("metric_value_output_allowed", "quality_truth_output_allowed", "tactical_truth_output_allowed", "claim_output_allowed", "validated_metric_truth", "aggregate_equivalence_truth", "exposure_authority_truth"):
        assert report[key] is False


def test_canonical_event_count_remains_unknown():
    report = load_policy_pack(CONFIG)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert all(m["canonical_event_count"] == "UNKNOWN" for m in report["metrics"])


def test_confidence_policy_requires_calibration_and_has_no_default_formula():
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
