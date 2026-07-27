from hpfa.modules.core.cross_role_relation_review_profiler_lite.src.cross_role_relation_review_profiler import build_review_profile


def _record(status="REVIEW_REQUIRED", reasons=None, family="PASS"):
    return {
        "resolved_relation_candidate_id": "crr_1",
        "source_relation_candidate_id": "src_1",
        "match_surface_binding_id": "msb_1",
        "relation_record_status": status,
        "relation_classification": "REVIEW_REQUIRED_PLAYER_TEAM_UNRESOLVED_CONTEXT",
        "source_roles": ["PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
        "action_family_candidate": family,
        "taxonomy_context_record_ids": [],
        "review_hits": reasons or ["unresolved_multi_family_relation_context"],
        "relation_candidate_is_event_truth": False,
        "cross_role_fusion_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def _payload(records):
    return {
        "module_id": "cross_role_relation_candidate_resolver_lite_v1",
        "match_surface_binding_id": "msb_1",
        "resolved_relation_candidates": records,
        "resolved_relation_candidate_count": len(records),
        "review_required_relation_count": sum(r["relation_record_status"] == "REVIEW_REQUIRED" for r in records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_profiles_review_reasons_without_resolving_relations():
    result = build_review_profile(_payload([_record()]))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["profiled_review_relation_count"] == 1
    assert result["review_reason_counts"] == {"unresolved_multi_family_relation_context": 1}
    assert result["review_relation_profiles"][0]["match_surface_binding_id"] == "msb_1"
    assert result["profile_resolves_relations"] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_pass_relations_are_not_added_to_review_profile():
    result = build_review_profile(_payload([_record(status="PASS_CANDIDATE_CLASSIFICATION")]))
    assert result["status"] == "PASS"
    assert result["profiled_review_relation_count"] == 0


def test_missing_review_reason_is_preserved_as_review():
    record = _record()
    record["review_hits"] = []
    result = build_review_profile(_payload([record]))
    assert result["review_reason_counts"] == {"review_reason_missing": 1}
    assert "review_reason_missing_present" in result["review_hits"]


def test_count_mismatch_fails_closed():
    payload = _payload([_record()])
    payload["review_required_relation_count"] = 0
    result = build_review_profile(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "review_required_relation_count_mismatch" in result["hard_block_hits"]


def test_event_truth_claim_fails_closed():
    record = _record()
    record["relation_candidate_is_event_truth"] = True
    result = build_review_profile(_payload([record]))
    assert result["status"] == "FAIL_CLOSED"


def test_production_release_claim_fails_closed():
    payload = _payload([_record()])
    payload["production_release"] = True
    result = build_review_profile(payload)
    assert result["status"] == "FAIL_CLOSED"


def test_family_reason_matrix_is_emitted():
    records = [_record(family="PASS"), _record(family="DUEL")]
    records[1]["resolved_relation_candidate_id"] = "crr_2"
    result = build_review_profile(_payload(records))
    assert result["family_reason_matrix"]["PASS"]["unresolved_multi_family_relation_context"] == 1
    assert result["family_reason_matrix"]["DUEL"]["unresolved_multi_family_relation_context"] == 1


def test_missing_top_level_match_binding_fails_closed():
    payload = _payload([_record()])
    payload["match_surface_binding_id"] = ""
    result = build_review_profile(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_surface_binding_id_missing" in result["hard_block_hits"]


def test_missing_relation_match_binding_fails_closed():
    record = _record()
    record.pop("match_surface_binding_id")
    result = build_review_profile(_payload([record]))
    assert result["status"] == "FAIL_CLOSED"
    assert "relation_match_surface_binding_id_missing:crr_1" in result["hard_block_hits"]


def test_mixed_relation_match_binding_fails_closed():
    record = _record()
    record["match_surface_binding_id"] = "msb_other"
    result = build_review_profile(_payload([record]))
    assert result["status"] == "FAIL_CLOSED"
    assert "relation_match_surface_binding_id_mismatch:crr_1" in result["hard_block_hits"]
