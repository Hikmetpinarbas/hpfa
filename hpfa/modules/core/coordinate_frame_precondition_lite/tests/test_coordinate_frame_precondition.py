from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from coordinate_frame_precondition import (  # noqa: E402
    build_coordinate_frame_precondition,
    validate_out,
    write_outputs,
)

BINDING = "msb_generic"
TEAM_A = "team_a"
TEAM_B = "team_b"


def provider_payload(include_goalkeeper: bool = True, exact: bool = True) -> dict:
    rows = []
    if include_goalkeeper:
        rows.append(
            {
                "record_id": "p_goalkeeper_goal_kick",
                "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
                "normalized_label": "goal kicks",
                "mapping_status": (
                    "EXACT_REVIEWED_CANDIDATE"
                    if exact
                    else "TOKEN_FALLBACK_REVIEW_REQUIRED"
                ),
                "restart_type_candidate": "GOAL_KICK",
            }
        )
    rows.append(
        {
            "record_id": "p_team_goal_kick",
            "source_role": "TEAM_SURFACE_CANDIDATE",
            "normalized_label": "goal kicks",
            "mapping_status": "EXACT_REVIEWED_CANDIDATE",
            "restart_type_candidate": "GOAL_KICK",
        }
    )
    return {
        "module_id": "provider_label_value_semantics_lite_v1",
        "module_status": "PASS",
        "provider_label_records": rows,
        "provider_label_record_count": len(rows),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def bundle(
    bundle_id: str,
    team: str,
    period: str,
    x: float,
    family: str,
    role: str,
    labels: list[str],
) -> dict:
    return {
        "action_bundle_candidate_id": bundle_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": (
            "actor" if role != "TEAM_SURFACE_CANDIDATE" else None
        ),
        "period_candidate": period,
        "start_candidate": "1",
        "end_candidate": "2",
        "pos_x_candidate": x,
        "pos_y_candidate": 34,
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": family,
        "normalized_labels": labels,
        "bundle_status": "PASS",
    }


def action_payload(
    *,
    goal_x: float = 4.0,
    include_goalkeeper: bool = True,
    include_team_reflections: bool = True,
) -> dict:
    rows = []
    for team in (TEAM_A, TEAM_B):
        for period in ("1", "2"):
            if include_goalkeeper:
                rows.extend(
                    [
                        bundle(
                            f"gk_{team}_{period}_1",
                            team,
                            period,
                            goal_x,
                            "RESTART",
                            "GOALKEEPER_SURFACE_CANDIDATE",
                            ["goal kicks"],
                        ),
                        bundle(
                            f"gk_{team}_{period}_2",
                            team,
                            period,
                            goal_x + 1,
                            "RESTART",
                            "GOALKEEPER_SURFACE_CANDIDATE",
                            ["goal kicks"],
                        ),
                    ]
                )
            if include_team_reflections:
                rows.append(
                    bundle(
                        f"team_gk_{team}_{period}",
                        team,
                        period,
                        95,
                        "RESTART",
                        "TEAM_SURFACE_CANDIDATE",
                        ["goal kicks"],
                    )
                )
            rows.extend(
                [
                    bundle(
                        f"clr_{team}_{period}_1",
                        team,
                        period,
                        20,
                        "CLEARANCE",
                        "PLAYER_SURFACE_CANDIDATE",
                        ["clearance"],
                    ),
                    bundle(
                        f"clr_{team}_{period}_2",
                        team,
                        period,
                        25,
                        "CLEARANCE",
                        "PLAYER_SURFACE_CANDIDATE",
                        ["clearance"],
                    ),
                    bundle(
                        f"clr_{team}_{period}_3",
                        team,
                        period,
                        30,
                        "CLEARANCE",
                        "PLAYER_SURFACE_CANDIDATE",
                        ["clearance"],
                    ),
                ]
            )
    return {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "action_bundle_candidates": rows,
        "action_bundle_candidate_count": len(rows),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def selected_event_payload(
    *, bounds: str = "PASS_CANDIDATE_BOUNDS"
) -> dict:
    directions = []
    for team in (TEAM_A, TEAM_B):
        for period in ("1", "2"):
            directions.append(
                {
                    "team_identity_candidate_id": team,
                    "period_candidate": period,
                    "shot_support_node_count": 4,
                    "attack_direction_candidate": (
                        "ATTACK_TOWARD_HIGH_X_CANDIDATE"
                    ),
                    "attack_direction_support_status": (
                        "PASS_SHOT_CONCENTRATION_CANDIDATE"
                    ),
                }
            )
    return {
        "module_id": "selected_event_consequence_surface_lite_v1",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "coordinate_frame_candidate": {
            "coordinate_scale_candidate": "PROVIDER_105X68_SCALE_CANDIDATE",
            "coordinate_bounds_status": bounds,
            "pitch_length_candidate": 105.0,
            "pitch_width_candidate": 68.0,
            "team_period_attack_direction_candidates": directions,
        },
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_multi_anchor_frame_candidate_passes_and_ignores_team_reflections():
    result = build_coordinate_frame_precondition(
        provider_payload(), action_payload(), selected_event_payload()
    )
    assert (
        result["coordinate_frame_candidate"]
        == "TEAM_ATTACK_NORMALIZED_POSITIVE_X_CANDIDATE"
    )
    assert result["progression_metric_recheck_allowed"] is True
    assert result["multi_anchor_pass_group_count"] == 4
    assert result["goalkeeper_goal_kick_anchor_count"] == 8
    assert all(
        row["goalkeeper_goal_kick_normalized_x_median"] < 0.1
        for row in result["team_period_coordinate_frame_candidates"]
    )
    assert all(
        row["clearance_relation_to_primary"]
        == "AGREES_WITH_PRIMARY_DIRECTION"
        for row in result["team_period_coordinate_frame_candidates"]
    )


def test_goal_kick_team_reflections_cannot_open_direction_gate():
    result = build_coordinate_frame_precondition(
        provider_payload(),
        action_payload(
            include_goalkeeper=False,
            include_team_reflections=True,
        ),
        selected_event_payload(),
    )
    assert result["goalkeeper_goal_kick_anchor_count"] == 0
    assert result["progression_metric_recheck_allowed"] is False
    assert result["multi_anchor_pass_group_count"] == 0


def test_conflicting_goal_kick_and_shot_anchors_block_recheck():
    result = build_coordinate_frame_precondition(
        provider_payload(),
        action_payload(goal_x=100),
        selected_event_payload(),
    )
    assert result["multi_anchor_conflict_group_count"] == 4
    assert result["progression_metric_recheck_allowed"] is False
    assert result["coordinate_frame_candidate"] == "FRAME_UNRESOLVED"


def test_non_exact_provider_goal_kick_semantics_do_not_open_gate():
    result = build_coordinate_frame_precondition(
        provider_payload(exact=False),
        action_payload(),
        selected_event_payload(),
    )
    assert result["goalkeeper_goal_kick_anchor_count"] == 0
    assert result["progression_metric_recheck_allowed"] is False
    assert (
        "goalkeeper_goal_kick_exact_label_lineage_unavailable"
        in result["review_hits"]
    )


def test_bounds_failure_blocks_recheck_even_with_anchor_agreement():
    result = build_coordinate_frame_precondition(
        provider_payload(),
        action_payload(),
        selected_event_payload(
            bounds="OUTSIDE_SUPPORTED_SCALE_REVIEW_REQUIRED"
        ),
    )
    assert result["progression_metric_recheck_allowed"] is False
    assert (
        "coordinate_scale_or_bounds_precondition_not_met"
        in result["review_hits"]
    )


def test_binding_mismatch_fails_closed():
    actions = action_payload()
    actions["match_surface_binding_id"] = "other_binding"
    result = build_coordinate_frame_precondition(
        provider_payload(), actions, selected_event_payload()
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "match_surface_binding_mismatch_or_missing" in result["hard_block_hits"]
    assert result["progression_metric_recheck_allowed"] is False


def test_claim_boundaries_remain_closed():
    result = build_coordinate_frame_precondition(
        provider_payload(), action_payload(), selected_event_payload()
    )
    assert result["attack_direction_is_validated_truth"] is False
    assert result["coordinate_frame_is_validated_provider_truth"] is False
    assert result["clearance_is_primary_direction_anchor"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_nested_phone_output_rejected(tmp_path: Path):
    with pytest.raises(
        ValueError, match="nested_phone_output_directory_rejected"
    ):
        validate_out(tmp_path / "HPFA" / "nested")


def test_outputs_written(tmp_path: Path):
    result = build_coordinate_frame_precondition(
        provider_payload(), action_payload(), selected_event_payload()
    )
    paths = write_outputs(result, tmp_path)
    assert all(path.exists() for path in paths.values())
    stored = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert stored["module_id"] == "coordinate_frame_precondition_lite_v1"


def test_no_sample_match_identity_leak():
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src").glob("*.py")
    )
    forbidden = [
        "Australia",
        "Turkey",
        "World Cup",
        "Galatasaray",
        "Juventus",
        "6935",
        "77798",
    ]
    assert not any(item in text for item in forbidden)
