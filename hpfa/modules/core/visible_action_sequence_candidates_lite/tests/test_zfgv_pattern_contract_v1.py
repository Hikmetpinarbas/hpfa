import json
from pathlib import Path

CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "contract"
    / "zfgv_pattern_contract_v1.json"
)

REQUIRED_PATTERN_FIELDS = {
    "pattern_id",
    "pattern_question",
    "required_observation_families",
    "ordered_relation_requirement",
    "allowed_same_time_semantics",
    "actor_bindings",
    "process_family_requirement",
    "time_window",
    "spatial_requirement",
    "outcome_requirement",
    "counterexample_definition",
    "claim_ceiling",
    "forbidden_inference",
    "withdrawal_conditions",
    "degraded_behavior",
    "current_owner_components",
}


def _payload():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_pattern_contract_is_declarative_and_not_parallel_engine():
    payload = _payload()
    assert payload["contract_role"] == "DECLARATIVE_PATTERN_QUESTION_CONTRACT_ONLY"
    assert payload["execution_owner"] == "visible_action_sequence_candidates_lite_existing_sequence_variant_spine"
    assert payload["creates_parallel_engine"] is False
    assert payload["creates_new_evidence"] is False
    assert payload["can_authorize_emit"] is False
    assert payload["can_strengthen_claim_ceiling"] is False


def test_pattern_contracts_have_noncompensating_safety_fields():
    payload = _payload()
    patterns = payload["patterns"]
    assert len(patterns) >= 4
    ids = [row["pattern_id"] for row in patterns]
    assert len(ids) == len(set(ids))
    for row in patterns:
        assert REQUIRED_PATTERN_FIELDS <= set(row)
        assert row["required_observation_families"]
        assert row["forbidden_inference"]
        assert row["withdrawal_conditions"]
        assert row["current_owner_components"]
        assert row["claim_ceiling"].startswith("MATCH_LOCAL_")
        assert "CAUSALITY" in row["forbidden_inference"]


def test_set_piece_contract_rejects_unbounded_second_ball_promotion():
    payload = _payload()
    row = next(
        item for item in payload["patterns"]
        if item["pattern_id"] == "SET_PIECE_TO_BOUNDED_FIRST_VISIBLE_STATE_V1"
    )
    assert row["time_window"] == "DECLARED_OCCURRENCE_CONSEQUENCE_MAXIMUM_HORIZON"
    assert "SECOND_BALL_TRUTH" in row["forbidden_inference"]
    assert "RECYCLE_TRUTH" in row["forbidden_inference"]
    assert "OUTSIDE_HORIZON" in row["degraded_behavior"]


def test_access_terminal_contract_forbids_rate_without_denominator():
    payload = _payload()
    row = next(
        item for item in payload["patterns"]
        if item["pattern_id"] == "POSITIONAL_ACCESS_TO_TERMINAL_CONTEXT_V1"
    )
    assert "CONVERSION_EFFICIENCY_WITHOUT_ELIGIBLE_DENOMINATOR" in row["forbidden_inference"]
    assert row["degraded_behavior"].endswith("EMIT_NO_RATE")


def test_contract_truth_locks_remain_closed():
    locks = _payload()["truth_locks"]
    assert all(value is False for value in locks.values())
