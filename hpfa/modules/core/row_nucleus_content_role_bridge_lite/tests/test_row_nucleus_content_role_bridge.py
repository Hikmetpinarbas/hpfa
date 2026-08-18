from __future__ import annotations

from hpfa.modules.core.row_nucleus_content_role_bridge_lite.src import (
    row_nucleus_content_role_bridge as bridge,
)


def _role_resolution(role: str) -> dict[str, object]:
    return {
        "resolved_short_role": role,
        "resolved_source_role": f"{role}_SURFACE_CANDIDATE",
        "resolution_status": "ROLE_CANDIDATE_ADMITTED",
        "resolution_reasons": ["CONTENT_EVIDENCE"],
    }


def test_role_map_uses_content_admission_not_filename() -> None:
    report = {
        "files": [
            {
                "extension": ".csv",
                "relative_path": "ambiguous_a.csv",
                "resolution": _role_resolution("PLAYER"),
            },
            {
                "extension": ".xml",
                "relative_path": "ambiguous_b.xml",
                "resolution": _role_resolution("GOALKEEPER"),
            },
            {
                "extension": ".xlsx",
                "relative_path": "aggregate.xlsx",
                "resolution": _role_resolution("PLAYER"),
            },
        ]
    }
    role_map, missing = bridge.role_map_from_report(report)
    assert role_map == {
        "ambiguous_a.csv": "PLAYER",
        "ambiguous_b.xml": "GOALKEEPER",
    }
    assert missing == []


def test_role_map_preserves_unresolved_row_surface() -> None:
    report = {
        "files": [
            {
                "extension": ".csv",
                "relative_path": "surface.csv",
                "resolution": {
                    "resolved_short_role": "UNRESOLVED",
                    "resolution_status": "REVIEW_REQUIRED",
                },
            }
        ]
    }
    role_map, missing = bridge.role_map_from_report(report)
    assert role_map == {}
    assert missing == ["surface.csv"]


def test_build_nuclei_from_rows_keeps_cross_role_candidates_separate() -> None:
    base = {
        "provider_row_id": "001",
        "start": "1.0",
        "end": "2.0",
        "code": "x",
        "team": "candidate_team",
        "action": "candidate_action",
        "half": "1",
        "pos_x": "10",
        "pos_y": "20",
        "_source_format": "csv",
        "_source_file": "ambiguous.csv",
        "_source_row_index": 1,
    }
    rows = [
        {**base, "_source_role": "PLAYER"},
        {**base, "_source_role": "TEAM", "_source_row_index": 2},
    ]
    nuclei, stats = bridge._build_nuclei_from_rows(
        rows,
        {
            "unique_surface_file_count": 1,
            "duplicate_surface_file_reflection_count": 0,
            "surface_row_count": 2,
            "xlsx_file_count": 0,
            "xlsx_used_for_row_nucleus_identity": False,
            "source_role_override_applied_surface_file_count": 1,
            "source_role_override_missing_surface_file_count": 0,
            "filename_role_used_for_nucleus_grouping": False,
        },
    )
    assert len(nuclei) == 2
    assert {item["source_role"] for item in nuclei} == {"PLAYER", "TEAM"}
    assert all(item["filename_role_used_for_nucleus_grouping"] is False for item in nuclei)
    assert stats["missing_provider_id_surface_row_count"] == 0


def test_bridge_claim_boundaries_are_locked() -> None:
    rows = [
        {
            "provider_row_id": "a",
            "start": "1",
            "end": "2",
            "code": "x",
            "team": "candidate_team",
            "action": "candidate_action",
            "half": "1",
            "pos_x": "1",
            "pos_y": "1",
            "_source_format": "csv",
            "_source_file": "a.csv",
            "_source_row_index": 1,
            "_source_role": "PLAYER",
        }
    ]
    nuclei, _ = bridge._build_nuclei_from_rows(
        rows,
        {
            "unique_surface_file_count": 1,
            "duplicate_surface_file_reflection_count": 0,
            "surface_row_count": 1,
            "xlsx_file_count": 0,
            "xlsx_used_for_row_nucleus_identity": False,
            "source_role_override_applied_surface_file_count": 1,
            "source_role_override_missing_surface_file_count": 0,
            "filename_role_used_for_nucleus_grouping": False,
        },
    )
    assert nuclei[0]["row_nucleus_is_canonical_event"] is False
    assert nuclei[0]["physical_action_identity_truth"] is False
    assert nuclei[0]["validated_event_identity"] is False
