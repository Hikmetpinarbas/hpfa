from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import (
    build_dictionary_report,
    derivation_semantic_fingerprint,
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


def load(name: str):
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def build(*, metric_policy=None, denominator_policy=None, aggregate=None, derivations=None):
    return build_dictionary_report(
        load("provider_metric_dictionary_v1.json"),
        load("provider_alias_registry_v1.json"),
        derivations or load("metric_derivation_registry_v1.json"),
        load("metric_conflict_queue_v1.json"),
        metric_policy=metric_policy or load("metric_registry_v1.json"),
        denominator_policy=denominator_policy or load("metric_denominator_policy_v1.json"),
        aggregate_registry=aggregate or json.loads(AGG.read_text(encoding="utf-8")),
    )


class ProviderMetricDictionaryReviewRound4Tests(unittest.TestCase):
    def test_duplicate_metric_policy_identifier_is_ambiguous_and_binding_invalid(self):
        policy = load("metric_registry_v1.json")
        source = next(
            row for row in policy["metrics"]
            if row["metric_id"] == "pass_completion_rate_candidate"
        )
        duplicate = copy.deepcopy(source)
        duplicate["construct_target"] = "conflicting_duplicate_construct"
        policy["metrics"].append(duplicate)

        report = build(metric_policy=policy)
        hard_types = {gap["gap_type"] for gap in report["hard_block_hits"]}
        self.assertIn("duplicate_upstream_metric_policy_id", hard_types)
        self.assertIn("upstream_metric_policy_identifier_ambiguous", hard_types)
        self.assertIn(
            ("pass_completion_rate", "metric_policy", "INVALID"),
            {
                (item["metric_id"], item["binding"], item["status"])
                for item in report["upstream_binding_results"]
            },
        )

    def test_duplicate_denominator_policy_identifier_is_ambiguous(self):
        policy = load("metric_denominator_policy_v1.json")
        source = next(
            row for row in policy["policies"]
            if row["denominator_policy_id"] == "provider_bound_rate_v1"
        )
        duplicate = copy.deepcopy(source)
        duplicate["zero_denominator_behavior"] = "CONFLICTING_DUPLICATE"
        policy["policies"].append(duplicate)

        report = build(denominator_policy=policy)
        hard_types = {gap["gap_type"] for gap in report["hard_block_hits"]}
        self.assertIn("duplicate_upstream_denominator_policy_id", hard_types)
        self.assertIn("upstream_denominator_policy_identifier_ambiguous", hard_types)

    def test_duplicate_aggregate_identifier_is_ambiguous_and_binding_invalid(self):
        aggregate = json.loads(AGG.read_text(encoding="utf-8"))
        duplicate = copy.deepcopy(aggregate["definitions"][0])
        duplicate["provider_id"] = "conflicting-provider"
        aggregate["definitions"].append(duplicate)

        report = build(aggregate=aggregate)
        hard_types = {gap["gap_type"] for gap in report["hard_block_hits"]}
        self.assertIn("duplicate_upstream_aggregate_definition_id", hard_types)
        self.assertIn("upstream_aggregate_definition_identifier_ambiguous", hard_types)
        self.assertIn(
            ("pass_completion_rate", "aggregate_definition", "INVALID"),
            {
                (item["metric_id"], item["binding"], item["status"])
                for item in report["upstream_binding_results"]
            },
        )

    def test_cleared_derivation_formula_tamper_invalidates_reviewed_semantics(self):
        derivations = load("metric_derivation_registry_v1.json")
        row = derivations["derivations"][0]
        row["provider_id"] = "sportsbase"
        row["provider_version"] = "sportsbase-v1"
        row["derivation_status"] = "CLEARED"
        row["derivation_semantic_fingerprint_sha256"] = derivation_semantic_fingerprint(row)
        row["formula"] = "pass_accurate - pass_inaccurate"

        report = build(derivations=derivations)
        self.assertIn(
            "cleared_derivation_semantic_fingerprint_mismatch",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )

    def test_cleared_derivation_cannot_review_an_empty_formula(self):
        derivations = load("metric_derivation_registry_v1.json")
        row = derivations["derivations"][0]
        row["provider_id"] = "sportsbase"
        row["provider_version"] = "sportsbase-v1"
        row["derivation_status"] = "CLEARED"
        row["formula"] = ""
        row["derivation_semantic_fingerprint_sha256"] = derivation_semantic_fingerprint(row)

        report = build(derivations=derivations)
        self.assertIn(
            "cleared_derivation_formula_missing",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )


if __name__ == "__main__":
    unittest.main()
