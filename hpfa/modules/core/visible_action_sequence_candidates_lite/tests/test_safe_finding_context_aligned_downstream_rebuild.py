import json

import safe_finding_admission_current_v1 as runner


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _sequence_payload():
    return {
        "dependency_aware_partial_order_similarity_pairs": [
            {
                "partial_order_similarity_pair_id": "pair_1",
                "comparison_eligible": True,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _install_common_stubs(monkeypatch):
    def apply_context(sequence, process, consequence):
        result = dict(sequence)
        pairs = [dict(row) for row in sequence["dependency_aware_partial_order_similarity_pairs"]]
        pairs[0]["comparison_eligible"] = False
        result["dependency_aware_partial_order_similarity_pairs"] = pairs
        result["process_comparison_context_consumed"] = True
        result["process_comparison_context_binding_state"] = "TEST_CONTEXT_APPLIED"
        result["process_comparison_context_lowered_pair_count"] = 1
        return result

    monkeypatch.setattr(runner, "apply_process_context_to_comparison", apply_context)
    monkeypatch.setattr(
        runner,
        "build_comparable_outcome_counterevidence",
        lambda payload: {
            "status": "PASS",
            "comparable_outcome_counterevidence_records": [],
            "comparable_outcome_counterevidence_record_count": 0,
            "comparable_outcome_contrast_state_counts": {},
            "comparison_eligible_record_count": 0,
            "comparable_counterevidence_candidate_count": 0,
            "safe_finding_handoff_candidates": [],
            "safe_finding_handoff_candidate_count": 0,
            "safe_finding_handoff_finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_ceiling": "TEST",
            "safe_finding_handoff_claim_ceiling": "TEST",
        },
    )

    def grammar(payload):
        assert payload["dependency_aware_partial_order_similarity_pairs"][0]["comparison_eligible"] is False
        return {
            "status": "PASS",
            "supported_sequence_grammar_alignment_count": 0,
            "marker": "fresh_grammar",
        }

    def process_variant(payload, grammar_payload):
        assert grammar_payload["marker"] == "fresh_grammar"
        return {
            "status": "REVIEW_REQUIRED",
            "observable_process_variant_binding_count": 0,
            "observable_process_variant_family_count": 0,
            "grammar_stable_visible_outcome_variation_family_count": 0,
            "marker": "fresh_process",
        }

    def feature_delta(payload, process_payload, state_payload, consequence_payload):
        assert process_payload["marker"] == "fresh_process"
        assert state_payload["status"] == "PASS"
        return {
            "status": "REVIEW_REQUIRED",
            "grammar_stable_variant_feature_delta_record_count": 0,
            "marker": "fresh_feature",
        }

    def enrich(payload, feature_payload, process_payload, consequence_payload):
        assert feature_payload["marker"] == "fresh_feature"
        enriched = dict(feature_payload)
        enriched["process_participation_context_enrichment_consumed"] = True
        enriched["process_participation_context_binding_state"] = "TEST_ENRICHED"
        enriched["process_context_feature_difference_appended_count"] = 0
        return enriched

    monkeypatch.setattr(runner, "build_supported_sequence_grammar_alignment", grammar)
    monkeypatch.setattr(runner, "build_observable_process_variant_binding", process_variant)
    monkeypatch.setattr(runner, "build_grammar_stable_variant_feature_delta", feature_delta)
    monkeypatch.setattr(runner, "apply_process_participation_context", enrich)
    monkeypatch.setattr(
        runner,
        "build_variant_feature_challenge_projection",
        lambda feature, process: {"status": "REVIEW_REQUIRED", "marker": process.get("marker")},
    )
    monkeypatch.setattr(
        runner,
        "build_safe_finding_admission",
        lambda payload: {
            "status": "REVIEW_REQUIRED",
            "safe_finding_admission_decisions": [],
            "safe_finding_admission_decision_count": 0,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
        },
    )
    monkeypatch.setattr(
        runner,
        "apply_variant_feature_challenge_to_admission",
        lambda payload, base, challenge, process: base,
    )
    monkeypatch.setattr(
        runner,
        "build_puzzle_finding_contract",
        lambda payload, admission: {
            "status": "REVIEW_REQUIRED",
            "puzzle_finding_contract_version": "PUZZLE_FINDING_V1",
            "puzzle_finding_count": 0,
            "puzzle_finding_status_counts": {},
            "bound_puzzle_ids": [],
        },
    )


def test_context_filter_rebuilds_recurrence_chain_before_safe_finding(tmp_path, monkeypatch):
    _install_common_stubs(monkeypatch)
    sequence_path = tmp_path / "visible_action_sequence_candidates_lite_v1.json"
    _write(sequence_path, _sequence_payload())
    _write(tmp_path / runner.PROCESS_PARTICIPATION_NAME, {"status": "PASS"})
    _write(tmp_path / runner.OCCURRENCE_CONSEQUENCE_NAME, {"status": "PASS"})
    _write(tmp_path / runner.OCCURRENCE_STATE_TRANSITION_NAME, {"status": "PASS"})
    _write(tmp_path / runner.PROCESS_VARIANT_NAME, {"status": "REVIEW_REQUIRED", "marker": "stale_process"})
    _write(tmp_path / runner.FEATURE_DELTA_NAME, {"status": "REVIEW_REQUIRED", "marker": "stale_feature"})

    result = runner.runtime_write_outputs(sequence_path, tmp_path)

    assert result["process_context_downstream_recomputed"] is True
    assert result["process_context_stale_process_variant_surface_reused"] is False
    assert result["context_aligned_process_variant_binding_count"] == 0
    refreshed_process = json.loads((tmp_path / runner.PROCESS_VARIANT_NAME).read_text(encoding="utf-8"))
    refreshed_feature = json.loads((tmp_path / runner.FEATURE_DELTA_NAME).read_text(encoding="utf-8"))
    assert refreshed_process["marker"] == "fresh_process"
    assert refreshed_feature["marker"] == "fresh_feature"


def test_context_filter_fails_closed_instead_of_reusing_stale_family_when_state_surface_missing(tmp_path, monkeypatch):
    _install_common_stubs(monkeypatch)
    sequence_path = tmp_path / "visible_action_sequence_candidates_lite_v1.json"
    _write(sequence_path, _sequence_payload())
    _write(tmp_path / runner.PROCESS_PARTICIPATION_NAME, {"status": "PASS"})
    _write(tmp_path / runner.OCCURRENCE_CONSEQUENCE_NAME, {"status": "PASS"})
    _write(tmp_path / runner.PROCESS_VARIANT_NAME, {"status": "REVIEW_REQUIRED", "marker": "stale_process"})
    _write(tmp_path / runner.FEATURE_DELTA_NAME, {"status": "REVIEW_REQUIRED", "marker": "stale_feature"})

    result = runner.runtime_write_outputs(sequence_path, tmp_path)

    assert result["status"] == "FAIL_CLOSED"
    assert "process_context_downstream_recompute_fail_closed" in result["hard_block_hits"]
    assert result["process_context_downstream_recomputed"] is False
