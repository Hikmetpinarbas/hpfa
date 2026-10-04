from __future__ import annotations

import unittest

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.supported_sequence_grammar_alignment_projection import (
    build_supported_sequence_grammar_alignment,
)


def _variant(variant_id, layers, outcomes=None):
    node_records = []
    edge_relations = []
    time_layer_refs = []
    for index, families in enumerate(layers):
        layer_ref = f"{variant_id}_l{index}"
        time_layer_refs.append(layer_ref)
        node_records.append({
            "trace_ref": f"{variant_id}_t{index}",
            "occurrence_refs": [f"{variant_id}_o{index}"],
            "time_layer_ref": layer_ref,
            "time_candidate": float(index + 1),
            "action_family_candidates": list(families),
            "outcome_candidate": (outcomes or [""] * len(layers))[index] or None,
            "same_time_peer_count": max(0, len(families) - 1),
            "internal_same_time_order": "SAME_TIME_UNORDERED" if len(families) > 1 else "NOT_APPLICABLE",
        })
        if index:
            edge_relations.append({
                "from_layer_ref": time_layer_refs[index - 1],
                "to_layer_ref": layer_ref,
                "relation": "BEFORE_CONFIRMED",
                "relation_is_football_chronology": True,
            })
    return {
        "partial_order_occurrence_variant_id": variant_id,
        "time_layer_refs": time_layer_refs,
        "node_records": node_records,
        "edge_relations": edge_relations,
        "outcome_signature": [
            {"outcome_candidate": value, "count": 1}
            for value in (outcomes or [])
            if value
        ],
    }


def _payload(left, right, **overrides):
    payload = {
        "partial_order_occurrence_variants": [left, right],
        "dependency_aware_partial_order_similarity_pairs": [{
            "partial_order_similarity_pair_id": "pair_1",
            "left_variant_ref": left["partial_order_occurrence_variant_id"],
            "right_variant_ref": right["partial_order_occurrence_variant_id"],
            "comparison_eligibility_state":
                "COMPARABLE_FOR_MATCH_LOCAL_RECURRENCE_CANDIDATE_INDEPENDENCE_UNPROVEN",
            "comparison_eligible": True,
            "outcome_used_in_similarity_decision": False,
        }],
        "dependency_aware_partial_order_similarity_status": "PASS",
        "outcome_used_in_similarity_decision": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    payload.update(overrides)
    return payload


class SupportedSequenceGrammarAlignmentTest(unittest.TestCase):
    def test_common_core_and_first_divergence_are_exposed(self):
        left = _variant(
            "left",
            [["RECOVERY"], ["PASS"], ["PROGRESSION"], ["SHOT"]],
        )
        right = _variant(
            "right",
            [["RECOVERY"], ["PASS"], ["TURNOVER"], ["DEAD_BALL"]],
        )
        out = build_supported_sequence_grammar_alignment(_payload(left, right))
        self.assertEqual(out["status"], "PASS")
        row = out["supported_sequence_grammar_alignments"][0]
        self.assertEqual(
            row["supported_common_core_tokens"][:2],
            ["LAYER[RECOVERY]", "LAYER[PASS]"],
        )
        self.assertEqual(
            row["first_supported_grammar_divergence"]["operation"],
            "SUBSTITUTE",
        )
        self.assertFalse(row["lcs_is_causal_backbone"])
        self.assertFalse(row["grammar_alignment_is_tactical_equivalence_truth"])

    def test_same_time_member_order_does_not_change_layer_token(self):
        left = _variant(
            "left",
            [["RECOVERY"], ["PASS", "CARRY"], ["SHOT"]],
        )
        right = _variant(
            "right",
            [["RECOVERY"], ["CARRY", "PASS"], ["SHOT"]],
        )
        out = build_supported_sequence_grammar_alignment(_payload(left, right))
        row = out["supported_sequence_grammar_alignments"][0]
        self.assertEqual(row["left_layer_tokens"], row["right_layer_tokens"])
        self.assertEqual(row["grammar_edit_distance"], 0.0)
        self.assertTrue(row["same_time_layer_token_members_are_unordered"])

    def test_outcome_is_excluded_from_alignment(self):
        left = _variant(
            "left",
            [["RECOVERY"], ["PASS"], ["SHOT"]],
            ["A", "B", "SUCCESS"],
        )
        right = _variant(
            "right",
            [["RECOVERY"], ["PASS"], ["SHOT"]],
            ["X", "Y", "FAILURE"],
        )
        out = build_supported_sequence_grammar_alignment(_payload(left, right))
        row = out["supported_sequence_grammar_alignments"][0]
        self.assertEqual(row["grammar_edit_distance"], 0.0)
        self.assertTrue(row["outcome_excluded_from_alignment"])

    def test_non_comparable_pair_is_not_aligned(self):
        left = _variant("left", [["RECOVERY"], ["PASS"]])
        right = _variant("right", [["RECOVERY"], ["PASS"]])
        payload = _payload(left, right)
        payload["dependency_aware_partial_order_similarity_pairs"][0][
            "comparison_eligible"
        ] = False
        out = build_supported_sequence_grammar_alignment(payload)
        self.assertEqual(out["supported_sequence_grammar_alignment_count"], 0)

    def test_order_indeterminate_is_review_not_fabricated_order(self):
        left = _variant("left", [["RECOVERY"], ["PASS"]])
        right = _variant("right", [["RECOVERY"], ["PASS"]])
        left["edge_relations"][0]["relation"] = "ORDER_INDETERMINATE"
        out = build_supported_sequence_grammar_alignment(_payload(left, right))
        self.assertEqual(out["status"], "REVIEW_REQUIRED")
        self.assertEqual(out["supported_sequence_grammar_alignment_count"], 0)
        self.assertTrue(
            any(
                "grammar_alignment_order_indeterminate" in hit
                for hit in out["review_hits"]
            )
        )

    def test_outcome_similarity_leakage_fails_closed(self):
        left = _variant("left", [["RECOVERY"], ["PASS"]])
        right = _variant("right", [["RECOVERY"], ["PASS"]])
        out = build_supported_sequence_grammar_alignment(
            _payload(
                left,
                right,
                outcome_used_in_similarity_decision=True,
            )
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["supported_sequence_grammar_alignment_count"], 0)

    def test_truth_counts_remain_unknown(self):
        left = _variant("left", [["RECOVERY"], ["PASS"]])
        right = _variant("right", [["RECOVERY"], ["PASS"]])
        out = build_supported_sequence_grammar_alignment(_payload(left, right))
        self.assertEqual(out["canonical_event_count"], "UNKNOWN")
        self.assertEqual(out["true_action_count"], "UNKNOWN")
        self.assertFalse(out["production_release"])

    def test_no_sample_match_identity_leak(self):
        left = _variant("left", [["RECOVERY"], ["PASS"]])
        right = _variant("right", [["RECOVERY"], ["PASS"]])
        out = build_supported_sequence_grammar_alignment(_payload(left, right))
        serialized = repr(out).lower()
        for token in ("sporting", "roma", "fenerbah", "galatasaray"):
            self.assertNotIn(token, serialized)


if __name__ == "__main__":
    unittest.main()
