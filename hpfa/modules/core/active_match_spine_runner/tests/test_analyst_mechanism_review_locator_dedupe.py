import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analyst_mechanism_review import _clip_locator_lines


def test_same_focus_occurrence_is_rendered_once_without_time_window() -> None:
    record = {
        "source_process_variant_family_ref": "family_1",
        "team_identity_candidate_ids": ["team_1"],
        "period_candidates": ["1"],
    }
    process_variants = {
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "member_variant_refs": ["vf", "vs1", "vs2"],
            }
        ]
    }
    sequence = {
        "partial_order_occurrence_variants": [
            {"partial_order_occurrence_variant_id": "vf", "sequence_ref": "seq_f"},
            {"partial_order_occurrence_variant_id": "vs1", "sequence_ref": "seq_s1"},
            {"partial_order_occurrence_variant_id": "vs2", "sequence_ref": "seq_s2"},
        ],
        "first_supported_branch_divergence_candidates": [
            {
                "team_identity_candidate_id": "team_1",
                "period_candidate": 1,
                "shared_anchor_time_candidate": 118.0,
                "branch_profiles": [
                    {
                        "branch_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 122.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_f"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "focus", "primary_family_candidate": "PASS"}
                        ],
                    },
                    {
                        "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 121.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_s1"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "other_1", "primary_family_candidate": "PASS"}
                        ],
                    },
                ],
            },
            {
                "team_identity_candidate_id": "team_1",
                "period_candidate": 1,
                "shared_anchor_time_candidate": 120.0,
                "branch_profiles": [
                    {
                        "branch_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 122.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_f"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "focus", "primary_family_candidate": "PASS"}
                        ],
                    },
                    {
                        "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 124.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_s1"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "other_1", "primary_family_candidate": "PASS"}
                        ],
                    },
                    {
                        "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 125.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_s2"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "other_2", "primary_family_candidate": "PASS"}
                        ],
                    },
                ],
            },
            {
                "team_identity_candidate_id": "team_1",
                "period_candidate": 1,
                "shared_anchor_time_candidate": 136.0,
                "branch_profiles": [
                    {
                        "branch_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 140.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_f"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "focus", "primary_family_candidate": "PASS"}
                        ],
                    },
                    {
                        "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 141.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_s1"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "other_1", "primary_family_candidate": "PASS"}
                        ],
                    },
                ],
            },
        ],
    }
    actors = {"focus": "Focus Player", "other_1": "Other One", "other_2": "Other Two"}

    lines = _clip_locator_lines(
        record,
        "focus",
        actors,
        sequence,
        process_variants,
        limit=3,
    )

    assert len(lines) == 2
    assert sum("02:02 Focus Player FAILURE PASS" in line for line in lines) == 1
    assert any("shared_anchor=02:00" in line and "02:05 Other Two SUCCESS PASS" in line for line in lines)
    assert any("02:20 Focus Player FAILURE PASS" in line for line in lines)
