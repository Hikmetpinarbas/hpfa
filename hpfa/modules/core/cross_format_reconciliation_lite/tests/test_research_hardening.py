from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "cross_format_reconciliation_lite" / "src"
sys.path.insert(0, str(SRC))

from research_hardening import apply_research_hardening


def base_payload() -> dict:
    return {
        "status": "PASS",
        "module_status": "PASS",
        "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS",
        "fusion_admissibility": "CANDIDATE_ONLY",
        "hard_block_hits": [],
        "parse_warnings": [],
        "active_match_evidence_pass": True,
        "label_semantics_version": "sportsbase_label_semantics_reviewed_v2",
        "validated_cross_format_equivalence": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "sequence_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "pair_reports": [
            {
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "csv_relative_path": "players.csv",
                "xml_relative_path": "players.xml",
                "cross_id_collision_count": 0,
                "local_duplicate_candidate_count": 0,
                "csv_only_id_candidate_count": 0,
                "xml_only_id_candidate_count": 0,
                "required_field_mismatch_candidate_count": 0,
                "supporting_field_mismatch_candidate_count": 0,
            }
        ],
    }


def test_bare_id_never_becomes_global_event_identity() -> None:
    result = apply_research_hardening(base_payload())
    guard = result["pair_reports"][0]["identifier_namespace_guard"]
    assert guard["global_event_identity_allowed"] is False
    assert guard["linkage_eligibility"] == "SAME_ROLE_CANDIDATE_ONLY"
    assert result["validated_cross_format_equivalence"] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_cross_role_identifier_join_fails_closed() -> None:
    payload = base_payload()
    pair = payload["pair_reports"][0]
    pair["csv_source_role"] = "PLAYER_SURFACE_CANDIDATE"
    pair["xml_source_role"] = "TEAM_SURFACE_CANDIDATE"
    result = apply_research_hardening(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "cross_role_identifier_join_forbidden:pair_0" in result["hard_block_hits"]


def test_transitive_promotion_fails_closed() -> None:
    payload = base_payload()
    payload["validated_player_identity"] = True
    result = apply_research_hardening(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "transitive_promotion_without_direct_evidence:validated_player_identity" in result["hard_block_hits"]


def test_missing_counterpart_is_not_contradiction_without_expectation() -> None:
    payload = base_payload()
    payload["pair_reports"][0]["csv_only_id_candidate_count"] = 1
    result = apply_research_hardening(payload)
    guard = result["pair_reports"][0]["counterpart_expectation_guard"]
    assert guard["counterpart_expectation_established"] is False
    assert guard["missing_counterpart_is_contradiction"] is False
    assert guard["state"] == "MISSING_COUNTERPART_EXPECTATION_UNRESOLVED"
    assert result["status"] == "REVIEW_REQUIRED"


def test_numeric_equality_has_no_arbitrary_epsilon() -> None:
    result = apply_research_hardening(base_payload())
    guard = result["pair_reports"][0]["measurement_resolution_guard"]
    assert guard["numeric_comparison_mode"] == "EXACT_NORMALIZED_CANDIDATE_ONLY"
    assert guard["arbitrary_epsilon_allowed"] is False
    assert guard["epsilon"] is None
    assert guard["numeric_equality_is_semantic_equivalence_truth"] is False


def test_conflict_has_no_format_precedence_or_majority_vote() -> None:
    payload = base_payload()
    payload["pair_reports"][0]["required_field_mismatch_candidate_count"] = 1
    result = apply_research_hardening(payload)
    guard = result["pair_reports"][0]["conflict_authority_guard"]
    assert guard["authority_precedence"] == "NONE"
    assert guard["majority_vote_allowed"] is False
    assert guard["automatic_resolution_allowed"] is False
    assert guard["state"] == "UNRESOLVED_REVIEW_REQUIRED"
    assert result["status"] == "REVIEW_REQUIRED"


def test_start_end_are_source_timeline_evidence_only() -> None:
    result = apply_research_hardening(base_payload())
    guard = result["pair_reports"][0]["temporal_attachment_guard"]
    assert guard["start_end_role"] == "SOURCE_TIMELINE_EVIDENCE_ONLY"
    assert guard["football_order_truth"] is False
    assert guard["same_time_simultaneity_truth"] is False
    assert guard["sequence_attachment_allowed"] is False


def test_no_sample_match_identity_leak_in_research_hardening() -> None:
    source = (SRC / "research_hardening.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "Sturm Graz", "Heart of Midlothian", "Galatasaray", "6935", "77798", "2062"]
    assert not any(token in source for token in forbidden)
