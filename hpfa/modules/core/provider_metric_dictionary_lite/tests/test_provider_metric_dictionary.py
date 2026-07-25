import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_metric_dictionary_lite" / "src"
CONFIG = ROOT / "configs" / "metrics"
sys.path.insert(0, str(SRC))

from provider_metric_dictionary import build_dictionary_report, load_dictionary_pack


def docs():
    names = [
        "provider_metric_dictionary_v1.json",
        "provider_alias_registry_v1.json",
        "metric_derivation_registry_v1.json",
        "metric_conflict_queue_v1.json",
    ]
    return [json.loads((CONFIG / name).read_text(encoding="utf-8")) for name in names]


class ProviderMetricDictionaryTests(unittest.TestCase):
    def test_seed_pack_has_exactly_25_metrics(self):
        report = load_dictionary_pack(CONFIG)
        self.assertEqual(report["status"], "SPEC_ONLY")
        self.assertEqual(report["metric_record_count"], 25)
        self.assertFalse(report["production_release"])
        self.assertEqual(report["canonical_event_count"], "UNKNOWN")

    def test_forward_progressive_and_final_third_are_distinct(self):
        dictionary = docs()[0]
        ids = {row["metric_id"] for row in dictionary["metrics"]}
        self.assertTrue({
            "forward_pass_accurate",
            "progressive_pass_accurate",
            "progressive_open_pass",
            "forward_pass_to_final_third",
            "final_third_boundary_entry",
        }.issubset(ids))

    def test_progressive_open_requires_one_action_continuation(self):
        dictionary = docs()[0]
        row = next(item for item in dictionary["metrics"] if item["metric_id"] == "progressive_open_pass")
        self.assertIn("one subsequent team action is observed and classified", row["inclusion_rules"])
        self.assertIn("longer-horizon consequence attribution", row["exclusion_rules"])

    def test_boundary_entry_and_inside_access_do_not_merge(self):
        dictionary = docs()[0]
        by_id = {row["metric_id"]: row for row in dictionary["metrics"]}
        self.assertIn("double count of one physical crossing", by_id["final_third_boundary_entry"]["exclusion_rules"])
        self.assertIn("fabricated boundary crossing", by_id["final_third_access_established"]["exclusion_rules"])

    def test_chances_successful_not_chances_created(self):
        dictionary = docs()[0]
        by_id = {row["metric_id"]: row for row in dictionary["metrics"]}
        self.assertNotEqual(by_id["chances_successful"]["provider_id"], by_id["chances_created"]["provider_id"])
        self.assertNotEqual(by_id["chances_successful"]["claim_ceiling"], by_id["chances_created"]["claim_ceiling"])

    def test_duplicate_provider_role_alias_fails_closed(self):
        payload = docs()
        payload[1]["aliases"].append(copy.deepcopy(payload[1]["aliases"][0]))
        report = build_dictionary_report(*payload)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertTrue(any(gap["gap_type"] == "duplicate_provider_role_alias" for gap in report["policy_gaps"]))

    def test_same_semantic_metric_can_have_provider_specific_definitions(self):
        payload = docs()
        duplicate_semantic = copy.deepcopy(payload[0]["metrics"][0])
        duplicate_semantic["provider_id"] = "another_provider"
        duplicate_semantic["provider_version"] = "v2"
        payload[0]["metrics"].append(duplicate_semantic)
        report = build_dictionary_report(*payload)
        self.assertEqual(report["status"], "SPEC_ONLY")
        self.assertEqual(report["metric_record_count"], 26)

    def test_same_provider_version_metric_definition_cannot_duplicate(self):
        payload = docs()
        payload[0]["metrics"].append(copy.deepcopy(payload[0]["metrics"][0]))
        report = build_dictionary_report(*payload)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertTrue(any(gap["gap_type"] == "duplicate_provider_definition_key" for gap in report["policy_gaps"]))

    def test_rate_requires_explicit_denominator(self):
        payload = docs()
        row = next(item for item in payload[0]["metrics"] if item["metric_id"] == "pass_completion_rate")
        row["denominator_definition"] = ""
        report = build_dictionary_report(*payload)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertTrue(any(gap["gap_type"] == "rate_without_explicit_fraction" for gap in report["policy_gaps"]))

    def test_unreviewed_definition_cannot_clear_derivation(self):
        payload = docs()
        payload[2]["derivations"].append({
            "metric_id": "progressive_pass_accurate",
            "formula": "provider unpublished",
            "component_metric_ids": [],
            "derivation_status": "CLEARED",
        })
        report = build_dictionary_report(*payload)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertTrue(any(gap["gap_type"] == "derivation_cleared_without_definition" for gap in report["policy_gaps"]))

    def test_output_permissions_remain_closed(self):
        report = load_dictionary_pack(CONFIG)
        self.assertFalse(report["metric_value_output_allowed"])
        self.assertFalse(report["comparison_allowed"])
        self.assertFalse(report["claim_allowed"])

    def test_no_sample_match_identity_leak(self):
        source = (SRC / "provider_metric_dictionary.py").read_text(encoding="utf-8")
        for token in ["Fenerbahce", "Górnik", "21.07.2026", "19721253"]:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
