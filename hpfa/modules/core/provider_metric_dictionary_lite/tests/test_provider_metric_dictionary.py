from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import (
    FINGERPRINT_FIELDS,
    build_dictionary_report,
    definition_fingerprint,
    load_dictionary_pack,
    operational_semantic_fingerprint,
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


def load(name):
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def build(
    dictionary=None,
    aliases=None,
    derivations=None,
    conflicts=None,
    metric_policy=None,
    denominator_policy=None,
    aggregate=None,
):
    return build_dictionary_report(
        dictionary or load("provider_metric_dictionary_v1.json"),
        aliases or load("provider_alias_registry_v1.json"),
        derivations or load("metric_derivation_registry_v1.json"),
        conflicts or load("metric_conflict_queue_v1.json"),
        metric_policy=metric_policy or load("metric_registry_v1.json"),
        denominator_policy=denominator_policy or load("metric_denominator_policy_v1.json"),
        aggregate_registry=aggregate or json.loads(AGG.read_text(encoding="utf-8")),
    )


class ProviderMetricDictionaryTests(unittest.TestCase):
    def test_current_pack_is_safe_review_required(self):
        report = load_dictionary_pack(ROOT)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertTrue(report["spec_contract_valid"])
        self.assertEqual(report["metric_record_count"], 27)
        self.assertEqual(report["provider_definition_ready_count"], 0)
        self.assertGreaterEqual(report["hpfa_domain_contract_ready_count"], 4)
        self.assertFalse(report["downstream_provider_definition_gate_open"])
        self.assertEqual(report["canonical_event_count"], "UNKNOWN")
        self.assertFalse(report["production_release"])

    def test_all_definition_fingerprints_match(self):
        d = load("provider_metric_dictionary_v1.json")
        self.assertEqual(tuple(d["fingerprint_fields"]), FINGERPRINT_FIELDS)
        for row in d["metrics"]:
            self.assertRegex(row["definition_fingerprint_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                row["definition_fingerprint_sha256"],
                definition_fingerprint(row),
            )

    def test_fingerprint_tamper_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        d["metrics"][0]["construct"] = "tampered"
        r = build(dictionary=d)
        self.assertEqual(r["status"], "FAIL_CLOSED")
        self.assertIn(
            "definition_fingerprint_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_event_only_operational_tamper_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        d["metrics"][0]["event_only_compatible"] = False
        r = build(dictionary=d)
        self.assertIn(
            "event_only_compatibility_required",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_bound_metric_family_operational_tamper_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_completion_rate")
        row["metric_family"] = "tampered_family"
        r = build(dictionary=d)
        self.assertIn(
            "upstream_metric_family_binding_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_unknown_upstream_binding_key_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_completion_rate")
        row["upstream_bindings"]["unsafe_binding"] = "x"
        r = build(dictionary=d)
        self.assertIn(
            "upstream_binding_key_unknown",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_unverified_provider_cannot_be_admitted(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_accurate")
        row["definition_evidence_status"] = "REVIEWED_PROVIDER_DEFINITION"
        row["provider_binding_admitted"] = True
        row["definition_fingerprint_sha256"] = definition_fingerprint(row)
        r = build(dictionary=d)
        self.assertEqual(r["status"], "FAIL_CLOSED")
        self.assertIn(
            "provider_binding_admitted_without_version",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )
        self.assertEqual(r["provider_definition_ready_count"], 0)

    def test_provider_source_role_allowlist_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_accurate")
        row["provider_version"] = "sportsbase-v1"
        row["source_role"] = "HPFA_DOMAIN_CONTRACT"
        row["definition_evidence_status"] = "REVIEWED_PROVIDER_DEFINITION"
        row["provider_binding_admitted"] = True
        row["definition_fingerprint_sha256"] = definition_fingerprint(row)
        r = build(dictionary=d)
        self.assertIn(
            "provider_binding_admitted_from_non_authoritative_source_role",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )
        self.assertEqual(r["provider_definition_ready_count"], 0)

    def test_provider_ready_requires_operational_fingerprint(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_accurate")
        row["provider_version"] = "sportsbase-v1"
        row["source_role"] = "PROVIDER_DOCUMENTATION"
        row["definition_evidence_status"] = "REVIEWED_PROVIDER_DEFINITION"
        row["provider_binding_admitted"] = True
        row["definition_fingerprint_sha256"] = definition_fingerprint(row)
        row["operational_semantic_fingerprint_sha256"] = "0" * 64
        r = build(dictionary=d)
        self.assertIn(
            "operational_semantic_fingerprint_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )
        self.assertEqual(r["provider_definition_ready_count"], 0)

    def test_operational_fingerprint_changes_with_direct_operational_semantics(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_accurate")
        original = operational_semantic_fingerprint(row)
        row["metric_family"] = "changed"
        changed = operational_semantic_fingerprint(row)
        self.assertNotEqual(original, changed)

    def test_hpfa_domain_contract_does_not_validate_provider_alias(self):
        aliases = load("provider_alias_registry_v1.json")
        aliases["aliases"].append({
            "provider_id": "sportsbase",
            "provider_version": "provider_definition_unverified",
            "surface_role": "player_aggregate",
            "raw_label": "unsafe",
            "metric_id": "progressive_open_pass",
            "alias_status": "CANDIDATE_ONLY",
        })
        r = build(aliases=aliases)
        self.assertEqual(r["status"], "FAIL_CLOSED")
        self.assertIn(
            "candidate_provider_alias_targets_hpfa_domain_contract",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_progressive_open_provider_label_is_split_from_hpfa_contract(self):
        d = load("provider_metric_dictionary_v1.json")
        a = load("provider_alias_registry_v1.json")
        alias = next(x for x in a["aliases"] if x["raw_label"] == "Progressive open passes")
        self.assertEqual(
            alias["metric_id"],
            "sportsbase_progressive_open_pass_label_candidate",
        )
        hpfa = next(x for x in d["metrics"] if x["metric_id"] == "progressive_open_pass")
        self.assertEqual(hpfa["provider_id"], "hpfa")
        self.assertTrue(hpfa["domain_contract_admitted"])
        self.assertNotIn("Progressive open passes", hpfa["raw_labels"])

    def test_final_third_provider_label_is_split_from_hpfa_constructs(self):
        a = load("provider_alias_registry_v1.json")
        alias = next(x for x in a["aliases"] if x["raw_label"] == "Final third entries")
        self.assertEqual(
            alias["metric_id"],
            "sportsbase_final_third_entries_label_candidate",
        )
        self.assertNotEqual(alias["metric_id"], "final_third_boundary_entry")
        self.assertNotEqual(alias["metric_id"], "final_third_access_established")

    def test_rate_requires_explicit_zero_denominator_policy(self):
        d = load("provider_metric_dictionary_v1.json")
        row = next(x for x in d["metrics"] if x["metric_id"] == "pass_completion_rate")
        row["missing_zero_denominator_policy"] = "NOT_APPLICABLE"
        row["definition_fingerprint_sha256"] = definition_fingerprint(row)
        r = build(dictionary=d)
        self.assertIn(
            "rate_without_zero_denominator_policy",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_pass_completion_binds_current_upstream_semantics(self):
        r = build()
        bindings = {
            (x["metric_id"], x["binding"], x["status"])
            for x in r["upstream_binding_results"]
        }
        self.assertIn(("pass_completion_rate", "metric_policy", "BOUND"), bindings)
        self.assertIn(("pass_completion_rate", "aggregate_definition", "BOUND"), bindings)

    def test_upstream_denominator_drift_fails_closed(self):
        policy = load("metric_registry_v1.json")
        row = next(
            x for x in policy["metrics"]
            if x["metric_id"] == "pass_completion_rate_candidate"
        )
        row["denominator_definition"] = "different denominator"
        r = build(metric_policy=policy)
        self.assertIn(
            "upstream_metric_policy_semantic_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_resolved_denominator_policy_drift_fails_closed(self):
        policy = load("metric_denominator_policy_v1.json")
        row = next(
            x for x in policy["policies"]
            if x["denominator_policy_id"] == "provider_bound_rate_v1"
        )
        row["required_scope_keys"].append("unsafe_scope")
        r = build(denominator_policy=policy)
        self.assertIn(
            "upstream_denominator_policy_fingerprint_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_upstream_aggregate_fingerprint_drift_fails_closed(self):
        aggregate = json.loads(AGG.read_text(encoding="utf-8"))
        aggregate["definitions"][0]["metric_definition_fingerprint_sha256"] = "0" * 64
        r = build(aggregate=aggregate)
        self.assertIn(
            "upstream_aggregate_fingerprint_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_upstream_aggregate_provider_provenance_drift_fails_closed(self):
        aggregate = json.loads(AGG.read_text(encoding="utf-8"))
        aggregate["definitions"][0]["provider_id"] = "different-provider"
        r = build(aggregate=aggregate)
        self.assertIn(
            "upstream_aggregate_provider_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_upstream_aggregate_metric_namespace_drift_fails_closed(self):
        aggregate = json.loads(AGG.read_text(encoding="utf-8"))
        aggregate["definitions"][0]["metric_id"] = "different_metric"
        r = build(aggregate=aggregate)
        self.assertIn(
            "upstream_aggregate_metric_namespace_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_upstream_aggregate_source_role_drift_fails_closed(self):
        aggregate = json.loads(AGG.read_text(encoding="utf-8"))
        aggregate["definitions"][0]["source_roles"] = ["REFERENCE_ONLY"]
        r = build(aggregate=aggregate)
        self.assertIn(
            "upstream_aggregate_source_role_mismatch",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_admitted_alias_requires_validated_ready_provider_binding(self):
        aliases = load("provider_alias_registry_v1.json")
        aliases["aliases"][0]["alias_status"] = "ADMITTED"
        r = build(aliases=aliases)
        self.assertIn(
            "alias_admitted_without_provider_version_binding",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_derivation_cannot_clear_candidate_provider_metric(self):
        deriv = load("metric_derivation_registry_v1.json")
        deriv["derivations"][0]["derivation_status"] = "CLEARED"
        r = build(derivations=deriv)
        self.assertIn(
            "derivation_cleared_without_admitted_definition",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_tracking_truth_leak_fails_closed(self):
        d = load("provider_metric_dictionary_v1.json")
        row = d["metrics"][0]
        row["produced_truths"] = ["pitch_control_truth"]
        r = build(dictionary=d)
        self.assertIn(
            "tracking_truth_leak",
            {g["gap_type"] for g in r["hard_block_hits"]},
        )

    def test_reference_only_definition_never_opens_provider_binding(self):
        r = build()
        self.assertGreaterEqual(len(r["reference_only_metric_ids"]), 2)
        self.assertEqual(r["provider_definition_ready_count"], 0)

    def test_open_conflicts_keep_review_required(self):
        r = build()
        self.assertGreater(r["open_conflict_count"], 0)
        self.assertIn(
            "metric_definition_conflicts_open",
            {g["gap_type"] for g in r["review_hits"]},
        )

    def test_claim_boundary(self):
        r = build()
        self.assertFalse(r["metric_value_output_allowed"])
        self.assertFalse(r["comparison_allowed"])
        self.assertFalse(r["claim_allowed"])
        self.assertFalse(r["provider_candidate_is_validated_provider_identity"])
        self.assertFalse(r["same_label_is_same_definition"])
        self.assertFalse(r["arithmetic_reproduction_is_provider_definition_truth"])

    def test_no_sample_match_identity_leak(self):
        forbidden = re.compile(
            r"(?i)(sturm|hearts|fenerbah|galatasaray|besiktas|beşiktaş|trabzon|2026[-_]0[1-9][-_][0-9]{2})"
        )
        files = [
            ROOT / "provider_metric_dictionary_lite.py",
            ROOT / "docs/contracts/provider_metric_dictionary_lite_v1.md",
            ROOT / "configs/metrics/provider_metric_dictionary_v1.json",
            ROOT / "configs/metrics/provider_alias_registry_v1.json",
            ROOT / "configs/metrics/metric_derivation_registry_v1.json",
            ROOT / "configs/metrics/metric_conflict_queue_v1.json",
            ROOT / "hpfa/modules/core/provider_metric_dictionary_lite/src/provider_metric_dictionary.py",
        ]
        for path in files:
            self.assertIsNone(
                forbidden.search(path.read_text(encoding="utf-8")),
                path,
            )


if __name__ == "__main__":
    unittest.main()
