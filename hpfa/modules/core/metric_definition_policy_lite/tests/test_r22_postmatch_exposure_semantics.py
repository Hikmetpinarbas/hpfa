from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_definition_policy_lite" / "src"
CONFIG = ROOT / "configs" / "metrics"
sys.path.insert(0, str(SRC))

from metric_definition_policy import build_metric_definition_policy, load_policy_pack


def _docs() -> list[dict]:
    names = [
        "metric_registry_v1.json",
        "metric_denominator_policy_v1.json",
        "metric_context_schema_v1.json",
        "metric_confidence_rules_v1.json",
        "metric_misuse_warnings_v1.json",
        "metric_exposure_policy_v1.json",
    ]
    return [json.loads((CONFIG / name).read_text(encoding="utf-8")) for name in names]


def test_r22_exposure_is_not_physical_cost_truth() -> None:
    exposure = _docs()[5]["policies"][0]
    assert exposure["construct_family"] == "EXPOSURE_NORMALIZATION"
    assert exposure["exposure_semantic_type"] == "PLAYER_ON_PITCH_TIME"
    assert exposure["physical_cost_semantics"] is False

    report = load_policy_pack(CONFIG)
    assert report["research_hardening_guards"]["R22_minutes_played_is_physical_cost"] is False
    assert report["exposure_authority_truth"] is False
    assert report["metric_value_output_allowed"] is False


def test_r22_physical_cost_misclassification_fails_closed() -> None:
    docs = _docs()
    docs[5]["policies"][0]["physical_cost_semantics"] = True
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "exposure_misclassified_as_physical_cost" for gap in report["policy_gaps"])


def test_r22_per90_requires_validated_exposure_and_closed_denominator() -> None:
    docs = _docs()
    metric = copy.deepcopy(docs[0]["metrics"][1])
    metric.update(
        {
            "value_type": "per_90",
            "unit": "per_90",
            "denominator_policy_id": "validated_exposure_per90_v1",
            "exposure_policy_id": "player_on_pitch_exposure_candidate_v1",
        }
    )
    docs[0]["metrics"][1] = metric

    blocked = build_metric_definition_policy(*docs)
    candidate = blocked["metrics"][1]
    assert candidate["exposure_authority_status"] == "UNKNOWN"
    assert candidate["per90_calculation_admitted"] is False

    docs[5]["policies"][0]["exposure_authority_status"] = "VALIDATED"
    still_blocked = build_metric_definition_policy(*docs)
    candidate = still_blocked["metrics"][1]
    assert candidate["exposure_authority_status"] == "VALIDATED"
    assert candidate["denominator_closure_status"] == "UNKNOWN"
    assert candidate["per90_calculation_admitted"] is False

    denominator = docs[1]["policies"][2]
    denominator.update(
        {
            "component_relation": "PARTITION",
            "mutual_exclusivity_status": "PROVEN",
            "collective_exhaustiveness_status": "PROVEN",
            "uncovered_opportunity_status": "NONE",
            "denominator_nucleus_count": 90,
        }
    )
    admitted = build_metric_definition_policy(*docs)
    candidate = admitted["metrics"][1]
    assert candidate["denominator_closure_status"] == "CLOSED"
    assert candidate["per90_calculation_admitted"] is True


def test_r22_foundation_surface_has_no_sample_match_identity_leak() -> None:
    content = (SRC / "metric_definition_policy.py").read_text(encoding="utf-8")
    content += (CONFIG / "metric_exposure_policy_v1.json").read_text(encoding="utf-8")
    for token in ["Australia", "Turkey", "World Cup", "Sturm Graz", "Heart of Midlothian", "Galatasaray"]:
        assert token not in content
