from __future__ import annotations

import copy
import unittest

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.variant_feature_challenge_projection import (
    build_variant_feature_challenge_projection,
)


def _payloads() -> tuple[dict, dict]:
    feature_delta = {
        "status": "REVIEW_REQUIRED",
        "outcome_used_only_as_partition_label": True,
        "outcome_used_to_define_features": False,
        "feature_absence_is_counterevidence": False,
        "grammar_stable_variant_feature_delta_records": [
            {
                "grammar_stable_variant_feature_delta_id": "delta_1",
                "source_process_variant_family_ref": "family_1",
                "context_coverage_incomplete_variant_count": 0,
                "consequence_coverage_incomplete_variant_count": 1,
                "context_feature_difference_candidates": [
                    {
                        "feature_token": "provider_direction_candidates:FORWARD",
                        "success_visible_numerator": 18,
                        "success_eligible_denominator": 31,
                        "failure_visible_numerator": 11,
                        "failure_eligible_denominator": 13,
                        "descriptive_rate_delta_success_minus_failure": -0.265509,
                        "dependency_independence_proven": False,
                        "statistical_independence_proven": False,
                    }
                ],
                "consequence_feature_difference_candidates": [
                    {
                        "feature_token": "primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE",
                        "success_visible_numerator": 0,
                        "success_eligible_denominator": 31,
                        "failure_visible_numerator": 7,
                        "failure_eligible_denominator": 13,
                        "descriptive_rate_delta_success_minus_failure": -0.538462,
                        "dependency_independence_proven": False,
                        "statistical_independence_proven": False,
                    }
                ],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    process_variant = {
        "status": "REVIEW_REQUIRED",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "same_grammar_visible_outcome_variation_observed": True,
                "team_identity_candidate_ids": ["team_1"],
                "period_candidates": ["1", "2"],
                "dependency_group_ref_count": 4,
                "dependency_group_refs": ["dep_1", "dep_2", "dep_3", "dep_4"],
                "family_is_independent_recurrence_truth": False,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return feature_delta, process_variant


class VariantFeatureChallengeProjectionTest(unittest.TestCase):
    def test_builds_compact_challenge_rows_without_promoting_difference_to_finding(self):
        feature_delta, process_variant = _payloads()
        report = build_variant_feature_challenge_projection(feature_delta, process_variant)

        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["variant_feature_challenge_record_count"], 2)
        self.assertFalse(report["projection_creates_new_evidence"])
        self.assertFalse(report["projection_reconstructs_sequences"])
        self.assertFalse(report["professional_finding_emit_allowed"])
        self.assertFalse(report["period_spread_is_context_robustness_truth"])

        context = next(
            row for row in report["variant_feature_challenge_records"]
            if row["feature_surface"] == "CONTEXT"
        )
        self.assertEqual(context["sample_strength_state"], "UNCALIBRATED_NO_ARBITRARY_THRESHOLD_APPLIED")
        self.assertFalse(context["dependency_independence_proven"])
        self.assertFalse(context["statistical_independence_proven"])
        self.assertFalse(context["context_robustness_proven"])
        self.assertFalse(context["hypothesis_candidate_is_truth"])
        self.assertTrue(context["analyst_hypothesis_review_candidate"])
        self.assertEqual(
            context["segment_falsifier_state"],
            "MULTI_PERIOD_SCOPE_PRESENT_PERIOD_ALONE_NOT_CONTEXT_ROBUSTNESS",
        )
        self.assertEqual(
            context["failed_trace_falsifier_state"],
            "NON_DISCRIMINATIVE_PRESENCE_VISIBLE",
        )
        self.assertIn("FEATURE_VISIBLE_IN_BOTH_OUTCOME_PARTITIONS", context["challenge_reasons"])

        consequence = next(
            row for row in report["variant_feature_challenge_records"]
            if row["feature_surface"] == "CONSEQUENCE"
        )
        self.assertEqual(
            consequence["failed_trace_falsifier_state"],
            "ONE_PARTITION_ONLY_VISIBLE_ABSENCE_NOT_COUNTEREVIDENCE",
        )
        self.assertFalse(consequence["feature_absence_is_counterevidence"])
        self.assertEqual(consequence["relevant_coverage_incomplete_variant_count"], 1)
        self.assertIn("OBSERVATION_COVERAGE_PARTIAL", consequence["challenge_reasons"])

    def test_unresolved_source_family_fails_closed(self):
        feature_delta, process_variant = _payloads()
        process_variant["observable_process_variant_families"] = []
        report = build_variant_feature_challenge_projection(feature_delta, process_variant)

        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["variant_feature_challenge_records"], [])
        self.assertTrue(
            any(hit.startswith("source_process_variant_family_unresolved:") for hit in report["hard_block_hits"])
        )

    def test_period_difference_never_becomes_context_robustness_truth(self):
        feature_delta, process_variant = _payloads()
        report = build_variant_feature_challenge_projection(feature_delta, process_variant)
        for row in report["variant_feature_challenge_records"]:
            self.assertFalse(row["period_spread_is_context_robustness_truth"])
            self.assertFalse(row["context_robustness_proven"])

    def test_upstream_claim_lock_breach_fails_closed(self):
        feature_delta, process_variant = _payloads()
        breached = copy.deepcopy(feature_delta)
        breached["feature_absence_is_counterevidence"] = True
        report = build_variant_feature_challenge_projection(breached, process_variant)

        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertIn("absence_counterevidence_lock_breached", report["hard_block_hits"])


if __name__ == "__main__":
    unittest.main()
