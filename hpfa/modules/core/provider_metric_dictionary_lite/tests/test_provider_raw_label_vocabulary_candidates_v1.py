from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
REGISTRY = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "provider_metric_dictionary_lite"
    / "registry"
    / "provider_raw_label_vocabulary_candidates_v1.json"
)


def _load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_raw_label_vocabulary_is_reference_only_and_unique() -> None:
    payload = _load()
    assert payload["status"] == "REFERENCE_ONLY"
    rows = payload["labels"]
    assert payload["raw_label_count"] == len(rows) == 113
    normalized = [row["raw_label"].casefold().strip() for row in rows]
    assert len(normalized) == len(set(normalized))


def test_raw_label_vocabulary_cannot_create_metric_or_provider_truth() -> None:
    payload = _load()
    locks = payload["claim_locks"]
    assert locks["raw_label_is_metric_identity"] is False
    assert locks["historical_family_hint_is_provider_definition"] is False
    assert locks["phase_mapping_admitted"] is False
    assert locks["dimension_mapping_admitted"] is False
    assert locks["provider_identity_validated"] is False
    assert locks["comparison_allowed"] is False
    assert locks["metric_value_output_allowed"] is False
    assert locks["production_release"] is False
    for row in payload["labels"]:
        assert row["mapping_status"] == "REFERENCE_ONLY_UNMAPPED_LABEL"
        assert row["provider_identity"] == "UNKNOWN"
        assert row["metric_identity_admitted"] is False
        assert row["phase_mapping_admitted"] is False
        assert row["dimension_mapping_admitted"] is False
        assert "metric_id" not in row
        assert "hp_phase_proxy" not in row
        assert "hp_dimensions" not in row
