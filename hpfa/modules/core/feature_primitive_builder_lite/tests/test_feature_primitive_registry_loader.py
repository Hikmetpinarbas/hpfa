import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "feature_primitive_builder_lite" / "src"
sys.path.insert(0, str(SRC))

from feature_primitive_registry_loader import INITIAL_FEATURES, load_registry, write_registry


def test_initial_registry_loads_expected_records():
    report = load_registry()
    assert report["module_id"] == "feature_primitive_registry_loader_lite_v1"
    assert report["registry_record_count"] == 11
    assert report["status"] == "SMOKE_PASS"


def test_registry_includes_required_initial_features():
    report = load_registry()
    ids = {record["feature_id"] for record in report["registry_records"]}
    for feature_id in [
        "action_family_count",
        "zone_entry_count",
        "final_third_entry",
        "box_entry",
        "sequence_length",
        "sequence_duration",
        "loss_severity",
        "turnover_exposure",
        "event_density_window",
        "restart_surface_count",
        "terminal_action_count",
    ]:
        assert feature_id in ids


def test_family_and_readiness_counts_written():
    report = load_registry()
    assert report["family_counts"]["progression_territory"] == 2
    assert report["family_counts"]["sequence_surface"] == 2
    assert report["readiness_seed_counts"] == {"READY": 11}


def test_dependency_graph_from_explicit_requires_only():
    report = load_registry()
    graph = report["dependency_graph"]
    assert "final_third_entry" in graph["nodes"]
    assert {"type": "requires_feature", "from": "final_third_entry", "to": "zone_entry_count"} in graph["edges"]
    assert {"type": "requires_feature", "from": "sequence_duration", "to": "sequence_length"} in graph["edges"]


def test_missing_required_fields_become_registry_gaps():
    bad = [{"feature_id": "bad_feature", "feature_family": "bad_family"}]
    report = load_registry(bad)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["registry_gaps"][0]["gap_type"] == "MISSING_REQUIRED_REGISTRY_FIELDS"
    assert report["registry_records"][0]["readiness_seed"] == "BLOCKED"


def test_duplicate_feature_ids_fail_closed():
    dup = [dict(INITIAL_FEATURES[0]), dict(INITIAL_FEATURES[0])]
    report = load_registry(dup)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "DUPLICATE_FEATURE_ID" for gap in report["registry_gaps"])


def test_no_feature_value_or_claim_output_allowed():
    report = load_registry()
    assert report["feature_value_output_allowed"] is False
    assert report["metric_value_output_allowed"] is False
    assert report["claim_output_allowed"] is False
    assert report["canonical_event_count"] == "UNKNOWN"


def test_records_keep_claim_boundaries():
    report = load_registry()
    record = next(item for item in report["registry_records"] if item["feature_id"] == "event_density_window")
    assert record["claim_safety"] == "REGISTRY_ONLY_NO_FEATURE_VALUE"
    assert record["claim_ceiling"] == "density_candidate_not_momentum_truth"
    assert "density_candidate_as_momentum_truth" in record["blocked_language_families"]


def test_write_registry_outputs_json(tmp_path):
    report = write_registry(tmp_path)
    out = tmp_path / "feature_primitive_registry_lite_v1.json"
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["registry_record_count"] == report["registry_record_count"]


def test_no_sample_match_identity_leak():
    src = (SRC / "feature_primitive_registry_loader.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
