from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team_attribution_projection import project_team_attribution  # noqa: E402


def _semantic(rows, *, status="PASS"):
    return {
        "module_id": "context_action_semantics_rebind_lite_v1",
        "status": status,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "context_action_semantic_records": rows,
    }


def _evidence(atoms, *, status="PASS"):
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": status,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "evidence_atoms": atoms,
    }


def _identity(bindings, *, status="PASS"):
    return {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": status,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "team_subject_code_prefix_bridge_mode": "EXACT_SUFFIX_ONLY_WHEN_TEAM_FIELD_ABSENT",
        "identity_bindings": bindings,
    }


def _row(context_id, nucleus_id, team, *, role="TEAM", eligible=True):
    return {
        "context_id": context_id,
        "row_nucleus_candidate_id": nucleus_id,
        "source_role": role,
        "context_team_candidate": team,
        "action_occurrence_eligible": eligible,
        "provider_action_family_candidate": "PASS",
    }


def _atom(atom_id, nucleus_id, *, role="TEAM"):
    return {
        "evidence_atom_id": atom_id,
        "row_nucleus_candidate_id": nucleus_id,
        "source_role_short": role,
    }


def _binding(
    atom_id,
    team_name=None,
    team_id=None,
    *,
    team_subject=None,
    role="TEAM_SURFACE_CANDIDATE",
):
    return {
        "evidence_atom_id": atom_id,
        "source_role": role,
        "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND" if team_id else "REVIEW_REQUIRED",
        "team_identity_candidate_id": team_id,
        "team_name_raw_candidate": team_name,
        "team_subject_raw_candidate": team_subject,
        "validated_team_identity": False,
    }


def test_direct_visible_team_is_never_overwritten():
    result = project_team_attribution(
        _semantic([_row("ctx1", "rn1", "alpha")]),
        _evidence([_atom("ea1", "rn1")]),
        _identity([_binding("ea1", "beta", "team_beta", team_subject="beta (202)")]),
    )
    row = result["context_action_semantic_records"][0]
    assert row["context_team_candidate"] == "alpha"
    assert row["team_attribution_state_candidate"] == "DIRECT_VISIBLE_CONTEXT_TEAM"
    assert row["team_attribution_recovered"] is False


def test_unknown_team_is_recovered_only_from_existing_match_local_identity_binding():
    result = project_team_attribution(
        _semantic([_row("ctx1", "rn1", "unknown")]),
        _evidence([_atom("ea1", "rn1")]),
        _identity([_binding("ea1", "alpha", "team_alpha")]),
    )
    row = result["context_action_semantic_records"][0]
    assert row["context_team_candidate_raw_surface"] == "unknown"
    assert row["context_team_candidate"] == "alpha"
    assert row["team_identity_candidate_id"] == "team_alpha"
    assert row["team_attribution_state_candidate"] == "RECOVERED_FROM_MATCH_LOCAL_IDENTITY_CANDIDATE"
    assert row["team_attribution_basis"] == "EXISTING_MATCH_LOCAL_IDENTITY_BINDING"
    assert row["team_attribution_recovered"] is True
    assert row["team_attribution_is_validated_truth"] is False


def test_provider_subject_is_preferred_so_direct_and_recovered_labels_do_not_split():
    direct_label = "alpha (101)"
    result = project_team_attribution(
        _semantic([
            _row("ctx1", "rn1", direct_label),
            _row("ctx2", "rn2", "unknown"),
        ]),
        _evidence([
            _atom("ea1", "rn1"),
            _atom("ea2", "rn2"),
        ]),
        _identity([
            _binding("ea1", "alpha", "team_alpha", team_subject=direct_label),
            _binding("ea2", "alpha", "team_alpha", team_subject=direct_label),
        ]),
    )
    labels = [row["context_team_candidate"] for row in result["context_action_semantic_records"]]
    assert labels == [direct_label, direct_label]
    assert result["direct_known_team_eligible_count"] == 1
    assert result["recovered_team_eligible_count"] == 1
    assert result["unresolved_team_eligible_count"] == 0
    assert result["effective_known_team_coverage_candidate"] == 1.0


def test_missing_or_non_team_identity_binding_stays_unknown():
    result = project_team_attribution(
        _semantic([
            _row("ctx1", "rn1", "unknown"),
            _row("ctx2", "rn2", "unknown", role="PLAYER"),
        ]),
        _evidence([
            _atom("ea1", "rn1"),
            _atom("ea2", "rn2", role="PLAYER"),
        ]),
        _identity([
            _binding("ea1"),
            _binding("ea2", "alpha", "team_alpha", role="PLAYER_SURFACE_CANDIDATE"),
        ]),
    )
    assert result["unresolved_team_eligible_count"] == 2
    assert all(
        row["team_attribution_state_candidate"] == "UNRESOLVED_TEAM_CANDIDATE"
        for row in result["context_action_semantic_records"]
    )


def test_projection_preserves_action_eligibility_and_accounts_same_units():
    rows = [
        _row("ctx1", "rn1", "alpha", eligible=True),
        _row("ctx2", "rn2", "unknown", eligible=True),
        _row("ctx3", "rn3", "unknown", eligible=True),
        _row("ctx4", "rn4", "unknown", eligible=False),
    ]
    result = project_team_attribution(
        _semantic(rows),
        _evidence([
            _atom("ea1", "rn1"),
            _atom("ea2", "rn2"),
            _atom("ea3", "rn3"),
            _atom("ea4", "rn4"),
        ]),
        _identity([
            _binding("ea1", "alpha", "team_alpha"),
            _binding("ea2", "beta", "team_beta"),
            _binding("ea3"),
            _binding("ea4", "beta", "team_beta"),
        ]),
    )
    assert result["input_action_occurrence_eligible_count"] == 3
    assert result["direct_known_team_eligible_count"] == 1
    assert result["recovered_team_eligible_count"] == 1
    assert result["unresolved_team_eligible_count"] == 1
    assert result["raw_known_team_coverage_candidate"] == 0.333333
    assert result["effective_known_team_coverage_candidate"] == 0.666667
    assert result["action_occurrence_count_changed_by_projection"] is False
    assert [r["action_occurrence_eligible"] for r in result["context_action_semantic_records"]] == [True, True, True, False]


def test_review_required_upstream_cannot_be_promoted_to_pass():
    result = project_team_attribution(
        _semantic([_row("ctx1", "rn1", "unknown")], status="REVIEW_REQUIRED"),
        _evidence([_atom("ea1", "rn1")], status="REVIEW_REQUIRED"),
        _identity([_binding("ea1", "alpha", "team_alpha")], status="REVIEW_REQUIRED"),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["recovered_team_eligible_count"] == 1
    assert set(result["review_hits"]) == {
        "semantic_upstream_review_required",
        "evidence_upstream_review_required",
        "identity_upstream_review_required",
    }


def test_identity_bridge_mode_mismatch_fails_closed():
    identity = _identity([_binding("ea1", "alpha", "team_alpha")])
    identity["team_subject_code_prefix_bridge_mode"] = "FUZZY"
    result = project_team_attribution(
        _semantic([_row("ctx1", "rn1", "unknown")]),
        _evidence([_atom("ea1", "rn1")]),
        identity,
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "identity_team_bridge_mode_mismatch" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    text = (SRC / "team_attribution_projection.py").read_text(encoding="utf-8").casefold()
    forbidden = ["fenerbah", "genclerbir", "15.08.2026", "27041", "29575"]
    assert not any(token in text for token in forbidden)
