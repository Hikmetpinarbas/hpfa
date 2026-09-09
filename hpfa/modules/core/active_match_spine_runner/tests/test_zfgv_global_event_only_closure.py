from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_current_postmatch_product_model_is_zfgv_not_global_event_only() -> None:
    registry = _json("configs/metrics/metric_registry_v1.json")
    ledger = _json("docs/governance/HPFA_EVENT_ONLY_MIGRATION_LEDGER_V1.json")

    assert registry["observation_model"] == "ZFGV_MULTI_SURFACE_FOOTBALL_OBSERVATION_FABRIC"
    assert registry["global_event_only_gate"] is False
    assert registry["admission_rule"] == "required_observation_capabilities_subset_of_admitted_capabilities"
    assert ledger["status"] == "CLOSED_FOR_CURRENT_SINGLE_MATCH_POSTMATCH_SCOPE"
    assert ledger["global_event_only_product_gate_allowed"] is False
    assert ledger["scope_boundary"] == "CURRENT_SINGLE_MATCH_POSTMATCH_ONLY"


def test_event_only_compatibility_is_legacy_metadata_not_metric_admission_authority() -> None:
    registry = _json("configs/metrics/metric_registry_v1.json")
    assert registry["metrics"]
    for row in registry["metrics"]:
        assert isinstance(row.get("required_observation_capabilities"), list)
        assert row["required_observation_capabilities"]
        assert row.get("event_only_compatible_role") == "LEGACY_COMPATIBILITY_METADATA_ONLY"


def test_runtime_metric_governance_uses_current_zfgv_capability_admission() -> None:
    source = (ROOT / "hpfa/modules/core/active_match_spine_runner/src/metric_governance_bridge.py").read_text(encoding="utf-8")
    admission = (ROOT / "hpfa/modules/core/active_match_spine_runner/src/zfgv_runtime_capability_admission.py").read_text(encoding="utf-8")

    assert "build_runtime_capability_admission" in source
    assert "REQUIRED_CAPABILITIES_SUBSET_OF_ADMITTED_CAPABILITIES" in source
    assert "ELIGIBLE_REQUIRED_CAPABILITIES_PRESENT" in source
    assert "NOT_ELIGIBLE_MISSING_REQUIRED_CAPABILITIES" in source
    assert "CURRENT_SINGLE_MATCH_ONLY" in admission
    assert '"metric_value_output_allowed": False' in admission
    assert '"construct_truth_granted": False' in admission
    assert '"event_identity_created": False' in admission
    assert '"tactical_truth": False' in admission
    assert '"causality_truth": False' in admission


def test_legacy_provider_validator_is_not_current_global_admission_authority() -> None:
    wrapper = (ROOT / "hpfa/modules/core/provider_metric_dictionary_lite/src/provider_metric_dictionary.py").read_text(encoding="utf-8")
    assert 'report["event_only_compatibility_is_global_admission_gate"] = False' in wrapper
    assert 'report["event_only_compatibility_is_legacy_metadata"] = True' in wrapper
    assert 'report["metric_admission_policy"] = "REQUIRED_CAPABILITIES_SUBSET_OF_ADMITTED_CAPABILITIES"' in wrapper
    assert "_neutralize_legacy_event_only_gate" in wrapper


def test_future_module_capabilities_are_not_pulled_into_single_match_postmatch_closure() -> None:
    ledger = _json("docs/governance/HPFA_EVENT_ONLY_MIGRATION_LEDGER_V1.json")
    later = set(ledger["explicitly_later_outside_current_postmatch_scope"])
    assert "multi_match_gold_corpus_generalization" in later
    assert "cross_match_context_standardization" in later
    assert "longitudinal_team_or_player_tendency" in later
