from __future__ import annotations

import unittest

from hpfa.modules.core.trackable_action_trace_candidates_lite.src.observed_actor_acquisition_release_interval_projection import (
    build_observed_actor_acquisition_release_interval_projection,
)


class AcquisitionReleaseWindowSemanticsTest(unittest.TestCase):
    def test_temporal_relation_window_is_not_promoted_to_right_censoring_truth(self) -> None:
        payload = {
            "status": "PASS",
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "provider_time_contract_admission_status": "ADMITTED",
            "temporal_relation_uses_start_timestamp_only": True,
            "trace_end_candidate_used_for_ordering": False,
            "same_timestamp_is_total_order": False,
            "source_row_order_is_temporal_truth": False,
            "legacy_trace_records_are_primary_action_member_surface": False,
            "temporal_relation_max_window_seconds": 12.0,
            "primary_occurrence_trace_candidates": [
                {
                    "trackable_action_trace_candidate_id": "anchor",
                    "action_family_candidates": ["RECOVERY"],
                    "actor_identity_candidate_id": "actor_a",
                    "team_identity_candidate_id": "team_a",
                    "period_candidate": "1",
                    "start_candidate": 10.0,
                    "primary_occurrence_member_candidate": True,
                    "occurrence_backed_trace_candidate": True,
                    "supporting_action_occurrence_candidate_ids": ["occ_anchor"],
                },
                {
                    "trackable_action_trace_candidate_id": "release",
                    "action_family_candidates": ["PASS"],
                    "actor_identity_candidate_id": "actor_a",
                    "team_identity_candidate_id": "team_a",
                    "period_candidate": "1",
                    "start_candidate": 13.0,
                    "primary_occurrence_member_candidate": True,
                    "occurrence_backed_trace_candidate": True,
                    "supporting_action_occurrence_candidate_ids": ["occ_release"],
                },
            ],
            "temporal_relation_admission_records": [
                {
                    "anchor_trackable_action_trace_candidate_id": "anchor",
                    "candidate_trackable_action_trace_candidate_id": "release",
                    "relation_state": "AFTER_CONFIRMED",
                    "temporal_basis": "ABSOLUTE_MATCH_SECONDS",
                    "ordering_basis": "START_TIMESTAMP_POINT_CANDIDATE",
                    "provider_time_contract_rule_id": "test_time_contract_v1",
                }
            ],
        }

        report = build_observed_actor_acquisition_release_interval_projection(payload)

        self.assertTrue(report["interval_candidate_visibility_is_window_limited"])
        self.assertFalse(report["temporal_relation_window_is_observation_horizon_truth"])
        self.assertFalse(report["interval_candidates_are_right_censored"])
        self.assertIn("interval_candidate_visibility_window_limited", report["review_hits"])
        self.assertNotIn(
            "interval_candidates_censored_by_temporal_relation_window",
            report["review_hits"],
        )

    def test_no_sample_match_identity_leak(self) -> None:
        product_text = __import__(
            "inspect"
        ).getsource(build_observed_actor_acquisition_release_interval_projection)
        self.assertNotIn("Genclerbirligi", product_text)
        self.assertNotIn("Fenerbahce", product_text)
        self.assertNotIn("Sporting", product_text)
        self.assertNotIn("Galatasaray", product_text)


if __name__ == "__main__":
    unittest.main()
