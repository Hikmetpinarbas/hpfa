from hpfa.modules.core.visible_action_sequence_candidates_lite.src.derived_lineage_guard import (
    lineage_independent_support_count,
    resolve_lineage,
)


def test_same_observation_two_findings_one_claim_count_once():
    observed = resolve_lineage(
        "obs_1",
        parent_refs=[],
        derivation_type="OBSERVED",
    )
    index = {"obs_1": observed}

    finding_a = resolve_lineage(
        "finding_a",
        parent_refs=["obs_1"],
        derivation_type="PROJECT",
        lineage_index=index,
    )
    finding_b = resolve_lineage(
        "finding_b",
        parent_refs=["obs_1"],
        derivation_type="PROJECT",
        lineage_index=index,
    )
    index.update({"finding_a": finding_a, "finding_b": finding_b})
    claim = resolve_lineage(
        "claim_1",
        parent_refs=["finding_a", "finding_b"],
        derivation_type="NARRATIVE",
        lineage_index=index,
    )

    assert observed["root_refs"] == ["obs_1"]
    assert finding_a["root_refs"] == ["obs_1"]
    assert finding_b["root_refs"] == ["obs_1"]
    assert claim["root_refs"] == ["obs_1"]
    assert finding_a["lineage_group_id"] == finding_b["lineage_group_id"] == claim["lineage_group_id"]
    counted = lineage_independent_support_count([finding_a, finding_b, claim])
    assert counted["lineage_independent_support_count"] == 1
    assert counted["shared_root_candidates_collapsed"] is True
    assert counted["lineage_count_can_strengthen_existing_independent_support"] is False


def test_parent_relation_never_becomes_causality_or_temporal_order():
    observed = resolve_lineage("obs_1", parent_refs=[], derivation_type="OBSERVED")
    derived = resolve_lineage(
        "finding_1",
        parent_refs=["obs_1"],
        derivation_type="PROJECT",
        lineage_index={"obs_1": observed},
    )
    assert derived["parent_relation_is_causality"] is False
    assert derived["parent_relation_is_temporal_order"] is False
    assert derived["shared_root_is_independent_support"] is False
    assert derived["lineage_creates_new_evidence"] is False


def test_direct_self_parent_cycle_fails_closed():
    result = resolve_lineage(
        "finding_1",
        parent_refs=["finding_1"],
        derivation_type="PROJECT",
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["reason"] == "SELF_PARENT_CYCLE"


def test_indirect_cycle_fails_closed():
    index = {
        "a": {"parent_refs": ["b"], "root_refs": [], "derivation_type": "PROJECT"},
        "b": {"parent_refs": ["a"], "root_refs": [], "derivation_type": "FILTER"},
    }
    result = resolve_lineage(
        "claim_1",
        parent_refs=["a"],
        derivation_type="NARRATIVE",
        lineage_index=index,
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["reason"] == "LINEAGE_CYCLE_DETECTED"


def test_missing_parent_is_review_not_fabricated_root():
    result = resolve_lineage(
        "finding_1",
        parent_refs=["missing_obs"],
        derivation_type="PROJECT",
        lineage_index={},
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["root_refs"] == []
    assert result["unresolved_lineage_refs"] == ["missing_obs"]
    assert result["lineage_group_id"] is None


def test_multiple_proven_roots_stay_multiple_and_form_one_shared_group_signature():
    obs_a = resolve_lineage("obs_a", parent_refs=[], derivation_type="OBSERVED")
    obs_b = resolve_lineage("obs_b", parent_refs=[], derivation_type="OBSERVED")
    result = resolve_lineage(
        "relation_1",
        parent_refs=["obs_a", "obs_b"],
        derivation_type="RELATE",
        lineage_index={"obs_a": obs_a, "obs_b": obs_b},
    )
    assert result["status"] == "PASS"
    assert result["root_refs"] == ["obs_a", "obs_b"]
    assert result["lineage_group_id"].startswith("lin_")


def test_unknown_derivation_type_fails_closed():
    result = resolve_lineage(
        "finding_1",
        parent_refs=[],
        derivation_type="CAUSE",
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["reason"] == "DERIVATION_TYPE_NOT_ALLOWLISTED"
