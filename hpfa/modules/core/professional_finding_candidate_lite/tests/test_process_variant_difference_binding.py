from hpfa.modules.core.professional_finding_candidate_lite.src.process_variant_difference_binding import (
    attach_process_variant_difference_explanations,
)


def _finding_payload():
    return {
        "module_id": "professional_finding_candidate_lite_v1",
        "status": "REVIEW_REQUIRED",
        "professional_finding_candidates": [
            {
                "professional_finding_candidate_id": "pf1",
                "process_family_signature_candidate": {
                    "anchor_action_families": ["PASS", "PROGRESSION"],
                    "response_action_families": ["RECOVERY"],
                },
                "uncertainty": {},
                "ANALYST_ACTION": "İlgili process örneklerini kontrol et.",
                "claim_output_allowed": False,
                "professional_finding_emitted": False,
            }
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _difference_payload():
    return {
        "status": "PASS",
        "process_variant_difference_explanations": [
            {
                "process_family_signature_candidate": {
                    "anchor_action_families": ["PROGRESSION", "PASS"],
                    "response_action_families": ["RECOVERY"],
                },
                "modal_resolution_class_candidate": "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT",
                "deviant_resolution_class_candidate": "ADVERSE_HANDOVER_VISIBLE_VARIANT",
                "visible_difference_candidates": [
                    {
                        "observation_dimension": "response_latency_median_candidate_seconds",
                        "modal_candidate": 1.2,
                        "deviant_candidate": 2.8,
                    },
                    {
                        "observation_dimension": "counter_response_action_family_presence_counts",
                        "modal_candidate": {"PASS": 2},
                        "deviant_candidate": {},
                    },
                ],
                "difference_is_causal_explanation": False,
                "right_censoring_used_as_counterevidence": False,
            }
        ],
        "right_censoring_used_as_counterevidence": False,
        "difference_is_causal_explanation": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_visible_variant_differences_are_bound_to_existing_finding_family():
    result = attach_process_variant_difference_explanations(_finding_payload(), _difference_payload())
    assert result["process_variant_difference_binding_status"] == "PASS"
    assert result["process_variant_difference_explanation_attached_finding_count"] == 1
    row = result["professional_finding_candidates"][0]
    assert row["visible_process_variant_difference_explanation_count"] == 1
    assert "response_latency_median_candidate_seconds" in row["process_variant_difference_analyst_summary_tr"][0]
    assert "nedensellik kanıtı değildir" in row["process_variant_difference_analyst_summary_tr"][0]
    assert "Modal ve ayrışan process örneklerini" in row["ANALYST_ACTION"]
    assert row["process_variant_difference_creates_independent_evidence"] is False
    assert row["right_censoring_used_as_process_counterevidence"] is False
    assert row["claim_output_allowed"] is False
    assert row["professional_finding_emitted"] is False


def test_unmatched_family_remains_valid_finding_without_fabricated_difference():
    payload = _difference_payload()
    payload["process_variant_difference_explanations"][0]["process_family_signature_candidate"] = {
        "anchor_action_families": ["CARRY"],
        "response_action_families": ["DUEL"],
    }
    result = attach_process_variant_difference_explanations(_finding_payload(), payload)
    row = result["professional_finding_candidates"][0]
    assert row["visible_process_variant_difference_explanation_count"] == 0
    assert row["process_variant_difference_analyst_summary_tr"] == []
    assert result["process_variant_difference_explanation_attached_finding_count"] == 0


def test_causal_or_censoring_lock_breach_fails_closed():
    for field in ("difference_is_causal_explanation", "right_censoring_used_as_counterevidence"):
        payload = _difference_payload()
        payload[field] = True
        result = attach_process_variant_difference_explanations(_finding_payload(), payload)
        assert result["status"] == "FAIL_CLOSED"
        assert result["process_variant_difference_binding_status"] == "FAIL_CLOSED"
        assert result["claim_output_allowed_count"] == 0
        assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    import inspect
    from hpfa.modules.core.professional_finding_candidate_lite.src import process_variant_difference_binding

    text = inspect.getsource(process_variant_difference_binding).casefold()
    for token in ("genclerbirligi", "fenerbahce", "15.08.2026", "galatasaray", "besiktas"):
        assert token not in text
