from pathlib import Path

from hpfa.modules.core.player_aggregate_process_reconciliation_lite.src.player_aggregate_process_reconciliation import (
    build_player_aggregate_process_reconciliation,
    write_outputs,
)


def _inputs(*, team_mismatch=False, ambiguous=False):
    xlsx = {
        "module_id": "xlsx_entity_metric_row_projection_lite_v1", "status": "PASS",
        "files": [{"sheets": [{"rows": [{
            "row_projection_id": "x1", "sheet_name": "Players", "source_row_number": 2, "source_sha256": "a" * 64,
            "validated_identity": False,
            "identity_candidates": {"player_raw_candidate": "José Álvarez", "team_raw_candidate": "Beta" if team_mismatch else "Alpha", "position_raw_candidate": "CM", "minutes_raw_candidate": 90},
            "metric_values": {
                "passes": {"raw_metric_label": "Passes", "raw_value": 42, "value_kind": "number", "value_status": "OBSERVED", "number_format": "General", "percent_header_candidate": False},
                "note": {"raw_metric_label": "Note", "raw_value": "-", "value_kind": "string", "value_status": "OBSERVED"},
            },
        }]}]}],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    actors = [{"actor_identity_candidate_id": "p1", "actor_normalized_key": "jose_alvarez", "team_identity_candidate_id": "ta", "team_normalized_key": "alpha"}]
    if ambiguous:
        actors.append({"actor_identity_candidate_id": "p2", "actor_normalized_key": "jose_alvarez", "team_identity_candidate_id": "ta", "team_normalized_key": "alpha"})
    identity = {
        "module_id": "match_local_identity_candidates_lite_v1", "status": "PASS",
        "actor_identity_candidates": actors,
        "team_identity_candidates": [{"team_identity_candidate_id": "ta", "team_normalized_key": "alpha"}],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    reconciliation = {
        "module_id": "match_reconciliation_ledger_lite_v2", "status": "PASS",
        "player_process_membership_rows": [{
            "actor_identity_candidate_id": "p1", "unique_process_candidate_count": 3, "unique_episode_candidate_count": 4,
            "role_membership_counts": {"anchor": 2, "response": 1}, "visible_process_membership_share_of_team_candidate": 0.5,
        }],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    geometry = {
        "module_id": "visible_geometry_lens_lite_v1", "status": "PASS",
        "player_period_geometry_rows": [{"actor_identity_candidate_id": "p1", "period_candidate": "1", "point_count_candidate": 12, "direction_normalized": False}],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    return xlsx, identity, reconciliation, geometry


def test_exact_player_and_team_candidate_match_builds_dossier():
    result = build_player_aggregate_process_reconciliation(*_inputs())
    assert result["status"] == "PASS"
    assert result["xlsx_player_row_count"] == 1
    assert result["xlsx_player_row_bound_count"] == 1
    assert result["player_dossier_count"] == 1
    row = result["player_dossiers"][0]
    assert row["actor_identity_candidate_id"] == "p1"
    assert row["unique_process_candidate_count"] == 3
    assert row["unique_episode_candidate_count"] == 4
    assert row["aggregate_numeric_metric_candidate_count"] == 1
    assert row["aggregate_numeric_metric_candidates"][0]["raw_value"] == 42
    assert row["period_geometry_candidates"][0]["period_candidate"] == "1"
    assert row["validated_player_identity"] is False


def test_team_mismatch_is_not_force_bound():
    result = build_player_aggregate_process_reconciliation(*_inputs(team_mismatch=True))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["xlsx_player_row_bound_count"] == 0
    assert result["xlsx_player_row_team_mismatch_count"] == 1


def test_ambiguous_actor_match_is_not_force_bound():
    result = build_player_aggregate_process_reconciliation(*_inputs(ambiguous=True))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["xlsx_player_row_bound_count"] == 0
    assert result["xlsx_player_row_ambiguous_count"] == 1


def test_upstream_review_is_inherited_without_promoting_identity():
    xlsx, identity, reconciliation, geometry = _inputs()
    identity["status"] = "REVIEW_REQUIRED"
    result = build_player_aggregate_process_reconciliation(xlsx, identity, reconciliation, geometry)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["xlsx_creates_player_identity"] is False


def test_output_claim_locks(tmp_path: Path):
    result = build_player_aggregate_process_reconciliation(*_inputs())
    paths = write_outputs(result, tmp_path)
    text = paths["summary"].read_text(encoding="utf-8")
    assert "validated_player_identity=false" in text
    assert "aggregate_metric_truth=false" in text
    assert "production_release=false" in text


def test_no_sample_match_identity_leak():
    root = Path(__file__).resolve().parents[1] / "src"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py")).casefold()
    forbidden = ("genclerbirligi", "fenerbahce", "15.08.2026", "samsunspor", "galatasaray", "besiktas")
    assert not any(token in text for token in forbidden)
