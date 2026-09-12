from __future__ import annotations

import unittest

from hpfa.modules.core.trackable_action_trace_candidates_lite.src.observed_actor_acquisition_release_interval_projection import (
    build_observed_actor_acquisition_release_interval_projection,
)


def _trace(
    trace_id: str,
    family: str,
    *,
    actor: str = "actor_a",
    team: str = "team_a",
    period: str = "1",
    start: float = 10.0,
    end: float | None = None,
) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "action_family_candidates": [family],
        "actor_identity_candidate_id": actor,
        "team_identity_candidate_id": team,
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": start + 12.0 if end is None else end,
        "primary_occurrence_member_candidate": True,
        "occurrence_backed_trace_candidate": True,
        "supporting_action_occurrence_candidate_ids": [f"occ_{trace_id}"],
    }


def _after(anchor: str, candidate: str, period: str = "1") -> dict:
    return {
        "anchor_trackable_action_trace_candidate_id": anchor,
        "candidate_trackable_action_trace_candidate_id": candidate,
        "period_candidate": period,
        "relation_state": "AFTER_CONFIRMED",
        "temporal_basis": "ABSOLUTE_MATCH_SECONDS",
        "ordering_basis": "START_TIMESTAMP_POINT_CANDIDATE",
        "provider_time_contract_rule_id": "sportsbase_like_start_end_absolute_seconds_v1",
    }


def _base_payload(traces: list[dict], relations: list[dict]) -> dict:
    return {
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
        "primary_occurrence_trace_candidates": traces,
        "temporal_relation_admission_records": relations,
    }


class ObservedActorAcquisitionReleaseIntervalProjectionTest(unittest.TestCase):
    def test_recovery_to_same_actor_pass_emits_start_interval_candidate(self) -> None:
        payload = _base_payload(
            [
                _trace("t1", "RECOVERY", start=10.0),
                _trace("t2", "PASS", start=13.0),
            ],
            [_after("t1", "t2")],
        )

        report = build_observed_actor_acquisition_release_interval_projection(payload)

        self.assertEqual(report["observed_actor_acquisition_release_interval_candidate_count"], 1)
        row = report["observed_actor_acquisition_release_interval_candidates"][0]
        self.assertEqual(row["acquisition_to_release_start_interval_seconds"], 3.0)
        self.assertEqual(row["temporal_relation_state"], "AFTER_CONFIRMED")
        self.assertFalse(row["interval_is_physical_control_to_pass_time_truth"])
        self.assertFalse(row["interval_is_decision_speed_truth"])

    def test_same_time_unordered_never_becomes_zero_interval(self) -> None:
        payload = _base_payload(
            [
                _trace("t1", "RECOVERY", start=10.0),
                _trace("t2", "PASS", start=10.0),
            ],
            [
                {
                    **_after("t1", "t2"),
                    "relation_state": "SAME_TIME_UNORDERED",
                }
            ],
        )

        report = build_observed_actor_acquisition_release_interval_projection(payload)

        self.assertEqual(report["observed_actor_acquisition_release_interval_candidate_count"], 0)

    def test_different_actor_intervening_trace_breaks_chain(self) -> None:
        payload = _base_payload(
            [
                _trace("t1", "RECOVERY", actor="actor_a", start=10.0),
                _trace("tmid", "PASS", actor="actor_b", start=11.0),
                _trace("t2", "PASS", actor="actor_a", start=13.0),
            ],
            [_after("t1", "t2")],
        )

        report = build_observed_actor_acquisition_release_interval_projection(payload)

        self.assertEqual(report["observed_actor_acquisition_release_interval_candidate_count"], 0)
        self.assertEqual(report["rejection_reason_counts"].get("intervening_action_break"), 1)

    def test_same_actor_carry_can_remain_inside_candidate(self) -> None:
        payload = _base_payload(
            [
                _trace("t1", "INTERCEPTION", start=10.0),
                _trace("tmid", "CARRY", start=11.0),
                _trace("t2", "PASS", start=13.0),
            ],
            [_after("t1", "t2")],
        )

        report = build_observed_actor_acquisition_release_interval_projection(payload)

        self.assertEqual(report["observed_actor_acquisition_release_interval_candidate_count"], 1)
        row = report["observed_actor_acquisition_release_interval_candidates"][0]
        self.assertEqual(row["intervening_same_actor_retention_trace_ids"], ["tmid"])
        self.assertEqual(
            row["intervening_same_actor_retention_occurrence_candidate_ids"],
            ["occ_tmid"],
        )
        self.assertEqual(
            row["supporting_action_occurrence_candidate_ids"],
            ["occ_t1", "occ_t2", "occ_tmid"],
        )

    def test_later_acquisition_breaks_earlier_anchor_and_binds_nearest_anchor(self) -> None:
        payload = _base_payload(
            [
                _trace("t1", "RECOVERY", start=10.0),
                _trace("t2", "INTERCEPTION", start=12.0),
                _trace("t3", "PASS", start=14.0),
            ],
            [
                _after("t1", "t3"),
                _after("t2", "t3"),
            ],
        )

        report = build_observed_actor_acquisition_release_interval_projection(payload)

        self.assertEqual(report["observed_actor_acquisition_release_interval_candidate_count"], 1)
        row = report["observed_actor_acquisition_release_interval_candidates"][0]
        self.assertEqual(row["acquisition_trackable_action_trace_candidate_id"], "t2")
        self.assertEqual(row["acquisition_to_release_start_interval_seconds"], 2.0)

    def test_end_candidate_is_not_used_to_suppress_start_order(self) -> None:
        payload = _base_payload(
            [
                _trace("t1", "RECOVERY", start=10.0, end=100.0),
                _trace("t2", "PASS", start=11.0, end=12.0),
            ],
            [_after("t1", "t2")],
        )

        report = build_observed_actor_acquisition_release_interval_projection(payload)

        self.assertEqual(report["observed_actor_acquisition_release_interval_candidate_count"], 1)
        self.assertEqual(
            report["observed_actor_acquisition_release_interval_candidates"][0][
                "acquisition_to_release_start_interval_seconds"
            ],
            1.0,
        )

    def test_time_contract_not_admitted_fails_closed(self) -> None:
        payload = _base_payload([], [])
        payload["provider_time_contract_admission_status"] = "NOT_ADMITTED"

        report = build_observed_actor_acquisition_release_interval_projection(payload)

        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertIn("provider_time_contract_not_admitted", report["hard_block_hits"])


if __name__ == "__main__":
    unittest.main()
