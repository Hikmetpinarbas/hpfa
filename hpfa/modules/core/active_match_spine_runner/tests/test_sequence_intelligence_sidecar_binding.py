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
                report["analyst_output_claim_contract_status"],
                "NOT_APPLICABLE_PREREQUISITE_MISSING",
            )
            self.assertFalse(report["sequence_grammar_alignment_prerequisite_present"])
            self.assertFalse(report["analyst_output_claim_contract_prerequisite_present"])


if __name__ == "__main__":
    unittest.main()
