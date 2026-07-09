import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "composite_argument_builder_lite" / "src"
sys.path.insert(0, str(SRC))

from composite_argument_builder import build_argument_candidate, build_argument_report, write_outputs


def base_fusion():
    return {
        "fusion_id": "fusion_cep_progression_001",
        "packet_id": "cep_progression_001",
        "packet_family": "progression",
        "claim_ceiling": "fusion_relation_candidate_only",
        "relation_records": [
            {"signal_ref": "right_channel_access", "relation_type": "SUPPORTS"},
            {"signal_ref": "low_shot_volume", "relation_type": "QUALIFIES"},
            {"signal_ref": "final_third_entry", "relation_type": "COMPLEMENTS"},
            {"signal_ref": "window_001", "relation_type": "CONTEXTUALIZES"},
        ],
        "claim_output_allowed": False,
        "report_language_allowed": False,
    }


def explicit_contradiction_fusion():
    fusion = base_fusion()
    fusion["relation_records"].append({"signal_ref": "same_construct_opposite_direction", "relation_type": "CONTRADICTS"})
    return fusion


def test_argument_requires_fusion_id():
    fusion = base_fusion()
    fusion.pop("fusion_id")
    argument = build_argument_candidate(fusion)
    assert argument["decision"] == "BLOCK_ARGUMENT"
    assert "fusion_id" in argument["missing_fields"]
    assert "fusion_required_fields_missing" in argument["hard_block_hits"]
    assert argument["fusion_id"] == "MISSING_FUSION_ID"


def test_argument_requires_relation_records():
    fusion = base_fusion()
    fusion.pop("relation_records")
    argument = build_argument_candidate(fusion)
    assert argument["decision"] == "BLOCK_ARGUMENT"
    assert "relation_records" in argument["missing_fields"]


def test_argument_uses_predefined_family():
    argument = build_argument_candidate(base_fusion())
    assert argument["argument_family"] == "progression_without_terminal_value"
    assert argument["claim_ceiling"] == "argument_candidate_only"


def test_argument_preserves_support_qualifier_context_refs():
    argument = build_argument_candidate(base_fusion())
    assert "right_channel_access" in argument["supporting_refs"]
    assert "low_shot_volume" in argument["qualifying_refs"]
    assert "window_001" in argument["context_refs"]
    assert argument["status"] == "ARGUMENT_WITH_QUALIFIER"
    assert argument["decision"] == "READY_FOR_SAFE_ROUTER_WITH_QUALIFIER"


def test_argument_preserves_explicit_contradiction_refs():
    argument = build_argument_candidate(explicit_contradiction_fusion())
    assert "same_construct_opposite_direction" in argument["contradicting_refs"]
    assert argument["status"] == "ARGUMENT_WITH_EXPLICIT_CONTRADICTION"
    assert argument["decision"] == "READY_FOR_SAFE_ROUTER_WITH_CONTRADICTION"


def test_argument_requires_counter_scenario_and_withdrawal_condition():
    argument = build_argument_candidate(base_fusion())
    assert argument["counter_scenarios"]
    assert argument["withdrawal_conditions"]


def test_non_candidate_upstream_claim_ceiling_blocks_argument():
    fusion = base_fusion()
    fusion["claim_ceiling"] = "claim_text_allowed"
    argument = build_argument_candidate(fusion)
    assert argument["decision"] == "BLOCK_ARGUMENT"
    assert "claim_ceiling" in argument["missing_fields"]


def test_forbidden_upstream_output_blocks_argument():
    fusion = base_fusion()
    fusion["safe_sentence"] = "unsafe sentence"
    argument = build_argument_candidate(fusion)
    assert argument["decision"] == "BLOCK_ARGUMENT"
    assert "upstream_fusion_forbidden_output_attempted" in argument["hard_block_hits"]
    assert "safe_sentence" in argument["forbidden_output_hits"]


def test_argument_does_not_emit_claim_or_sentence():
    argument = build_argument_candidate(base_fusion())
    assert "claim_text" not in argument
    assert "safe_sentence" not in argument
    assert argument["claim_output_allowed"] is False
    assert argument["report_language_allowed"] is False
    assert argument["safe_sentence_allowed"] is False


def test_argument_blocks_truth_language_families():
    argument = build_argument_candidate(base_fusion())
    assert argument["tactical_truth"] is False
    assert argument["dominance_truth"] is False
    assert argument["control_truth"] is False
    assert argument["coach_intention_truth"] is False
    assert argument["off_ball_truth"] is False
    assert argument["pitch_control_truth"] is False
    assert argument["causal_truth"] is False
    assert "tactical_truth" in argument["blocked_language_families"]
    assert "causal_truth" in argument["blocked_language_families"]


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_fusion()], "/sdcard/Download/HPFA/composite_argument_builder_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_fusion()], tmp_path)
    assert report["module_id"] == "composite_argument_builder_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert (tmp_path / "composite_argument_builder_lite_v1.json").exists()
    assert (tmp_path / "composite_argument_builder_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "composite_argument_builder_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["argument_count"] == 1


def test_no_sample_match_identity_leak():
    src = (SRC / "composite_argument_builder.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
