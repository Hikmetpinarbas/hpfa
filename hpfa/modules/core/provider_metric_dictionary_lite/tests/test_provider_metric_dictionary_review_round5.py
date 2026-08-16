from __future__ import annotations

import copy
import unittest
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import (
    FINGERPRINT_FIELDS,
    build_dictionary_report,
    definition_fingerprint,
    derivation_semantic_fingerprint,
    operational_semantic_fingerprint,
)

ROOT = Path(__file__).resolve().parents[5]
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_provider_metric_dictionary_v1.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "provider-metric-dictionary-lite-v1.yml"


def admitted_provider_metric(metric_id: str) -> dict:
    row = {field: "DEFINED" for field in FINGERPRINT_FIELDS}
    row.update(
        {
            "provider_id": "test-provider",
            "provider_version": "test-v1",
            "source_role": "PROVIDER_DOCUMENTATION",
            "metric_id": metric_id,
            "construct": f"test construct {metric_id}",
            "unit": "count",
            "semantic_type": "count",
            "numerator_definition": "NOT_APPLICABLE_FOR_COUNT",
            "denominator_definition": "NOT_APPLICABLE_FOR_COUNT",
            "eligibility_scope": "synthetic regression scope",
            "success_outcome_rule": "synthetic regression outcome",
            "spatial_rule": "event coordinate not required",
            "temporal_window": "single admitted event",
            "aggregation_level": "event",
            "missing_zero_denominator_policy": "NOT_APPLICABLE",
            "derivation_lineage": "synthetic regression lineage",
            "definition_source": "synthetic regression fixture",
            "definition_evidence_status": "REVIEWED_PROVIDER_DEFINITION",
            "claim_ceiling": "TEST_ONLY",
            "raw_labels": [metric_id],
            "metric_family": "synthetic",
            "event_only_compatible": True,
            "provider_binding_admitted": True,
            "domain_contract_admitted": False,
            "comparison_allowed": False,
            "metric_value_output_allowed": False,
            "upstream_bindings": {},
            "produced_truths": [],
        }
    )
    row["definition_fingerprint_sha256"] = definition_fingerprint(row)
    row["operational_semantic_fingerprint_sha256"] = operational_semantic_fingerprint(row)
    return row


def cleared_derivation(formula: str) -> dict:
    row = {
        "provider_id": "test-provider",
        "provider_version": "test-v1",
        "metric_id": "target_metric",
        "formula": formula,
        "component_metric_ids": ["component_a", "component_b"],
        "derivation_status": "CLEARED",
        "provider_definition_required": True,
    }
    row["derivation_semantic_fingerprint_sha256"] = derivation_semantic_fingerprint(row)
    return row


class ProviderMetricDictionaryReviewRound5Tests(unittest.TestCase):
    def test_duplicate_namespaced_cleared_derivation_key_fails_closed(self):
        dictionary = {
            "dictionary_version": "2.0.0",
            "fingerprint_fields": list(FINGERPRINT_FIELDS),
            "metrics": [
                admitted_provider_metric("target_metric"),
                admitted_provider_metric("component_a"),
                admitted_provider_metric("component_b"),
            ],
        }
        first = cleared_derivation("component_a + component_b")
        second = copy.deepcopy(first)
        second["formula"] = "component_a - component_b"
        second["derivation_semantic_fingerprint_sha256"] = derivation_semantic_fingerprint(second)

        report = build_dictionary_report(
            dictionary,
            {"aliases": []},
            {"derivations": [first, second]},
            {"conflicts": []},
            metric_policy={"metrics": []},
            denominator_policy={"policies": []},
            aggregate_registry={"definitions": []},
        )

        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertFalse(report["spec_contract_valid"])
        self.assertFalse(report["downstream_provider_definition_gate_open"])
        self.assertIn(
            "duplicate_cleared_derivation_key",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )

    def test_bootstrap_neutralizes_repository_and_inherited_ssh_command_overrides(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('GIT_SSH_COMMAND="ssh"', text)
        self.assertIn('-c core.sshCommand=ssh', text)
        fetch_index = text.index('safe_git fetch origin "$BRANCH"')
        wrapper_index = text.index('GIT_SSH_COMMAND="ssh"')
        self.assertLess(wrapper_index, fetch_index)

    def test_workflow_runs_when_consumed_upstream_registries_change(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for path in (
            'configs/metrics/metric_registry_v1.json',
            'configs/metrics/metric_denominator_policy_v1.json',
            'hpfa/modules/core/aggregate_definition_alignment_lite/registry/sportsbase_aggregate_definition_candidates_v1.json',
        ):
            self.assertIn(path, text)


if __name__ == "__main__":
    unittest.main()
