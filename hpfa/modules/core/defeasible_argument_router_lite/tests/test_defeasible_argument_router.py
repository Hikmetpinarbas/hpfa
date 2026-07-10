import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "defeasible_argument_router_lite" / "src"
sys.path.insert(0, str(SRC))

from defeasible_argument_router import build_router_report, route_argument, write_outputs


def base_argument():
    return {
        "argument_id": "arg_fusion_progression_001",
        "argument_family": "progression_without_terminal_value",
        "supporting_refs": ["right_channel_access"],
        "qualifying_refs": [],
        "contradicting_refs": [],
        "withdrawal_conditions": [
            "supporting_relation_disappears_in_same_context",
            "explicit_contradiction_becomes_stronger_than_support",
        ],
        "claim_ceiling": "argument_candidate_only",
        "status": "ARGUMENT_SUPPORTED",
        "decision": "READY_FOR_SAFE_ROUTER",
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_router_requires_core_argument_fields():
    argument = base_argument()
    for field in ["argument_id", "supporting_refs", "contradicting_refs", "withdrawal_conditions"]:
        argument.pop(field)
    argument["claim_ceiling"] = "claim_allowed"
    route = route_argument(argument)
    assert route["defeasible_state"] == "BLOCKED"
    assert route["missing_fields"] == ["argument_id", "supporting_refs", "contradicting_refs", "withdrawal_conditions", "claim_ceiling"]


def test_supported_route_requires_support_and_no_defeater():
    route = route_argument(base_argument())
    assert route["defeasible_state"] == "SUPPORTED"
    assert route["decision"] == "ROUTE_ARGUMENT_AS_SUPPORTED_CANDIDATE"
    assert route["absence_of_counter_evidence_proves_support"] is False


def test_qualifier_weakens_argument():
    argument = base_argument()
    argument["qualifying_refs"] = ["low_shot_volume"]
    route = route_argument(argument)
    assert route["defeasible_state"] == "WEAKENED"
    assert route["qualifier_count"] == 1


def test_upstream_contradiction_weakens_argument():
    argument = base_argument()
    argument["contradicting_refs"] = ["same_construct_opposite_direction"]
    route = route_argument(argument)
    assert route["defeasible_state"] == "WEAKENED"
    assert route["counter_evidence_refs"] == ["same_construct_opposite_direction"]


def test_runtime_counter_evidence_weakens_argument():
    argument = base_argument()
    argument["counter_evidence_refs"] = ["later_window_counter_ref"]
    route = route_argument(argument)
    assert route["defeasible_state"] == "WEAKENED"
    assert route["counter_evidence_count"] == 1


def test_matched_withdrawal_with_counter_evidence_withdraws():
    argument = base_argument()
    argument["counter_evidence_refs"] = ["later_window_counter_ref"]
    argument["triggered_withdrawal_conditions"] = ["supporting_relation_disappears_in_same_context"]
    route = route_argument(argument)
    assert route["defeasible_state"] == "WITHDRAWN"
    assert route["matched_withdrawal_conditions"] == ["supporting_relation_disappears_in_same_context"]


def test_withdrawal_without_counter_evidence_fails_closed():
    argument = base_argument()
    argument["triggered_withdrawal_conditions"] = ["supporting_relation_disappears_in_same_context"]
    route = route_argument(argument)
    assert route["defeasible_state"] == "BLOCKED"
    assert "withdrawal_requires_explicit_counter_evidence" in route["hard_block_hits"]


def test_undeclared_withdrawal_condition_fails_closed():
    argument = base_argument()
    argument["counter_evidence_refs"] = ["counter_ref"]
    argument["triggered_withdrawal_conditions"] = ["free_text_condition"]
    route = route_argument(argument)
    assert route["defeasible_state"] == "BLOCKED"
    assert "undeclared_withdrawal_condition_rejected" in route["hard_block_hits"]


def test_missing_support_fails_closed():
    argument = base_argument()
    argument["supporting_refs"] = []
    route = route_argument(argument)
    assert route["defeasible_state"] == "BLOCKED"
    assert "supporting_evidence_required" in route["hard_block_hits"]


def test_failed_upstream_argument_fails_closed():
    argument = base_argument()
    argument["status"] = "BLOCKED"
    argument["decision"] = "BLOCK_ARGUMENT"
    argument["hard_block_hits"] = ["upstream_error"]
    route = route_argument(argument)
    assert "upstream_argument_failed_closed" in route["hard_block_hits"]


def test_forbidden_upstream_output_fails_closed():
    argument = base_argument()
    argument["claim_text"] = "forbidden"
    route = route_argument(argument)
    assert route["defeasible_state"] == "BLOCKED"
    assert "claim_text" in route["forbidden_upstream_hits"]


def test_canonical_event_count_claim_fails_closed():
    argument = base_argument()
    argument["canonical_event_count"] = 100
    route = route_argument(argument)
    assert "canonical_event_count_claim_rejected" in route["hard_block_hits"]
    assert route["canonical_event_count"] == "UNKNOWN"


def test_router_does_not_emit_claim_or_truth():
    route = route_argument(base_argument())
    assert "claim_text" not in route
    assert route["claim_output_allowed"] is False
    assert route["report_language_allowed"] is False
    assert route["safe_sentence_allowed"] is False
    for key in [
        "tactical_truth", "dominance_truth", "control_truth", "coach_intention_truth",
        "off_ball_truth", "pitch_control_truth", "causal_truth", "quality_truth",
        "sequence_truth", "organism_truth",
    ]:
        assert route[key] is False


def test_report_counts_all_states():
    supported = base_argument()
    weakened = base_argument()
    weakened["argument_id"] = "arg_weakened"
    weakened["counter_evidence_refs"] = ["counter_ref"]
    withdrawn = base_argument()
    withdrawn["argument_id"] = "arg_withdrawn"
    withdrawn["counter_evidence_refs"] = ["counter_ref"]
    withdrawn["triggered_withdrawal_conditions"] = ["supporting_relation_disappears_in_same_context"]
    blocked = base_argument()
    blocked["argument_id"] = "arg_blocked"
    blocked["supporting_refs"] = []
    report = build_router_report([supported, weakened, withdrawn, blocked])
    assert report["state_counts"] == {"SUPPORTED": 1, "WEAKENED": 1, "WITHDRAWN": 1, "BLOCKED": 1}
    assert report["status"] == "FAIL_CLOSED"


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_argument()], "/sdcard/Download/HPFA/defeasible_argument_router_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_write_outputs(tmp_path):
    report = write_outputs([base_argument()], tmp_path)
    assert report["status"] == "SMOKE_PASS"
    assert (tmp_path / "defeasible_argument_router_lite_v1.json").exists()
    assert (tmp_path / "defeasible_argument_router_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "defeasible_argument_router_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["state_counts"]["SUPPORTED"] == 1


def test_no_sample_match_identity_leak():
    src = (SRC / "defeasible_argument_router.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
