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
        "metric_registry_v1.json",
        "metric_denominator_policy_v1.json",
        "metric_context_schema_v1.json",
        "metric_confidence_rules_v1.json",
        "metric_misuse_warnings_v1.json",
        "metric_exposure_policy_v1.json",
    ]
    return [json.loads((CONFIG / name).read_text(encoding="utf-8")) for name in names]


def _first_metric(docs):
    return docs[0]["metrics"][0]


def test_l0_aggregate_construct_does_not_require_fake_event_family():
    docs = _docs()
    metric = _first_metric(docs)
    metric.pop("required_event_families", None)
    metric["required_observation_layers"] = ["L0_AGGREGATE_SURFACE"]
    metric["required_surface_semantics"] = ["aggregate_surface_admitted"]
    metric["required_observation_capabilities"] = ["AGGREGATE"]
    metric["optional_observation_capabilities"] = ["ACTOR", "CONTEXT"]
    metric["forbidden_without"] = ["DEPENDENCY_CONTROL"]
    metric["tracking_video_required"] = False
    metric["source_surface_roles"] = ["aggregate_candidate"]

    report = build_metric_definition_policy(*docs)

    assert report["status"] == "SMOKE_PASS"
    assert not any(
        gap.get("gap_type") == "required_event_families_missing"
        for gap in report["policy_gaps"]
    )
    assert report["metrics"][0]["observation_contract_status"] == "PASS"


def test_l8_tracking_construct_does_not_require_fake_event_family():
    docs = _docs()
    metric = _first_metric(docs)
    metric.pop("required_event_families", None)
    metric["required_observation_layers"] = ["L8_TRACKING_VIDEO_PHYSICAL_OFF_BALL_STATE"]
    metric["required_surface_semantics"] = ["tracking_surface_admitted"]
    metric["required_observation_capabilities"] = ["TRACKING_VIDEO_PHYSICAL"]
    metric["optional_observation_capabilities"] = ["ACTOR", "CONTEXT"]
    metric["forbidden_without"] = ["TRACKING"]
    metric["tracking_video_required"] = True
    metric["source_surface_roles"] = ["tracking_observation_candidate"]

    report = build_metric_definition_policy(*docs)

    assert report["status"] == "SMOKE_PASS"
    assert not any(
        gap.get("gap_type") == "required_event_families_missing"
        for gap in report["policy_gaps"]
    )
    assert report["metrics"][0]["observation_contract_status"] == "PASS"


def test_action_construct_still_requires_event_family_metadata():
    docs = _docs()
    metric = _first_metric(docs)
    metric.pop("required_event_families", None)
    metric["required_observation_layers"] = ["L1_ACTION_OBSERVATION"]
    metric["required_observation_capabilities"] = ["ACTION", "ACTOR"]
    metric["required_surface_semantics"] = ["action_family_admitted"]
    metric["tracking_video_required"] = False

    report = build_metric_definition_policy(*docs)

    assert report["status"] == "FAIL_CLOSED"
    assert any(
        gap.get("gap_type") == "required_event_families_missing"
        for gap in report["policy_gaps"]
    )
