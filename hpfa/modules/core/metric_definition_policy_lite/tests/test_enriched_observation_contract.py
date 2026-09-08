import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_definition_policy_lite" / "src"
CONFIG = ROOT / "configs" / "metrics"
sys.path.insert(0, str(SRC))

from metric_definition_policy import build_metric_definition_policy, load_policy_pack


def _docs():
    names = [
        "metric_registry_v1.json", "metric_denominator_policy_v1.json",
        "metric_context_schema_v1.json", "metric_confidence_rules_v1.json",
        "metric_misuse_warnings_v1.json", "metric_exposure_policy_v1.json",
    ]
    return [json.loads((CONFIG / name).read_text(encoding="utf-8")) for name in names]


def test_seed_pack_declares_enriched_observation_model():
    report = load_policy_pack(CONFIG)
    assert report["status"] == "SMOKE_PASS"
    assert report["observation_model"] == "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
    assert report["event_only_is_product_ceiling"] is False
    assert all(metric["observation_contract_status"] == "PASS" for metric in report["metrics"])


def test_nonphysical_rich_construct_can_exceed_legacy_event_only_flag():
    docs = _docs()
    metric = docs[0]["metrics"][0]
    metric["event_only_compatible"] = False
    metric["required_observation_layers"] = [
        "L1_ACTION_OBSERVATION",
        "L2_TEMPORAL_OBSERVATION",
        "L3_SPATIAL_OBSERVATION",
        "L6_CONSEQUENCE_OPPONENT_RESPONSE_OBSERVATION",
    ]
    metric["required_surface_semantics"] = [
        "action_family_admitted",
        "football_time_semantics_admitted",
        "coordinate_semantics_admitted",
        "visible_consequence_relation_admitted",
    ]
    metric["tracking_video_required"] = False

    report = build_metric_definition_policy(*docs)
    assert report["status"] == "SMOKE_PASS"
    observed = report["metrics"][0]
    assert observed["observation_contract_status"] == "PASS"
    assert observed["legacy_event_only_shadow_compatible"] is True
    assert observed["event_only_is_product_ceiling"] is False


def test_unknown_observation_layer_fails_closed():
    docs = _docs()
    docs[0]["metrics"][0]["required_observation_layers"] = ["L9_MAGIC_TRUTH"]
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(gap["gap_type"] == "observation_contract_invalid" for gap in report["policy_gaps"])


def test_l8_physical_state_requires_tracking_or_video():
    docs = _docs()
    metric = docs[0]["metrics"][0]
    metric["required_observation_layers"] = ["L8_TRACKING_VIDEO_PHYSICAL_OFF_BALL_STATE"]
    metric["required_surface_semantics"] = ["tracking_trajectory"]
    metric["tracking_video_required"] = False
    report = build_metric_definition_policy(*docs)
    assert report["status"] == "FAIL_CLOSED"
    assert any(
        "tracking_video_requirement_missing_for_l8" in str(gap.get("detail", ""))
        for gap in report["policy_gaps"]
    )


def test_observation_fingerprint_changes_without_invalidating_legacy_definition_fingerprint():
    baseline = load_policy_pack(CONFIG)
    legacy_fp = baseline["metrics"][0]["definition_fingerprint_sha256"]
    observation_fp = baseline["metrics"][0]["observation_semantic_fingerprint_sha256"]

    docs = _docs()
    metric = docs[0]["metrics"][0]
    metric["required_surface_semantics"] = list(metric["required_surface_semantics"]) + ["new_semantic_requirement"]
    changed = build_metric_definition_policy(*docs)

    assert changed["metrics"][0]["definition_fingerprint_sha256"] == legacy_fp
    assert changed["metrics"][0]["observation_semantic_fingerprint_sha256"] != observation_fp


def test_no_sample_match_identity_leak():
    source = (
        ROOT
        / "hpfa"
        / "modules"
        / "core"
        / "observation_contract_lite"
        / "src"
        / "observation_contract.py"
    ).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
