import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_alias_registry_binding_lite" / "src"
sys.path.insert(0, str(SRC))

from provider_alias_registry_binding import find_alias, load_registry, normalize_alias


def payload():
    return {
        "registry_id": "provider_alias_registry_seed_v1",
        "records": [
            {
                "provider": "generic_event_surface",
                "raw_alias": "event_type",
                "normalized_alias": "event_type",
                "canonical_key_candidate": "event.action",
                "mapping_direction": "raw_to_candidate",
                "reverse_mapping_supported": False,
                "alias_reliability": "MEDIUM",
                "vendor_leakage_risk": "LOW",
                "rule_id": "provider_alias_rule_0001",
            }
        ],
    }


def test_provider_alias_registry_loads():
    result = load_registry(payload())
    assert result["module_id"] == "provider_alias_registry_binding_lite_v1"
    assert result["records_loaded"] == 1
    assert result["records_rejected"] == 0


def test_provider_mapping_has_rule_id():
    result = load_registry(payload())
    record = result["records"][0]
    assert record["rule_id"] == "provider_alias_rule_0001"


def test_unknown_provider_alias_abstains():
    result = load_registry(payload())
    match = find_alias(result, "generic_event_surface", "unknown_blob")
    assert match["provider_alias_status"] == "REVIEW_REQUIRED"
    assert match["canonical_key_candidate"] is None
    assert match["abstain_reason"] == "unknown_provider_alias"


def test_alias_candidate_not_truth():
    result = load_registry(payload())
    match = find_alias(result, "generic_event_surface", "event_type")
    assert match["provider_alias_status"] == "CANDIDATE_MATCH"
    assert match["runtime_verified"] is False


def test_duplicate_provider_alias_rejected():
    data = payload()
    data["records"].append(dict(data["records"][0]))
    result = load_registry(data)
    assert result["records_rejected"] == 1
    assert "duplicate_provider_alias" in result["errors"][0]["errors"]


def test_normalized_alias_rule():
    assert normalize_alias(" Event Type ") == "event_type"


def test_no_sample_match_identity_leak():
    src = (SRC / "provider_alias_registry_binding.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "United States", "World Cup", "25.06.2026"]:
        assert token not in src
