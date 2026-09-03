from pathlib import Path

from hpfa.modules.core.reciprocal_process_chain_lite.src.full_spine_packet_bridge import bridge_reciprocal_packets


def _reciprocal(_active_match_dir, _out_dir):
    return {
        "status": "REVIEW_REQUIRED",
        "reciprocal_process_chain_candidate_count": 3,
        "outcome_contrast_candidate_count": 2,
        "different_outcome_analogue_link_count": 1,
        "defeasible_process_finding_input_count": 3,
        "defeasible_process_finding_inputs": [
            {
                "defeasible_process_finding_input_id": "dfi_counter",
                "evidence_balance_state_candidate": "SUPPORT_AND_COUNTEREVIDENCE_VISIBLE_CANDIDATE",
                "dependent_support_chain_ids": ["rpc_support"],
                "counterevidence_chain_ids": ["rpc_counter"],
                "counter_search_scope_state": "PARTIAL_SCOPE_EVALUATED",
                "counter_search_complete_for_final_finding": False,
                "alternative_explanation_search_state": "NOT_EVALUATED",
                "falsifier_coverage_state": "PARTIAL",
            },
            {
                "defeasible_process_finding_input_id": "dfi_support",
                "evidence_balance_state_candidate": "DEPENDENT_SUPPORT_VISIBLE_NO_COUNTEREXAMPLE_CANDIDATE",
                "dependent_support_chain_ids": ["rpc_support_2"],
                "counterevidence_chain_ids": [],
                "counter_search_scope_state": "PARTIAL_SCOPE_EVALUATED",
                "counter_search_complete_for_final_finding": False,
                "alternative_explanation_search_state": "NOT_EVALUATED",
                "falsifier_coverage_state": "PARTIAL",
            },
            {
                "defeasible_process_finding_input_id": "dfi_isolated",
                "evidence_balance_state_candidate": "ISOLATED_VISIBLE_PROCESS_NO_ANALOGUE_CANDIDATE",
                "dependent_support_chain_ids": [],
                "counterevidence_chain_ids": [],
                "counter_search_scope_state": "PARTIAL_SCOPE_EVALUATED_NO_ANALOGUE",
                "counter_search_complete_for_final_finding": False,
                "alternative_explanation_search_state": "NOT_EVALUATED",
                "falsifier_coverage_state": "PARTIAL",
            },
        ],
        "reciprocal_c4_packet_candidates": [
            {"candidate_id": "rpc4_1", "claim_output_allowed": False},
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _packet_builder(candidate):
    return {
        "status": "SMOKE_PASS",
        "packet_id": candidate["candidate_id"],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _intelligence_runner(packet):
    return {
        "packet": packet,
        "fusion": {"status": "SMOKE_PASS"},
        "argument": {"status": "REVIEW_REQUIRED"},
        "route": {"status": "REVIEW_REQUIRED"},
        "graph": {"status": "REVIEW_REQUIRED"},
        "safe_sentence": {"status": "REVIEW_REQUIRED"},
        "report_block": {"status": "REVIEW_REQUIRED"},
        "output_contract": {"status": "REVIEW_REQUIRED", "claim_output_allowed": False},
        "assembly": {"status": "REVIEW_REQUIRED"},
    }


def test_bridge_reuses_existing_chain_without_opening_claims(tmp_path: Path):
    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path / "match",
        out_dir=tmp_path / "out",
        reciprocal_runner=_reciprocal,
        packet_builder=_packet_builder,
        intelligence_runner=_intelligence_runner,
    )

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["reciprocal_c4_packet_candidate_count"] == 1
    assert report["existing_packet_builder_admitted_count"] == 1
    assert report["claim_output_allowed_count"] == 0
    assert report["creates_parallel_engine"] is False
    assert report["creates_occurrence"] is False
    assert report["creates_episode"] is False
    assert report["creates_independent_evidence"] is False
    assert report["creates_final_finding"] is False
    assert report["active_match_evidence_pass"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False

    coverage = report["match_tomography_coverage"]
    assert coverage["finding_input_count"] == 3
    assert coverage["finding_inputs_with_counterevidence_count"] == 1
    assert coverage["finding_inputs_with_dependent_support_count"] == 2
    assert coverage["isolated_finding_input_count"] == 1
    assert coverage["counter_search_complete_for_final_finding_count"] == 0
    assert coverage["counter_search_incomplete_for_final_finding_count"] == 3
    assert coverage["alternative_explanation_not_evaluated_count"] == 3
    assert coverage["partial_falsifier_coverage_count"] == 3
    assert coverage["counter_search_scope_state_counts"] == {
        "PARTIAL_SCOPE_EVALUATED": 2,
        "PARTIAL_SCOPE_EVALUATED_NO_ANALOGUE": 1,
    }
    assert coverage["absence_of_counterevidence_is_confirmation"] is False
    assert coverage["counter_search_incomplete_never_confirms"] is True
    assert coverage["alternative_explanation_absence_is_not_evidence"] is True
    assert coverage["dependent_support_is_independent_vote"] is False
    assert coverage["finding_emitted"] is False
    assert coverage["claim_output_allowed"] is False
    assert coverage["canonical_event_count"] == "UNKNOWN"
    assert coverage["true_action_count"] == "UNKNOWN"
    assert coverage["production_release"] is False
    assert (tmp_path / "out" / "reciprocal_full_spine_packet_bridge_v1.json").is_file()


def test_bridge_fails_closed_with_reciprocal_failure(tmp_path: Path):
    def failed(_active_match_dir, _out_dir):
        return {
            "status": "FAIL_CLOSED",
            "reciprocal_c4_packet_candidates": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path / "match",
        out_dir=tmp_path / "out",
        reciprocal_runner=failed,
        packet_builder=_packet_builder,
        intelligence_runner=_intelligence_runner,
    )

    assert report["status"] == "FAIL_CLOSED"
    assert "reciprocal_process_chain_fail_closed" in report["hard_block_hits"]
    assert report["claim_output_allowed_count"] == 0
    assert report["match_tomography_coverage"]["finding_input_count"] == 0
    assert report["match_tomography_coverage"]["counter_search_complete_for_final_finding_count"] == 0
    assert report["match_tomography_coverage"]["counter_search_incomplete_for_final_finding_count"] == 0
    assert report["match_tomography_coverage"]["claim_output_allowed"] is False
    assert report["production_release"] is False
