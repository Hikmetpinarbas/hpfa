from __future__ import annotations

import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[5] / "canon" / "football_action_process_grammar_v1.json"


def _load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_registry_has_closed_classes_and_unique_ids() -> None:
    payload = _load()
    classes = set(payload["classes"])
    rows = payload["entries"]
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert {"ACTION", "QUALIFIER", "OUTCOME", "RELATION", "PROCESS", "META"}.issubset(classes)
    assert all(row["class"] in classes for row in rows)


def test_core_semantic_distinctions_are_explicit() -> None:
    rows = {row["id"]: row for row in _load()["entries"]}
    assert rows["PASS"]["class"] == "ACTION"
    assert rows["ASSIST"]["class"] == "RELATION"
    assert rows["GOAL"]["class"] == "OUTCOME"
    assert rows["TRANSITION_ATTACK"]["class"] == "PROCESS"
    assert rows["PROGRESSIVE"]["class"] == "QUALIFIER"
    assert rows["RECOVERY"]["id"] != rows["INTERCEPTION"]["id"]
    assert rows["TACKLE"]["id"] != rows["RECOVERY"]["id"]


def test_provider_label_and_same_time_do_not_become_truth_authority() -> None:
    payload = _load()
    assert payload["provider_binding_policy"]["provider_label_is_canonical_truth"] is False
    assert payload["provider_binding_policy"]["same_occurrence_facets_do_not_increase_true_action_count"] is True
    assert "SAME TIMESTAMP != TOTAL ORDER" in payload["truth_locks"]
    assert payload["production_release"] is False


def test_metric_binding_requires_estimand_and_denominator_semantics() -> None:
    required = set(_load()["metric_binding_required_fields"])
    assert {"football_question", "construct_id", "numerator", "eligible_denominator", "unit_of_analysis", "claim_ceiling"}.issubset(required)


def test_tracking_boundaries_are_preserved() -> None:
    rows = {row["id"]: row for row in _load()["entries"]}
    assert any("physical pressure geometry" in item for item in rows["PRESSURE_ACTION_EXPLICIT"]["forbidden_inferences"])
    assert any("true speed" in item for item in rows["CARRY"]["forbidden_inferences"])


def test_registry_has_broad_v1_coverage() -> None:
    payload = _load()
    assert len(payload["entries"]) >= 90
    families = {row["family"] for row in payload["entries"]}
    assert {"BALL_TRANSFER", "BALL_TRANSPORT", "FINISHING", "DEFENSIVE_DISRUPTION", "POSSESSION_CHANGE", "RESTART", "GOALKEEPER_ACTION", "PROCESS", "RELATION"}.issubset(families)
