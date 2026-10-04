import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analyst_mechanism_review import _clip_locator_lines


def test_one_divergence_card_is_not_rendered_twice_when_focus_actor_is_on_both_branches() -> None:
    record = {
        "source_process_variant_family_ref": "family_1",
        "team_identity_candidate_ids": ["team_1"],
        "period_candidates": ["2"],
    }
    process_variants = {
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "member_variant_refs": ["vf", "vs"],
            }
        ]
    }
    sequence = {
        "partial_order_occurrence_variants": [
            {"partial_order_occurrence_variant_id": "vf", "sequence_ref": "seq_f"},
            {"partial_order_occurrence_variant_id": "vs", "sequence_ref": "seq_s"},
        ],
        "first_supported_branch_divergence_candidates": [
            {
                "team_identity_candidate_id": "team_1",
                "period_candidate": 2,
                "shared_anchor_time_candidate": 3161.0,
                "branch_profiles": [
                    {
                        "branch_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 3171.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_f"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "focus", "primary_family_candidate": "PASS"}
                        ],
                    },
                    {
                        "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 3166.0,
                        "supporting_visible_sequence_candidate_ids": ["seq_s"],
                        "semantic_profiles": [
                            {"actor_identity_candidate_id": "focus", "primary_family_candidate": "PASS"}
                        ],
                    },
                ],
            }
        ],
    }

    lines = _clip_locator_lines(
        record,
        "focus",
        {"focus": "Focus Player"},
        sequence,
        process_variants,
        limit=3,
    )

    assert len(lines) == 1
    assert lines[0].count("Focus Player") == 2
    assert "shared_anchor=52:41" in lines[0]
