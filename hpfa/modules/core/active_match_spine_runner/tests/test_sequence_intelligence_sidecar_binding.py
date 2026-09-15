from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hpfa.modules.core.active_match_spine_runner.src import orphan_capability_sidecars as sidecars


def _sequence_payload() -> dict:
    left = {
        "partial_order_occurrence_variant_id": "left",
        "time_layer_refs": ["left_l0", "left_l1", "left_l2"],
        "supporting_action_occurrence_candidate_ids": ["o1"],
        "node_records": [
            {
                "time_layer_ref": "left_l0",
                "action_family_candidates": ["RECOVERY"],
            },
            {
                "time_layer_ref": "left_l1",
                "action_family_candidates": ["PASS"],
            },
            {
                "time_layer_ref": "left_l2",
                "action_family_candidates": ["SHOT"],
            },
        ],
        "edge_relations": [
            {"relation": "BEFORE_CONFIRMED"},
            {"relation": "BEFORE_CONFIRMED"},
        ],
    }
    right = {
        "partial_order_occurrence_variant_id": "right",
        "time_layer_refs": ["right_l0", "right_l1", "right_l2"],
        "supporting_action_occurrence_candidate_ids": ["o2"],
        "node_records": [
            {
                "time_layer_ref": "right_l0",
                "action_family_candidates": ["RECOVERY"],
            },
            {
                "time_layer_ref": "right_l1",
                "action_family_candidates": ["PASS"],
            },
            {
                "time_layer_ref": "right_l2",
                "action_family_candidates": ["TURNOVER"],
            },
        ],
        "edge_relations": [
            {"relation": "BEFORE_CONFIRMED"},
            {"relation": "BEFORE_CONFIRMED"},
        ],
    }
    return {
        "partial_order_occurrence_variants": [left, right],
        "dependency_aware_partial_order_similarity_pairs": [
            {
                "partial_order_similarity_pair_id": "pair_1",
                "left_variant_ref": "left",
                "right_variant_ref": "right",
                "comparison_eligibility_state":
                    "COMPARABLE_FOR_MATCH_LOCAL_RECURRENCE_CANDIDATE_INDEPENDENCE_UNPROVEN",
                "comparison_eligible": True,
                "outcome_used_in_similarity_decision": False,
            }
        ],
        "dependency_aware_partial_order_similarity_status": "PASS",
        "outcome_used_in_similarity_decision": False,
        "safe_finding_handoff_professional_emit_allowed": False,
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sf_1",
                "professional_finding_emit_allowed": False,
                "evidence_sufficiency": {
                    "state": "INSUFFICIENT_FOR_PROFESSIONAL_EMIT",
                    "blocking_dimensions": ["INDEPENDENT_SUPPORT_NOT_ADMITTED"],
                },
                "forbidden_inference": ["CAUSALITY"],
            }
        ],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_variant_payload() -> dict:
    return {
        "status": "PASS",
        "grammar_stable_visible_outcome_variation_family_count": 1,
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "fam_1",
                "same_grammar_visible_outcome_variation_observed": True,
                "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "member_records": [
                    {
                        "variant_ref": "left",
                        "sequence_ref": "s1",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                    {
                        "variant_ref": "right",
                        "sequence_ref": "s2",
                        "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                    },
                ],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _occurrence_projection_payload() -> dict:
    return {
        "status": "PASS",
        "source_consequence_horizon": {
            "horizon_definition_state": "DECLARED_SOURCE_HORIZON",
            "horizon_basis": "FIXED_TIME_WITH_LAYER_CAP_VISIBLE_TRACE_SEARCH",
            "window_seconds": [5.0, 8.0, 12.0],
            "maximum_window_seconds": 12.0,
            "max_follow_up_time_layers": 3,
            "right_censoring_assessed": True,
        },
        "right_censoring_assessed": True,
        "no_visible_followup_is_failure": False,
        "followup_is_terminal_outcome_truth": False,
        "projection_is_causal_truth": False,
        "ensuing_terminal_support_is_causal_truth": False,
        "admitted_followup_horizon_sensitivity_is_terminal_outcome_truth": False,
        "occurrence_consequence_projections": [
            {
                "action_occurrence_candidate_id": "o1",
                "right_censoring_status": "NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
                "right_censoring_assessed": True,
                "right_censored": False,
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
                "admitted_followup_horizon_sensitivity_state": "STABLE_ACROSS_DECLARED_WINDOWS",
                "admitted_followup_horizon_sensitivity_tested": True,
                "admitted_followup_horizon_sensitive": False,
            },
            {
                "action_occurrence_candidate_id": "o2",
                "right_censoring_status": "NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
                "right_censoring_assessed": True,
                "right_censored": False,
                "consequence_signal_candidates": ["OPPONENT_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
                "admitted_followup_horizon_sensitivity_state": "STABLE_ACROSS_DECLARED_WINDOWS",
                "admitted_followup_horizon_sensitivity_tested": True,
                "admitted_followup_horizon_sensitive": False,
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _occurrence_state_payload() -> dict:
    return {
        "status": "PASS",
        "occurrence_state_transition_projections": [
            {
                "action_occurrence_candidate_id": "o1",
                "provider_context_candidates": [],
                "provider_direction_candidates": ["FORWARD"],
                "provider_progression_candidates": [],
                "provider_zone_candidates": ["FINAL_THIRD"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "adverse_consequence_candidates": [],
                "transition_class_candidates": ["VISIBLE_DIRECTIONAL_CONSEQUENCE_TRANSITION_CANDIDATE"],
                "support_candidates": ["VISIBLE_CONSEQUENCE_CANDIDATE_PRESENT"],
            },
            {
                "action_occurrence_candidate_id": "o2",
                "provider_context_candidates": [],
                "provider_direction_candidates": [],
                "provider_progression_candidates": [],
                "provider_zone_candidates": [],
                "primary_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
                "adverse_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
                "transition_class_candidates": ["VISIBLE_DIRECTIONAL_CONSEQUENCE_TRANSITION_CANDIDATE"],
                "support_candidates": ["VISIBLE_CONSEQUENCE_CANDIDATE_PRESENT"],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


class SequenceIntelligenceSidecarBindingTest(unittest.TestCase):
    def test_active_match_sidecar_writes_grammar_and_claim_contract_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / sidecars.SEQUENCE_OUTPUT).write_text(
                json.dumps(_sequence_payload()),
                encoding="utf-8",
            )
            with patch.object(
                sidecars.report_lite,
                "write_report",
                return_value={"status": "PASS", "engineering_evidence": {}},
            ), patch.object(
                sidecars,
                "run_metric_governance_bridge",
                return_value={"status": "SMOKE_PASS", "current_invocation_artifacts": []},
            ):
                report = sidecars.run_sidecars(output, output, output)

            grammar_path = output / sidecars.GRAMMAR_ALIGNMENT_OUTPUT
            claim_path = output / sidecars.ANALYST_OUTPUT_CLAIM_CONTRACT_OUTPUT
            self.assertTrue(grammar_path.is_file())
            self.assertTrue(claim_path.is_file())
            self.assertEqual(report["sequence_grammar_alignment_status"], "PASS")
            self.assertEqual(report["analyst_output_claim_contract_status"], "PASS")
            self.assertTrue(report["sequence_grammar_alignment_prerequisite_present"])
            self.assertTrue(report["analyst_output_claim_contract_prerequisite_present"])
            self.assertEqual(
                report["grammar_stable_variant_feature_delta_status"],
                "NOT_APPLICABLE_PREREQUISITE_MISSING",
            )
            self.assertFalse(report["grammar_stable_variant_feature_delta_prerequisite_present"])

            grammar = json.loads(grammar_path.read_text(encoding="utf-8"))
            claim = json.loads(claim_path.read_text(encoding="utf-8"))
            self.assertEqual(grammar["supported_sequence_grammar_alignment_count"], 1)
            self.assertEqual(claim["analyst_output_contract_count"], 1)
            self.assertFalse(claim["professional_emit_allowed"])
            self.assertFalse(claim["probability_language_allowed_from_raw_rate"])
            self.assertEqual(claim["canonical_event_count"], "UNKNOWN")
            self.assertEqual(claim["true_action_count"], "UNKNOWN")
            self.assertFalse(claim["production_release"])

            artifact_names = {Path(value).name for value in report["current_invocation_artifacts"]}
            self.assertIn(sidecars.GRAMMAR_ALIGNMENT_OUTPUT, artifact_names)
            self.assertIn(sidecars.ANALYST_OUTPUT_CLAIM_CONTRACT_OUTPUT, artifact_names)
            self.assertNotIn(sidecars.GRAMMAR_STABLE_VARIANT_FEATURE_DELTA_OUTPUT, artifact_names)

    def test_feature_delta_uses_existing_occurrence_surfaces_without_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / sidecars.SEQUENCE_OUTPUT).write_text(json.dumps(_sequence_payload()), encoding="utf-8")
            for name in (sidecars.TRACE_OUTPUT, sidecars.CONSEQUENCE_OUTPUT, sidecars.EVIDENCE_OUTPUT):
                (output / name).write_text("{}", encoding="utf-8")

            occurrence_projection = _occurrence_projection_payload()
            occurrence_state = _occurrence_state_payload()
            process_variant = _process_variant_payload()

            with patch.object(
                sidecars.report_lite,
                "write_report",
                return_value={"status": "PASS", "engineering_evidence": {}},
            ), patch.object(
                sidecars,
                "build_occurrence_consequence_projection",
                return_value=occurrence_projection,
            ), patch.object(
                sidecars,
                "write_occurrence_consequence_outputs",
                return_value={},
            ), patch.object(
                sidecars.spatial_transition,
                "build_spatial_transition_candidates",
                return_value={"status": "PASS"},
            ), patch.object(
                sidecars.spatial_transition,
                "write_outputs",
                return_value={},
            ), patch.object(
                sidecars.state_transition,
                "build_state_transition_dynamics",
                return_value={"status": "PASS"},
            ), patch.object(
                sidecars.state_transition,
                "write_outputs",
                return_value={},
            ), patch.object(
                sidecars,
                "build_occurrence_state_transition_projection",
                return_value=occurrence_state,
            ), patch.object(
                sidecars,
                "write_occurrence_state_transition_outputs",
                return_value={},
            ), patch.object(
                sidecars,
                "build_observable_process_variant_binding",
                return_value=process_variant,
            ), patch.object(
                sidecars,
                "run_metric_governance_bridge",
                return_value={"status": "SMOKE_PASS", "current_invocation_artifacts": []},
            ):
                report = sidecars.run_sidecars(output, output, output)

            delta_path = output / sidecars.GRAMMAR_STABLE_VARIANT_FEATURE_DELTA_OUTPUT
            self.assertTrue(delta_path.is_file())
            self.assertEqual(report["grammar_stable_variant_feature_delta_status"], "PASS")
            self.assertTrue(report["grammar_stable_variant_feature_delta_prerequisite_present"])

            delta = json.loads(delta_path.read_text(encoding="utf-8"))
            self.assertEqual(delta["grammar_stable_variant_feature_delta_record_count"], 1)
            family = delta["grammar_stable_variant_feature_delta_records"][0]
            context_tokens = {
                row["feature_token"] for row in family["context_feature_difference_candidates"]
            }
            consequence_tokens = {
                row["feature_token"] for row in family["consequence_feature_difference_candidates"]
            }
            self.assertIn("provider_direction_candidates:FORWARD", context_tokens)
            self.assertIn(
                "primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE",
                consequence_tokens,
            )
            self.assertTrue(family["admitted_followup_horizon_sensitivity_tested"])
            self.assertEqual(family["admitted_followup_horizon_sensitive_variant_count"], 0)
            self.assertTrue(family["right_censoring_assessed"])
            self.assertEqual(family["right_censored_variant_count"], 0)
            self.assertFalse(family["difference_is_failure_cause_truth"])
            self.assertFalse(family["difference_is_tactical_explanation"])
            self.assertFalse(delta["difference_rows_are_independent_evidence_votes"])

            artifact_names = {Path(value).name for value in report["current_invocation_artifacts"]}
            self.assertIn(sidecars.GRAMMAR_STABLE_VARIANT_FEATURE_DELTA_OUTPUT, artifact_names)

    def test_missing_sequence_output_does_not_fabricate_runtime_intelligence(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with patch.object(
                sidecars.report_lite,
                "write_report",
                return_value={"status": "PASS", "engineering_evidence": {}},
            ), patch.object(
                sidecars,
                "run_metric_governance_bridge",
                return_value={"status": "SMOKE_PASS", "current_invocation_artifacts": []},
            ):
                report = sidecars.run_sidecars(output, output, output)

            self.assertEqual(
                report["sequence_grammar_alignment_status"],
                "NOT_APPLICABLE_PREREQUISITE_MISSING",
            )
            self.assertEqual(
                report["grammar_stable_variant_feature_delta_status"],
                "NOT_APPLICABLE_PREREQUISITE_MISSING",
            )
            self.assertEqual(
                report["analyst_output_claim_contract_status"],
                "NOT_APPLICABLE_PREREQUISITE_MISSING",
            )
            self.assertFalse(report["sequence_grammar_alignment_prerequisite_present"])
            self.assertFalse(report["grammar_stable_variant_feature_delta_prerequisite_present"])
            self.assertFalse(report["analyst_output_claim_contract_prerequisite_present"])


if __name__ == "__main__":
    unittest.main()