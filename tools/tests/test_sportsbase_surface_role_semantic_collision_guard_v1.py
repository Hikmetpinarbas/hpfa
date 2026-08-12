from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLVS_SRC = ROOT / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "src"
EVIDENCE_SRC = ROOT / "hpfa" / "modules" / "core" / "evidence_atom_inventory_lite" / "src"
BUNDLE_SRC = ROOT / "hpfa" / "modules" / "core" / "semantic_role_action_bundle_candidates_lite" / "src"
REGISTRY = ROOT / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "registry" / "sportsbase_label_semantics_seed_v1.json"
CSV_REGISTRY = ROOT / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "registry" / "sportsbase_label_semantics_reviewed_v2.csv"
RUNNER = ROOT / "tools" / "run_active_match_sportsbase_surface_role_semantic_collision_guard_v1.sh"

for path in (PLVS_SRC, EVIDENCE_SRC, BUNDLE_SRC):
    sys.path.insert(0, str(path))

from provider_label_value_semantics import classify_label, load_registry
from evidence_atom_inventory import _classify_nucleus
from semantic_role_action_bundle_candidates import _route_atom


def classify(label: str, role: str) -> dict:
    return classify_label(label, source_format="csv", source_role=role, registry=load_registry(REGISTRY))


def test_registry_csv_has_no_malformed_rows() -> None:
    with CSV_REGISTRY.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert all(None not in row for row in rows)


def test_team_goal_kick_length_labels_are_reference_attributes() -> None:
    for label, distance in (
        ("Goal kicks short (0-15 m)", "SHORT"),
        ("Goal kicks medium (15-40 m)", "MEDIUM"),
        ("Goal kicks long (40+ m)", "LONG"),
    ):
        result = classify(label, "TEAM_SURFACE_CANDIDATE")
        assert result["semantic_role_candidate"] == "ATTRIBUTE_REFERENCE"
        assert result["action_family_candidate"] == "PASS"
        assert result["distance_candidate"] == distance
        assert result["restart_type_candidate"] is None
        assert result["action_subtype_candidate"] == "PASS_DISTANCE_ATTRIBUTE_CANDIDATE"
        assert result["downstream_eligibility"] == "REFERENCE_ONLY"
        assert result["semantics_decision"] == "CONTEXT_DEPENDENT_SEMANTIC_COLLISION"


def test_goalkeeper_goal_kick_length_labels_remain_restart_candidates() -> None:
    for label in (
        "Goal kicks short (0-15 m)",
        "Goal kicks medium (15-40 m)",
        "Goal kicks long (40+ m)",
    ):
        result = classify(label, "GOALKEEPER_SURFACE_CANDIDATE")
        assert result["semantic_role_candidate"] == "ACTION_ANCHOR"
        assert result["action_family_candidate"] == "RESTART"
        assert result["restart_type_candidate"] == "GOAL_KICK"
        assert result["downstream_eligibility"] == "ACTION_CANDIDATE_ELIGIBLE"


def test_plain_goal_kicks_literal_rule_is_goalkeeper_scoped() -> None:
    goalkeeper = classify("Goal kicks", "GOALKEEPER_SURFACE_CANDIDATE")
    team = classify("Goal kicks", "TEAM_SURFACE_CANDIDATE")
    assert goalkeeper["mapping_status"] == "EXACT_REVIEWED_CANDIDATE"
    assert goalkeeper["restart_type_candidate"] == "GOAL_KICK"
    assert team["mapping_status"] == "TOKEN_FALLBACK_REVIEW_REQUIRED"
    assert team["downstream_eligibility"] == "BLOCKED_PENDING_REVIEW"


def test_unexpected_player_goal_kick_label_is_not_action_admitted() -> None:
    result = classify("Goal kicks short (0-15 m)", "PLAYER_SURFACE_CANDIDATE")
    assert result["mapping_status"] == "TOKEN_FALLBACK_REVIEW_REQUIRED"
    assert result["downstream_eligibility"] == "BLOCKED_PENDING_REVIEW"


def test_attribute_reference_maps_to_reference_atom() -> None:
    nucleus = {
        "semantic_role_candidates": ["ATTRIBUTE_REFERENCE"],
        "mapping_statuses": ["EXACT_REVIEWED_CANDIDATE"],
        "downstream_eligibility_candidates": ["REFERENCE_ONLY"],
        "action_family_candidates": ["PASS"],
    }
    atom_class, role, reviews = _classify_nucleus(nucleus)
    assert atom_class == "REFERENCE_ATOM"
    assert role == "ATTRIBUTE_REFERENCE"
    assert reviews == []


def test_attribute_reference_never_routes_to_action_bundle() -> None:
    atom = {
        "atom_status": "PASS",
        "atom_class": "REFERENCE_ATOM",
        "source_role": "TEAM_SURFACE_CANDIDATE",
        "semantic_role_candidate": "ATTRIBUTE_REFERENCE",
    }
    binding = {"decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"}
    route, reasons = _route_atom(atom, binding)
    assert route == "REFERENCE_ROUTE"
    assert reasons == []
    assert route not in {
        "TEAM_ACTION_REFLECTION_ROUTE",
        "GOALKEEPER_ACTION_ROUTE",
        "PRIMARY_ACTION_ANCHOR_ROUTE",
    }


def test_runner_uses_current_downstream_cli_contracts() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    required = (
        '--runtime-authority "$RUNTIME_REAL"',
        '--expected-runtime-authority "$EXPECTED_RUNTIME_REAL"',
        '--csv-audit "$CSV"',
        '--xlsx-audit "$XLSX"',
        '--xml-audit "$XML"',
        '--evidence-atom "$EVIDENCE"',
        '--evidence-atoms "$EVIDENCE"',
        '--identity-candidates "$IDENTITY"',
    )
    assert all(item in text for item in required)
    forbidden = (
        '--runtime-root "$RUNTIME_REAL"',
        '--expected-active-match "$EXPECTED_RUNTIME_REAL"',
        '--csv "$CSV"',
        '--xlsx "$XLSX"',
        '--xml "$XML"',
        '--evidence "$EVIDENCE"',
        '--identity "$IDENTITY"',
    )
    assert all(item not in text for item in forbidden)


def test_active_match_collision_audit_is_casefolded_and_format_agnostic() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert 'norm=lambda value: str(value or "").strip().casefold()' in text
    assert '"team_surface_three_labels_observed": team_sem_observed_labels==affected' in text
    assert 'len(team_sem_ok)==len(team_sem)' in text
    assert 'len(team_sem)==3' not in text


def test_claim_boundaries_remain_fail_closed() -> None:
    assert classify("Goal kicks short (0-15 m)", "TEAM_SURFACE_CANDIDATE")["semantics_decision"] == "CONTEXT_DEPENDENT_SEMANTIC_COLLISION"
    source = (EVIDENCE_SRC / "evidence_atom_inventory.py").read_text(encoding="utf-8")
    assert 'CANONICAL_EVENT_COUNT = "UNKNOWN"' in source
    assert '"production_release": False' in source


def test_no_sample_match_identity_leak() -> None:
    texts = [
        CSV_REGISTRY.read_text(encoding="utf-8"),
        (EVIDENCE_SRC / "evidence_atom_inventory.py").read_text(encoding="utf-8"),
        RUNNER.read_text(encoding="utf-8"),
    ]
    forbidden = ["Sturm Graz", "Heart of Midlothian", "Fenerbahce", "Galatasaray", "Besiktas"]
    assert not any(token in text for token in forbidden for text in texts)
