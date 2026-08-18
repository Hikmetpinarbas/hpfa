from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.content_source_role_resolver_lite.src import (
    content_source_role_resolver as resolver,
)


def _registry() -> dict[str, list[set[str]]]:
    return {
        resolver.normalize_label("Shots saved"): [{"GOALKEEPER"}],
        resolver.normalize_label("Outfield marker"): [{"PLAYER", "TEAM"}],
        resolver.normalize_label("Goalkeeper or team marker"): [{"GOALKEEPER", "TEAM"}],
    }


def test_filename_support_never_admits_role() -> None:
    role, status, reasons = resolver.admit_from_evidence(
        structural_roles={"PLAYER", "GOALKEEPER"},
        structural_admission=None,
        semantic_votes={"PLAYER": 0, "GOALKEEPER": 0, "TEAM": 0},
        content_support=[],
    )
    assert role == "UNRESOLVED"
    assert status == "REVIEW_REQUIRED"
    assert reasons == ["CONTENT_ROLE_EVIDENCE_INSUFFICIENT"]


def test_reviewed_role_semantics_narrows_direct_team_surface_to_goalkeeper() -> None:
    votes = resolver.label_role_votes(
        ["Shots saved"], _registry(), {"PLAYER", "GOALKEEPER"}
    )
    assert votes["GOALKEEPER"] == 1
    assert votes["PLAYER"] == 0


def test_reviewed_outfield_semantics_narrows_direct_team_surface_to_player() -> None:
    votes = resolver.label_role_votes(
        ["Outfield marker"], _registry(), {"PLAYER", "GOALKEEPER"}
    )
    assert votes["PLAYER"] == 1
    assert votes["GOALKEEPER"] == 0


def test_team_structural_evidence_is_sufficient_candidate_only() -> None:
    role, status, reasons = resolver.admit_from_evidence(
        structural_roles={"TEAM"},
        structural_admission="TEAM",
        semantic_votes={"PLAYER": 0, "GOALKEEPER": 0, "TEAM": 0},
        content_support=[],
    )
    assert role == "TEAM"
    assert status == "ROLE_CANDIDATE_ADMITTED"
    assert reasons == ["STRUCTURAL_ROLE_EVIDENCE"]


def test_conflicting_content_evidence_stays_review_required() -> None:
    role, status, reasons = resolver.admit_from_evidence(
        structural_roles={"PLAYER", "GOALKEEPER"},
        structural_admission=None,
        semantic_votes={"PLAYER": 1, "GOALKEEPER": 1, "TEAM": 0},
        content_support=[],
    )
    assert role == "UNRESOLVED"
    assert status == "REVIEW_REQUIRED"
    assert reasons == ["CONTENT_ROLE_EVIDENCE_CONFLICT"]


def test_turkish_sheet_names_are_content_evidence() -> None:
    assert resolver.sheet_name_support(["Kaleci verileri"]) == ["GOALKEEPER"]
    assert resolver.sheet_name_support(["Oyuncuların verileri"]) == ["PLAYER"]


def test_embedded_team_candidate_uses_row_anatomy_not_filename() -> None:
    rows = [
        {
            "code": "Some Team - Passes accurate",
            "action": "Passes accurate",
            "team": "",
        }
    ]
    assert resolver.embedded_team_candidate(rows) is True


def test_resolved_inventory_overrides_filename_driven_role_only_after_admission() -> None:
    raw = {
        "files": [
            {
                "relative_path": "misleading_goalkeepers.csv",
                "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    report = {
        "status": "PASS",
        "files": [
            {
                "relative_path": "misleading_goalkeepers.csv",
                "role_resolution_applicable": True,
                "resolution": {
                    "resolution_status": "ROLE_CANDIDATE_ADMITTED",
                    "resolved_source_role": "PLAYER_SURFACE_CANDIDATE",
                    "resolution_reasons": ["REVIEWED_PROVIDER_ROLE_SEMANTICS"],
                },
            }
        ],
    }
    resolved = resolver.resolved_inventory(report, raw)
    item = resolved["files"][0]
    assert item["inventory_source_role"] == "GOALKEEPER_SURFACE_CANDIDATE"
    assert item["source_role"] == "PLAYER_SURFACE_CANDIDATE"
    assert item["filename_support_used_for_role_admission"] is False


def test_roleless_fingerprint_does_not_depend_on_filename_or_role() -> None:
    left = {
        field: str(index)
        for index, field in enumerate(resolver.reflection.FINGERPRINT_FIELDS)
    }
    right = dict(left)
    left["_source_file"] = "players.csv"
    left["_source_role"] = "PLAYER"
    right["_source_file"] = "anything.xml"
    right["_source_role"] = "UNKNOWN"
    assert resolver.roleless_row_fingerprint(left) == resolver.roleless_row_fingerprint(right)


def test_no_sample_match_identity_leak() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "content_source_role_resolver.py"
    )
    source = source_path.read_text(encoding="utf-8").casefold()
    forbidden = (
        "genclerbirligi",
        "fenerbahce",
        "15.08.2026",
        "3979",
        "3337",
        "174",
    )
    for token in forbidden:
        assert token.casefold() not in source
