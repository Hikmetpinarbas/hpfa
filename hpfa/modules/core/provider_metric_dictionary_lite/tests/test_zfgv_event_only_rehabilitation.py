from __future__ import annotations

import copy
import json
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import (
    build_dictionary_report,
    load_dictionary_pack,
)

ROOT = Path(__file__).resolve().parents[5]
CONFIG = ROOT / "configs" / "metrics"
AGG = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "aggregate_definition_alignment_lite"
    / "registry"
    / "sportsbase_aggregate_definition_candidates_v1.json"
)


def _load(name: str) -> dict:
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def _build(dictionary: dict | None = None, metric_policy: dict | None = None) -> dict:
    return build_dictionary_report(
        dictionary or _load("provider_metric_dictionary_v1.json"),
        _load("provider_alias_registry_v1.json"),
        _load("metric_derivation_registry_v1.json"),
        _load("metric_conflict_queue_v1.json"),
        metric_policy=metric_policy or _load("metric_registry_v1.json"),
        denominator_policy=_load("metric_denominator_policy_v1.json"),
        aggregate_registry=json.loads(AGG.read_text(encoding="utf-8")),
    )


def test_current_pack_declares_zfgv_capability_admission_without_truth_upgrade():
    report = load_dictionary_pack(ROOT)

    assert report["zfgv_observation_model"] == "MULTI_SURFACE_FOOTBALL_OBSERVATION_FABRIC"
    assert report["event_only_compatibility_is_global_admission_gate"] is False
    assert report["event_only_compatibility_is_legacy_metadata"] is True
    assert report["metric_admission_policy"] == "REQUIRED_CAPABILITIES_SUBSET_OF_ADMITTED_CAPABILITIES"
    assert report["runtime_capability_admission_evaluated"] is False
    assert report["metric_value_output_allowed_by_zfgv_projection"] is False
    assert report["construct_truth_granted_by_zfgv_projection"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_event_only_false_is_compatibility_metadata_not_global_metric_rejection():
    dictionary = _load("provider_metric_dictionary_v1.json")
    row = next(x for x in dictionary["metrics"] if x["metric_id"] == "pass_accurate")
    row["event_only_compatible"] = False

    report = _build(dictionary=dictionary)
    gap_types = {gap["gap_type"] for gap in report.get("hard_block_hits", [])}

    assert "event_only_compatibility_required" not in gap_types
    projected = next(
        item for item in report["zfgv_metric_capability_requirements"]
        if item["metric_id"] == "pass_accurate"
    )
    assert projected["event_only_compatible_legacy_metadata"] is False
    assert projected["event_only_compatibility_is_global_admission_gate"] is False
    assert projected["runtime_capability_admission_evaluated"] is False
    assert projected["metric_value_output_allowed_by_this_projection"] is False
    assert projected["construct_truth_granted_by_this_projection"] is False


def test_event_only_legacy_metadata_must_remain_boolean_when_present():
    dictionary = _load("provider_metric_dictionary_v1.json")
    row = next(x for x in dictionary["metrics"] if x["metric_id"] == "pass_accurate")
    row["event_only_compatible"] = "yes"

    report = _build(dictionary=dictionary)
    gap_types = {gap["gap_type"] for gap in report.get("hard_block_hits", [])}

    assert report["status"] == "FAIL_CLOSED"
    assert "event_only_compatibility_metadata_invalid" in gap_types


def test_capability_projection_recovers_non_event_observation_requirements():
    dictionary = _load("provider_metric_dictionary_v1.json")
    policy = _load("metric_registry_v1.json")
    dictionary = copy.deepcopy(dictionary)
    policy = copy.deepcopy(policy)

    provider_row = next(
        x for x in dictionary["metrics"] if x["metric_id"] == "pass_completion_rate"
    )
    policy_id = provider_row["upstream_bindings"]["metric_policy_id"]
    policy_row = next(x for x in policy["metrics"] if x["metric_id"] == policy_id)
    policy_row["source_surface_roles"] = ["occurrence_candidate", "aggregate_candidate"]

    report = _build(dictionary=dictionary, metric_policy=policy)
    projected = next(
        item for item in report["zfgv_metric_capability_requirements"]
        if item["metric_id"] == "pass_completion_rate"
    )

    assert "ACTION_EVENT" in projected["required_observation_capabilities"]
    assert "AGGREGATE_TABULAR" in projected["required_observation_capabilities"]
    assert "ENTITY_ACTOR" in projected["required_observation_capabilities"]
    assert "TEMPORAL" in projected["required_observation_capabilities"]
    assert projected["runtime_capability_admission_evaluated"] is False
