from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "context_action_semantics_rebind_lite" / "src"
sys.path.insert(0, str(SRC))

import context_action_semantics_rebind as rebind_module
from context_action_semantics_rebind import build_rebind, validate_output_root


def _nucleus(idx: int, role: str, label: str) -> dict:
    return {
        "row_nucleus_candidate_id": f"rn_{idx}",
        "source_role": role,
        "status": "PASS",
        "resolved_visible_fields": {
            "action": label,
            "code": label,
        },
    }


def _context(idx: int) -> dict:
    return {
        "context_id": f"ctx_{idx}",
        "period": "1",
        "team_label": "team_candidate",
        "zone_candidate": "MIDDLE_THIRD",
        "channel_candidate": "CENTRAL_CHANNEL",
        "time_admission_status": "ADMITTED",
        "football_minute_candidate": 1,
        "_preserved_unmapped": {
            "row_nucleus_candidate_id": f"rn_{idx}",
        },
    }


def _payloads() -> tuple[dict, dict]:
    rows = [
        ("TEAM", "Goal kicks medium (15-40 m)"),
        ("GOALKEEPER", "Goal kicks medium (15-40 m)"),
        ("PLAYER", "Lost balls"),
        ("PLAYER", "Ball recoveries"),
        ("PLAYER", "Involvement in positional attacks"),
        ("GOALKEEPER", "Shots on target"),
        ("TEAM", "Shots"),
    ]
    nuclei = [_nucleus(i, role, label) for i, (role, label) in enumerate(rows)]
    contexts = [_context(i) for i in range(len(rows))]
    row_payload = {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "PASS",
        "row_nucleus_candidate_count": len(nuclei),
        "row_nuclei": nuclei,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    mvc = {
        "module_id": "minimum_viable_context_lite_v1",
        "status": "REVIEW_REQUIRED",
        "context_candidate_count": len(contexts),
        "context_candidates": contexts,
        "time_admission_status": "ADMITTED",
        "context_occurrence_basis": "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT",
        "row_nucleus_context_binding": {
            "enabled": True,
            "reflection_inflation_prevented": True,
            "row_nucleus_candidate_count": len(nuclei),
        },
        "source_row_order_is_temporal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return mvc, row_payload


def _append_row(mvc: dict, row: dict, role: str, label: str) -> int:
    idx = len(row["row_nuclei"])
    row["row_nuclei"].append(_nucleus(idx, role, label))
    mvc["context_candidates"].append(_context(idx))
    row["row_nucleus_candidate_count"] = len(row["row_nuclei"])
    mvc["context_candidate_count"] = len(mvc["context_candidates"])
    mvc["row_nucleus_context_binding"]["row_nucleus_candidate_count"] = len(row["row_nuclei"])
    return idx


def _record(result: dict, context_id: str) -> dict:
    return next(row for row in result["context_action_semantic_records"] if row["context_id"] == context_id)


def _patched_provider(monkeypatch: pytest.MonkeyPatch, mutate):
    provider_module, registry = rebind_module.load_registry(ROOT)
    original = provider_module.classify_label

    class PatchedProvider:
        normalize_label = staticmethod(provider_module.normalize_label)

        @staticmethod
        def classify_label(label, **kwargs):
            result = dict(original(label, **kwargs))
            return mutate(label, kwargs, result)

    monkeypatch.setattr(rebind_module, "load_registry", lambda _root: (PatchedProvider, registry))


def test_reviewed_provider_semantics_rebinds_action_and_non_action_surfaces() -> None:
    mvc, row = _payloads()
    result = build_rebind(mvc, row, repo_root=ROOT)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["context_semantic_assignment_complete"] is True
    assert result["context_action_semantic_record_count"] == 7
    assert result["action_occurrence_eligible_count"] == 4
    assert result["non_action_context_or_reference_count"] == 3
    assert result["reviewed_provider_semantics_bound_count"] == 7
    assert result["provider_semantics_unresolved_or_review_required_count"] == 0


def test_team_goal_kick_length_is_reference_not_action_occurrence() -> None:
    mvc, row = _payloads()
    result = build_rebind(mvc, row, repo_root=ROOT)
    record = _record(result, "ctx_0")
    assert record["provider_semantic_role_candidate"] == "ATTRIBUTE_REFERENCE"
    assert record["provider_action_family_candidate"] == "PASS"
    assert record["provider_downstream_eligibility"] == "REFERENCE_ONLY"
    assert record["action_occurrence_eligible"] is False
    audit = result["semantic_collision_audit"]
    assert audit["team_goal_kick_length_record_count"] == 1
    assert audit["team_goal_kick_length_action_occurrence_eligible_count"] == 0


def test_goalkeeper_goal_kick_remains_restart_action_candidate() -> None:
    mvc, row = _payloads()
    result = build_rebind(mvc, row, repo_root=ROOT)
    record = _record(result, "ctx_1")
    assert record["provider_semantic_role_candidate"] == "ACTION_ANCHOR"
    assert record["provider_action_family_candidate"] == "RESTART"
    assert record["provider_restart_type_candidate"] == "GOAL_KICK"
    assert record["action_occurrence_eligible"] is True


def test_lost_balls_and_ball_recoveries_are_correct_action_candidates() -> None:
    mvc, row = _payloads()
    result = build_rebind(mvc, row, repo_root=ROOT)
    lost = _record(result, "ctx_2")
    recovery = _record(result, "ctx_3")
    assert lost["provider_action_family_candidate"] == "TURNOVER"
    assert lost["action_occurrence_eligible"] is True
    assert recovery["provider_action_family_candidate"] == "RECOVERY"
    assert recovery["action_occurrence_eligible"] is True
    audit = result["semantic_collision_audit"]
    assert audit["lost_ball_turnover_candidate_count"] == 1
    assert audit["lost_ball_reconciliation_mismatch_count"] == 0
    assert audit["ball_recovery_candidate_count"] == 1
    assert audit["ball_recovery_reconciliation_mismatch_count"] == 0


def test_participation_and_goalkeeper_opponent_shot_reference_do_not_add_action_volume() -> None:
    mvc, row = _payloads()
    result = build_rebind(mvc, row, repo_root=ROOT)
    participation = _record(result, "ctx_4")
    gk_reference = _record(result, "ctx_5")
    assert participation["provider_semantic_role_candidate"] == "PARTICIPATION_INTERVAL"
    assert participation["action_occurrence_eligible"] is False
    assert gk_reference["provider_semantic_role_candidate"] == "OPPONENT_ACTION_REFERENCE"
    assert gk_reference["provider_action_family_candidate"] == "SHOT"
    assert gk_reference["action_occurrence_eligible"] is False
    audit = result["semantic_collision_audit"]
    assert audit["goalkeeper_shot_reference_record_count"] == 1
    assert audit["goalkeeper_shot_reference_routing_mismatch_count"] == 0
    assert audit["goalkeeper_shot_reference_action_occurrence_eligible_count"] == 0


def test_goalkeeper_shot_reference_audit_survives_semantic_role_regression(monkeypatch: pytest.MonkeyPatch) -> None:
    mvc, row = _payloads()

    def mutate(label, kwargs, result):
        if label == "Shots on target" and kwargs.get("source_role") == "GOALKEEPER_SURFACE_CANDIDATE":
            result.update({
                "semantic_role_candidate": "ACTION_ANCHOR",
                "action_family_candidate": "SHOT",
                "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "review_status": "REVIEWED_CANDIDATE",
            })
        return result

    _patched_provider(monkeypatch, mutate)
    result = build_rebind(mvc, row, repo_root=ROOT)
    audit = result["semantic_collision_audit"]
    assert result["status"] == "FAIL_CLOSED"
    assert audit["goalkeeper_shot_reference_record_count"] == 1
    assert audit["goalkeeper_shot_reference_action_occurrence_eligible_count"] == 1
    assert audit["goalkeeper_shot_reference_routing_mismatch_count"] == 1
    assert "goalkeeper_opponent_shot_reference_promoted_to_action_occurrence" in result["hard_block_hits"]


def test_partial_lost_ball_and_recovery_regressions_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    mvc, row = _payloads()
    _append_row(mvc, row, "PLAYER", "Lost balls in own half")
    _append_row(mvc, row, "PLAYER", "Ball recoveries in opponent's half")

    def mutate(label, _kwargs, result):
        if label == "Lost balls in own half":
            result.update({
                "semantic_role_candidate": "ACTION_ANCHOR",
                "action_family_candidate": "PASS",
                "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "review_status": "REVIEWED_CANDIDATE",
            })
        if label == "Ball recoveries in opponent's half":
            result.update({
                "semantic_role_candidate": "ACTION_ANCHOR",
                "action_family_candidate": "PASS",
                "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "review_status": "REVIEWED_CANDIDATE",
            })
        return result

    _patched_provider(monkeypatch, mutate)
    result = build_rebind(mvc, row, repo_root=ROOT)
    audit = result["semantic_collision_audit"]
    assert result["status"] == "FAIL_CLOSED"
    assert audit["lost_ball_reviewed_record_count"] == 2
    assert audit["lost_ball_turnover_candidate_count"] == 1
    assert audit["lost_ball_reconciliation_mismatch_count"] == 1
    assert audit["ball_recovery_reviewed_record_count"] == 2
    assert audit["ball_recovery_candidate_count"] == 1
    assert audit["ball_recovery_reconciliation_mismatch_count"] == 1
    assert "lost_ball_turnover_reconciliation_mismatch" in result["hard_block_hits"]
    assert "ball_recovery_reconciliation_mismatch" in result["hard_block_hits"]


def test_attacking_team_shot_anchor_can_remain_action_candidate() -> None:
    mvc, row = _payloads()
    result = build_rebind(mvc, row, repo_root=ROOT)
    record = _record(result, "ctx_6")
    assert record["provider_semantic_role_candidate"] == "ACTION_ANCHOR"
    assert record["provider_action_family_candidate"] == "SHOT"
    assert record["action_occurrence_eligible"] is True


def test_missing_row_nucleus_binding_fails_closed() -> None:
    mvc, row = _payloads()
    mvc = copy.deepcopy(mvc)
    mvc["row_nucleus_context_binding"]["enabled"] = False
    result = build_rebind(mvc, row, repo_root=ROOT)
    assert result["status"] == "FAIL_CLOSED"
    assert "row_nucleus_context_binding_missing" in result["hard_block_hits"]


def test_claim_locks_remain_closed() -> None:
    mvc, row = _payloads()
    result = build_rebind(mvc, row, repo_root=ROOT)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["physical_action_truth"] is False
    assert result["possession_truth"] is False
    assert result["sequence_truth"] is False
    assert result["phase_truth"] is False
    assert result["rhythm_truth"] is False
    assert result["tactical_truth"] is False
    assert result["dominance_truth"] is False
    assert result["production_release"] is False


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root("/sdcard/Download/HPFA/semantic-rebind")


def test_no_sample_match_identity_leak() -> None:
    text = (SRC / "context_action_semantics_rebind.py").read_text(encoding="utf-8")
    forbidden = ["Fenerbahce", "Galatasaray", "Genclerbirligi", "15.08.2026", "World Cup"]
    assert not any(token in text for token in forbidden)
