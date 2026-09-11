from hpfa.modules.core.analyst_report_block_composer_lite.src.process_variant_difference_report_projection import compose_process_variant_difference_report


def _finding_payload():
    return {
        "module_id": "professional_finding_candidate_lite_v1",
        "status": "PASS",
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "professional_finding_candidates": [
            {
                "professional_finding_candidate_id": "pf_test_1",
                "ANALYST_ACTION": "72-75 ile 75-78 aralıklarını aynı ölçütlerle karşılaştır.",
                "visible_process_variant_difference_explanations": [
                    {
                        "modal_resolution_class_candidate": "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT",
                        "deviant_resolution_class_candidate": "ADVERSE_HANDOVER_VISIBLE_VARIANT",
                        "visible_difference_candidates": [
                            {
                                "observation_dimension": "response_latency_median_candidate_seconds",
                                "modal_candidate": 2.0,
                                "deviant_candidate": 5.0,
                            },
                            {
                                "observation_dimension": "counter_response_visible_count",
                                "modal_candidate": 2,
                                "deviant_candidate": 0,
                            },
                        ],
                        "safe_meaning": "Observed match-local difference only.",
                        "alternative_explanations": ["SMALL_COHORT"],
                        "difference_is_causal_explanation": False,
                        "difference_is_tactical_adaptation_truth": False,
                        "difference_is_coach_intention_truth": False,
                        "right_censoring_used_as_counterevidence": False,
                    }
                ],
            }
        ],
    }


def test_projects_normal_deviant_visible_difference_and_analyst_action():
    out = compose_process_variant_difference_report(_finding_payload())
    assert out["status"] == "PASS"
    assert out["report_block_count"] == 1
    block = out["report_blocks"][0]
    assert "NORMAL VARYANT" in block["report_block_candidate_tr"]
    assert "AYRIŞAN VARYANT" in block["report_block_candidate_tr"]
    assert "GÖRÜNÜR FARK" in block["report_block_candidate_tr"]
    assert "ANALİST AKSİYONU" in block["report_block_candidate_tr"]
    assert "rakip görünür cevabının zamanlaması" in block["visible_difference_tr"]
    assert block["difference_is_causal_explanation"] is False
    assert block["production_release"] is False


def test_no_bound_difference_does_not_invent_report_block():
    payload = _finding_payload()
    payload["professional_finding_candidates"][0]["visible_process_variant_difference_explanations"] = []
    out = compose_process_variant_difference_report(payload)
    assert out["status"] == "NO_ELIGIBLE_PROCESS_VARIANT_DIFFERENCE_REPORT_BLOCK"
    assert out["report_block_count"] == 0


def test_causal_or_censored_difference_is_not_projected():
    payload = _finding_payload()
    row = payload["professional_finding_candidates"][0]["visible_process_variant_difference_explanations"][0]
    row["difference_is_causal_explanation"] = True
    out = compose_process_variant_difference_report(payload)
    assert out["report_block_count"] == 0

    payload = _finding_payload()
    row = payload["professional_finding_candidates"][0]["visible_process_variant_difference_explanations"][0]
    row["right_censoring_used_as_counterevidence"] = True
    out = compose_process_variant_difference_report(payload)
    assert out["report_block_count"] == 0


def test_release_and_count_locks_fail_closed():
    payload = _finding_payload()
    payload["production_release"] = True
    out = compose_process_variant_difference_report(payload)
    assert out["status"] == "FAIL_CLOSED"
    assert out["report_block_count"] == 0


def test_no_sample_match_identity_leak():
    import inspect
    from hpfa.modules.core.analyst_report_block_composer_lite.src import process_variant_difference_report_projection as module

    source = inspect.getsource(module).lower()
    assert "gençlerbirliği" not in source
    assert "fenerbahçe" not in source
    assert "15.08.2026" not in source
