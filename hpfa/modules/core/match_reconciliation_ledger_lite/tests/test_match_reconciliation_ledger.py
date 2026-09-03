from pathlib import Path

from hpfa.modules.core.match_reconciliation_ledger_lite.src.match_reconciliation_ledger import (
    build_match_reconciliation_ledger,
    validate_out,
)


def _chain(a: str, b: str, team_a: str, team_b: str, ep_a: str, ep_b: str) -> dict:
    return {
        "reciprocal_process_chain_candidate_id": f"rpc:{a}:{b}",
        "anchor_visible_action_sequence_candidate_id": a,
        "anchor_team_identity_candidate_id": team_a,
        "anchor_episode_candidate_id": ep_a,
        "response_visible_action_sequence_candidate_id": b,
        "response_team_identity_candidate_id": team_b,
        "response_episode_candidate_id": ep_b,
        "supporting_trackable_action_trace_candidate_ids": [f"tr:{a}", f"tr:{b}"],
    }


def _payload(rows: list[dict]) -> dict:
    return {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "reciprocal_process_chain_candidates": rows,
        "reciprocal_process_chain_candidate_count": len(rows),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_forward_reverse_views_share_one_edge_identity() -> None:
    report = build_match_reconciliation_ledger(_payload([_chain("a1", "b1", "TEAM_A", "TEAM_B", "epA", "epB")]))
    assert report["status"] == "PASS"
    assert report["reciprocal_consistency_edge_count"] == 1
    edge = report["reciprocal_consistency_edges"][0]
    assert edge["shared_edge_identity"] is True
    assert edge["forward_projection"] == "TEAM_A:a1 -> TEAM_B:b1"
    assert edge["reverse_projection"] == "TEAM_B:b1 <- TEAM_A:a1"
    assert report["cross_side_consistency_pass"] is True


def test_team_episode_accounting_uses_union_not_membership_sum() -> None:
    report = build_match_reconciliation_ledger(_payload([
        _chain("a1", "b1", "TEAM_A", "TEAM_B", "epA", "epB1"),
        _chain("a2", "b2", "TEAM_A", "TEAM_B", "epA", "epB2"),
    ]))
    team_a = next(row for row in report["team_episode_union_rows"] if row["team_identity_candidate_id"] == "TEAM_A")
    assert team_a["reciprocal_process_membership_count"] == 2
    assert team_a["unique_episode_candidate_count"] == 1
    assert team_a["episode_count_is_union_not_membership_sum"] is True


def test_same_team_edge_fails_closed() -> None:
    report = build_match_reconciliation_ledger(_payload([_chain("a1", "a2", "TEAM_A", "TEAM_A", "ep1", "ep2")]))
    assert report["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("reciprocal_edge_same_team") for hit in report["hard_block_hits"])


def test_missing_episode_binding_stays_review_required() -> None:
    report = build_match_reconciliation_ledger(_payload([_chain("a1", "b1", "TEAM_A", "TEAM_B", "", "epB")]))
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["reciprocal_consistency_edge_count"] == 1


def test_empty_ledger_never_claims_cross_side_consistency_pass() -> None:
    report = build_match_reconciliation_ledger(_payload([]))
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["reciprocal_consistency_edge_count"] == 0
    assert report["cross_side_consistency_pass"] is False
    assert "no_reciprocal_edges_to_reconcile" in report["review_hits"]


def test_claim_locks_and_unavailable_reconciliations_are_explicit() -> None:
    report = build_match_reconciliation_ledger(_payload([]))
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False
    assert report["possession_truth"] is False
    assert report["phase_truth"] is False
    assert report["sequence_truth"] is False
    assert report["tactical_truth"] is False
    assert report["loss_recovery_reconciliation_status"].startswith("NOT_EVALUATED")
    assert report["shot_gk_reconciliation_status"].startswith("NOT_EVALUATED")


def test_nested_phone_output_rejected() -> None:
    try:
        validate_out("/sdcard/Download/HPFA/nested")
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested phone output should be rejected")


def test_no_sample_match_identity_leak() -> None:
    paths = [
        Path("hpfa/modules/core/match_reconciliation_ledger_lite/src/match_reconciliation_ledger.py"),
        Path("match_reconciliation_ledger_current_v1.py"),
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
