from hpfa.modules.core.professional_finding_candidate_lite.src.context_conditioned_trace_deviation import build_context_conditioned_trace_deviations


def _variant(vid, period, outcome, *, deps=None, start="CONTINUATION", end="PERIOD_END", team="TEAM_A"):
    return {
        "trace_variant_id":vid,
        "action_family_signature":[{"action_family_candidate":"PASS","count":1}],
        "ordering_completeness":"LAYER_ORDER_CONFIRMED_INTERNAL_SINGLETONS",
        "context_signature":{
            "period_candidate":period,
            "start_reason_candidate":start,
            "end_reason_candidate":end,
            "team_identity_candidate_id":team,
        },
        "outcome_signature":[{"outcome_candidate":outcome,"count":1}],
        "dependency_group_refs":deps or [],
    }


def _payload(rows):
    return {"module_id":"partial_order_trace_variant_lite_v1","status":"PASS","partial_order_trace_variants":rows,"hard_block_hits":[],"canonical_event_count":"UNKNOWN","true_action_count":"UNKNOWN","production_release":False}


def test_context_missing_not_zero_and_excluded():
    rows=[_variant("a","1","X"),_variant("b","2","Y"),_variant("m","","X")]
    result=build_context_conditioned_trace_deviations(_payload(rows),context_dimension="period_candidate",baseline_context_value="1",comparison_context_value="2")
    assert result["missing_context_trace_refs"]==["m"]
    row=result["context_conditioned_trace_deviations"][0]
    assert row["uncertainty"]["missing_context_is_zero"] is False


def test_context_cohorts_preserve_dependency():
    rows=[_variant("a","1","X",deps=["d1"]),_variant("b","2","Y",deps=["d1"])]
    row=build_context_conditioned_trace_deviations(_payload(rows),context_dimension="period_candidate",baseline_context_value="1",comparison_context_value="2")["context_conditioned_trace_deviations"][0]
    assert row["dependency_summary"]["shared_dependency_group_refs"]==["d1"]
    assert row["dependency_summary"]["independence_proven"] is False


def test_small_context_cohort_warns():
    rows=[_variant("a","1","X"),_variant("b","2","Y")]
    result=build_context_conditioned_trace_deviations(_payload(rows),context_dimension="period_candidate",baseline_context_value="1",comparison_context_value="2")
    assert result["status"]=="REVIEW_REQUIRED"
    assert result["context_conditioned_trace_deviations"][0]["sample_warning"]=="SMALL_CONTEXT_COHORT_REVIEW_REQUIRED"


def test_context_difference_not_causality_or_adaptation():
    rows=[_variant("a1","1","X"),_variant("a2","1","X"),_variant("b1","2","Y"),_variant("b2","2","Y")]
    row=build_context_conditioned_trace_deviations(_payload(rows),context_dimension="period_candidate",baseline_context_value="1",comparison_context_value="2")["context_conditioned_trace_deviations"][0]
    assert row["outcome_difference"] is True
    assert row["context_difference_is_causality_truth"] is False
    assert row["context_difference_is_tactical_adaptation_truth"] is False
    assert row["context_difference_is_coach_intention_truth"] is False


def test_team_identity_scopes_trace_family_and_prevents_cross_team_context_mix():
    rows=[
        _variant("a1","1","X",team="TEAM_A"),
        _variant("a2","1","X",team="TEAM_A"),
        _variant("b1","2","Y",team="TEAM_B"),
        _variant("b2","2","Y",team="TEAM_B"),
    ]
    result=build_context_conditioned_trace_deviations(_payload(rows),context_dimension="period_candidate",baseline_context_value="1",comparison_context_value="2")
    assert result["context_conditioned_trace_deviation_count"]==0
    assert "no_trace_family_with_both_context_cohorts" in result["review_hits"]


def test_conditioned_end_reason_not_reused_as_sequence_difference():
    rows=[
        _variant("a1","1","X",start="CONTINUATION",end="LOSS_BOUNDARY"),
        _variant("a2","1","X",start="CONTINUATION",end="LOSS_BOUNDARY"),
        _variant("b1","1","X",start="CONTINUATION",end="PERIOD_END"),
        _variant("b2","1","X",start="CONTINUATION",end="PERIOD_END"),
    ]
    row=build_context_conditioned_trace_deviations(_payload(rows),context_dimension="end_reason_candidate",baseline_context_value="LOSS_BOUNDARY",comparison_context_value="PERIOD_END")["context_conditioned_trace_deviations"][0]
    assert row["sequence_difference"] is False
    assert row["sequence_distribution_excludes_conditioned_dimension"] is True
    assert row["effect_descriptor"]=="NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION"


def test_unsupported_context_dimension_fails_closed():
    result=build_context_conditioned_trace_deviations(_payload([_variant("a","1","X")]),context_dimension="score_state",baseline_context_value="0-0",comparison_context_value="1-0")
    assert result["status"]=="FAIL_CLOSED"
    assert any(x.startswith("unsupported_context_dimension") for x in result["hard_block_hits"])


def test_claim_locks_preserved():
    rows=[_variant("a","1","X"),_variant("b","2","X")]
    result=build_context_conditioned_trace_deviations(_payload(rows),context_dimension="period_candidate",baseline_context_value="1",comparison_context_value="2")
    assert result["canonical_event_count"]=="UNKNOWN"
    assert result["true_action_count"]=="UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    from pathlib import Path
    text=Path("hpfa/modules/core/professional_finding_candidate_lite/src/context_conditioned_trace_deviation.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi","Fenerbahce","15.08.2026"):
        assert token not in text
