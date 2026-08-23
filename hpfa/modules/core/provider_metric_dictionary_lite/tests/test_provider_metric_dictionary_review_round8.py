from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import (
    build_dictionary_report,
    definition_fingerprint,
    derivation_semantic_fingerprint,
    operational_semantic_fingerprint,
)

ROOT = Path(__file__).resolve().parents[5]
CONFIG = ROOT / "configs" / "metrics"
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_provider_metric_dictionary_v1.sh"


def load(name: str):
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def admitted_copy(metric_id: str, *, metric_policy=None, denominator_policy=None) -> dict:
    source = next(
        row for row in load("provider_metric_dictionary_v1.json")["metrics"]
        if row["metric_id"] == metric_id and row["provider_id"] == "sportsbase"
    )
    row = copy.deepcopy(source)
    row["provider_id"] = "test-provider"
    row["provider_version"] = "test-v1"
    row["source_role"] = "PROVIDER_DOCUMENTATION"
    row["definition_evidence_status"] = "REVIEWED_PROVIDER_DEFINITION"
    row["provider_binding_admitted"] = True
    row["domain_contract_admitted"] = False
    row["raw_labels"] = [metric_id]
    row["comparison_allowed"] = False
    row["metric_value_output_allowed"] = False
    row["produced_truths"] = []
    row["definition_fingerprint_sha256"] = definition_fingerprint(row)
    row["operational_semantic_fingerprint_sha256"] = operational_semantic_fingerprint(
        row,
        metric_policy_row=metric_policy,
        denominator_policy_row=denominator_policy,
        aggregate_definition_row=None,
    )
    return row


class ProviderMetricDictionaryReviewRound8Tests(unittest.TestCase):
    def test_cleared_rate_requires_targets_denominator_policy_declaration(self):
        policy_pack = load("metric_registry_v1.json")
        denominator_pack = load("metric_denominator_policy_v1.json")
        policy = next(
            row for row in policy_pack["metrics"]
            if row["metric_id"] == "pass_completion_rate_candidate"
        )
        denominator = next(
            row for row in denominator_pack["policies"]
            if row["denominator_policy_id"] == policy["denominator_policy_id"]
        )

        target = admitted_copy(
            "pass_completion_rate",
            metric_policy=policy,
            denominator_policy=denominator,
        )
        target["upstream_bindings"] = {"metric_policy_id": policy["metric_id"]}
        target["definition_fingerprint_sha256"] = definition_fingerprint(target)
        target["operational_semantic_fingerprint_sha256"] = operational_semantic_fingerprint(
            target,
            metric_policy_row=policy,
            denominator_policy_row=denominator,
            aggregate_definition_row=None,
        )
        accurate = admitted_copy("pass_accurate")
        attempts = admitted_copy("pass_attempts")

        derivation = {
            "provider_id": "test-provider",
            "provider_version": "test-v1",
            "metric_id": "pass_completion_rate",
            "formula": "pass_accurate / pass_attempts",
            "component_metric_ids": ["pass_accurate", "pass_attempts"],
            "derivation_status": "CLEARED",
            "provider_definition_required": True,
        }
        derivation["derivation_semantic_fingerprint_sha256"] = derivation_semantic_fingerprint(
            derivation
        )

        report = build_dictionary_report(
            {
                "dictionary_version": "2.0.0",
                "fingerprint_fields": load("provider_metric_dictionary_v1.json")["fingerprint_fields"],
                "metrics": [target, accurate, attempts],
            },
            {"aliases": []},
            {
                "global_derivation_rules": {
                    "arithmetic_reproduction_is_provider_definition_truth": False
                },
                "derivations": [derivation],
            },
            {"conflicts": []},
            metric_policy=policy_pack,
            denominator_policy=denominator_pack,
            aggregate_registry={"definitions": []},
        )

        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertFalse(report["spec_contract_valid"])
        self.assertFalse(report["downstream_provider_definition_gate_open"])
        self.assertIn(
            "cleared_derivation_required_denominator_policy_missing",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )

    def test_bootstrap_materializes_from_clean_bare_repo_without_second_fetch(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('WORK_REPO="$FETCH_TMP/work"', text)
        self.assertIn('worktree add -B "$BRANCH" "$WORK_REPO" "$REMOTE_HEAD"', text)
        self.assertNotIn('safe_git fetch --no-tags --no-recurse-submodules "$FETCH_REPO"', text)
        self.assertNotIn('refs/heads/remote:refs/remotes/origin/$BRANCH', text)
        self.assertIn('HPFA_REPO="$WORK_REPO"', text)


if __name__ == "__main__":
    unittest.main()
