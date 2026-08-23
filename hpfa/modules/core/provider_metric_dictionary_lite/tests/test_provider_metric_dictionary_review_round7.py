from __future__ import annotations

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
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_provider_metric_dictionary_v1.sh"


def load(name: str):
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def build(*, dictionary=None, derivations=None):
    return build_dictionary_report(
        dictionary or load("provider_metric_dictionary_v1.json"),
        load("provider_alias_registry_v1.json"),
        derivations or load("metric_derivation_registry_v1.json"),
        load("metric_conflict_queue_v1.json"),
        metric_policy=load("metric_registry_v1.json"),
        denominator_policy=load("metric_denominator_policy_v1.json"),
        aggregate_registry=json.loads(AGG.read_text(encoding="utf-8")),
    )


def cleared_pass_rate_derivation(policy_id: str) -> dict:
    derivations = load("metric_derivation_registry_v1.json")
    row = next(
        item for item in derivations["derivations"]
        if item["metric_id"] == "pass_completion_rate"
    )
    row["provider_id"] = "sportsbase"
    row["provider_version"] = "provider_definition_unverified"
    row["derivation_status"] = "CLEARED"
    row["upstream_denominator_policy_id"] = policy_id
    row["derivation_semantic_fingerprint_sha256"] = derivation_semantic_fingerprint(row)
    return derivations


class ProviderMetricDictionaryReviewRound7Tests(unittest.TestCase):
    def test_network_fetch_uses_clean_git_config_and_verified_tls(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        for token in (
            "clean_fetch_git(){",
            "GIT_CONFIG_GLOBAL=/dev/null",
            "GIT_CONFIG_SYSTEM=/dev/null",
            "GIT_CONFIG_NOSYSTEM=1",
            "-u GIT_SSL_NO_VERIFY",
            "-c http.sslVerify=true",
            "-c protocol.ext.allow=never",
            'clean_fetch_git --git-dir="$FETCH_REPO" fetch --no-tags --no-recurse-submodules',
            '"$ORIGIN_URL" "$BRANCH:refs/heads/remote"',
        ):
            self.assertIn(token, text)
        self.assertNotIn('safe_git fetch --no-recurse-submodules origin "$BRANCH"', text)

    def test_domain_contract_rejects_external_raw_labels_before_ready_publication(self):
        dictionary = load("provider_metric_dictionary_v1.json")
        row = next(
            item for item in dictionary["metrics"]
            if item["metric_id"] == "progressive_open_pass" and item["provider_id"] == "hpfa"
        )
        key = f"{row['provider_id']}::{row['provider_version']}::{row['metric_id']}"
        row["raw_labels"] = ["Progressive open passes"]

        report = build(dictionary=dictionary)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertNotIn(key, report["hpfa_domain_contract_ready_metric_ids"])
        self.assertIn(
            "domain_contract_raw_labels_must_be_empty",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )

    def test_cleared_derivation_rejects_missing_denominator_policy(self):
        report = build(derivations=cleared_pass_rate_derivation("missing-policy"))
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertIn(
            "cleared_derivation_denominator_policy_missing",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )

    def test_cleared_derivation_rejects_unrelated_denominator_policy(self):
        report = build(derivations=cleared_pass_rate_derivation("count_not_applicable_v1"))
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertIn(
            "cleared_derivation_denominator_policy_mismatch",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )

    def test_registry_cannot_promote_arithmetic_reproduction_to_provider_truth(self):
        derivations = load("metric_derivation_registry_v1.json")
        derivations["global_derivation_rules"][
            "arithmetic_reproduction_is_provider_definition_truth"
        ] = True
        report = build(derivations=derivations)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertFalse(report["downstream_provider_definition_gate_open"])
        self.assertIn(
            "arithmetic_reproduction_provider_truth_policy_must_be_false",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )


if __name__ == "__main__":
    unittest.main()
