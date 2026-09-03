from pathlib import Path

from hpfa.modules.core.reciprocal_process_chain_lite.src.full_spine_packet_bridge import bridge_reciprocal_packets


def _safety_metadata() -> dict:
    return {
        "counter_search_scope": "SAME_ADMITTED_PROCESS_FAMILY_SIGNATURE_ONLY",
        "counter_search_scope_state": "PARTIAL_SCOPE_EVALUATED",
        "counter_search_peer_count": 2,
        "counter_search_evaluated_families": ["DIRECT_VISIBLE_OUTCOME_CONTRAST"],
        "counter_search_pending_families": [
            "CONTEXT_DEPENDENCE",
            "SEGMENT_ONLY",
            "PLAYER_OUTLIER",
            "THRESHOLD_SENSITIVITY",
            "OPPONENT_SYMMETRY",
            "FAILED_TRACE_SUPPORT",
            "DUPLICATE_REFLECTION_RISK",
            "ALTERNATIVE_EXPLANATION",
        ],
        "counter_search_complete_for_final_finding": False,
        "alternative_explanation_search_state": "NOT_EVALUATED",
        "alternative_explanation_required": True,
        "falsifier_coverage_state": "PARTIAL",
        "falsifier_families_evaluated": ["DIRECT_VISIBLE_OUTCOME_CONTRAST"],
        "falsifier_families_pending": [
            "CONTEXT_DEPENDENCE",
            "SEGMENT_ONLY",
            "PLAYER_OUTLIER",
            "THRESHOLD_SENSITIVITY",
            "OPPONENT_SYMMETRY",
            "FAILED_TRACE_SUPPORT",
            "DUPLICATE_REFLECTION_RISK",
            "ALTERNATIVE_EXPLANATION",
        ],
        "no_visible_counterexample_is_confirmation": False,
        "support_links_are_independent_votes": False,
        "counterevidence_links_are_independent_votes": False,
        "withdrawal_condition": "Withdraw if source reciprocal evidence is invalidated.",
        "finding_emitted": False,
        "claim_safety_metadata_is_truth_claim": False,
    }


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
            {
                "candidate_id": "rpc4_1",
                "claim_output_allowed": False,
                "claim_safety_metadata": _safety_metadata(),
            },
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
    metadata = packet["claim_safety_metadata"]
    assert metadata["counter_search_complete_for_final_finding"] is False
    assert "ALTERNATIVE_EXPLANATION" in metadata["counter_search_pending_families"]

    def stage(status="REVIEW_REQUIRED", **extra):
        return {"status": status, "claim_safety_metadata": metadata, **extra}

    return {
        "packet": packet,
        "fusion": stage("SMOKE_PASS"),
        "argument": stage(),
        "route": stage(),
        "graph": stage(),
        "lens": stage(),
        "safe_sentence": stage(),
        "report_block": stage(),
        "output_contract": stage(claim_output_allowed=False),
        "assembly": stage(),
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
    assert report["claim_safety_metadata_preserved_candidate_count"] == 1
    assert report["claim_safety_metadata_required_for_reciprocal_c4"] is True
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

    chain_row = report["chains"][0]
    expected_metadata = _safety_metadata()
    assert chain_row["claim_safety_metadata"] == expected_metadata
    assert chain_row["packet"]["claim_safety_metadata"] == expected_metadata
    for stage in ("packet", "fusion", "argument", "route", "graph", "lens", "safe_sentence", "report_block", "output_contract", "assembly"):
        assert chain_row["chain"][stage]["claim_safety_metadata"] == expected_metadata

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


def test_bridge_fails_closed_if_claim_safety_metadata_is_missing(tmp_path: Path):
    def missing_metadata(_active_match_dir, _out_dir):
        payload = _reciprocal(_active_match_dir, _out_dir)
        payload["reciprocal_c4_packet_candidates"] = [{"candidate_id": "rpc4_missing"}]
        return payload

    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path / "match",
        out_dir=tmp_path / "out_missing",
        reciprocal_runner=missing_metadata,
        packet_builder=_packet_builder,
        intelligence_runner=_intelligence_runner,
    )
    assert report["status"] == "FAIL_CLOSED"
    assert "reciprocal_claim_safety_metadata_missing_or_invalid" in report["hard_block_hits"]
    assert report["claim_safety_metadata_preserved_candidate_count"] == 0
    assert report["claim_output_allowed_count"] == 0


def test_bridge_fails_closed_if_partial_search_is_promoted_to_complete(tmp_path: Path):
    def promoted(_active_match_dir, _out_dir):
        payload = _reciprocal(_active_match_dir, _out_dir)
        metadata = _safety_metadata()
        metadata["counter_search_complete_for_final_finding"] = True
        payload["reciprocal_c4_packet_candidates"] = [{
            "candidate_id": "rpc4_promoted",
            "claim_safety_metadata": metadata,
        }]
        return payload

    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path / "match",
        out_dir=tmp_path / "out_promoted",
        reciprocal_runner=promoted,
        packet_builder=_packet_builder,
        intelligence_runner=_intelligence_runner,
    )
    assert report["status"] == "FAIL_CLOSED"
    assert "reciprocal_counter_search_completeness_lock_breached" in report["hard_block_hits"]


def test_bridge_fails_closed_if_other_safety_constraints_are_promoted(tmp_path: Path):
    mutations = [
        ("alternative_explanation_required", False, "reciprocal_alternative_explanation_requirement_removed"),
        ("alternative_explanation_search_state", "EVALUATED", "reciprocal_alternative_explanation_state_promoted"),
        ("falsifier_coverage_state", "COMPLETE", "reciprocal_falsifier_coverage_promoted"),
        ("counter_search_pending_families", [], "reciprocal_counter_search_pending_families_promoted_or_invalid"),
        ("falsifier_families_pending", [], "reciprocal_falsifier_pending_families_promoted_or_invalid"),
        ("withdrawal_condition", "", "reciprocal_withdrawal_condition_missing"),
        ("claim_safety_metadata_is_truth_claim", True, "reciprocal_claim_safety_metadata_promoted_to_truth"),
    ]
    for index, (field, value, expected_error) in enumerate(mutations):
        def promoted(_active_match_dir, _out_dir, field=field, value=value):
            payload = _reciprocal(_active_match_dir, _out_dir)
            metadata = _safety_metadata()
            metadata[field] = value
            payload["reciprocal_c4_packet_candidates"] = [{
                "candidate_id": f"rpc4_promoted_{field}",
                "claim_safety_metadata": metadata,
            }]
            return payload

        report = bridge_reciprocal_packets(
            active_match_dir=tmp_path / "match",
            out_dir=tmp_path / f"out_promoted_{index}",
            reciprocal_runner=promoted,
            packet_builder=_packet_builder,
            intelligence_runner=_intelligence_runner,
        )
        assert report["status"] == "FAIL_CLOSED"
        assert expected_error in report["hard_block_hits"]


def test_bridge_fails_closed_if_lens_drops_safety_metadata(tmp_path: Path):
    def broken_runner(packet):
        chain = _intelligence_runner(packet)
        chain["lens"].pop("claim_safety_metadata")
        return chain

    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path / "match",
        out_dir=tmp_path / "out_lens_missing",
        reciprocal_runner=_reciprocal,
        packet_builder=_packet_builder,
        intelligence_runner=broken_runner,
    )
    assert report["status"] == "FAIL_CLOSED"
    assert "claim_safety_metadata_not_preserved:lens" in report["hard_block_hits"]


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
