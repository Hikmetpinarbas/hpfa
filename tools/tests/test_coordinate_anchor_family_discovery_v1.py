from pathlib import Path
import importlib.util

MODULE_PATH = Path(__file__).resolve().parents[1] / "coordinate_anchor_family_discovery_v1.py"
spec = importlib.util.spec_from_file_location("discovery", MODULE_PATH)
d = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(d)


def provider(rows):
    return {
        "module_id": "provider_label_value_semantics_lite_v1",
        "provider_label_records": rows,
        "provider_label_record_count": len(rows),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }


def save_rule(mapping="EXACT_REVIEWED_CANDIDATE"):
    return {
        "mapping_status": mapping,
        "source_role": d.GK_ROLE,
        "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
        "action_family_candidate": "GOALKEEPER_ACTION",
        "outcome_candidate": "SUCCESS",
        "shot_result_candidate": "SAVED",
        "action_subtype_candidate": "SAVE",
        "object_action_family_candidate": "SHOT",
        "normalized_label": "shots saved",
    }


def action_payload(rows):
    return {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "match_surface_binding_id": "msb_test",
        "action_bundle_candidates": rows,
        "action_bundle_candidate_count": len(rows),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }


def frame(shot_direction="ATTACK_TOWARD_HIGH_X_CANDIDATE"):
    return {
        "module_id": "coordinate_frame_precondition_lite_v1",
        "match_surface_binding_id": "msb_test",
        "pitch_length_candidate": 105.0,
        "coordinate_frame_candidate": "FRAME_UNRESOLVED",
        "progression_metric_recheck_allowed": False,
        "team_period_coordinate_frame_candidates": [
            {
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "multi_anchor_gate": "INDEPENDENT_PRIMARY_ANCHORS_INSUFFICIENT",
                "shot_direction_candidate": shot_direction,
                "goalkeeper_goal_kick_direction_candidate": "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
                "clearance_direction_candidate": "ATTACK_TOWARD_HIGH_X_CANDIDATE",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }


def gk_save(x, start):
    return {
        "bundle_status": "PASS",
        "source_role": d.GK_ROLE,
        "action_family_candidate": "GOALKEEPER_ACTION",
        "normalized_labels": ["shots saved"],
        "team_identity_candidate_id": "team_a",
        "period_candidate": "1",
        "start_candidate": start,
        "end_candidate": start + 0.1,
        "pos_x_candidate": x,
        "pos_y_candidate": 34.0,
    }


def player_shot(x, start):
    return {
        "bundle_status": "PASS",
        "source_role": d.PLAYER_ROLE,
        "action_family_candidate": "SHOT",
        "normalized_labels": ["shots"],
        "team_identity_candidate_id": "team_b",
        "period_candidate": "1",
        "start_candidate": start,
        "end_candidate": start + 0.1,
        "pos_x_candidate": x,
        "pos_y_candidate": 34.0,
    }


def save_family(result):
    return next(row for row in result["anchor_family_records"] if row["anchor_family"] == "GK_SAVE")


def test_exact_save_semantics_selected():
    result = d.build_discovery(provider([save_rule()]), action_payload([gk_save(5, 10), gk_save(6, 20)]), frame())
    family = save_family(result)
    assert family["exact_semantic_lineage_status"] == "EXACT_REVIEWED_CANDIDATE"
    assert family["team_period_visible_support"] == 2


def test_token_fallback_not_admitted():
    result = d.build_discovery(provider([save_rule("TOKEN_FALLBACK_REVIEW_REQUIRED")]), action_payload([gk_save(5, 10)]), frame())
    family = save_family(result)
    assert family["exact_semantic_lineage_status"] == "EXACT_SEMANTIC_LINEAGE_UNAVAILABLE"
    assert family["recommended_role"] == "REJECT"


def test_exact_shot_surface_overlap_rejects_independence():
    rows = [gk_save(5, 10), gk_save(6, 20), player_shot(5, 10)]
    result = d.build_discovery(provider([save_rule()]), action_payload(rows), frame())
    family = save_family(result)
    assert family["exact_object_action_surface_overlap_count"] == 1
    assert family["recommended_role"] == "REJECT"


def test_no_overlap_still_not_primary_without_coordinate_attachment_semantics():
    result = d.build_discovery(provider([save_rule()]), action_payload([gk_save(5, 10), gk_save(6, 20)]), frame())
    family = save_family(result)
    assert family["recommended_role"] == "COUNTER_SUPPORT_ONLY"
    assert family["primary_anchor_admission_allowed"] is False
    assert family["coordinate_attachment_semantics_status"] == "UNVERIFIED_PROVIDER_COORDINATE_ATTACHMENT"


def test_direction_conflict_rejects_candidate():
    result = d.build_discovery(provider([save_rule()]), action_payload([gk_save(5, 10), gk_save(6, 20)]), frame("ATTACK_TOWARD_LOW_X_CANDIDATE"))
    family = save_family(result)
    assert family["directional_conflict_count"] == 1
    assert family["recommended_role"] == "REJECT"


def test_unresolved_group_coverage_is_counted():
    result = d.build_discovery(provider([save_rule()]), action_payload([gk_save(5, 10)]), frame())
    assert save_family(result)["unresolved_group_coverage_count"] == 1


def test_wrong_match_binding_fails_closed():
    f = frame()
    f["match_surface_binding_id"] = "other"
    result = d.build_discovery(provider([save_rule()]), action_payload([]), f)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_surface_binding_mismatch_or_missing" in result["hard_block_hits"]


def test_claim_boundary_preserved():
    result = d.build_discovery(provider([save_rule()]), action_payload([]), frame())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["coordinate_frame_contract_change_allowed"] is False
    assert result["threshold_relaxation_allowed"] is False


def test_nested_phone_output_rejected():
    try:
        d.validate_out("/sdcard/Download/HPFA/nested")
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("expected rejection")


def test_no_sample_match_identity_leak():
    text = MODULE_PATH.read_text(encoding="utf-8").casefold()
    for forbidden in ("juventus", "galatasaray", "besiktas", "fenerbahce", "trabzonspor", "city_gs"):
        assert forbidden not in text
