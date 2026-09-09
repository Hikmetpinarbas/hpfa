from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import (
    build_dictionary_report,
)

ROOT = Path(__file__).resolve().parents[5]
CONFIG = ROOT / "configs" / "metrics"
AGG = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "aggregate_definition_alignment_lite"
    / "registry"
    / "sportsbase_aggregate_definition_candidates_v1.json"
)


def _load(name: str):
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def _build(dictionary, metric_policy):
    return build_dictionary_report(
        dictionary,
        _load("provider_alias_registry_v1.json"),
        _load("metric_derivation_registry_v1.json"),
        _load("metric_conflict_queue_v1.json"),
        metric_policy=metric_policy,
        denominator_policy=_load("metric_denominator_policy_v1.json"),
        aggregate_registry=json.loads(AGG.read_text(encoding="utf-8")),
    )


def test_bound_explicit_zfgv_contract_is_authoritative_over_legacy_event_only_flag():
    dictionary = _load("provider_metric_dictionary_v1.json")
    metric_policy = _load("metric_registry_v1.json")
    row = next(x for x in dictionary["metrics"] if x["metric_id"] == "pass_completion_rate")

    # This legacy compatibility field must not be the product-wide admission ceiling.
    row["event_only_compatible"] = False

    report = _build(dictionary, metric_policy)
    hard_types = {gap["gap_type"] for gap in report.get("hard_block_hits", [])}

    assert "event_only_compatibility_required" not in hard_types
    assert "pass_completion_rate" in report["observation_contract_inherited_metric_ids"]
    assessment = next(
        item
        for item in report["observation_contract_assessments"]
        if item["metric_id"] == "pass_completion_rate"
    )
    assert assessment["event_only_is_product_ceiling"] is False
    assert assessment["capability_manifest_state"] == "EXPLICIT_CAPABILITY_MANIFEST"
    assert "ACTION" in assessment["required_observation_capabilities"]
    assert "ACTOR" in assessment["required_observation_capabilities"]
    assert "PROVENANCE" in assessment["required_observation_capabilities"]


def test_invalid_inherited_zfgv_contract_still_fails_closed():
    dictionary = _load("provider_metric_dictionary_v1.json")
    metric_policy = _load("metric_registry_v1.json")
    policy = next(
        x for x in metric_policy["metrics"] if x["metric_id"] == "pass_completion_rate_candidate"
    )
    policy["required_observation_capabilities"] = ["ACTION", "ACTOR", "UNKNOWN_CAPABILITY"]

    report = _build(dictionary, metric_policy)

    assert report["status"] == "FAIL_CLOSED"
    details = [str(gap.get("detail")) for gap in report.get("hard_block_hits", [])]
    assert any("unknown_required_observation_capability" in detail for detail in details)


def test_no_sample_match_identity_leak():
    source = (
        ROOT
        / "hpfa"
        / "modules"
        / "core"
        / "provider_metric_dictionary_lite"
        / "src"
        / "provider_metric_dictionary.py"
    ).read_text(encoding="utf-8")
    for token in (
        "Genclerbirligi",
        "Fenerbahce",
        "Galatasaray",
        "Roma",
        "Atalanta",
        "15.08.2026",
    ):
        assert token not in source
