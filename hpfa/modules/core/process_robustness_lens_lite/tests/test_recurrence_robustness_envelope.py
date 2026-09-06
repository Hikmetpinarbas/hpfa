from hpfa.modules.core.process_robustness_lens_lite.src.recurrence_robustness_envelope import build_recurrence_robustness_envelopes


def _variant(vid, *, context="1", chronology="EXPLICIT_POSITIVE_TIME_LAYER_ORDER"):
    return {"trace_variant_id": vid, "chronology_confidence": chronology, "context_signature": {"period_candidate": context}}


def _payload(variants):
    return {"module_id":"partial_order_trace_variant_lite_v1","status":"PASS","partial_order_trace_variants":variants,"hard_block_hits":[],"canonical_event_count":"UNKNOWN","true_action_count":"UNKNOWN","production_release":False}


def _contrast(eligible, scores):
    anchor=eligible[0]
    return {"module_id":"trace_contrast_packet_lite_v1","status":"PASS","trace_contrast_packets":[{"anchor_trace_family":anchor,"eligible_trace_refs":eligible,"pair_eligibility_evidence":[{"trace_ref":ref,"eligibility_similarity":score} for ref,score in scores.items()]}],"hard_block_hits":[],"canonical_event_count":"UNKNOWN","true_action_count":"UNKNOWN","production_release":False}


def test_nominal_recurrence_not_only_output_and_threshold_sensitivity_reported():
    result=build_recurrence_robustness_envelopes(_payload([_variant("a"),_variant("b"),_variant("c")]),_contrast(["a","b","c"],{"b":0.85,"c":0.72}),tested_similarity_thresholds=(0.7,0.8,0.9))
    row=result["recurrence_robustness_envelopes"][0]
    assert row["nominal_recurrence"]==3
    assert row["min_supported_recurrence"]==1
    assert row["max_supported_recurrence"]==3
    assert row["robustness_state"]=="FRAGILE"
    assert len(row["threshold_sensitivity"])==3


def test_order_uncertainty_can_reduce_recurrence():
    variants=[_variant("a"),_variant("b",chronology="PARTIAL_EXPLICIT_TIME_EVIDENCE")]
    row=build_recurrence_robustness_envelopes(_payload(variants),_contrast(["a","b"],{"b":0.95}),tested_similarity_thresholds=(0.8,0.9))["recurrence_robustness_envelopes"][0]
    assert row["ordering_uncertainty_sensitivity"]["confirmed_order_recurrence"]==1
    assert row["robustness_state"]=="ORDER_SENSITIVE"


def test_context_variation_is_visible_but_not_causal_adaptation_truth():
    variants=[_variant("a",context="1"),_variant("b",context="2")]
    row=build_recurrence_robustness_envelopes(_payload(variants),_contrast(["a","b"],{"b":0.95}),tested_similarity_thresholds=(0.8,0.9))["recurrence_robustness_envelopes"][0]
    assert row["context_sensitivity"]["distinct_context_signature_count"]==2
    assert row["robustness_state"]=="CONTEXT_SENSITIVE"
    assert row["robustness_is_coach_intention_truth"] is False


def test_missing_player_and_reflection_evidence_are_not_invented():
    row=build_recurrence_robustness_envelopes(_payload([_variant("a"),_variant("b")]),_contrast(["a","b"],{"b":0.95}))["recurrence_robustness_envelopes"][0]
    assert row["player_removal_sensitivity"].startswith("NOT_EVALUATED")
    assert row["reflection_sensitivity"].startswith("NOT_EVALUATED")


def test_small_sample_returns_insufficient_evidence():
    row=build_recurrence_robustness_envelopes(_payload([_variant("a")]),_contrast(["a"],{}))["recurrence_robustness_envelopes"][0]
    assert row["robustness_state"]=="INSUFFICIENT_EVIDENCE"


def test_claim_locks_remain_closed():
    result=build_recurrence_robustness_envelopes(_payload([_variant("a"),_variant("b")]),_contrast(["a","b"],{"b":0.95}))
    assert result["robustness_is_tactical_pattern_truth"] is False
    assert result["canonical_event_count"]=="UNKNOWN"
    assert result["true_action_count"]=="UNKNOWN"
    assert result["production_release"] is False
