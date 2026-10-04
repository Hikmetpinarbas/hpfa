from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.observation_layer_admission import (
    L1,
    L2,
    L3,
    L6,
    L8,
    OBSERVATION_MODEL,
    assess_observation_contract,
)
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


def load(name: str):
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def build(dictionary, metric_policy=None):
    return build_dictionary_report(
        dictionary,
        load("provider_alias_registry_v1.json"),
        load("metric_derivation_registry_v1.json"),
        load("metric_conflict_queue_v1.json"),
        metric_policy=metric_policy or load("metric_registry_v1.json"),
        denominator_policy=load("metric_denominator_policy_v1.json"),
        aggregate_registry=json.loads(AGG.read_text(encoding="utf-8")),
    )


def test_rich_nonphysical_layers_are_not_tracking_only():
    assessment = assess_observation_contract({
        "metric_id": "spatiotemporal_progression_candidate",
        "event_only_compatible": False,
        "required_observation_layers": [L1, L2, L3, L6],
        "required_surface_semantics": [
            "action_family_admitted",
            "football_time_semantics_admitted",
            "coordinate_semantics_admitted",
            "visible_consequence_relation_admitted",
        ],
        "tracking_video_required": False,
    })
    assert assessment["status"] == "PASS"
    assert assessment["legacy_event_only_shadow_compatible"] is True
    assert assessment["event_only_is_product_ceiling"] is False
    assert assessment["observation_model"] == OBSERVATION_MODEL


def test_l8_requires_explicit_tracking_or_video():
    assessment = assess_observation_contract({
        "metric_id": "physical_closing_velocity_truth",
        "required_observation_layers": [L8],
        "required_surface_semantics": ["tracking_trajectory"],
        "tracking_video_required": False,
    })
    assert assessment["status"] == "FAIL_CLOSED"
    assert any(
        hit.startswith("tracking_video_requirement_missing_for_l8")
        for hit in assessment["hard_block_hits"]
    )


def test_rich_layers_require_declared_surface_semantics():
    assessment = assess_observation_contract({
        "metric_id": "opponent_response_candidate",
        "required_observation_layers": [L2, L6],
        "tracking_video_required": False,
    })
    assert assessment["status"] == "FAIL_CLOSED"
    assert any(
        hit.startswith("required_surface_semantics_missing")
        for hit in assessment["hard_block_hits"]
    )


def test_provider_row_legacy_flag_cannot_veto_zfgv_policy_contract():
    dictionary = load("provider_metric_dictionary_v1.json")
    dictionary["metrics"][0]["event_only_compatible"] = False

    report = build(dictionary)
    gap_types = {gap["gap_type"] for gap in report.get("hard_block_hits", [])}

    assert report["observation_model"] == "ZFGV_V1"
    assert "event_only_compatibility_required" not in gap_types
    assessed_ids = {
        item["metric_id"] for item in report["observation_contract_assessments"]
    }
    assert "surface_action_volume_candidate" in assessed_ids
    assert dictionary["metrics"][0]["metric_id"] not in assessed_ids


def test_invalid_zfgv_metric_policy_fails_closed_even_if_provider_row_looks_compatible():
    dictionary = load("provider_metric_dictionary_v1.json")
    dictionary["metrics"][0]["event_only_compatible"] = True
    metric_policy = load("metric_registry_v1.json")
    metric_policy["metrics"][0]["required_observation_layers"] = []

    report = build(dictionary, metric_policy=metric_policy)
    gap_types = {gap["gap_type"] for gap in report.get("hard_block_hits", [])}

    assert report["status"] == "FAIL_CLOSED"
    assert "observation_contract_invalid" in gap_types
    assessment = next(
        item
        for item in report["observation_contract_assessments"]
        if item["metric_id"] == "surface_action_volume_candidate"
    )
    assert assessment["status"] == "FAIL_CLOSED"


def test_no_sample_match_identity_leak():
    source = (
        ROOT
        / "hpfa"
        / "modules"
        / "core"
        / "provider_metric_dictionary_lite"
        / "src"
        / "observation_layer_admission.py"
    ).read_text(encoding="utf-8")
    for token in (
        "Genclerbirligi",
        "Fenerbahce",
        "15.08.2026",
        "Sporting",
        "Galatasaray",
        "09.09.2026",
    ):
        assert token not in source
