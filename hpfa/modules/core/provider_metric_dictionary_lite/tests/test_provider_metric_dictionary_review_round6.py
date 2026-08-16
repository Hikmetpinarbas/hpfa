from __future__ import annotations

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


def build_synthetic_report(*, formula: str = "component_a + component_b", target_truths: list[str] | None = None) -> dict:
    target = admitted_provider_metric("target_metric")
    if target_truths is not None:
        target["produced_truths"] = target_truths
    dictionary = {
        "dictionary_version": "2.0.0",
        "fingerprint_fields": list(FINGERPRINT_FIELDS),
        "metrics": [
            target,
            admitted_provider_metric("component_a"),
            admitted_provider_metric("component_b"),
        ],
    }
    return build_dictionary_report(
        dictionary,
        {"aliases": []},
        {"derivations": [cleared_derivation(formula)]},
        {"conflicts": []},
        metric_policy={"metrics": []},
        denominator_policy={"policies": []},
        aggregate_registry={"definitions": []},
    )


class ProviderMetricDictionaryReviewRound6Tests(unittest.TestCase):
    def test_bootstrap_disables_recursive_submodule_fetch(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('safe_git fetch --no-recurse-submodules origin "$BRANCH"', text)

    def test_cleared_formula_references_must_match_declared_components(self):
        report = build_synthetic_report(formula="component_a + unadmitted_metric")
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertFalse(report["spec_contract_valid"])
        self.assertFalse(report["downstream_provider_definition_gate_open"])
        self.assertIn(
            "cleared_derivation_formula_component_mismatch",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )

    def test_nonempty_produced_truths_are_rejected_before_ready_publication(self):
        report = build_synthetic_report(target_truths=["goal_truth"])
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertFalse(report["spec_contract_valid"])
        self.assertNotIn(
            "test-provider::test-v1::target_metric",
            report["provider_definition_ready_metric_ids"],
        )
        self.assertIn(
            "produced_truths_not_allowed_in_dictionary_layer",
            {gap["gap_type"] for gap in report["hard_block_hits"]},
        )


if __name__ == "__main__":
    unittest.main()
