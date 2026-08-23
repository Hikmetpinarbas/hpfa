import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_definition_policy_lite" / "src"
CONFIG = ROOT / "configs" / "metrics"
sys.path.insert(0, str(SRC))

from metric_definition_policy import build_metric_definition_policy


def _docs():
    names = [
        "metric_registry_v1.json", "metric_denominator_policy_v1.json",
        "metric_context_schema_v1.json", "metric_confidence_rules_v1.json",
        "metric_misuse_warnings_v1.json", "metric_exposure_policy_v1.json",
    ]
    return [json.loads((CONFIG / name).read_text(encoding="utf-8")) for name in names]


def _make_other_relations_affirmative(policy):
    policy.update({
        "numerator_subset_status": "PROVEN",
        "component_relation": "PARTITION",
        "mutual_exclusivity_status": "PROVEN",
        "collective_exhaustiveness_status": "PROVEN",
        "uncovered_opportunity_status": "NONE",
        "denominator_nucleus_count": 10,
    })


def test_r19_rejects_non_string_empty_and_sentinel_denominator_set_ids():
    for invalid in (False, True, 0, 1.5, None, "", "   ", "UNKNOWN", "NOT_APPLICABLE", "UNRESOLVED", "NONE", "NULL"):
        docs = _docs()
        policy = docs[1]["policies"][1]
        _make_other_relations_affirmative(policy)
        policy["denominator_set_id"] = invalid
        report = build_metric_definition_policy(*docs)
        metric = report["metrics"][1]
        assert metric["denominator_closure_status"] == "UNKNOWN", invalid
        assert metric["rate_calculation_admitted"] is False, invalid


def test_r19_requires_actual_positive_integer_denominator_nucleus_count():
    for invalid in (True, False, 1.5, 0.5, 0, -1, "10", None):
        docs = _docs()
        policy = docs[1]["policies"][1]
        _make_other_relations_affirmative(policy)
        policy["denominator_nucleus_count"] = invalid
        report = build_metric_definition_policy(*docs)
        metric = report["metrics"][1]
        assert metric["denominator_closure_status"] == "UNKNOWN", invalid
        assert metric["rate_calculation_admitted"] is False, invalid


def test_r19_positive_integer_nucleus_with_real_set_id_can_close():
    docs = _docs()
    policy = docs[1]["policies"][1]
    _make_other_relations_affirmative(policy)
    policy["denominator_set_id"] = "eligible_pass_attempt_set_v1"
    policy["denominator_nucleus_count"] = 10
    report = build_metric_definition_policy(*docs)
    metric = report["metrics"][1]
    assert metric["denominator_closure_status"] == "CLOSED"
    assert metric["rate_calculation_admitted"] is True
