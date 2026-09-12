from hpfa.modules.core.observation_contract_lite.src.observation_contract import (
    L8,
    CAP_TRACKING_VIDEO_PHYSICAL,
    assess_observation_contract,
    normalize_dictionary_for_zfgv,
)


def _tracking_metric():
    return {
        "metric_id": "tracking_space_control_candidate",
        "required_observation_layers": [L8],
        "required_surface_semantics": ["tracking_surface_admitted"],
        "required_observation_capabilities": [CAP_TRACKING_VIDEO_PHYSICAL],
        "optional_observation_capabilities": [],
        "forbidden_without": ["TRACKING"],
        "tracking_video_required": True,
        "claim_ceiling": "TRACKING_BOUND_PHYSICAL_CANDIDATE_ONLY",
        "does_not_measure": ["coach_intention"],
        "forbidden_claims": ["causality"],
        "event_only_compatible": False,
    }


def test_explicit_zfgv_tracking_contract_is_not_blocked_by_event_only_flag():
    row = _tracking_metric()
    assessment = assess_observation_contract(row)
    assert assessment["status"] == "PASS"
    assert assessment["event_only_is_product_ceiling"] is False
    assert assessment["legacy_event_only_shadow_compatible"] is True
    assert assessment["required_observation_layers"] == [L8]
    assert CAP_TRACKING_VIDEO_PHYSICAL in assessment["required_observation_capabilities"]


def test_provider_dictionary_cannot_veto_explicit_zfgv_policy_capability():
    row = _tracking_metric()
    dictionary = {
        "metrics": [
            {
                "metric_id": row["metric_id"],
                "provider_definition": "provider_surface_only",
                "event_only_compatible": False,
            }
        ]
    }
    policy = {"metrics": [dict(row)]}

    normalized_dictionary, normalized_policy, assessments = normalize_dictionary_for_zfgv(
        dictionary,
        policy,
    )

    assert assessments[0]["status"] == "PASS"
    assert assessments[0]["assessment_scope"] == "HPFA_METRIC_POLICY"
    assert normalized_dictionary == dictionary
    assert normalized_policy is not None
    assert normalized_policy["metrics"][0]["event_only_compatible"] is True
    assert normalized_policy["metrics"][0]["required_observation_layers"] == [L8]
    assert normalized_policy["metrics"][0]["tracking_video_required"] is True


def test_no_sample_match_identity_leak():
    payload = repr(_tracking_metric())
    for forbidden in ("Genclerbirligi", "Fenerbahce", "Galatasaray", "15.08.2026"):
        assert forbidden not in payload
