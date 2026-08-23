import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_report_block_composer_lite" / "src"
sys.path.insert(0, str(SRC))

from analyst_report_block_composer import build_report_block_report, compose_report_block, write_outputs


def base_safe_sentence():
    return {
        "safe_sentence_id": "safe_sentence_graph_arg_fusion_cep_progression_001",
        "graph_id": "graph_arg_fusion_cep_progression_001",
        "defeasible_state": "SUPPORTED",
        "review_required": False,
        "review_reasons": [],
        "status": "SMOKE_PASS",
        "decision": "READY_FOR_REPORT_COMPOSER_CANDIDATE",
        "safe_sentence_candidate_tr": "Görünür kanıt grafiği context_bound_relation kapsamındaki bidirectional okumasında right_channel_access referanslarının argüman adayını desteklediğini; low_shot_volume referanslarının okumayı nitelendirdiğini; window_001 referanslarının bağlam verdiğini; shot_timing_or_angle_limited_terminal_action karşı senaryosunun dikkate alınması gerektiğini; terminal_action_value_becomes_high_in_same_window gerçekleşirse aday okumanın geri çekilebileceğini gösterir.",
        "claim_ceiling": "safe_sentence_candidate_only",
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": True,
    }


def test_report_block_requires_safe_sentence_id():
    item = base_safe_sentence()
    item.pop("safe_sentence_id")
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "safe_sentence_id" in block["missing_fields"]
    assert "safe_sentence_required_fields_missing" in block["hard_block_hits"]
    assert block["safe_sentence_id"] == "MISSING_SAFE_SENTENCE_ID"


def test_report_block_requires_standard_safe_sentence_key():
    item = base_safe_sentence()
    item.pop("safe_sentence_candidate_tr")
    item["sentence_candidate_tr"] = "legacy alias only"
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "safe_sentence_candidate_tr" in block["missing_fields"]


def test_report_block_rejects_empty_standard_value_even_with_legacy_alias():
    item = base_safe_sentence()
    item["safe_sentence_candidate_tr"] = ""
    item["sentence_candidate_tr"] = "legacy alias should not be promoted"
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "safe_sentence_candidate_tr" in block["missing_fields"]
    assert "safe_sentence_candidate_required" in block["hard_block_hits"]
    assert block["report_block_candidate_tr"] == ""


def test_report_block_requires_upstream_claim_ceiling():
    item = base_safe_sentence()
    item["claim_ceiling"] = "claim_text_allowed"
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "claim_ceiling" in block["missing_fields"]


def test_report_block_composes_candidate_tr():
    block = compose_report_block(base_safe_sentence())
    assert block["status"] == "SMOKE_PASS"
    assert block["decision"] == "READY_FOR_REPORT_OUTPUT_CONTRACT_CANDIDATE"
    assert block["block_family"] == "analyst_reading_candidate"
    assert block["review_required"] is False
    assert block["report_block_candidate_tr"].startswith("Analist okuması:")
    assert "right_channel_access" in block["report_block_candidate_tr"]
    assert block["claim_ceiling"] == "analyst_report_block_candidate_only"


def test_review_required_safe_sentence_routes_report_block_to_review():
    item = base_safe_sentence()
    item["defeasible_state"] = "WEAKENED"
    item["status"] = "REVIEW_REQUIRED"
    item["decision"] = "ROUTE_REVIEW_SAFE_SENTENCE_CANDIDATE"
    item["review_required"] = True
    item["review_reasons"] = ["defeasible_argument_weakened"]
    item["safe_sentence_candidate_tr"] = "Gözden geçirme gerektiren kanıt grafiği context_bound_relation kapsamındaki bidirectional okumasında support_1 referanslarının argüman adayını desteklediğini; counter_1 referanslarının karşı-kanıt taşıdığını; bu nedenle argüman adayının zayıflamış durumda olduğunu gösterir."
    block = compose_report_block(item)
    assert block["status"] == "REVIEW_REQUIRED"
    assert block["decision"] == "ROUTE_REPORT_BLOCK_TO_REVIEW"
    assert block["block_family"] == "review_required_candidate"
    assert block["review_required"] is True
    assert block["review_reasons"] == ["defeasible_argument_weakened"]
    assert block["defeasible_state"] == "WEAKENED"
    assert block["report_block_candidate_tr"].startswith("Analist okuması:")


def test_review_required_without_reason_gets_fallback_reason():
    item = base_safe_sentence()
    item["status"] = "REVIEW_REQUIRED"
    item["review_required"] = True
    block = compose_report_block(item)
    assert block["status"] == "REVIEW_REQUIRED"
    assert block["review_reasons"] == ["upstream_safe_sentence_review_required"]


def test_failed_upstream_safe_sentence_blocks_report_block():
    item = base_safe_sentence()
    item["decision"] = "BLOCK_SAFE_SENTENCE"
    item["hard_block_hits"] = ["upstream_graph_failed_closed"]
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "upstream_safe_sentence_failed_closed" in block["hard_block_hits"]
    assert block["report_block_candidate_tr"] == ""


def test_forbidden_upstream_output_blocks_report_block():
    item = base_safe_sentence()
    item["claim_text"] = "unsafe claim"
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "upstream_safe_sentence_forbidden_output_attempted" in block["hard_block_hits"]
    assert "claim_text" in block["forbidden_upstream_hits"]


def test_nested_forbidden_upstream_output_blocks_report_block():
    item = base_safe_sentence()
    item["metadata"] = {"nested": {"quality_truth": "unsafe"}}
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "metadata.nested.quality_truth" in block["forbidden_upstream_hits"]


def test_report_text_upstream_output_blocks_report_block():
    item = base_safe_sentence()
    item["report_text"] = "premature report text"
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "upstream_safe_sentence_forbidden_output_attempted" in block["hard_block_hits"]
    assert "report_text" in block["forbidden_upstream_hits"]


def test_report_language_upstream_output_blocks_report_block():
    item = base_safe_sentence()
    item["report_language"] = "premature report language"
    block = compose_report_block(item)
    assert block["decision"] == "BLOCK_REPORT_BLOCK"
    assert "upstream_safe_sentence_forbidden_output_attempted" in block["hard_block_hits"]
    assert "report_language" in block["forbidden_upstream_hits"]


def test_report_block_does_not_emit_final_report_or_claim_text():
    block = compose_report_block(base_safe_sentence())
    assert "claim_text" not in block
    assert "final_report_text" not in block
    assert block["claim_output_allowed"] is False
    assert block["production_report_allowed"] is False
    assert block["final_report_allowed"] is False


def test_report_block_blocks_truth_language_families():
    block = compose_report_block(base_safe_sentence())
    assert block["tactical_truth"] is False
    assert block["dominance_truth"] is False
    assert block["control_truth"] is False
    assert block["coach_intention_truth"] is False
    assert block["off_ball_truth"] is False
    assert block["pitch_control_truth"] is False
    assert block["causal_truth"] is False
    assert block["quality_truth"] is False
    assert block["sequence_truth"] is False
    assert block["organism_truth"] is False


def test_report_block_avoids_forbidden_fragments():
    block = compose_report_block(base_safe_sentence())
    assert block["forbidden_block_hits"] == []
    lowered = block["report_block_candidate_tr"].lower()
    for fragment in ["domine etti", "hoca planladı", "bilinçli olarak", "kanıtlıyor", "nedeni budur"]:
        assert fragment not in lowered


def test_report_rollup_preserves_review_required():
    normal = base_safe_sentence()
    review = base_safe_sentence()
    review["safe_sentence_id"] = "safe_sentence_review"
    review["status"] = "REVIEW_REQUIRED"
    review["review_required"] = True
    review["review_reasons"] = ["defeasible_argument_weakened"]
    report = build_report_block_report([normal, review])
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["blocked_report_block_count"] == 0
    assert report["review_report_block_count"] == 1


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_safe_sentence()], "/sdcard/Download/HPFA/analyst_report_block_composer_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_safe_sentence()], tmp_path)
    assert report["module_id"] == "analyst_report_block_composer_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert report["review_report_block_count"] == 0
    assert (tmp_path / "analyst_report_block_composer_lite_v1.json").exists()
    assert (tmp_path / "analyst_report_block_composer_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "analyst_report_block_composer_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["report_block_count"] == 1
    assert loaded["report_blocks"][0]["report_block_candidate_tr"]


def test_no_sample_match_identity_leak():
    src = (SRC / "analyst_report_block_composer.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
