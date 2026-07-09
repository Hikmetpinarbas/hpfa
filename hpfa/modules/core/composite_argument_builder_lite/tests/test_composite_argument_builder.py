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


def standalone_fusion():
    fusion = base_fusion()
    fusion["relation_records"] = [
        {"signal_ref": "single_action_ref", "relation_type": "SUPPORTS"},
        {"signal_ref": "action_family_count", "relation_type": "COMPLEMENTS"},
    ]
    return fusion


def sequence_fusion():
    fusion = base_fusion()
    fusion["sequence_candidate"] = True
    fusion["sequence_refs"] = ["sequence_001"]
    fusion["relation_records"].append({"signal_ref": "sequence_001", "relation_type": "COMPLEMENTS", "evidence_role": "sequence_window_ref"})
    return fusion


def explicit_contradiction_fusion():
    fusion = base_fusion()
    fusion["relation_records"].append({"signal_ref": "same_construct_opposite_direction", "relation_type": "CONTRADICTS"})
    return fusion


def whole_to_unit_fusion():
    fusion = base_fusion()
    fusion["analysis_route"] = "whole_to_unit"
    fusion["whole_refs"] = ["team_context_window_001"]
    return fusion


def unit_to_whole_fusion():
    fusion = standalone_fusion()
    fusion["analysis_route"] = "unit_to_whole"
    fusion["unit_refs"] = ["single_action_ref"]
    return fusion


def bidirectional_fusion():
    fusion = base_fusion()
    fusion["unit_refs"] = ["final_third_entry", "low_shot_volume"]
    fusion["whole_refs"] = ["window_001", "right_channel_context"]
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


def test_context_bound_relation_scope_detected():
    argument = build_argument_candidate(base_fusion())
    assert argument["relation_scope"] == "context_bound_relation"
    assert argument["context_bound_relation"] is True
    assert argument["standalone_observation"] is False
    assert argument["sequence_candidate"] is False


def test_standalone_observation_scope_detected():
    argument = build_argument_candidate(standalone_fusion())
    assert argument["relation_scope"] == "standalone_observation"
    assert argument["standalone_observation"] is True
    assert argument["context_bound_relation"] is False
    assert argument["sequence_candidate"] is False
    assert "observation_may_be_munferit_not_chain_evidence" in argument["counter_scenarios"]


def test_sequence_candidate_scope_detected():
    argument = build_argument_candidate(sequence_fusion())
    assert argument["relation_scope"] == "sequence_candidate"
    assert argument["sequence_candidate"] is True
    assert argument["sequence_truth"] is False
    assert argument["organism_truth"] is False
    assert "precedent_successor_link_requires_sequence_validation" in argument["counter_scenarios"]


def test_bidirectional_route_detected_from_unit_and_whole_refs():
    argument = build_argument_candidate(bidirectional_fusion())
    assert argument["analysis_route"] == "bidirectional"
    assert argument["whole_to_unit"] is True
    assert argument["unit_to_whole"] is True
    assert argument["bidirectional"] is True
    assert "bidirectional_alignment_requires_both_routes_to_remain_present" in argument["counter_scenarios"]


def test_whole_to_unit_route_detected():
    argument = build_argument_candidate(whole_to_unit_fusion())
    assert argument["analysis_route"] == "whole_to_unit"
    assert argument["whole_to_unit"] is True
    assert argument["unit_to_whole"] is False
    assert argument["bidirectional"] is False
    assert "whole_surface_may_not_explain_individual_action" in argument["counter_scenarios"]


def test_unit_to_whole_route_detected():
    argument = build_argument_candidate(unit_to_whole_fusion())
    assert argument["analysis_route"] == "unit_to_whole"
    assert argument["unit_to_whole"] is True
    assert argument["whole_to_unit"] is False
    assert argument["bidirectional"] is False
    assert "unit_surface_may_not_scale_to_whole_pattern" in argument["counter_scenarios"]


def test_sequence_argument_requires_sequence_scope():
    fusion = base_fusion()
    fusion["argument_family"] = "recovery_to_progression_chain"
    argument = build_argument_candidate(fusion)
    assert argument["decision"] == "BLOCK_ARGUMENT"
    assert "sequence_argument_requires_sequence_scope" in argument["hard_block_hits"]


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


def test_failed_upstream_fusion_blocks_argument():
    fusion = base_fusion()
    fusion["decision"] = "BLOCK_FUSION"
    fusion["hard_block_hits"] = ["upstream_packet_claim_ceiling_not_candidate_only"]
    argument = build_argument_candidate(fusion)
    assert argument["decision"] == "BLOCK_ARGUMENT"
    assert "upstream_fusion_failed_closed" in argument["hard_block_hits"]


def test_forbidden_upstream_output_blocks_argument():
    fusion = base_fusion()
    fusion["safe_sentence"] = "unsafe sentence"
    argument = build_argument_candidate(fusion)
    assert argument["decision"] == "BLOCK_ARGUMENT"
    assert "upstream_fusion_forbidden_output_attempted" in argument["hard_block_hits"]
    assert "safe_sentence" in argument["forbidden_output_hits"]


def test_quality_truth_upstream_output_blocks_argument():
    fusion = base_fusion()
    fusion["quality_truth"] = True
    argument = build_argument_candidate(fusion)
    assert argument["decision"] == "BLOCK_ARGUMENT"
    assert "upstream_fusion_forbidden_output_attempted" in argument["hard_block_hits"]
    assert "quality_truth" in argument["forbidden_output_hits"]


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
    assert argument["quality_truth"] is False
    assert argument["sequence_truth"] is False
    assert argument["organism_truth"] is False
    assert "tactical_truth" in argument["blocked_language_families"]
    assert "causal_truth" in argument["blocked_language_families"]
    assert "quality_truth" in argument["blocked_language_families"]


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
