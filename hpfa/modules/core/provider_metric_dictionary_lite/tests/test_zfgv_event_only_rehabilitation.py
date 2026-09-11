from __future__ import annotations

import copy
import json
import unittest
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


class ZfgvEventOnlyRehabilitationTests(unittest.TestCase):
    def test_current_pack_declares_zfgv_capability_admission_without_truth_upgrade(self):
        report = load_dictionary_pack(ROOT)
        self.assertEqual(report["zfgv_observation_model"], "MULTI_SURFACE_FOOTBALL_OBSERVATION_FABRIC")
        self.assertFalse(report["event_only_compatibility_is_global_admission_gate"])
        self.assertTrue(report["event_only_compatibility_is_legacy_metadata"])
        self.assertEqual(report["metric_admission_policy"], "REQUIRED_CAPABILITIES_SUBSET_OF_ADMITTED_CAPABILITIES")
        self.assertTrue(report["metric_capability_requirement_sources_are_union_preserved"])
        self.assertTrue(report["supporting_capabilities_are_not_implicitly_required"])
        self.assertFalse(report["runtime_capability_admission_evaluated"])
        self.assertFalse(report["metric_value_output_allowed_by_zfgv_projection"])
        self.assertFalse(report["construct_truth_granted_by_zfgv_projection"])
        self.assertEqual(report["canonical_event_count"], "UNKNOWN")
        self.assertFalse(report["production_release"])

    def test_explicit_zfgv_capabilities_replace_global_event_only_gate(self):
        dictionary = _load("provider_metric_dictionary_v1.json")
        row = next(x for x in dictionary["metrics"] if x["metric_id"] == "pass_accurate")
        row["event_only_compatible"] = False
        row["required_observation_capabilities"] = ["ACTION_EVENT", "ENTITY_ACTOR", "TEMPORAL"]
        report = _build(dictionary=dictionary)
        gap_types = {gap["gap_type"] for gap in report.get("hard_block_hits", [])}
        self.assertNotIn("event_only_compatibility_required", gap_types)
        projected = next(item for item in report["zfgv_metric_capability_requirements"] if item["metric_id"] == "pass_accurate")
        self.assertFalse(projected["event_only_compatible_legacy_metadata"])
        self.assertFalse(projected["event_only_compatibility_is_global_admission_gate"])
        self.assertTrue(projected["capability_contract_explicit"])
        self.assertTrue(projected["dictionary_capability_contract_explicit"])
        self.assertFalse(projected["policy_capability_contract_explicit"])
        self.assertTrue(projected["capability_requirement_sources_are_union_preserved"])
        self.assertEqual(projected["required_observation_capabilities"], ["ACTION_EVENT", "ENTITY_ACTOR", "TEMPORAL"])
        self.assertFalse(projected["runtime_capability_admission_evaluated"])
        self.assertFalse(projected["metric_value_output_allowed_by_this_projection"])
        self.assertFalse(projected["construct_truth_granted_by_this_projection"])

    def test_false_without_capability_replacement_stays_fail_closed(self):
        dictionary = _load("provider_metric_dictionary_v1.json")
        row = next(x for x in dictionary["metrics"] if x["metric_id"] == "pass_accurate")
        row["event_only_compatible"] = False
        report = _build(dictionary=dictionary)
        gap_types = {gap["gap_type"] for gap in report.get("hard_block_hits", [])}
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertIn("event_only_compatibility_required", gap_types)

    def test_event_only_legacy_metadata_must_remain_boolean_when_present(self):
        dictionary = _load("provider_metric_dictionary_v1.json")
        row = next(x for x in dictionary["metrics"] if x["metric_id"] == "pass_accurate")
        row["event_only_compatible"] = "yes"
        report = _build(dictionary=dictionary)
        gap_types = {gap["gap_type"] for gap in report.get("hard_block_hits", [])}
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertIn("event_only_compatibility_metadata_invalid", gap_types)

    def test_capability_projection_recovers_non_event_observation_requirements(self):
        dictionary = copy.deepcopy(_load("provider_metric_dictionary_v1.json"))
        policy = copy.deepcopy(_load("metric_registry_v1.json"))
        provider_row = next(x for x in dictionary["metrics"] if x["metric_id"] == "pass_completion_rate")
        policy_id = provider_row["upstream_bindings"]["metric_policy_id"]
        policy_row = next(x for x in policy["metrics"] if x["metric_id"] == policy_id)
        report = _build(dictionary=dictionary, metric_policy=policy)
        projected = next(item for item in report["zfgv_metric_capability_requirements"] if item["metric_id"] == "pass_completion_rate")
        self.assertIn("ACTION_EVENT", projected["required_observation_capabilities"])
        self.assertIn("OUTCOME_QUALIFIER", projected["required_observation_capabilities"])
        self.assertIn("ENTITY_ACTOR", projected["required_observation_capabilities"])
        self.assertIn("TEMPORAL", projected["required_observation_capabilities"])
        self.assertNotIn("AGGREGATE_TABULAR", projected["required_observation_capabilities"])
        self.assertIn("AGGREGATE_TABULAR", projected["supporting_observation_capabilities"])
        self.assertIn("AGGREGATE_TABULAR", policy_row["supporting_observation_capabilities"])
        self.assertTrue(projected["supporting_capabilities_are_not_implicitly_required"])
        self.assertTrue(projected["policy_capability_contract_explicit"])
        self.assertTrue(projected["capability_contract_explicit"])
        self.assertTrue(projected["capability_requirement_sources_are_union_preserved"])
        self.assertFalse(projected["runtime_capability_admission_evaluated"])

    def test_dictionary_explicit_capabilities_cannot_erase_policy_requirements(self):
        dictionary = copy.deepcopy(_load("provider_metric_dictionary_v1.json"))
        policy = copy.deepcopy(_load("metric_registry_v1.json"))
        provider_row = next(x for x in dictionary["metrics"] if x["metric_id"] == "pass_completion_rate")
        provider_row["required_observation_capabilities"] = ["AGGREGATE_TABULAR"]
        report = _build(dictionary=dictionary, metric_policy=policy)
        projected = next(item for item in report["zfgv_metric_capability_requirements"] if item["metric_id"] == "pass_completion_rate")
        self.assertTrue(projected["dictionary_capability_contract_explicit"])
        self.assertTrue(projected["policy_capability_contract_explicit"])
        self.assertTrue(projected["capability_requirement_sources_are_union_preserved"])
        self.assertEqual(projected["required_observation_capabilities"], ["ACTION_EVENT", "AGGREGATE_TABULAR", "ENTITY_ACTOR", "OUTCOME_QUALIFIER", "TEMPORAL"])

    def test_explicit_capabilities_cannot_erase_structural_spatial_requirement(self):
        dictionary = copy.deepcopy(_load("provider_metric_dictionary_v1.json"))
        row = next(x for x in dictionary["metrics"] if x["metric_id"] == "progressive_pass_accurate")
        row["required_observation_capabilities"] = ["ACTION_EVENT"]
        report = _build(dictionary=dictionary)
        projected = next(item for item in report["zfgv_metric_capability_requirements"] if item["metric_id"] == "progressive_pass_accurate")
        self.assertIn("ACTION_EVENT", projected["required_observation_capabilities"])
        self.assertIn("ENTITY_ACTOR", projected["required_observation_capabilities"])
        self.assertIn("TEMPORAL", projected["required_observation_capabilities"])
        self.assertIn("SPATIAL", projected["required_observation_capabilities"])
        self.assertTrue(projected["capability_requirement_sources_are_union_preserved"])


if __name__ == "__main__":
    unittest.main()
