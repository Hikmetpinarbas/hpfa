from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import (
    build_dictionary_report,
    definition_fingerprint,
    operational_semantic_fingerprint,
)

ROOT = Path(__file__).resolve().parents[5]
CONFIG = ROOT / "configs" / "metrics"
AGG = ROOT / "hpfa" / "modules" / "core" / "aggregate_definition_alignment_lite" / "registry" / "sportsbase_aggregate_definition_candidates_v1.json"


def load(name):
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def build(dictionary=None, aliases=None, derivations=None, conflicts=None, metric_policy=None, denominator_policy=None, aggregate=None):
    return build_dictionary_report(
        dictionary or load("provider_metric_dictionary_v1.json"),
        aliases or load("provider_alias_registry_v1.json"),
        derivations or load("metric_derivation_registry_v1.json"),
        conflicts or load("metric_conflict_queue_v1.json"),
        metric_policy=metric_policy or load("metric_registry_v1.json"),
        denominator_policy=denominator_policy or load("metric_denominator_policy_v1.json"),
        aggregate_registry=aggregate or json.loads(AGG.read_text(encoding="utf-8")),
    )


class ProviderMetricDictionaryReviewRound3Tests(unittest.TestCase):
    def test_upstream_success_rule_drift_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_completion_rate")
        row["success_outcome_rule"] = "tampered-success-rule"
        row["definition_fingerprint_sha256"] = definition_fingerprint(row)
        r = build(dictionary=d)
        self.assertIn("upstream_metric_policy_semantic_mismatch", {g["gap_type"] for g in r["hard_block_hits"]})

    def test_upstream_temporal_window_drift_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_completion_rate")
        row["temporal_window"] = "different-window"
        row["definition_fingerprint_sha256"] = definition_fingerprint(row)
        r = build(dictionary=d)
        self.assertIn("upstream_metric_policy_semantic_mismatch", {g["gap_type"] for g in r["hard_block_hits"]})

    def test_domain_operational_identity_is_fingerprinted_before_ready(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "progressive_open_pass")
        key = f"{row['provider_id']}::{row['provider_version']}::{row['metric_id']}"
        baseline = build(dictionary=d)
        self.assertIn(key, baseline["hpfa_domain_contract_ready_metric_ids"])
        row["metric_family"] = "tampered-family"
        r = build(dictionary=d)
        self.assertIn("domain_operational_fingerprint_mismatch", {g["gap_type"] for g in r["hard_block_hits"]})
        self.assertNotIn(key, r["hpfa_domain_contract_ready_metric_ids"])

    def test_row_level_claim_permission_true_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_accurate")
        row["comparison_allowed"] = True
        r = build(dictionary=d)
        self.assertIn("row_comparison_permission_must_be_false", {g["gap_type"] for g in r["hard_block_hits"]})

    def test_duplicate_admitted_definition_key_is_removed_from_ready_publication(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_accurate")
        row["provider_version"] = "sportsbase-v1"
        row["source_role"] = "PROVIDER_DOCUMENTATION"
        row["definition_evidence_status"] = "REVIEWED_PROVIDER_DEFINITION"
        row["provider_binding_admitted"] = True
        row["definition_fingerprint_sha256"] = definition_fingerprint(row)
        row["operational_semantic_fingerprint_sha256"] = operational_semantic_fingerprint(row)
        duplicate = copy.deepcopy(row)
        d["metrics"].append(duplicate)
        r = build(dictionary=d)
        key = "sportsbase::sportsbase-v1::pass_accurate"
        self.assertIn("duplicate_provider_definition_key", {g["gap_type"] for g in r["hard_block_hits"]})
        self.assertNotIn(key, r["provider_definition_ready_metric_ids"])

    def test_cleared_derivation_requires_explicit_namespace(self):
        deriv = load("metric_derivation_registry_v1.json")
        deriv["derivations"][0]["derivation_status"] = "CLEARED"
        r = build(derivations=deriv)
        self.assertIn("derivation_namespace_required", {g["gap_type"] for g in r["hard_block_hits"]})

    def test_cleared_derivation_namespace_must_have_all_components(self):
        d = load("provider_metric_dictionary_v1.json")
        target = next(x for x in d["metrics"] if x["metric_id"] == "pass_attempts")
        target["provider_version"] = "sportsbase-v1"
        target["source_role"] = "PROVIDER_DOCUMENTATION"
        target["definition_evidence_status"] = "REVIEWED_PROVIDER_DEFINITION"
        target["provider_binding_admitted"] = True
        target["definition_fingerprint_sha256"] = definition_fingerprint(target)
        target["operational_semantic_fingerprint_sha256"] = operational_semantic_fingerprint(target)
        deriv = load("metric_derivation_registry_v1.json")
        row = deriv["derivations"][0]
        row["derivation_status"] = "CLEARED"
        row["provider_id"] = "sportsbase"
        row["provider_version"] = "sportsbase-v1"
        r = build(dictionary=d, derivations=deriv)
        self.assertIn("derivation_components_not_admitted_same_namespace", {g["gap_type"] for g in r["hard_block_hits"]})


if __name__ == "__main__":
    unittest.main()
