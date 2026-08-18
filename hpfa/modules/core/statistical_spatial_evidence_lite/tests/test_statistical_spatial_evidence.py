from __future__ import annotations

import math

from hpfa.modules.core.statistical_spatial_evidence_lite.src import (
    statistical_spatial_evidence as spatial,
)


def _nucleus(
    nucleus_id: str,
    *,
    x: float | None,
    y: float | None,
    team: str | None = "team_candidate",
    role: str = "PLAYER",
    status: str = "PASS",
    code: str = "candidate_action",
    action: str = "candidate_action",
) -> dict[str, object]:
    return {
        "row_nucleus_candidate_id": nucleus_id,
        "status": status,
        "source_role": role,
        "resolved_visible_fields": {
            "pos_x": None if x is None else str(x),
            "pos_y": None if y is None else str(y),
            "team": team,
            "code": code,
            "action": action,
        },
    }


def _bridge_report(nuclei: list[dict[str, object]], status: str = "PASS") -> dict[str, object]:
    return {
        "module_id": "row_nucleus_content_role_bridge_lite_v1",
        "status": status,
        "content_role_resolution_status": "PASS",
        "row_nuclei": nuclei,
    }


def test_entropy_uniform_four_cells_is_two_bits() -> None:
    result = spatial._grid_distribution(
        [(10, 10), (40, 10), (10, 40), (40, 40)],
        pitch_length=60,
        pitch_width=60,
        columns=2,
        rows=2,
    )
    assert result["shannon_entropy_bits"] == 2.0
    assert result["normalized_grid_entropy"] == 1.0
    assert result["effective_cell_count"] == 4.0
    assert result["concentration_hhi"] == 0.25


def test_entropy_concentrated_points_is_zero() -> None:
    result = spatial._grid_distribution(
        [(1, 1), (2, 2), (3, 3)],
        pitch_length=100,
        pitch_width=100,
        columns=2,
        rows=2,
    )
    assert result["shannon_entropy_bits"] == 0.0
    assert result["effective_cell_count"] == 1.0
    assert result["concentration_hhi"] == 1.0


def test_grid_boundary_maps_pitch_edge_to_last_cell() -> None:
    assert spatial._grid_cell(
        105.0,
        68.0,
        pitch_length=105.0,
        pitch_width=68.0,
        columns=16,
        rows=12,
    ) == (15, 11)


def test_raw_x_thirds_are_absolute_not_team_relative() -> None:
    assert spatial._raw_x_third(0.0, 105.0) == "RAW_X_THIRD_1"
    assert spatial._raw_x_third(35.0, 105.0) == "RAW_X_THIRD_2"
    assert spatial._raw_x_third(70.0, 105.0) == "RAW_X_THIRD_3"


def test_team_candidate_prefers_direct_visible_field() -> None:
    value, source = spatial._team_candidate(
        "PLAYER",
        {"team": "A", "code": "ignored", "action": "ignored"},
    )
    assert value == "A"
    assert source == "DIRECT_VISIBLE_TEAM_FIELD_CANDIDATE"


def test_team_surface_candidate_can_be_extracted_from_exact_code_suffix() -> None:
    value, source = spatial._team_candidate(
        "TEAM",
        {"team": "", "code": "A - Positional attack", "action": "Positional attack"},
    )
    assert value == "A"
    assert source == "TEAM_CODE_PREFIX_CANDIDATE"


def test_team_code_prefix_is_not_guessed_without_exact_action_suffix() -> None:
    value, source = spatial._team_candidate(
        "TEAM",
        {"team": "", "code": "A - Something else", "action": "Positional attack"},
    )
    assert value is None
    assert source == "TEAM_CANDIDATE_UNRESOLVED"


def test_groups_never_mix_source_roles_or_team_candidates() -> None:
    report = spatial.build_from_bridge_report(
        _bridge_report(
            [
                _nucleus("a", x=10, y=10, team="A", role="PLAYER"),
                _nucleus("b", x=20, y=20, team="B", role="PLAYER"),
                _nucleus(
                    "c",
                    x=30,
                    y=30,
                    team=None,
                    role="TEAM",
                    code="A - candidate_action",
                    action="candidate_action",
                ),
            ]
        ),
        pitch_length=105.0,
        pitch_width=68.0,
        frame_provenance="TEST_FRAME_CANDIDATE",
    )
    keys = {
        (item["source_role"], item["team_candidate"])
        for item in report["spatial_distribution_candidates"]
    }
    assert keys == {("PLAYER", "A"), ("PLAYER", "B"), ("TEAM", "A")}
    assert report["spatial_distribution_candidate_group_count"] == 3
    team_group = next(
        item
        for item in report["spatial_distribution_candidates"]
        if item["source_role"] == "TEAM"
    )
    assert team_group["team_candidate_derivation_counts"] == {
        "TEAM_CODE_PREFIX_CANDIDATE": 1
    }


def test_unresolved_team_candidate_is_excluded_not_pooled() -> None:
    report = spatial.build_from_bridge_report(
        _bridge_report(
            [
                _nucleus(
                    "a",
                    x=10,
                    y=10,
                    team=None,
                    role="TEAM",
                    code="unresolved",
                    action="candidate_action",
                )
            ]
        ),
        pitch_length=105.0,
        pitch_width=68.0,
        frame_provenance="TEST_FRAME_CANDIDATE",
    )
    assert report["eligible_coordinate_nucleus_count"] == 0
    assert report["excluded_missing_team_candidate_nucleus_count"] == 1
    assert report["spatial_distribution_candidates"] == []
    assert "team_candidate_unresolved_nuclei_excluded" in report["review_hits"]
    assert report["status"] == "REVIEW_REQUIRED"


def test_review_required_nuclei_do_not_enter_spatial_denominator() -> None:
    report = spatial.build_from_bridge_report(
        _bridge_report(
            [
                _nucleus("a", x=10, y=10, status="PASS"),
                _nucleus("b", x=20, y=20, status="REVIEW_REQUIRED"),
            ]
        ),
        pitch_length=105.0,
        pitch_width=68.0,
        frame_provenance="TEST_FRAME_CANDIDATE",
    )
    assert report["eligible_coordinate_nucleus_count"] == 1
    assert report["excluded_review_required_nucleus_count"] == 1


def test_out_of_frame_coordinate_is_excluded_and_reviewed() -> None:
    report = spatial.build_from_bridge_report(
        _bridge_report([_nucleus("a", x=106, y=20)]),
        pitch_length=105.0,
        pitch_width=68.0,
        frame_provenance="TEST_FRAME_CANDIDATE",
    )
    assert report["eligible_coordinate_nucleus_count"] == 0
    assert report["excluded_out_of_frame_nucleus_count"] == 1
    assert report["status"] == "REVIEW_REQUIRED"


def test_invalid_frame_fails_deterministically() -> None:
    try:
        spatial.build_from_bridge_report(
            _bridge_report([]),
            pitch_length=0.0,
            pitch_width=68.0,
            frame_provenance="TEST_FRAME_CANDIDATE",
        )
    except ValueError as exc:
        assert str(exc) == "invalid_coordinate_frame_dimensions"
    else:
        raise AssertionError("invalid frame must fail")


def test_method_registry_defers_unadmitted_inference_families() -> None:
    statuses = {
        item["method"]: item["status"]
        for item in spatial.METHOD_ADMISSION_REGISTRY
    }
    assert statuses["SPATIAL_GRID_SHANNON_ENTROPY"] == "IMPLEMENTED_CANDIDATE_ONLY"
    assert statuses["BIVARIATE_POISSON_DIXON_COLES"] == "DEFERRED"
    assert statuses["KAPLAN_MEIER_COX"] == "DEFERRED"
    assert statuses["PCA_FACTOR_ANALYSIS"] == "DEFERRED"
    assert statuses["BETA_BINOMIAL_BAYESIAN_SHRINKAGE"] == "DEFERRED"


def test_claim_boundaries_remain_closed() -> None:
    report = spatial.build_from_bridge_report(
        _bridge_report([_nucleus("a", x=10, y=10)]),
        pitch_length=105.0,
        pitch_width=68.0,
        frame_provenance="TEST_FRAME_CANDIDATE",
    )
    assert report["team_candidate_is_validated_identity"] is False
    assert report["spatial_point_is_canonical_event"] is False
    assert report["row_nucleus_is_physical_action"] is False
    assert report["team_shape_truth"] is False
    assert report["pitch_control_truth"] is False
    assert report["dominance_truth"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["production_release"] is False
    assert math.isfinite(
        report["spatial_distribution_candidates"][0][
            "coordinate_centroid_candidate"
        ]["x"]
    )
