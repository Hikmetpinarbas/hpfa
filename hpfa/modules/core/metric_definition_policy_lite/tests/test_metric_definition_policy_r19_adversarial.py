import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_definition_policy_lite" / "src"
CONFIG = ROOT / "configs" / "metrics"
SCHEMA = ROOT / "hpfa" / "modules" / "core" / "metric_definition_policy_lite" / "contracts" / "metric_definition_policy_lite_v1.schema.json"
sys.path.insert(0, str(SRC))

from metric_definition_policy import build_metric_definition_policy, load_policy_pack  # noqa: E402


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


def _closed_candidate_docs():
    docs = _docs()
    policy = docs[1]["policies"][1]
    policy.update(
        {
            "numerator_subset_status": "PROVEN",
            "component_relation": "PARTITION",
            "mutual_exclusivity_status": "PROVEN",
            "collective_exhaustiveness_status": "PROVEN",
            "uncovered_opportunity_status": "NONE",
            "denominator_nucleus_count": 10,
        }
    )
    return docs, policy


@pytest.mark.parametrize(
    ("field", "value", "expected_closure"),
    [
        ("mutual_exclusivity_status", "FALSE", "VIOLATED"),
        ("mutual_exclusivity_status", "ASSERTED", "UNKNOWN"),
        ("collective_exhaustiveness_status", "VIOLATED", "VIOLATED"),
        ("collective_exhaustiveness_status", "INCOMPLETE", "VIOLATED"),
        ("uncovered_opportunity_status", "PRESENT", "VIOLATED"),
        ("uncovered_opportunity_status", "NONZERO", "VIOLATED"),
        ("component_relation", "NESTED", "UNKNOWN"),
        ("component_relation", "OVERLAPPING", "UNKNOWN"),
    ],
)
def test_r19_nonaffirmative_or_conflicting_states_never_admit_rate(field, value, expected_closure):
    docs, policy = _closed_candidate_docs()
    policy[field] = value

    report = build_metric_definition_policy(*docs)
    rate = report["metrics"][1]

    assert rate["denominator_closure_status"] == expected_closure
    assert rate["rate_calculation_admitted"] is False
    assert rate["metric_value_output_allowed"] is False


def test_r19_positive_nucleus_is_required_for_closure():
    docs, policy = _closed_candidate_docs()
    policy["denominator_nucleus_count"] = 0

    report = build_metric_definition_policy(*docs)
    rate = report["metrics"][1]

    assert rate["denominator_closure_status"] == "UNKNOWN"
    assert rate["rate_calculation_admitted"] is False


def test_generated_report_hardening_version_matches_schema_const():
    report = load_policy_pack(CONFIG)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert report["research_hardening_version"] == schema["properties"]["research_hardening_version"]["const"]
    assert report["research_hardening_version"] == "R07_R17_R18_R19_R22_v2"
