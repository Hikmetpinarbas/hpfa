from pathlib import Path

from hpfa.modules.core.match_reconciliation_ledger_lite.src.match_reconciliation_ledger import (
    MODULE_ID,
    build_match_reconciliation_ledger,
    write_outputs,
)


def _inputs(*, missing_anchor_episode: bool = False, counter_response: bool = False):
    reciprocal = {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "REVIEW_REQUIRED" if missing_anchor_episode else "PASS",
        "reciprocal_process_chain_candidate_count": 1,
        "reciprocal_process_chain_candidates": [{
            "reciprocal_process_chain_candidate_id": "rpc_1",
            "anchor_visible_action_sequence_candidate_id": "seq_a",
            "anchor_team_identity_candidate_id": "team_a",
            "anchor_episode_candidate_id": None if missing_anchor_episode else "ep_a",
            "response_visible_action_sequence_candidate_id": "seq_b",
            "response_team_identity_candidate_id": "team_b",
            "response_episode_candidate_id": "ep_b",
            "counter_response_visible": counter_response,
            "counter_response_visible_action_sequence_candidate_id": "seq_c" if counter_response else None,
            "counter_response_team_identity_candidate_id": "team_a" if counter_response else None,
            "counter_response_episode_candidate_id": "ep_c" if counter_response else None,
        }],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    sequence_rows = [
        {"visible_action_sequence_candidate_id": "seq_a", "team_identity_candidate_id": "team_a", "trackable_action_trace_candidate_ids": ["ta1", "ta2", "ta3"]},
        {"visible_action_sequence_candidate_id": "seq_b", "team_identity_candidate_id": "team_b", "trackable_action_trace_candidate_ids": ["tb1"]},
    ]
    if counter_response:
        sequence_rows.append({"visible_action_sequence_candidate_id": "seq_c", "team_identity_candidate_id": "team_a", "trackable_action_trace_candidate_ids": ["ta1"]})
    sequence = {
        "module_id": "visible_action_sequence_candidates_lite_v1", "status": "PASS",
        "visible_action_sequence_candidates": sequence_rows,
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    trace = {
        "module_id": "trackable_action_trace_candidates_lite_v1", "status": "PASS",
        "trackable_action_trace_candidates": [
            {"trackable_action_trace_candidate_id": "ta1", "team_identity_candidate_id": "team_a", "actor_identity_candidate_id": "pa1"},
            {"trackable_action_trace_candidate_id": "ta2", "team_identity_candidate_id": "team_a", "actor_identity_candidate_id": "pa1"},
            {"trackable_action_trace_candidate_id": "ta3", "team_identity_candidate_id": "team_a", "actor_identity_candidate_id": "pa2"},
            {"trackable_action_trace_candidate_id": "tb1", "team_identity_candidate_id": "team_b", "actor_identity_candidate_id": "pb1"},
        ],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    identity = {
        "module_id": "match_local_identity_candidates_lite_v1", "status": "PASS",
        "actor_identity_candidates": [
            {"actor_identity_candidate_id": "pa1", "actor_normalized_key": "a_one", "team_identity_candidate_id": "team_a"},
            {"actor_identity_candidate_id": "pa2", "actor_normalized_key": "a_two", "team_identity_candidate_id": "team_a"},
            {"actor_identity_candidate_id": "pb1", "actor_normalized_key": "b_one", "team_identity_candidate_id": "team_b"},
        ],
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_normalized_key": "a"},
            {"team_identity_candidate_id": "team_b", "team_normalized_key": "b"},
        ],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    return reciprocal, sequence, trace, identity


def test_team_to_player_to_team_episode_union_is_set_consistent():
    result = build_match_reconciliation_ledger(*_inputs())
    assert result["module_id"] == MODULE_ID
    assert result["status"] == "PASS"
    assert result["reciprocal_consistency_edge_count"] == 1
    assert result["player_process_membership_row_count"] == 3
    assert result["player_team_episode_reconciliation_state"] == "CONSISTENT_CANDIDATE"
    assert result["player_team_episode_union_consistent_team_count"] == 2


def test_many_traces_for_one_player_do_not_inflate_process_or_episode_counts():
    result = build_match_reconciliation_ledger(*_inputs())
    row = next(row for row in result["player_process_membership_rows"] if row["actor_identity_candidate_id"] == "pa1")
    assert row["unique_process_candidate_count"] == 1
    assert row["unique_episode_candidate_count"] == 1
    assert row["supporting_unique_trace_candidate_count"] == 2
    assert row["role_membership_counts"] == {"anchor": 1}


def test_process_membership_share_uses_unique_process_units_for_a_b_a_chain():
    result = build_match_reconciliation_ledger(*_inputs(counter_response=True))
    pa1 = next(row for row in result["player_process_membership_rows"] if row["actor_identity_candidate_id"] == "pa1")
    team_a = next(row for row in result["team_reconciliation_rows"] if row["team_identity_candidate_id"] == "team_a")
    assert team_a["reciprocal_process_role_membership_count"] == 2
    assert team_a["unique_team_process_candidate_count"] == 1
    assert pa1["unique_process_candidate_count"] == 1
    assert pa1["visible_process_membership_share_of_team_candidate"] == 1.0
    assert pa1["visible_process_membership_share_units"] == "UNIQUE_PLAYER_PROCESS_IDS / UNIQUE_TEAM_PROCESS_IDS"


def test_incomplete_episode_binding_remains_review_required_without_fabrication():
    result = build_match_reconciliation_ledger(*_inputs(missing_anchor_episode=True))
    assert result["status"] == "REVIEW_REQUIRED"
    assert any("anchor_episode_binding_incomplete" in hit for hit in result["review_hits"])
    team_a = next(row for row in result["team_reconciliation_rows"] if row["team_identity_candidate_id"] == "team_a")
    assert team_a["unique_team_episode_candidate_count"] == 0
    assert team_a["player_episode_union_candidate_count"] == 0


def test_module_identity_mismatch_fails_closed():
    reciprocal, sequence, trace, identity = _inputs()
    reciprocal["module_id"] = "wrong"
    result = build_match_reconciliation_ledger(reciprocal, sequence, trace, identity)
    assert result["status"] == "FAIL_CLOSED"
    assert "reciprocal_module_id_mismatch" in result["hard_block_hits"]


def test_output_writer_keeps_claim_locks(tmp_path: Path):
    result = build_match_reconciliation_ledger(*_inputs())
    paths = write_outputs(result, tmp_path)
    text = paths["summary"].read_text(encoding="utf-8")
    assert "process_membership_share_units=UNIQUE_PLAYER_PROCESS_IDS/UNIQUE_TEAM_PROCESS_IDS" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "true_action_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_no_sample_match_identity_leak():
    root = Path(__file__).resolve().parents[1] / "src"
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in root.glob("*.py")).casefold()
    forbidden = ("genclerbirligi", "fenerbahce", "15.08.2026", "samsunspor", "galatasaray", "besiktas")
    assert not any(token in text for token in forbidden)
