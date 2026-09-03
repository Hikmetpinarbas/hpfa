from hpfa.modules.core.reciprocal_process_chain_lite.src.outcome_contrast import (
    attach_outcome_contrast,
    build_defeasible_process_finding_inputs,
    build_outcome_contrast_candidates,
)


def _chain(chain_id: str, response_consequence: str, counter_visible: bool) -> dict:
    return {
        "reciprocal_process_chain_candidate_id": chain_id,
        "anchor_action_family_counts": {"RECOVERY": 1},
        "response_action_family_counts": {"PASS": 1},
        "response_consequence_candidate_counts": {response_consequence: 1},
        "counter_response_consequence_candidate_counts": (
            {"SHOT_CANDIDATE": 1} if counter_visible else {}
        ),
        "counter_response_visible": counter_visible,
    }


def _payload(rows: list[dict]) -> dict:
    return {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "reciprocal_process_chain_candidates": rows,
        "reciprocal_process_chain_candidate_count": len(rows),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_same_process_signature_exposes_different_outcome_analogue_as_counterevidence() -> None:
    payload = _payload([
        _chain("rpc_a", "SAME_TEAM_CONTINUATION_CANDIDATE", True),
        _chain("rpc_b", "TURNOVER_CANDIDATE", False),
    ])
    result = build_outcome_contrast_candidates(payload)
    assert result["outcome_contrast_status"] == "PASS"
    assert result["outcome_contrast_candidate_count"] == 2
    first = next(row for row in result["outcome_contrast_candidates"] if row["reciprocal_process_chain_candidate_id"] == "rpc_a")
    assert first["different_visible_outcome_analogue_chain_ids"] == ["rpc_b"]
    assert first["counterevidence_candidate_present"] is True
    assert first["outcome_contrast_is_causal_truth"] is False
    assert first["outcome_contrast_is_tactical_success_truth"] is False


def test_different_process_family_is_not_used_as_outcome_analogue() -> None:
    a = _chain("rpc_a", "SHOT_CANDIDATE", True)
    b = _chain("rpc_b", "TURNOVER_CANDIDATE", False)
    b["anchor_action_family_counts"] = {"DRIBBLE": 1}
    result = build_outcome_contrast_candidates(_payload([a, b]))
    for row in result["outcome_contrast_candidates"]:
        assert row["different_visible_outcome_analogue_chain_ids"] == []


def test_same_outcome_is_support_not_counterevidence() -> None:
    payload = _payload([
        _chain("rpc_a", "SHOT_CANDIDATE", True),
        _chain("rpc_b", "SHOT_CANDIDATE", True),
    ])
    result = build_outcome_contrast_candidates(payload)
    first = next(row for row in result["outcome_contrast_candidates"] if row["reciprocal_process_chain_candidate_id"] == "rpc_a")
    assert first["same_visible_outcome_support_chain_ids"] == ["rpc_b"]
    assert first["different_visible_outcome_analogue_chain_ids"] == []
    assert first["counterevidence_candidate_present"] is False


def test_finding_input_preserves_support_and_counterevidence_without_emitting_finding() -> None:
    contrast = build_outcome_contrast_candidates(_payload([
        _chain("rpc_a", "SHOT_CANDIDATE", True),
        _chain("rpc_b", "SHOT_CANDIDATE", True),
        _chain("rpc_c", "TURNOVER_CANDIDATE", False),
    ]))
    result = build_defeasible_process_finding_inputs(contrast)
    row = next(item for item in result["defeasible_process_finding_inputs"] if item["reciprocal_process_chain_candidate_id"] == "rpc_a")
    assert row["dependent_support_chain_ids"] == ["rpc_b"]
    assert row["counterevidence_chain_ids"] == ["rpc_c"]
    assert row["evidence_balance_state_candidate"] == "SUPPORT_AND_COUNTEREVIDENCE_VISIBLE_CANDIDATE"
    assert row["finding_emitted"] is False
    assert row["support_links_are_independent_votes"] is False
    assert row["counterevidence_links_are_independent_votes"] is False


def test_no_visible_counterexample_is_not_confirmation() -> None:
    contrast = build_outcome_contrast_candidates(_payload([
        _chain("rpc_a", "SHOT_CANDIDATE", True),
        _chain("rpc_b", "SHOT_CANDIDATE", True),
    ]))
    result = build_defeasible_process_finding_inputs(contrast)
    row = next(item for item in result["defeasible_process_finding_inputs"] if item["reciprocal_process_chain_candidate_id"] == "rpc_a")
    assert row["counterevidence_chain_ids"] == []
    assert row["no_visible_counterexample_is_confirmation"] is False
    assert row["evidence_balance_state_candidate"] == "DEPENDENT_SUPPORT_VISIBLE_NO_COUNTEREXAMPLE_CANDIDATE"


def test_fail_closed_upstream_does_not_emit_contrasts_or_finding_inputs() -> None:
    contrast = build_outcome_contrast_candidates({
        "status": "FAIL_CLOSED",
        "reciprocal_process_chain_candidates": [_chain("rpc_a", "SHOT_CANDIDATE", True)],
    })
    assert contrast["outcome_contrast_status"] == "FAIL_CLOSED"
    assert contrast["outcome_contrast_candidate_count"] == 0
    finding = build_defeasible_process_finding_inputs(contrast)
    assert finding["finding_input_status"] == "FAIL_CLOSED"
    assert finding["defeasible_process_finding_input_count"] == 0


def test_attachment_preserves_claim_locks_and_no_independent_vote() -> None:
    result = attach_outcome_contrast(_payload([_chain("rpc_a", "SHOT_CANDIDATE", True)]))
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["outcome_contrast_is_independent_evidence"] is False
    assert result["finding_input_is_final_finding"] is False
    assert result["finding_input_is_independent_evidence"] is False


def test_no_sample_match_identity_leak() -> None:
    import inspect
    from hpfa.modules.core.reciprocal_process_chain_lite.src import outcome_contrast

    source = inspect.getsource(outcome_contrast)
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
