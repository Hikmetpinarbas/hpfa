import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import user_output_bundle
from user_output_bundle import (
    ANALYST_REPORT,
    ANALYST_REPORT_EN,
    ANALYST_REPORT_TR,
    BUNDLE_MANIFEST,
    BUNDLE_ZIP,
    build_analyst_report,
    build_human_analyst_report_en,
    build_human_analyst_report_tr,
    snapshot_output_state,
    write_standard_user_outputs,
)


def _feature_payload():
    return {
        "module_id": "episode_feature_vector_lite_v1",
        "status": "REVIEW_REQUIRED",
        "episode_feature_vector_count": 2,
        "total_eligible_action_candidate_count": 30,
        "eligible_action_family_candidate_counts": {"PASS": 20, "SHOT": 4, "TURNOVER": 3, "RECOVERY": 3},
        "review_debt_feature_vector_count": 1,
        "total_unresolved_semantics_context_count": 2,
        "episode_feature_vectors": [
            {
                "start_second_candidate": 60,
                "end_second_candidate": 120,
                "eligible_action_candidate_count": 10,
                "shot_candidate_count": 1,
                "turnover_candidate_count": 1,
                "recovery_candidate_count": 1,
                "eligible_action_count_by_team_candidate": {"Team A": 7},
                "unknown_team_eligible_action_count": 3,
                "eligible_action_zone_counts": {"MIDDLE_THIRD": 6, "FINAL_THIRD": 4},
                "eligible_action_channel_counts": {"LEFT": 5, "CENTRE": 5},
                "action_family_counts": {"PASS": 7, "SHOT": 1, "TURNOVER": 1, "RECOVERY": 1},
            },
            {
                "start_second_candidate": 300,
                "end_second_candidate": 360,
                "eligible_action_candidate_count": 20,
                "shot_candidate_count": 3,
                "turnover_candidate_count": 2,
                "recovery_candidate_count": 2,
                "eligible_action_count_by_team_candidate": {"Team A": 5, "Team B": 10},
                "unknown_team_eligible_action_count": 5,
                "eligible_action_zone_counts": {"FINAL_THIRD": 12, "MIDDLE_THIRD": 8},
                "eligible_action_channel_counts": {"RIGHT": 12, "CENTRE": 8},
                "action_family_counts": {"PASS": 13, "SHOT": 3, "TURNOVER": 2, "RECOVERY": 2},
            },
        ],
    }


def _full_spine(
    *,
    feature_current=True,
    c4_current=True,
    status="REVIEW_REQUIRED",
    current_artifacts=None,
):
    return {
        "status": status,
        "decision": "FULL_SPINE_COMPLETED_REVIEW_REQUIRED" if status != "FAIL_CLOSED" else "BLOCK_FULL_SPINE",
        "episode_candidate_count": 2 if feature_current else None,
        "episode_feature_vector_count": 2 if feature_current else None,
        "temporal_episode_signature_count": 2 if feature_current else None,
        "intelligence_chain_count": 1 if c4_current else 0,
        "hard_block_hits": [] if status != "FAIL_CLOSED" else ["synthetic_failure"],
        "review_hits": ["synthetic_review"] if status != "FAIL_CLOSED" else [],
        "active_match_authority": "/runtime/active_single_match/current",
        "current_invocation_artifacts": list(current_artifacts or []),
        "engineering_evidence": {
            "current_context_episode_feature_lane_completed": feature_current,
            "current_c4_producers_reused": c4_current,
        },
        "intelligence_chains": [
            {
                "safe_sentence": {
                    "safe_sentence_candidate_tr": "Gorunur kanit grafigi aday okumayi destekler."
                }
            }
        ] if c4_current else [],
    }


def test_analyst_report_uses_current_episode_surface(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    text = build_analyst_report(tmp_path, _full_spine())
    assert "eligible_action_candidate_total=30" in text
    assert "05:00-06:00 shots=3" in text
    assert '"Team A": 12' in text
    assert '"Team B": 10' in text
    assert "SAFE_ARGUMENT_CANDIDATES" in text
    assert "feature_surface_current_invocation=true" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_process_contest_cards_put_attack_and_opponent_exposure_on_same_surface():
    rich = {
        "constructs": {
            "C03": {
                "team_process_profiles": [
                    {
                        "team_identity_candidate_id": "team_a",
                        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                        "eligible_process_n": 12,
                        "shot_ending_process_n": 3,
                        "visible_loss_process_n": 5,
                    },
                    {
                        "team_identity_candidate_id": "team_b",
                        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                        "eligible_process_n": 9,
                        "shot_ending_process_n": 1,
                        "visible_loss_process_n": 4,
                    },
                ]
            }
        }
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_normalized_key": "alpha"},
            {"team_identity_candidate_id": "team_b", "team_normalized_key": "beta"},
        ]
    }
    cards = user_output_bundle._human_process_contest_cards(rich, identity, "tr")
    text = "\n".join(cards)
    assert "Alpha — yerleşik hücum" in text
    assert "12 görünür süreç" in text
    assert "savunma maruziyeti tarafında beta" in text.casefold()
    assert "9 süreç kurdu" in text
    assert "Savunma maruziyeti rakibin görünür süreç hacmi" in text


def test_six_phase_matrix_renders_all_twelve_direction_slots():
    rows = []
    phases = [
        ("ESTABLISHED_ATTACK", "ATTACK", "POSITIONAL_ATTACK_CANDIDATE"),
        ("ATTACKING_TRANSITION", "ATTACK", "COUNTERATTACK_CANDIDATE"),
        ("ATTACKING_SET_PIECE", "ATTACK", "SET_PIECE_ATTACK_CANDIDATE"),
        ("ESTABLISHED_DEFENCE", "DEFENCE", "POSITIONAL_ATTACK_CANDIDATE"),
        ("DEFENSIVE_TRANSITION", "DEFENCE", "COUNTERATTACK_CANDIDATE"),
        ("DEFENSIVE_SET_PIECE", "DEFENCE", "SET_PIECE_ATTACK_CANDIDATE"),
    ]
    for team, opp in (("team_a", "team_b"), ("team_b", "team_a")):
        for phase, perspective, family in phases:
            rows.append({
                "team_identity_candidate_id": team,
                "opponent_team_identity_candidate_id": opp,
                "canonical_phase_slot": phase,
                "perspective": perspective,
                "source_process_family_candidate": family,
                "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
                "eligible_process_n": 10,
                "shot_ending_process_n": 2,
                "visible_loss_process_n": 4,
                "visible_recovery_process_n": 1,
            })
    rich = {"constructs": {"C03": {"six_phase_team_matrix": rows}}}
    identity = {"team_identity_candidates": [
        {"team_identity_candidate_id": "team_a", "team_normalized_key": "alpha"},
        {"team_identity_candidate_id": "team_b", "team_normalized_key": "beta"},
    ]}
    cards = user_output_bundle._human_process_contest_cards(rich, identity, "tr")
    text = "\n".join(cards)
    assert "Alpha — 6 faz" in text
    assert "Beta — 6 faz" in text
    for label in ("yerleşik hücum", "geçiş hücumu", "duran top hücumu", "yerleşik savunma", "geçiş savunması", "duran top savunması"):
        assert text.count(label + ":") == 2
    assert "Değerlendirme süreç hacmi" in text


def test_phase_motif_sentence_exposes_recurrence_without_calling_it_tactical_truth():
    row = {
        "recurring_process_motif_family_count": 3,
        "recurring_process_motif_covered_process_n": 12,
        "top_recurring_process_motifs": [{
            "member_process_n": 6,
            "shot_variant_n": 2,
            "visible_loss_variant_n": 3,
            "visible_recovery_variant_n": 1,
            "morphology_signature": {
                "length_bucket": "MEDIUM_3_5_LAYERS",
                "action_family_presence": ["PASS", "CARRY"],
                "pass_carry_style": "MIXED_PASS_CARRY",
                "route_hint": "MIDDLE_THIRD->FINAL_THIRD",
            },
        }],
    }
    text = user_output_bundle._phase_motif_sentence(row, "tr")
    assert "3 aile" in text
    assert "12 süreç" in text
    assert "En sık motif 6 örnek" in text
    assert "2 şut bağlantılı" in text
    assert "3 görünür kayıp" in text


def test_phase_motif_sentence_surfaces_first_supported_divergence_safely():
    row = {
        "recurring_process_motif_family_count": 1,
        "recurring_process_motif_covered_process_n": 4,
        "top_recurring_process_motifs": [{
            "member_process_n": 4,
            "shot_variant_n": 1,
            "visible_loss_variant_n": 2,
            "visible_recovery_variant_n": 0,
            "morphology_signature": {
                "length_bucket": "MEDIUM_3_5_LAYERS",
                "action_family_presence": ["PASS", "CARRY"],
                "pass_carry_style": "MIXED_PASS_CARRY",
                "route_hint": "NO_UNAMBIGUOUS_ROUTE_HINT",
            },
            "representative_first_supported_grammar_divergence": {
                "left_variant_context": "SHOT_LINKED",
                "right_variant_context": "LOSS_LINKED",
                "first_supported_grammar_divergence": {
                    "operation": "SUBSTITUTE",
                    "left_token": "LAYER[PASS]",
                    "right_token": "LAYER[CARRY]",
                },
            },
        }],
    }
    text = user_output_bundle._phase_motif_sentence(row, "tr")
    assert "İlk destekli grammar ayrışması" in text
    assert "SHOT_LINKED ↔ LOSS_LINKED" in text
    assert "LAYER[PASS] ↔ LAYER[CARRY]" in text
    assert "görünür ayrışma noktasını" in text


def test_human_reports_use_football_language_and_keep_evidence_note_separate():
    rich = {
        "status": "REVIEW_REQUIRED",
        "m09_opponent_interaction_synthesis": {
            "status": "PASS",
            "profiles": [{
                "team_identity_candidate_id": "team_a",
                "reciprocal_same_family_comparisons": [{
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "opponent_team_identity_candidate_id": "team_b",
                    "self_visible_process_profile": {"eligible_process_n": 12, "shot_ending_process_n": 3, "visible_loss_process_n": 5},
                    "opponent_visible_process_profile": {"eligible_process_n": 9, "shot_ending_process_n": 1, "visible_loss_process_n": 4},
                }],
            }],
        },
        "constructs": {
            "C02": {
                "representative_actor_argument": {
                    "actor_labels": ["Mason Greenwood"],
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "eligible_n": 36,
                    "visible_target_annotation_k": 7,
                    "target_outcome_unresolved_u": 29,
                    "observed_visible_target_annotation_frequency": 7 / 36,
                    "match_local_baseline_shot_frequency": 10 / 72,
                    "descriptive_lift": (7 / 36) / (10 / 72),
                    "eligible_episode_spread": 25,
                    "positive_episode_spread": 7,
                    "selection_candidate_pool_n": 75,
                    "selection_rank": 1,
                },
                "representative_dyad_argument": None,
            }
        },
    }
    spine = _full_spine()
    spine["rich_multiformat_analysis_lattice"] = rich
    spine["engineering_evidence"]["rich_multiformat_lane_executed"] = True

    tr = build_human_analyst_report_tr(".", spine)
    en = build_human_analyst_report_en(".", spine)

    assert "Greenwood" in tr
    assert "36 tanesinde" in tr
    assert "7 tanesinde" in tr
    assert "Kanıt notu:" in tr
    assert "admitted" not in tr
    assert "eligible süreç" not in tr
    assert "visible shot-present annotation" not in tr

    assert "Greenwood" in en
    assert "36 instances" in en
    assert "7 of those instances" in en
    assert "Evidence note:" in en
    assert "match-local descriptive ratio=" in en
    assert "match-local pool" not in en


def test_human_reports_render_team_process_and_mechanism_in_football_language(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    identity_path.write_text(
        json.dumps(
            {
                "team_identity_candidates": [
                    {
                        "team_identity_candidate_id": "team_1",
                        "team_normalized_key": "galatasaray",
                        "team_aliases_raw": ["Galatasaray"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    feature_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "grammar_stable_variant_feature_delta_records": [
                    {
                        "grammar_stable_variant_feature_delta_id": "m1",
                        "source_process_variant_family_ref": "family_1",
                        "team_identity_candidate_ids": ["team_1"],
                        "period_candidates": ["1"],
                        "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                        "resolved_variant_count": 4,
                        "success_resolved_variant_count": 3,
                        "failure_resolved_variant_count": 1,
                        "right_censored_variant_count": 0,
                        "first_supported_consequence_difference_layer_candidate": 1,
                        "consequence_feature_difference_candidates": [{"feature_token": "x"}],
                        "visible_episode_spread_count": 2,
                        "occurrence_disjoint_support_cluster_count": 2,
                        "success_failure_supported_branch_divergence_count": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rich = {
        "status": "REVIEW_REQUIRED",
        "constructs": {
            "C02": {"representative_actor_argument": None, "representative_dyad_argument": None},
            "C03": {
                "team_process_profiles": [
                    {
                        "team_identity_candidate_id": "team_1",
                        "eligible_process_n": 12,
                        "visible_loss_process_n": 5,
                        "visible_recovery_process_n": 3,
                        "shot_ending_process_n": 2,
                    }
                ]
            },
        },
    }
    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path)])
    spine["rich_multiformat_analysis_lattice"] = rich
    spine["engineering_evidence"]["rich_multiformat_lane_executed"] = True

    tr = build_human_analyst_report_tr(tmp_path, spine)
    en = build_human_analyst_report_en(tmp_path, spine)

    assert "Galatasaray: Sistem bu maçta 12 görünür oyun sürecini" in tr
    assert "MEKANİZMA KARTI 1 | SINIF=ANA MEKANİZMA ADAYI | TAKIM=Galatasaray | DÖNEM=1. devre | TRACE=pas → pas" in tr
    assert "İnceleme noktası 1: Galatasaray, 1. devre. pas → pas bağlantısı" in tr
    assert "hangi aksiyon veya bağlam değişiminin sonuçları ayırdığı" in tr
    assert "MEKANİZMA ADAYLARI" not in tr
    assert "Kanıt notu:" in tr
    assert "Kanıt olgunluğu:" in tr
    assert "4 çözümlenmiş varyant" in tr
    assert "2 görünür maç bölümü" in tr
    assert "dependency bağımsızlığı doğrulanmadı" in tr
    assert "tek güven skoruna indirgeme yapmaz" in tr
    assert "independent_support=" not in tr
    assert "grammar_signature_tokens" not in tr

    assert "Galatasaray: The system linked 12 visible match processes" in en
    assert "MECHANISM CARD 1 | CLASS=MAIN MECHANISM CANDIDATE | TEAM=Galatasaray | PERIOD=first half | TRACE=pass → pass" in en
    assert "Review point 1: Galatasaray, first half. The pass → pass connection" in en
    assert "which subsequent action or context change separates those outcomes" in en
    assert "MECHANISM CANDIDATES" not in en
    assert "Evidence note:" in en



def test_unvalidated_actor_aggregate_label_does_not_leak_into_human_mechanism_card(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    rich_path = tmp_path / "rich_multiformat_analysis_lattice_v1.json"

    identity_path.write_text(json.dumps({
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_1", "team_normalized_key": "galatasaray"}
        ],
        "actor_identity_candidates": [
            {
                "actor_identity_candidate_id": "actor_unsafe",
                "actor_normalized_key": "wrong_plausible_name",
                "actor_aliases_raw": ["99. Wrong Plausible Name (999999)"],
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
                "validated_player_identity": False,
            }
        ],
    }), encoding="utf-8")
    feature_path.write_text(json.dumps({
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [{
            "grammar_stable_variant_feature_delta_id": "m_unsafe",
            "source_process_variant_family_ref": "family_unsafe",
            "team_identity_candidate_ids": ["team_1"],
            "period_candidates": ["1"],
            "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
            "resolved_variant_count": 4,
            "success_resolved_variant_count": 3,
            "failure_resolved_variant_count": 1,
            "visible_episode_spread_count": 2,
            "occurrence_disjoint_support_cluster_count": 2,
            "first_supported_context_difference_layer_candidate": 0,
            "first_supported_consequence_difference_layer_candidate": 1,
            "context_feature_difference_candidates": [{
                "feature_token": "LAYER[0]::actor_identity_candidate_ids:actor_unsafe",
                "success_visible_numerator": 3,
                "success_eligible_denominator": 3,
                "failure_visible_numerator": 0,
                "failure_eligible_denominator": 1,
                "descriptive_rate_delta_success_minus_failure": 1.0,
            }],
            "consequence_feature_difference_candidates": [],
        }]
    }), encoding="utf-8")
    rich_path.write_text(json.dumps({
        "status": "PASS",
        "constructs": {
            "C02": {
                "player_function_profiles": [{
                    "actor_identity_candidate_id": "actor_unsafe",
                    "actor_label": "Wrong Plausible Name",
                    "function_dimensions": {},
                }]
            }
        }
    }), encoding="utf-8")

    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path), str(rich_path)])
    spine["rich_multiformat_analysis_lattice"] = json.loads(rich_path.read_text(encoding="utf-8"))
    spine["engineering_evidence"]["rich_multiformat_lane_executed"] = True

    tr = build_human_analyst_report_tr(tmp_path, spine)
    assert "Wrong Plausible Name" not in tr


def test_human_report_exposes_visible_same_team_vs_handover_split_without_causal_claim(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    identity_path.write_text(json.dumps({"team_identity_candidates": [{"team_identity_candidate_id": "team_1", "team_normalized_key": "galatasaray"}]}), encoding="utf-8")
    feature_path.write_text(json.dumps({
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [{
            "grammar_stable_variant_feature_delta_id": "m_split",
            "source_process_variant_family_ref": "family_split",
            "team_identity_candidate_ids": ["team_1"],
            "period_candidates": ["2"],
            "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
            "resolved_variant_count": 284,
            "success_resolved_variant_count": 277,
            "failure_resolved_variant_count": 7,
            "right_censored_variant_count": 0,
            "first_supported_consequence_difference_layer_candidate": 1,
            "consequence_feature_difference_candidates": [
                {"feature_token": "LAYER[1]::primary_consequence_candidates:SAME_TEAM_CONTINUATION_CANDIDATE", "partial_order_layer_index": 1, "success_visible_numerator": 252, "success_eligible_denominator": 277, "failure_visible_numerator": 0, "failure_eligible_denominator": 7, "descriptive_rate_delta_success_minus_failure": 0.91},
                {"feature_token": "LAYER[1]::primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE", "partial_order_layer_index": 1, "success_visible_numerator": 12, "success_eligible_denominator": 277, "failure_visible_numerator": 7, "failure_eligible_denominator": 7, "descriptive_rate_delta_success_minus_failure": -0.96},
            ],
            "visible_episode_spread_count": 16,
            "occurrence_disjoint_support_cluster_count": 33,
            "success_failure_supported_branch_divergence_count": 6,
        }]
    }), encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path)])
    tr = build_human_analyst_report_tr(tmp_path, spine)
    en = build_human_analyst_report_en(tmp_path, spine)
    assert "252/277 tanesinde aynı takım devamı" in tr
    assert "7/7 tanesinde rakibe geçiş" in tr
    assert "aynı başlangıçtan sonra oluşan görünür sonuç ayrımını" in tr
    assert "same-team continuation appears in 252/277" in en
    assert "opponent handover appears in 7/7" in en
    assert "summarizes the visible outcome split" in en


def test_single_episode_mechanism_candidate_is_rendered_as_limited_comparison(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    identity_path.write_text(json.dumps({"team_identity_candidates": [{"team_identity_candidate_id": "team_1", "team_normalized_key": "trabzonspor"}]}), encoding="utf-8")
    feature_path.write_text(json.dumps({
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [{
            "grammar_stable_variant_feature_delta_id": "m_single",
            "source_process_variant_family_ref": "family_single",
            "team_identity_candidate_ids": ["team_1"],
            "period_candidates": ["1"],
            "grammar_signature_tokens": ["LAYER[DUEL]", "LAYER[PASS]"],
            "resolved_variant_count": 2,
            "success_resolved_variant_count": 1,
            "failure_resolved_variant_count": 1,
            "right_censored_variant_count": 0,
            "first_supported_consequence_difference_layer_candidate": 1,
            "consequence_feature_difference_candidates": [
                {"feature_token": "LAYER[1]::primary_consequence_candidates:SAME_TEAM_CONTINUATION_CANDIDATE", "partial_order_layer_index": 1, "success_visible_numerator": 1, "success_eligible_denominator": 1, "failure_visible_numerator": 0, "failure_eligible_denominator": 1, "descriptive_rate_delta_success_minus_failure": 1.0},
                {"feature_token": "LAYER[1]::primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE", "partial_order_layer_index": 1, "success_visible_numerator": 0, "success_eligible_denominator": 1, "failure_visible_numerator": 1, "failure_eligible_denominator": 1, "descriptive_rate_delta_success_minus_failure": -1.0},
            ],
            "visible_episode_spread_count": 1,
            "occurrence_disjoint_support_cluster_count": 1,
            "success_failure_supported_branch_divergence_count": 1,
        }]
    }), encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path)])
    tr = build_human_analyst_report_tr(tmp_path, spine)
    assert "Sınırlı karşılaştırma 1:" in tr
    assert "ana mekanizma olarak yorumlanmamalıdır" in tr
    assert "1/1 tanesinde aynı takım devamı" not in tr

def test_fail_closed_report_does_not_consume_stale_feature_artifact(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    text = build_analyst_report(
        tmp_path,
        _full_spine(feature_current=False, c4_current=False, status="FAIL_CLOSED"),
    )
    assert "feature_surface_current_invocation=false" in text
    assert "eligible_action_candidate_total=UNAVAILABLE_CURRENT_INVOCATION" in text
    assert "05:00-06:00 shots=3" not in text
    assert "onceki run artifact'i kullanilmadi" in text
    assert "Current invocation Episode Feature yuzeyi tamamlanmadi" in text


def test_bundle_uses_producer_write_ledger_even_when_content_unchanged(tmp_path):
    stale = tmp_path / "stale_previous_run.txt"
    stale.write_text("stale", encoding="utf-8")
    rewritten = tmp_path / "deterministic_rewritten.json"
    rewritten.write_text("same", encoding="utf-8")
    before = snapshot_output_state(tmp_path)

    # Simulate deterministic producer rewrite with identical bytes.
    rewritten.write_text("same", encoding="utf-8")
    feature = tmp_path / "episode_feature_vector_lite_v1.json"
    feature.write_text(json.dumps(_feature_payload()), encoding="utf-8")
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")

    result = write_standard_user_outputs(
        tmp_path,
        _full_spine(
            current_artifacts=[str(rewritten), str(feature), str(full_json), str(full_txt)]
        ),
        before_state=before,
    )
    assert Path(result["analyst_report"]).name == ANALYST_REPORT
    assert Path(result["analyst_report_tr"]).name == ANALYST_REPORT_TR
    assert Path(result["analyst_report_en"]).name == ANALYST_REPORT_EN
    assert Path(result["mechanism_cards_graph_ready"]).name == "HPFA_MECHANISM_CARDS_GRAPH_READY.json"
    assert Path(result["bundle_zip"]).name == BUNDLE_ZIP
    assert Path(result["bundle_manifest"]).name == BUNDLE_MANIFEST

    with zipfile.ZipFile(tmp_path / BUNDLE_ZIP) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
    assert "deterministic_rewritten.json" in names
    assert "episode_feature_vector_lite_v1.json" in names
    assert "active_match_full_spine_v1.json" in names
    assert "active_match_full_spine_v1.txt" in names
    assert ANALYST_REPORT in names
    assert ANALYST_REPORT_TR in names
    assert ANALYST_REPORT_EN in names
    assert "HPFA_MECHANISM_CARDS_GRAPH_READY.json" in names
    assert BUNDLE_MANIFEST in names
    assert "stale_previous_run.txt" not in names

    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["bundle_scope"] == "PRODUCER_DECLARED_CURRENT_INVOCATION_ARTIFACTS_PLUS_STANDARD_DELIVERABLES"
    assert manifest["selection_basis"] == "PRODUCER_WRITE_LEDGER_NOT_MTIME_OR_CONTENT_CHANGE_HEURISTIC"
    assert manifest["feature_surface_current_invocation"] is True
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["production_release"] is False


def test_graph_ready_mechanism_card_payload_preserves_review_scope(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    identity_path.write_text(json.dumps({
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_1", "team_normalized_key": "galatasaray"}
        ]
    }), encoding="utf-8")
    feature_path.write_text(json.dumps({
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [{
            "grammar_stable_variant_feature_delta_id": "gsvfd_graph",
            "source_process_variant_family_ref": "family_graph",
            "team_identity_candidate_ids": ["team_1"],
            "period_candidates": ["2"],
            "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
            "resolved_variant_count": 10,
            "success_resolved_variant_count": 8,
            "failure_resolved_variant_count": 2,
            "visible_episode_spread_count": 3,
            "occurrence_disjoint_support_cluster_count": 3,
            "success_failure_supported_branch_divergence_count": 2,
            "first_supported_context_difference_layer_candidate": 0,
            "first_supported_consequence_difference_layer_candidate": 1,
            "consequence_feature_difference_candidates": [{"feature_token": "x"}],
        }]
    }), encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path)])

    payload = user_output_bundle.build_graph_ready_mechanism_cards_payload(tmp_path, spine)

    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["true_action_count"] == "UNKNOWN"
    assert payload["production_release"] is False
    assert payload["graphability_does_not_strengthen_evidence"] is True
    assert payload["card_count"] >= 1
    card = payload["cards"][0]
    assert card["graphability_state"] == "GRAPH_READY_WITH_REVIEW"
    assert card["can_authorize_emit"] is False
    assert card["creates_new_evidence"] is False
    assert card["claim_ceiling"] == "MATCH_LOCAL_VISIBLE_VARIANT_MECHANISM_CANDIDATE_ONLY"
    assert "VISIBLE_OUTCOME_SPLIT_BAR" in card["graph_recommendations"]


def test_bundle_rejects_declared_nested_or_outside_paths(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_file = nested / "should_not_ship.json"
    nested_file.write_text("{}", encoding="utf-8")
    outside = tmp_path.parent / "outside_should_not_ship.json"
    outside.write_text("{}", encoding="utf-8")
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")

    write_standard_user_outputs(
        tmp_path,
        _full_spine(
            feature_current=False,
            c4_current=False,
            current_artifacts=[str(nested_file), str(outside), str(full_json), str(full_txt)],
        ),
    )
    with zipfile.ZipFile(tmp_path / BUNDLE_ZIP) as archive:
        names = set(archive.namelist())
    assert nested_file.name not in names
    assert outside.name not in names
    outside.unlink()


def test_atomic_zip_publication_never_exposes_partial_new_bundle(tmp_path, monkeypatch):
    old_zip = tmp_path / BUNDLE_ZIP
    with zipfile.ZipFile(old_zip, "w") as archive:
        archive.writestr("old.txt", "old-valid-bundle")
    before_old = old_zip.read_bytes()

    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    before = snapshot_output_state(tmp_path)

    real_zipfile = user_output_bundle.zipfile.ZipFile

    class BrokenZipFile:
        def __init__(self, *args, **kwargs):
            self._inner = real_zipfile(*args, **kwargs)
        def __enter__(self):
            self._inner.__enter__()
            return self
        def __exit__(self, *args):
            return self._inner.__exit__(*args)
        def write(self, *args, **kwargs):
            self._inner.write(*args, **kwargs)
            raise OSError("synthetic archive failure")

    monkeypatch.setattr(user_output_bundle.zipfile, "ZipFile", BrokenZipFile)
    with pytest.raises(OSError):
        write_standard_user_outputs(
            tmp_path,
            _full_spine(feature_current=False, current_artifacts=[str(full_json), str(full_txt)]),
            before_state=before,
        )

    assert old_zip.read_bytes() == before_old
    assert not (tmp_path / f".{BUNDLE_ZIP}.tmp").exists()


def test_team_process_cards_expose_visible_consequence_response_without_inflating_meaning():
    rich = {
        "constructs": {
            "C03": {
                "team_process_profiles": [
                    {
                        "team_identity_candidate_id": "team_a",
                        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                        "eligible_process_n": 10,
                        "shot_ending_process_n": 2,
                        "visible_loss_process_n": 4,
                        "visible_recovery_process_n": 1,
                        "visible_consequence_response_profile": {
                            "process_presence_counts": {
                                "OPPONENT_HANDOVER_CANDIDATE": 5,
                                "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE": 3,
                                "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE": 2,
                                "NO_VISIBLE_FOLLOW_UP_CANDIDATE": 1,
                            }
                        },
                    }
                ]
            }
        }
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_normalized_key": "alpha"},
        ]
    }
    cards = user_output_bundle._human_team_process_cards(rich, identity, "tr")
    text = "\n".join(cards)

    assert "5 süreçte rakibe geçiş" in text
    assert "3 süreçte breakdown sonrası rakip takeover" in text
    assert "2 süreçte aynı-zamanlı iki takım belirsizliği" in text
    assert "1 süreçte görünür follow-up yokluğu" in text
    assert "maç-içi süreç kompozisyonunu gösterir" in text
    assert "Okuma çerçevesi" in text
    assert "follow-up durumlarının" in text
    assert "same-time review" in text



def _write_current_inventory(path: Path) -> None:
    path.write_text(
        json.dumps({
            "module_id": "multiformat_file_inventory_lite_v1",
            "status": "PASS",
            "files": [
                {"relative_path": "a.csv", "sha256": "a" * 64, "size_bytes": 10, "source_role": "PLAYER_SURFACE_CANDIDATE"},
                {"relative_path": "b.xml", "sha256": "b" * 64, "size_bytes": 20, "source_role": "PLAYER_SURFACE_CANDIDATE"},
            ],
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }),
        encoding="utf-8",
    )


def test_bundle_manifest_binds_exact_head_input_snapshot_environment_and_artifacts(tmp_path):
    inventory = tmp_path / "multiformat_file_inventory_lite_v1.json"
    _write_current_inventory(inventory)
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(inventory), str(full_json), str(full_txt)])
    spine["execution_root"] = str(ROOT)

    write_standard_user_outputs(tmp_path, spine)
    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    provenance = manifest["current_run_provenance_envelope"]

    assert provenance["status"] == "PASS"
    assert len(provenance["exact_head_sha"]) == 40
    assert provenance["input_snapshot"]["status"] == "PASS"
    assert provenance["input_snapshot"]["file_count"] == 2
    assert len(provenance["input_snapshot"]["fingerprint_sha256"]) == 64
    assert len(provenance["runtime_environment"]["fingerprint_sha256"]) == 64
    assert len(provenance["artifact_manifest_digest_sha256"]) == 64
    assert len(provenance["current_run_context_fingerprint_sha256"]) == 64
    assert provenance["identity_kind"] == "DETERMINISTIC_CONTEXT_FINGERPRINT_NOT_UNIQUE_INVOCATION_UUID"
    assert provenance["provenance_creates_new_football_evidence"] is False
    assert provenance["provenance_can_authorize_emit"] is False
    assert provenance["provenance_can_strengthen_claim_ceiling"] is False
    assert provenance["production_release"] is False


def test_missing_current_inventory_downgrades_provenance_only_not_bundle_or_claim_state(tmp_path):
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(full_json), str(full_txt)])
    spine["execution_root"] = str(ROOT)

    result = write_standard_user_outputs(tmp_path, spine)
    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    provenance = manifest["current_run_provenance_envelope"]

    assert provenance["status"] == "REVIEW_REQUIRED"
    assert provenance["input_snapshot"]["reason"] == "current_multiformat_inventory_not_declared"
    assert Path(result["bundle_zip"]).is_file()
    assert manifest["runtime_status"] == "REVIEW_REQUIRED"
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["true_action_count"] == "UNKNOWN"
    assert manifest["production_release"] is False
    assert provenance["provenance_can_authorize_emit"] is False


def test_current_run_context_fingerprint_is_stable_for_same_declared_context(tmp_path):
    inventory = tmp_path / "multiformat_file_inventory_lite_v1.json"
    _write_current_inventory(inventory)
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(inventory), str(full_json), str(full_txt)])
    spine["execution_root"] = str(ROOT)

    write_standard_user_outputs(tmp_path, spine)
    first = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))["current_run_provenance_envelope"]
    write_standard_user_outputs(tmp_path, spine)
    second = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))["current_run_provenance_envelope"]

    assert second["current_run_context_fingerprint_sha256"] == first["current_run_context_fingerprint_sha256"]
    assert second["artifact_manifest_digest_sha256"] == first["artifact_manifest_digest_sha256"]
    assert second["input_snapshot"]["fingerprint_sha256"] == first["input_snapshot"]["fingerprint_sha256"]

def test_mechanism_safe_context_uses_only_common_preoutcome_context(tmp_path):
    sequence = {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "source_first_supported_branch_divergence_ref": "fsbd_1",
            },
            {
                "safe_finding_handoff_candidate_id": "sfh_2",
                "source_first_supported_branch_divergence_ref": "fsbd_2",
            },
        ]
    }
    admission = {
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "decision": "ABSTAIN",
                "claim_output_allowed": False,
                "branch_preoutcome_context_enrichment": {
                    "state": "PRE_BRANCH_CONTEXT_ENRICHED_GAME_STATE_AND_PROCESS",
                    "score_state_candidate": {"Alpha": 0, "Beta": 0},
                    "provider_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
                },
            },
            {
                "source_safe_finding_handoff_ref": "sfh_2",
                "decision": "ABSTAIN",
                "claim_output_allowed": False,
                "branch_preoutcome_context_enrichment": {
                    "state": "PRE_BRANCH_CONTEXT_ENRICHED_PARTIAL",
                    "score_state_candidate": {"Alpha": 0, "Beta": 0},
                    "provider_process_family_candidates": [],
                },
            },
        ]
    }
    process_variant = {
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "opvf_1",
                "supported_branch_divergence_bindings": [
                    {"source_first_supported_branch_divergence_ref": "fsbd_1"},
                    {"source_first_supported_branch_divergence_ref": "fsbd_2"},
                ],
            }
        ]
    }
    seq_path = tmp_path / user_output_bundle.VISIBLE_SEQUENCE_JSON
    adm_path = tmp_path / user_output_bundle.SAFE_FINDING_ADMISSION_JSON
    seq_path.write_text(json.dumps(sequence), encoding="utf-8")
    adm_path.write_text(json.dumps(admission), encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(seq_path), str(adm_path)])

    result = user_output_bundle._mechanism_safe_context_by_family(
        tmp_path, spine, process_variant
    )
    row = result["opvf_1"]
    assert row["score_state_consensus"] is True
    assert row["score_state_candidate"] == {"Alpha": 0, "Beta": 0}
    assert row["provider_process_family_consensus"] is True
    assert row["provider_process_family_candidates"] == [
        "POSITIONAL_ATTACK_CANDIDATE"
    ]
    assert row["provider_process_context_partial_count"] == 1
    assert row["emit_decision_count"] == 0
    assert row["creates_new_evidence"] is False
    assert row["creates_independent_support"] is False
    assert row["can_change_shortlist_selection"] is False
    assert row["can_change_safe_finding_decision"] is False
    assert row["can_authorize_emit"] is False

def test_actor_aggregate_context_is_match_context_not_mechanism_evidence():
    locator = {
        "feature_token": "actor_identity_candidate_ids:actor_1",
        "success_visible_numerator": 3,
        "success_eligible_denominator": 4,
        "failure_visible_numerator": 0,
        "failure_eligible_denominator": 1,
    }
    profiles = {
        "actor_1": {
            "actor_identity_candidate_id": "actor_1",
            "actor_label": "hikmet",
            "function_dimensions": {
                "ACCESS": [
                    {"metric_key": "progressive_passes", "raw_value": 8},
                    {"metric_key": "progressive_passes_accurate", "raw_value": 6},
                    {"metric_key": "final_third_entries", "raw_value": 4},
                ],
                "CREATION": [
                    {"metric_key": "xa_expected_assists", "raw_value": 0.31},
                ],
                "TERMINAL": [
                    {"metric_key": "shots", "raw_value": 3},
                    {"metric_key": "xg_expected_goals", "raw_value": 0.44},
                ],
                "PROCESS": {
                    "process_participation_counts": {
                        "POSITIONAL_ATTACK_CANDIDATE": 12,
                        "COUNTERATTACK_CANDIDATE": 3,
                    }
                },
            },
        }
    }
    text = user_output_bundle._actor_aggregate_context_sentence(
        "actor_1", locator, profiles, {"actor_1": "Hikmet"}, "tr"
    )
    assert "Oyuncu inceleme odağı: Hikmet." in text
    assert "progressive pass=8" in text
    assert "isabetli progressive pass=6" in text
    assert "son üçte bir girişi=4" in text
    assert "xA=0.31" in text
    assert "şut=3" in text
    assert "xG=0.44" in text
    assert "yerleşik hücum 12" in text
    assert "mekanizma aksiyon kimliği" in text
    assert "nedensel katkı bu kapsamın dışında kalır" in text


def test_graph_ready_mechanism_cards_carry_safe_context_and_player_context_without_claim_promotion(tmp_path: Path) -> None:
    feature = {
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [{
            "grammar_stable_variant_feature_delta_id": "gsvfd_1",
            "source_process_variant_family_ref": "opvf_1",
            "team_identity_candidate_ids": ["team_a"],
            "period_candidates": ["1"],
            "grammar_signature_tokens": ["PASS", "PASS"],
            "resolved_variant_count": 3,
            "success_resolved_variant_count": 2,
            "failure_resolved_variant_count": 1,
            "visible_episode_spread_count": 2,
            "occurrence_disjoint_support_cluster_count": 2,
            "supported_branch_divergence_binding_count": 1,
            "success_failure_supported_branch_divergence_count": 1,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "first_supported_context_difference_layer_candidate": 1,
            "first_supported_consequence_difference_layer_candidate": 2,
            "process_context_feature_difference_candidates": [{
                "feature_token": "LAYER[0]::process_shot_present_annotation_candidate:TRUE",
                "partial_order_layer_index": 0,
                "success_visible_numerator": 2,
                "success_eligible_denominator": 2,
                "failure_visible_numerator": 0,
                "failure_eligible_denominator": 1,
                "descriptive_rate_delta_success_minus_failure": 1.0,
                "difference_is_failure_cause_truth": False,
                "difference_is_tactical_explanation": False,
                "dependency_independence_proven": False,
            }],
            "context_feature_difference_candidates": [{
                "feature_token": "actor_identity_candidate_ids:actor_1",
                "success_visible_numerator": 2,
                "success_eligible_denominator": 2,
                "failure_visible_numerator": 0,
                "failure_eligible_denominator": 1,
                "descriptive_rate_delta_success_minus_failure": 1.0,
            }],
        }],
    }
    process_variant = {
        "observable_process_variant_families": [{
            "observable_process_variant_family_id": "opvf_1",
            "grammar_stable_variant_feature_delta_ref": "gsvfd_1",
            "visible_episode_spread_count": 2,
            "occurrence_disjoint_support_cluster_count": 2,
            "supported_branch_divergence_bindings": [{
                "source_first_supported_branch_divergence_ref": "fsbd_1",
            }],
        }],
    }
    sequence = {
        "safe_finding_handoff_candidates": [{
            "safe_finding_handoff_candidate_id": "sfh_1",
            "source_first_supported_branch_divergence_ref": "fsbd_1",
        }],
    }
    admission = {
        "safe_finding_admission_decisions": [{
            "source_safe_finding_handoff_ref": "sfh_1",
            "decision": "ABSTAIN",
            "claim_output_allowed": False,
            "branch_preoutcome_context_enrichment": {
                "state": "PRE_BRANCH_CONTEXT_ENRICHED_GAME_STATE_AND_PROCESS",
                "score_state_candidate": {"Alpha": 0, "Beta": 0},
                "provider_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
            },
        }],
    }
    rich = {
        "status": "PASS",
        "m09_opponent_interaction_synthesis": {
            "status": "PASS",
            "profiles": [{
                "team_identity_candidate_id": "team_a",
                "reciprocal_same_family_comparisons": [{
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "opponent_team_identity_candidate_id": "team_b",
                    "self_visible_process_profile": {"eligible_process_n": 12, "shot_ending_process_n": 3, "visible_loss_process_n": 5},
                    "opponent_visible_process_profile": {"eligible_process_n": 9, "shot_ending_process_n": 1, "visible_loss_process_n": 4},
                }],
            }],
        },
        "constructs": {
            "C02": {
                "player_function_profiles": [{
                    "actor_identity_candidate_id": "actor_1",
                    "actor_label": "Hikmet",
                    "function_dimensions": {
                        "ACCESS": [{
                            "metric_key": "progressive_passes",
                            "raw_value": 8,
                        }],
                        "TERMINAL": [{
                            "metric_key": "shots",
                            "raw_value": 3,
                        }],
                        "PROCESS": {
                            "process_participation_counts": {
                                "POSITIONAL_ATTACK_CANDIDATE": 12,
                            }
                        },
                    },
                }]
            }
        },
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_aliases_raw": ["Alpha"]},
            {"team_identity_candidate_id": "team_b", "team_aliases_raw": ["Beta"]},
        ],
        "actor_identity_candidates": [{
            "actor_identity_candidate_id": "actor_1",
            "actor_aliases_raw": ["Hikmet"],
            "validated_player_identity": True,
            "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
        }],
    }
    challenge = {
        "status": "PASS",
        "variant_feature_challenge_records": [],
    }

    files = {
        user_output_bundle.FEATURE_DELTA_JSON: feature,
        user_output_bundle.PROCESS_VARIANT_JSON: process_variant,
        user_output_bundle.VISIBLE_SEQUENCE_JSON: sequence,
        user_output_bundle.SAFE_FINDING_ADMISSION_JSON: admission,
        user_output_bundle.RICH_MULTIFORMAT_JSON: rich,
        user_output_bundle.IDENTITY_JSON: identity,
        user_output_bundle.VARIANT_FEATURE_CHALLENGE_JSON: challenge,
    }
    current = []
    for name, payload in files.items():
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        current.append(str(path))

    spine = _full_spine(current_artifacts=current)
    result = user_output_bundle.build_graph_ready_mechanism_cards_payload(
        tmp_path,
        spine,
    )
    assert result["card_count"] == 1
    card = result["cards"][0]
    safe = card["safe_finding_context"]
    assert card["source_mechanism_review_ref"] == "gsvfd_1"
    assert card["source_process_variant_family_ref"] == "opvf_1"
    assert card["source_first_supported_branch_divergence_refs"] == ["fsbd_1"]
    assert card["source_safe_finding_handoff_refs"] == ["sfh_1"]
    assert safe["safe_finding_handoff_refs"] == ["sfh_1"]
    assert safe["source_first_supported_branch_divergence_refs"] == ["fsbd_1"]
    assert safe["source_process_variant_family_ref"] == "opvf_1"
    assert safe["score_state_consensus"] is True
    assert safe["score_state_candidate"] == {"Alpha": 0, "Beta": 0}
    assert safe["provider_process_family_consensus"] is True
    assert safe["provider_process_family_candidates"] == [
        "POSITIONAL_ATTACK_CANDIDATE"
    ]
    context_review = card["context_review"]
    assert len(context_review["provider_context_difference_candidates"]) == 1
    assert context_review["provider_context_difference_candidates"][0]["feature_token"].endswith("process_shot_present_annotation_candidate:TRUE")
    assert context_review["opponent_same_family_context"] == {}
    assert context_review["context_is_causal_explanation"] is False
    assert context_review["context_can_increase_claim_ceiling"] is False
    assert safe["emit_decision_count"] == 0
    assert safe["claim_output_allowed_count"] == 0
    assert safe["creates_independent_support"] is False
    assert safe["can_authorize_emit"] is False

    maturity = card["evidence_maturity_profile"]
    assert maturity["resolved_variant_denominator_n"] == 3
    assert maturity["episode_spread_n"] == 2
    assert maturity["occurrence_disjoint_support_cluster_n"] == 2
    assert maturity["success_failure_divergence_n"] == 1
    assert maturity["dependency_independence_proven"] is False
    assert maturity["maturity_is_confidence_score"] is False
    assert maturity["maturity_can_authorize_emit"] is False

    player = card["player_context"]
    assert player["actor_identity_candidate_id"] == "actor_1"
    assert player["actor_label"] == "Hikmet"
    assert player["aggregate_metric_values"]["progressive_passes"] == 8
    assert player["aggregate_metric_values"]["shots"] == 3
    assert player["process_participation_counts"] == {
        "POSITIONAL_ATTACK_CANDIDATE": 12
    }
    assert player["aggregate_context_is_mechanism_action_identity"] is False
    assert player["aggregate_context_is_player_quality_truth"] is False
    assert player["aggregate_context_is_causal_contribution_truth"] is False

    review = card["analyst_review_contract"]
    lineage = review["evidence_lineage"]
    assert lineage["source_mechanism_review_ref"] == "gsvfd_1"
    assert lineage["source_process_variant_family_ref"] == "opvf_1"
    assert lineage["source_first_supported_branch_divergence_refs"] == ["fsbd_1"]
    assert lineage["source_safe_finding_handoff_refs"] == ["sfh_1"]
    assert lineage["lineage_creates_new_evidence"] is False
    assert lineage["lineage_strengthens_claim"] is False
    assert review["what_visible"]["resolved_variant_n"] == 3
    assert review["what_visible"]["positive_visible_variant_n"] == 2
    assert review["what_visible"]["negative_visible_variant_n"] == 1
    assert review["support"]["visible_episode_spread_n"] >= 0
    assert review["support"]["safe_finding_match_count"] == 1
    assert review["uncertainty"]["independent_support_proven"] is False
    assert review["uncertainty"]["branch_context_completeness_promoted"] is False
    assert review["uncertainty"]["causal_explanation_admitted"] is False
    assert "CAUSALITY" in review["forbidden_inference"]
    assert "PLAYER_QUALITY_TRUTH" in review["forbidden_inference"]
    assert review["safe_meaning"] == (
        "MATCH_LOCAL_VISIBLE_VARIANT_DIFFERENCE_FOR_ANALYST_REVIEW"
    )
    assert review["creates_new_evidence"] is False
    assert review["creates_independent_support"] is False
    assert review["can_change_shortlist_selection"] is False
    assert review["can_change_safe_finding_decision"] is False
    assert review["can_authorize_emit"] is False
    assert card["can_authorize_emit"] is False
    assert card["can_strengthen_claim_ceiling"] is False

    human_text = "\n".join(
        user_output_bundle._human_mechanism_cards(
            tmp_path,
            spine,
            identity,
            "tr",
        )
    )
    assert "Güvenli anlam:" in human_text
    assert "Yasak çıkarım:" in human_text
    assert "Analist aksiyonu:" in human_text
    assert "nedensellik" in human_text
    assert "taktik plan gerçeği" in human_text
    assert "oyuncu aggregate verisini yalnız maç-içi işlev bağlamı olarak kullan" in human_text


def test_standard_bundle_publishes_governed_presentation_view_and_html(tmp_path):
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    spine = _full_spine(
        feature_current=False,
        c4_current=False,
        current_artifacts=[str(full_json), str(full_txt)],
    )

    result = write_standard_user_outputs(tmp_path, spine)

    view_path = Path(result["presentation_view_model"])
    html_path = Path(result["professional_report_html"])
    assert view_path.name == user_output_bundle.PRESENTATION_VIEW_MODEL_JSON
    assert html_path.name == user_output_bundle.PROFESSIONAL_REPORT_HTML
    assert view_path.is_file()
    assert html_path.is_file()

    view = json.loads(view_path.read_text(encoding="utf-8"))
    assert view["view_model_creates_new_evidence"] is False
    assert view["view_model_can_strengthen_claim_ceiling"] is False
    assert view["production_release"] is False

    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    names = {row["name"] for row in manifest["files"]}
    assert user_output_bundle.PRESENTATION_VIEW_MODEL_JSON in names
    assert user_output_bundle.PROFESSIONAL_REPORT_HTML in names

    with zipfile.ZipFile(tmp_path / BUNDLE_ZIP) as archive:
        zip_names = set(archive.namelist())
    assert user_output_bundle.PRESENTATION_VIEW_MODEL_JSON in zip_names
    assert user_output_bundle.PROFESSIONAL_REPORT_HTML in zip_names


def test_stale_analyst_claim_file_cannot_enter_presentation_without_current_ledger(tmp_path):
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    claim_path = tmp_path / user_output_bundle.ANALYST_OUTPUT_CLAIM_JSON
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    claim_path.write_text(json.dumps({
        "status": "PASS",
        "analyst_output_contract_count": 1,
        "professional_emit_allowed_count": 1,
        "analyst_output_contracts": [{
            "analyst_output_contract_id": "stale_claim",
            "professional_emit_allowed": True,
            "render_what_visible_text_tr": "STALE SHOULD NOT RENDER",
        }],
    }), encoding="utf-8")

    spine = _full_spine(
        feature_current=False,
        c4_current=False,
        current_artifacts=[str(full_json), str(full_txt)],
    )
    result = write_standard_user_outputs(tmp_path, spine)
    view = json.loads(Path(result["presentation_view_model"]).read_text(encoding="utf-8"))

    assert view["claim_admission_summary"]["professional_emit_allowed_count"] == 0
    assert view["professional_claim_records"] == []
    assert "STALE SHOULD NOT RENDER" not in Path(result["professional_report_html"]).read_text(encoding="utf-8")

def test_ambiguous_multi_process_context_is_not_main_mechanism_label(tmp_path, monkeypatch):
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    feature_path.write_text(
        json.dumps({
            "status": "PASS",
            "grammar_stable_variant_feature_delta_records": [{
                "grammar_stable_variant_feature_delta_id": "broad_1",
                "source_process_variant_family_ref": "family_broad",
                "team_identity_candidate_ids": ["team_1"],
                "period_candidates": ["2"],
                "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "resolved_variant_count": 284,
                "success_resolved_variant_count": 277,
                "failure_resolved_variant_count": 7,
                "right_censored_variant_count": 0,
                "first_supported_context_difference_layer_candidate": 0,
                "first_supported_consequence_difference_layer_candidate": 0,
            }],
        }),
        encoding="utf-8",
    )
    identity = {
        "team_identity_candidates": [{
            "team_identity_candidate_id": "team_1",
            "team_normalized_key": "galatasaray",
            "team_aliases_raw": ["Galatasaray"],
        }]
    }
    shortlist = {
        "shortlist": [{
            "source_mechanism_review_ref": "broad_1",
            "source_process_variant_family_ref": "family_broad",
            "team_identity_candidate_ids": ["team_1"],
            "period_candidates": ["2"],
            "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
            "resolved_variant_count": 284,
            "success_resolved_variant_count": 277,
            "failure_resolved_variant_count": 7,
            "visible_episode_spread_count": 16,
            "occurrence_disjoint_support_cluster_count": 33,
            "review_support_state": "MULTI_EPISODE_OCCURRENCE_DISJOINT_SUCCESS_FAILURE_DIVERGENCE_VISIBLE",
            "process_context_binding_state": "AMBIGUOUS_MULTI_PROCESS_FAMILY_CONTEXT",
            "process_context_visible_episode_count": 16,
            "process_family_episode_presence_counts": {
                "COUNTERATTACK_CANDIDATE": 5,
                "POSITIONAL_ATTACK_CANDIDATE": 16,
            },
            "mechanism_challenge_reason_codes": [],
        }]
    }
    monkeypatch.setattr(
        user_output_bundle,
        "build_mechanism_story_review_shortlist",
        lambda *args, **kwargs: shortlist,
    )
    monkeypatch.setattr(
        user_output_bundle,
        "_mechanism_safe_context_by_family",
        lambda *args, **kwargs: {},
    )
    spine = _full_spine(current_artifacts=[str(feature_path)])

    tr = "\n".join(user_output_bundle._human_mechanism_cards(tmp_path, spine, identity, "tr"))
    en = "\n".join(user_output_bundle._human_mechanism_cards(tmp_path, spine, identity, "en"))

    assert "SINIF=GENİŞ BAĞLAM KARŞILAŞTIRMASI" in tr
    assert "SINIF=ANA MEKANİZMA ADAYI" not in tr
    assert "ana mekanizma olarak sunulmaz" in tr
    assert "CLASS=BROAD CONTEXT COMPARISON" in en
    assert "CLASS=MAIN MECHANISM CANDIDATE" not in en
    assert "not presented as a main mechanism" in en


def test_loss_recovery_score_state_cards_keep_exposure_and_claim_ceiling() -> None:
    rich = {
        "m05_loss_recovery_dynamics_synthesis": {
            "status": "PASS",
            "profiles": [{
                "team_identity_candidate_id": "team_1",
                "score_state_profiles": [{
                    "score_state_candidate": {"Galatasaray (1)": 0, "Trabzonspor (2)": 1},
                    "score_state_exposure_seconds_candidate": 600.0,
                    "visible_loss_context_n": 4,
                    "visible_recovery_context_n": 3,
                    "loss_next_opponent_process_family_counts": {
                        "COUNTERATTACK_CANDIDATE": 1
                    },
                    "recovery_next_own_process_family_counts": {
                        "POSITIONAL_ATTACK_CANDIDATE": 2
                    },
                }],
            }],
        }
    }
    identity = {
        "team_identity_candidates": [{
            "team_identity_candidate_id": "team_1",
            "team_normalized_key": "trabzonspor",
            "team_aliases_raw": ["Trabzonspor (2)"],
        }]
    }

    tr = user_output_bundle._human_loss_recovery_score_state_cards(
        rich, identity, "tr"
    )
    en = user_output_bundle._human_loss_recovery_score_state_cards(
        rich, identity, "en"
    )

    assert len(tr) == 1
    assert "yaklaşık 10.0 dakikalık görünür skor-state maruziyetinde" in tr[0]
    assert "4 görünür kayıp bağlamı" in tr[0]
    assert "3 görünür geri kazanım bağlamı" in tr[0]
    assert "kontra atak 1" in tr[0]
    assert "yerleşik hücum 2" in tr[0]
    assert "neden, taktik plan veya geçiş kalitesi" in tr[0]

    assert len(en) == 1
    assert "approximately 10.0 minutes of visible score-state exposure" in en[0]
    assert "4 visible loss contexts" in en[0]
    assert "3 visible recovery contexts" in en[0]
    assert "not treated as cause, tactical plan, or transition quality" in en[0]


def test_process_variant_board_cards_surface_recurrence_variants_and_visible_actor_edges() -> None:
    rich = {
        "constructs": {
            "C03": {
                "process_variant_board": {
                    "status": "PASS",
                    "rows": [{
                        "team_identity_candidate_id": "team_1",
                        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                        "member_process_n": 4,
                        "morphology_signature": {
                            "length_bucket": "MEDIUM_3_5_LAYERS",
                            "pass_carry_style": "PASS_DOMINANT",
                            "route_hint": "MIDDLE_THIRD->FINAL_THIRD",
                            "action_family_presence": ["PASS", "CARRY"],
                        },
                        "member_variant_context_counts": {
                            "SHOT_LINKED": 2,
                            "LOSS_LINKED": 2,
                        },
                        "visible_start_actor_candidate_counts": {"actor_1": 3, "actor_2": 1},
                        "visible_end_actor_candidate_counts": {"actor_3": 2, "actor_4": 2},
                        "visible_score_state_context": {
                            "member_process_n": 4,
                            "bound_member_process_n": 4,
                            "unresolved_member_process_n": 0,
                            "relative_score_state_counts": {"DRAW": 1, "LEADING": 2, "TRAILING": 1},
                            "score_state_context_is_causal_explanation": False,
                            "score_state_context_is_tactical_adaptation_truth": False,
                        },
                        "provider_attack_axis_transition_profile": {
                            "member_process_n": 4,
                            "axis_admitted_member_process_n": 4,
                            "member_with_visible_axis_transition_n": 3,
                            "visible_axis_transition_n": 8,
                            "direction_transition_counts": {
                                "FORWARD_PROVIDER_ATTACK_AXIS_CANDIDATE": 5,
                                "REARWARD_PROVIDER_ATTACK_AXIS_CANDIDATE": 2,
                                "STABLE_PROVIDER_ATTACK_AXIS_CANDIDATE": 1,
                            },
                            "direction_member_presence_counts": {
                                "FORWARD_PROVIDER_ATTACK_AXIS_CANDIDATE": 3,
                                "REARWARD_PROVIDER_ATTACK_AXIS_CANDIDATE": 2,
                                "STABLE_PROVIDER_ATTACK_AXIS_CANDIDATE": 1,
                            },
                            "axis_profile_is_route_truth": False,
                            "axis_profile_is_physical_displacement_truth": False,
                            "axis_profile_is_tactical_progression_truth": False,
                            "claim_ceiling": "MATCH_LOCAL_PROVIDER_ATTACK_AXIS_TRANSITION_PROFILE_ONLY",
                        },
                        "representative_first_supported_grammar_divergence": {
                            "left_variant_context": "SHOT_LINKED",
                            "right_variant_context": "LOSS_LINKED",
                            "first_supported_grammar_divergence": {
                                "operation": "SUBSTITUTE",
                                "left_token": "SHOT",
                                "right_token": "TURNOVER",
                            },
                        },
                        "start_end_actor_candidates_are_sequence_initiator_ender_truth": False,
                        "motif_is_tactical_pattern_truth": False,
                        "claim_ceiling": "MATCH_LOCAL_PROCESS_VARIANT_BOARD_CANDIDATE_ONLY",
                    }],
                }
            }
        }
    }
    identity = {
        "team_identity_candidates": [{
            "team_identity_candidate_id": "team_1",
            "team_aliases_raw": ["Trabzonspor"],
        }],
        "actor_identity_candidates": [
            {
                "actor_identity_candidate_id": "actor_1",
                "actor_aliases_raw": ["Player A"],
                "validated_player_identity": True,
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
            },
            {
                "actor_identity_candidate_id": "actor_3",
                "actor_aliases_raw": ["Player C"],
                "validated_player_identity": True,
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
            },
        ],
    }

    cards = user_output_bundle._human_process_variant_board_cards(rich, identity, "tr")

    assert len(cards) == 1
    text = cards[0]
    assert "Trabzonspor" in text
    assert "4 görünür süreç" in text
    assert "2 şut bağlantılı" in text
    assert "2 kayıp bağlantılı" in text
    assert "Player A" in text
    assert "Player C" in text
    assert "şut bağlantılı varyant ↔ kayıp bağlantılı varyant" in text
    assert "şut ↔ top kaybı" in text
    assert "Skor bağlamı: beraberlikte 1, öndeyken 2, gerideyken 1" in text
    assert "taktik uyarlama ve nedensellik bu yüzeyin kapsamı dışındadır" in text
    assert "Provider hücum ekseni" in text
    assert "3/4 üye süreçte görünür yön geçişi" in text
    assert "ileri 5, geri 2, stabil 1" in text
    assert "fiziksel rota, line-break ve taktik progresyon bu kapsamın dışındadır" in text
    assert "SHOT_LINKED" not in text
    assert "TURNOVER" not in text
    assert "başlangıç/bitiş rolü yalnız görünür katman adayını gösterir" in text


def test_process_variant_board_cards_limit_to_three_attention_rows_per_team_without_truth_rank() -> None:
    rows = []
    for idx, n in enumerate((9, 7, 5, 3), start=1):
        rows.append({
            "process_motif_family_candidate_id": f"m{idx}",
            "team_identity_candidate_id": "team_1",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "member_process_n": n,
            "morphology_signature": {},
            "member_variant_context_counts": {},
            "visible_start_actor_candidate_counts": {},
            "visible_end_actor_candidate_counts": {},
            "representative_first_supported_grammar_divergence": None,
        })
    rich = {
        "constructs": {
            "C03": {
                "process_variant_board": {
                    "status": "PASS",
                    "rows": rows,
                }
            }
        }
    }
    identity = {
        "team_identity_candidates": [{
            "team_identity_candidate_id": "team_1",
            "team_aliases_raw": ["Trabzonspor"],
        }]
    }

    cards = user_output_bundle._human_process_variant_board_cards(rich, identity, "tr")

    assert len(cards) == 3
    assert "9 görünür süreç" in cards[0]
    assert "7 görünür süreç" in cards[1]
    assert "5 görünür süreç" in cards[2]
    assert all("yalnız inceleme önceliği üretir; futbol doğruluğu sıralaması üretmez" in card for card in cards)


def test_model_context_cards_surface_causal_ladder_and_calibration_warning() -> None:
    rich = {
        "constructs": {
            "C04": {
                "model_context_residual_profiles": [{
                    "entity_candidate": "Player One",
                    "xgt": 2.5,
                    "xgopp": 1.0,
                    "nxg_observed": 1.5,
                    "causal_ladder_rung": "RUNG_1_ASSOCIATIONAL_PREDICTIVE_CONTEXT_ONLY",
                    "causal_identification_proven": False,
                    "causal_language_allowed": False,
                    "model_calibration_state": "UNKNOWN_NOT_ADMITTED",
                    "model_calibration_warning_required": True,
                    "model_output_is_fact": False,
                    "claim_ceiling": "PROVIDER_MODEL_MATCH_CONTEXT_RESIDUAL_ONLY",
                }]
            }
        }
    }

    tr = user_output_bundle._human_model_context_cards(rich, "tr")
    en = user_output_bundle._human_model_context_cards(rich, "en")

    assert len(tr) == 1
    assert "Player One" in tr[0]
    assert "Rung-1" in tr[0]
    assert "oyuncu nedensel katkısı bu kapsam dışında kalır" in tr[0]
    assert "Model kalibrasyon durumu UNKNOWN_NOT_ADMITTED" in tr[0]
    assert "Model çıktısı yalnız model bağlamı olarak ele alınır" in tr[0]

    assert len(en) == 1
    assert "Rung-1" in en[0]
    assert "causal player contribution remains outside this scope" in en[0]
    assert "Model calibration state is UNKNOWN_NOT_ADMITTED" in en[0]


def test_opponent_interaction_cards_surface_existing_m09_without_response_or_causal_promotion():
    rich = {
        "m09_opponent_interaction_synthesis": {
            "status": "PASS",
            "profiles": [{
                "team_identity_candidate_id": "team_a",
                "six_phase_direction_n": 6,
                "visible_six_phase_direction_n": 5,
                "unresolved_six_phase_direction_n": 1,
                "reciprocal_same_family_comparison_n": 1,
                "reciprocal_same_family_comparisons": [{
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "team_identity_candidate_id": "team_a",
                    "opponent_team_identity_candidate_id": "team_b",
                    "self_visible_process_profile": {
                        "eligible_process_n": 12,
                        "shot_ending_process_n": 3,
                        "visible_loss_process_n": 5,
                        "visible_recovery_process_n": 2,
                        "visible_consequence_response_profile": {
                            "eligible_process_n": 12,
                            "categories_are_mutually_exclusive": False,
                            "no_visible_followup_is_failure": False,
                            "opponent_handover_is_forced_turnover_truth": False,
                            "opponent_takeover_is_pressure_success_truth": False,
                            "process_presence_counts": {
                                "SAME_TEAM_CONTINUATION_CANDIDATE": 8,
                                "OPPONENT_HANDOVER_CANDIDATE": 6,
                                "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE": 3,
                                "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE": 2,
                                "NO_VISIBLE_FOLLOW_UP_CANDIDATE": 4,
                            },
                        },
                    },
                    "opponent_visible_process_profile": {
                        "eligible_process_n": 9,
                        "shot_ending_process_n": 1,
                        "visible_loss_process_n": 4,
                        "visible_recovery_process_n": 1,
                        "visible_consequence_response_profile": {
                            "eligible_process_n": 9,
                            "categories_are_mutually_exclusive": False,
                            "no_visible_followup_is_failure": False,
                            "opponent_handover_is_forced_turnover_truth": False,
                            "opponent_takeover_is_pressure_success_truth": False,
                            "process_presence_counts": {
                                "SAME_TEAM_CONTINUATION_CANDIDATE": 5,
                                "OPPONENT_HANDOVER_CANDIDATE": 4,
                                "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE": 2,
                                "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE": 1,
                                "NO_VISIBLE_FOLLOW_UP_CANDIDATE": 3,
                            },
                        },
                    },
                    "difference_is_opponent_response_truth": False,
                    "difference_is_tactical_superiority_truth": False,
                    "difference_is_causal_truth": False,
                }],
                "reciprocal_difference_is_opponent_response_truth": False,
                "reciprocal_difference_is_tactical_superiority_truth": False,
                "reciprocal_difference_is_causal_truth": False,
                "claim_ceiling": "MATCH_LOCAL_VISIBLE_OPPONENT_INTERACTION_CONTEXT_CANDIDATE_ONLY",
            }],
        }
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_normalized_key": "alpha"},
            {"team_identity_candidate_id": "team_b", "team_normalized_key": "beta"},
        ]
    }

    cards = user_output_bundle._human_opponent_interaction_cards(rich, identity, "tr")
    text = "\n".join(cards)

    assert "Alpha ↔ Beta" in text
    assert "yerleşik hücum" in text
    assert "12 görünür süreç" in text
    assert "Beta aynı ailede 9 görünür süreç" in text
    assert "5/6 yön" in text
    assert "Görünür devam/sonuç kompozisyonu" in text
    assert "Alpha: aynı takım devamı 8, rakibe geçiş 6, breakdown sonrası rakip takeover 3, same-time review 2, görünür follow-up yok 4" in text
    assert "Beta: aynı takım devamı 5, rakibe geçiş 4, breakdown sonrası rakip takeover 2, same-time review 1, görünür follow-up yok 3" in text
    assert "kategoriler birbirini dışlamaz" in text
    assert "görünür follow-up yokluğu başarısızlık olarak yorumlanmaz" in text
    assert "Opponent-response, taktik üstünlük ve nedensellik için ayrı kanıt gerekir" in text


def test_opponent_interaction_cards_deduplicate_mirrored_team_perspectives():
    comparison_ab = {
        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
        "team_identity_candidate_id": "team_a",
        "opponent_team_identity_candidate_id": "team_b",
        "self_visible_process_profile": {"eligible_process_n": 12, "shot_ending_process_n": 3, "visible_loss_process_n": 5},
        "opponent_visible_process_profile": {"eligible_process_n": 9, "shot_ending_process_n": 1, "visible_loss_process_n": 4},
    }
    comparison_ba = {
        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
        "team_identity_candidate_id": "team_b",
        "opponent_team_identity_candidate_id": "team_a",
        "self_visible_process_profile": {"eligible_process_n": 9, "shot_ending_process_n": 1, "visible_loss_process_n": 4},
        "opponent_visible_process_profile": {"eligible_process_n": 12, "shot_ending_process_n": 3, "visible_loss_process_n": 5},
    }
    rich = {
        "m09_opponent_interaction_synthesis": {
            "status": "PASS",
            "profiles": [
                {
                    "team_identity_candidate_id": "team_a",
                    "six_phase_direction_n": 6,
                    "visible_six_phase_direction_n": 6,
                    "reciprocal_same_family_comparisons": [comparison_ab],
                },
                {
                    "team_identity_candidate_id": "team_b",
                    "six_phase_direction_n": 6,
                    "visible_six_phase_direction_n": 6,
                    "reciprocal_same_family_comparisons": [comparison_ba],
                },
            ],
        }
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_normalized_key": "alpha"},
            {"team_identity_candidate_id": "team_b", "team_normalized_key": "beta"},
        ]
    }

    cards = user_output_bundle._human_opponent_interaction_cards(rich, identity, "tr")

    assert len(cards) == 1
    assert "Alpha ↔ Beta" in cards[0]


def test_set_piece_process_cards_surface_visible_outcome_and_post_process_state_without_tactical_inflation() -> None:
    rich = {
        "set_piece_process_consequence_context": {
            "status": "PASS",
            "rows": [
                {
                    "team_identity_candidate_id": "team_a",
                    "provider_restart_type_candidates": ["CORNER"],
                    "shot_present_annotation_candidate": True,
                    "binding_state": "VISIBLE_CONSEQUENCE_CONTEXT_BOUND",
                    "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                    "post_set_piece_first_visible_team_state": "SAME_TEAM_FIRST_STRICT_AFTER_VISIBLE_CANDIDATE",
                },
                {
                    "team_identity_candidate_id": "team_a",
                    "provider_restart_type_candidates": ["FREE_KICK"],
                    "shot_present_annotation_candidate": False,
                    "binding_state": "NO_VISIBLE_CONSEQUENCE_MATCH",
                    "primary_consequence_candidates": [],
                    "post_set_piece_first_visible_team_state": "OPPONENT_FIRST_STRICT_AFTER_VISIBLE_CANDIDATE",
                },
                {
                    "team_identity_candidate_id": "team_a",
                    "provider_restart_type_candidates": ["THROW_IN"],
                    "shot_present_annotation_candidate": False,
                    "binding_state": "VISIBLE_CONSEQUENCE_CONTEXT_BOUND",
                    "primary_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
                    "post_set_piece_first_visible_team_state": "FIRST_STRICT_AFTER_OUTSIDE_DECLARED_CONSEQUENCE_HORIZON",
                },
            ],
            "declared_consequence_horizon_seconds": 12.0,
            "set_piece_process_is_designed_routine_truth": False,
            "visible_consequence_is_causal_truth": False,
        }
    }
    identity = {
        "team_identity_candidates": [{
            "team_identity_candidate_id": "team_a",
            "team_aliases_raw": ["Alpha FC"],
        }]
    }

    tr = user_output_bundle._human_set_piece_process_cards(rich, identity, "tr")
    en = user_output_bundle._human_set_piece_process_cards(rich, identity, "en")

    assert len(tr) == 2
    assert "Alpha FC" in tr[0]
    assert "3 görünür duran top hücum süreci" in tr[0]
    assert "provider-reviewed tür dağılımı: korner 1, serbest vuruş 1, taç 1" in tr[0]
    assert "1 süreçte şut anotasyonu" in tr[0]
    assert "2 süreç görünür sonuç bağlamına bağlandı" in tr[0]
    assert "aynı takım 1" in tr[0]
    assert "rakip 1" in tr[0]
    assert "12.0 sn" in tr[0]
    assert "tasarlanmış duran top rutini" in tr[1].lower()
    assert "nedensel sonuç" in tr[1]

    assert len(en) == 2
    assert "3 visible attacking set-piece processes" in en[0]
    assert "provider-reviewed restart types: corner 1, free kick 1, throw-in 1" in en[0]
    assert "1 carried a shot annotation" in en[0]
    assert "2 bound to visible consequence context" in en[0]
    assert "designed set-piece routine" in en[1].lower()
    assert "causal consequence" in en[1]


def test_actor_aggregate_context_surfaces_total_minutes_but_not_interval_exposure():
    sentence = user_output_bundle._actor_aggregate_context_sentence(
        "actor_1",
        {"some": "locator"},
        {
            "actor_1": {
                "actor_identity_candidate_id": "actor_1",
                "total_minutes_observed_candidate": 63.0,
                "total_exposure_state": "MATCH_TOTAL_MINUTES_OBSERVED_CANDIDATE",
                "interval_exposure_state": "NOT_ESTABLISHED_NO_SUBSTITUTION_TIMELINE_AUTHORITY",
                "per90_process_rate_admitted": False,
                "function_dimensions": {
                    "PROCESS": {
                        "process_participation_counts": {
                            "POSITIONAL_ATTACK_CANDIDATE": 4,
                        }
                    }
                },
            }
        },
        {"actor_1": "Player One"},
        "tr",
    )

    assert "toplam süre bağlamı: 63 dk" in sentence.lower()
    assert "süreç anındaki saha-içi zaman aralığı çözümlenmedi" in sentence
    assert "per-90 süreç oranı bu kartta üretilmez" in sentence.lower()


def test_set_piece_cards_surface_restart_type_outcome_counts_without_percentage():
    rich = {
        "set_piece_process_consequence_context": {
            "status": "PASS",
            "declared_consequence_horizon_seconds": 12.0,
            "rows": [{
                "team_identity_candidate_id": "team_a",
                "provider_restart_type_candidates": ["CORNER"],
                "shot_present_annotation_candidate": True,
                "binding_state": "VISIBLE_CONSEQUENCE_CONTEXT_BOUND",
                "post_set_piece_first_visible_team_state": "SAME_TEAM_FIRST_STRICT_AFTER_VISIBLE_CANDIDATE",
            }],
            "restart_type_profiles": [
                {
                    "team_identity_candidate_id": "team_a",
                    "provider_restart_type_candidate": "CORNER",
                    "process_n": 5,
                    "shot_annotated_n": 1,
                    "visible_consequence_bound_n": 3,
                    "same_team_first_visible_n": 1,
                    "opponent_first_visible_n": 1,
                    "outside_declared_horizon_n": 3,
                    "no_visible_continuation_n": 0,
                    "rate_emitted": False,
                },
                {
                    "team_identity_candidate_id": "team_a",
                    "provider_restart_type_candidate": "FREE_KICK",
                    "process_n": 2,
                    "shot_annotated_n": 0,
                    "visible_consequence_bound_n": 1,
                    "same_team_first_visible_n": 0,
                    "opponent_first_visible_n": 1,
                    "outside_declared_horizon_n": 1,
                    "no_visible_continuation_n": 0,
                    "rate_emitted": False,
                },
            ],
        }
    }
    identity = {
        "team_identity_candidates": [{
            "team_identity_candidate_id": "team_a",
            "team_aliases_raw": ["Alpha FC"],
        }]
    }

    tr = user_output_bundle._human_set_piece_process_cards(rich, identity, "tr")
    joined = " ".join(tr)

    assert "Tür bazında görünür sonuç:" in joined
    assert "korner n=5" in joined
    assert "şut=1" in joined
    assert "sonuç-bağlı=3" in joined
    assert "serbest vuruş n=2" in joined
    assert "%" not in joined


def test_match_story_cards_lead_with_visible_attack_process_summary_without_quality_claim() -> None:
    rich = {
        "constructs": {
            "C03": {
                "six_phase_team_matrix": [
                    {
                        "team_identity_candidate_id": "team_a",
                        "canonical_phase_slot": "ESTABLISHED_ATTACK",
                        "perspective": "ATTACK",
                        "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
                        "eligible_process_n": 12,
                        "shot_ending_process_n": 3,
                        "visible_loss_process_n": 4,
                        "visible_recovery_process_n": 1,
                    },
                    {
                        "team_identity_candidate_id": "team_a",
                        "canonical_phase_slot": "ATTACKING_TRANSITION",
                        "perspective": "ATTACK",
                        "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
                        "eligible_process_n": 5,
                        "shot_ending_process_n": 1,
                        "visible_loss_process_n": 2,
                        "visible_recovery_process_n": 0,
                    },
                    {
                        "team_identity_candidate_id": "team_b",
                        "canonical_phase_slot": "ESTABLISHED_ATTACK",
                        "perspective": "ATTACK",
                        "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
                        "eligible_process_n": 9,
                        "shot_ending_process_n": 2,
                        "visible_loss_process_n": 3,
                        "visible_recovery_process_n": 0,
                    },
                ]
            }
        }
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_aliases_raw": ["Alpha"]},
            {"team_identity_candidate_id": "team_b", "team_aliases_raw": ["Beta"]},
        ]
    }

    tr = user_output_bundle._human_match_story_cards(rich, identity, "tr")
    en = user_output_bundle._human_match_story_cards(rich, identity, "en")

    assert len(tr) == 3
    assert "Alpha" in tr[0]
    assert "yerleşik hücum" in tr[0]
    assert "12 görünür süreç" in tr[0]
    assert "3 şut bağlantılı" in tr[0]
    assert "4 görünür kayıp" in tr[0]
    assert "kalite" not in tr[0].lower()
    assert "üstün" not in tr[0].lower()
    assert "neden" not in tr[0].lower()
    assert "Beta" in tr[1]
    assert "görünür hacim özeti" in tr[2]

    assert len(en) == 3
    assert "Alpha" in en[0]
    assert "established attack" in en[0]
    assert "12 visible processes" in en[0]
    assert "quality" not in en[0].lower()
    assert "causal" not in en[0].lower()


def test_match_story_cards_add_score_arc_and_same_family_interaction_without_winner_language() -> None:
    rich = {
        "constructs": {
            "C03": {
                "six_phase_team_matrix": [
                    {
                        "team_identity_candidate_id": "team_a",
                        "canonical_phase_slot": "ESTABLISHED_ATTACK",
                        "perspective": "ATTACK",
                        "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
                        "eligible_process_n": 12,
                        "shot_ending_process_n": 3,
                        "visible_loss_process_n": 4,
                        "visible_recovery_process_n": 1,
                    },
                    {
                        "team_identity_candidate_id": "team_b",
                        "canonical_phase_slot": "ESTABLISHED_ATTACK",
                        "perspective": "ATTACK",
                        "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
                        "eligible_process_n": 9,
                        "shot_ending_process_n": 2,
                        "visible_loss_process_n": 3,
                        "visible_recovery_process_n": 0,
                    },
                ]
            }
        },
        "game_state_context": {
            "status": "PASS",
            "score_state_segments": [
                {
                    "duration_second_candidate": 300.0,
                    "score_state_candidate": {"Alpha": 0, "Beta": 0},
                },
                {
                    "duration_second_candidate": 1800.0,
                    "score_state_candidate": {"Alpha": 1, "Beta": 0},
                },
            ],
        },
        "m09_opponent_interaction_synthesis": {
            "status": "PASS",
            "profiles": [
                {
                    "team_identity_candidate_id": "team_a",
                    "reciprocal_same_family_comparisons": [
                        {
                            "opponent_team_identity_candidate_id": "team_b",
                            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                            "self_visible_process_profile": {
                                "eligible_process_n": 12,
                                "shot_ending_process_n": 3,
                                "visible_loss_process_n": 4,
                            },
                            "opponent_visible_process_profile": {
                                "eligible_process_n": 9,
                                "shot_ending_process_n": 2,
                                "visible_loss_process_n": 3,
                            },
                        }
                    ],
                },
                {
                    "team_identity_candidate_id": "team_b",
                    "reciprocal_same_family_comparisons": [
                        {
                            "opponent_team_identity_candidate_id": "team_a",
                            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                            "self_visible_process_profile": {
                                "eligible_process_n": 9,
                                "shot_ending_process_n": 2,
                                "visible_loss_process_n": 3,
                            },
                            "opponent_visible_process_profile": {
                                "eligible_process_n": 12,
                                "shot_ending_process_n": 3,
                                "visible_loss_process_n": 4,
                            },
                        }
                    ],
                },
            ],
        },
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_aliases_raw": ["Alpha"]},
            {"team_identity_candidate_id": "team_b", "team_aliases_raw": ["Beta"]},
        ]
    }

    tr = user_output_bundle._human_match_story_cards(rich, identity, "tr")
    en = user_output_bundle._human_match_story_cards(rich, identity, "en")

    joined_tr = " ".join(tr)
    joined_en = " ".join(en)
    assert "Skor akışı" in joined_tr
    assert "5.0 dk" in joined_tr
    assert "30.0 dk" in joined_tr
    assert "aynı süreç ailesi" in joined_tr
    assert "Alpha 12 süreç / 3 şut bağlantılı / 4 kayıp" in joined_tr
    assert "Beta 9 süreç / 2 şut bağlantılı / 3 kayıp" in joined_tr
    story_tr = " ".join(line for line in tr if not line.startswith("Kanıt kapsamı:"))
    story_en = " ".join(line for line in en if not line.startswith("Evidence scope:"))
    assert "üstün" not in story_tr.lower()
    assert "daha iyi" not in story_tr.lower()
    assert "neden" not in story_tr.lower()

    assert "Score-state exposure" in joined_en
    assert "same process family" in joined_en
    assert "superior" not in story_en.lower()
    assert "better" not in story_en.lower()


def test_match_story_mechanism_highlights_select_human_review_lines_only() -> None:
    mechanism_cards = [
        "MEKANİZMA KARTI 1 | SINIF=ANA MEKANİZMA ADAYI | ...",
        "İnceleme noktası 1: Alpha, 1. devre. pas arası → pas bağlantısı iki bölümde tekrar görülüyor. Bu bağlantının karşılaştırılabilir varyantları hem olumlu hem olumsuz görünür sonuçlara gidiyor. Analist için asıl soru, hangi değişimin sonuçları ayırdığı.",
        "Kanıt notu: dört varyant.",
        "MEKANİZMA KARTI 2 | SINIF=GENİŞ BAĞLAM KARŞILAŞTIRMASI | ...",
        "Geniş bağlam karşılaştırması 2: Alpha, 2. devre. pas → pas bağlantısı tekrar görülüyor.",
        "Kanıt notu: çoklu bağlam.",
        "MEKANİZMA KARTI 3 | SINIF=SINIRLI KARŞILAŞTIRMA | ...",
        "Sınırlı karşılaştırma 3: Beta, 1. devre. ikili mücadele → pas.",
        "Kanıt notu: tek bölüm.",
    ]

    tr = user_output_bundle._human_match_story_mechanism_highlights(
        mechanism_cards, "tr", limit=2
    )

    assert len(tr) == 2
    assert tr[0].startswith("İnceleme noktası 1:")
    assert tr[1].startswith("Geniş bağlam karşılaştırması 2:")
    assert "Analist için asıl soru" not in tr[0]
    assert all("MEKANİZMA KARTI" not in line for line in tr)
    assert all("Kanıt notu:" not in line for line in tr)


def test_match_story_mechanism_highlights_support_english_and_no_fixed_analysis_count() -> None:
    mechanism_cards = [
        "MECHANISM CARD 1 | CLASS=MAIN MECHANISM CANDIDATE | ...",
        "Review point 1: Alpha, first half. interception → pass repeats. Comparable variants lead to both positive and negative visible outcomes. The analyst question is what separates them.",
        "Evidence note: four variants.",
        "MECHANISM CARD 2 | CLASS=LIMITED COMPARISON | ...",
        "Limited comparison 2: Beta, second half. duel → pass.",
        "Evidence note: two variants.",
    ]

    en = user_output_bundle._human_match_story_mechanism_highlights(
        mechanism_cards, "en", limit=1
    )

    assert en == ["Review point 1: Alpha, first half. interception → pass repeats. Comparable variants lead to both positive and negative visible outcomes."]


def test_mechanism_context_review_sentence_combines_provider_context_and_same_family_opponent_view_without_causal_promotion():
    source_record = {
        "process_context_feature_difference_candidates": [
            {
                "feature_token": "LAYER[0]::process_shot_present_annotation_candidate:TRUE",
                "partial_order_layer_index": 0,
                "success_visible_numerator": 3,
                "success_eligible_denominator": 4,
                "failure_visible_numerator": 0,
                "failure_eligible_denominator": 2,
                "descriptive_rate_delta_success_minus_failure": 0.75,
                "difference_is_failure_cause_truth": False,
                "difference_is_tactical_explanation": False,
                "dependency_independence_proven": False,
            }
        ]
    }
    rich = {
        "m09_opponent_interaction_synthesis": {
            "status": "PASS",
            "profiles": [{
                "team_identity_candidate_id": "team_a",
                "reciprocal_same_family_comparisons": [{
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "opponent_team_identity_candidate_id": "team_b",
                    "self_visible_process_profile": {
                        "eligible_process_n": 12,
                        "shot_ending_process_n": 3,
                        "visible_loss_process_n": 5,
                    },
                    "opponent_visible_process_profile": {
                        "eligible_process_n": 9,
                        "shot_ending_process_n": 1,
                        "visible_loss_process_n": 4,
                    },
                }],
            }],
        }
    }
    teams = {"team_a": "Alpha", "team_b": "Beta"}

    text = user_output_bundle._mechanism_context_review_sentence(
        source_record,
        rich,
        ["team_a"],
        "POSITIONAL_ATTACK_CANDIDATE",
        teams,
        "tr",
    )

    assert "Bağlam ayrışması" in text
    assert "süreçte şut-var işareti" in text
    assert "olumlu 3/4" in text
    assert "olumsuz 0/2" in text
    assert "Aynı süreç ailesinin karşılıklı görünümü" in text
    assert "Alpha 12 süreç" in text
    assert "Beta 9 süreç" in text
    assert "neden, rakip tepkisi veya taktik üstünlük kanıtı üretmez" in text

def test_visible_state_function_lens_surfaces_observable_subset_and_unknowns() -> None:
    full = {
        "spatial_progression_evidence": {
            "status": "REVIEW_REQUIRED",
            "state_transition_dynamics_candidate_count": 100,
            "visible_state_change_function_counts": {
                "VISIBLE_SAME_TEAM_CONTINUATION_CANDIDATE": 50,
                "VISIBLE_STATE_ADVANCEMENT_CONTINUATION_CANDIDATE": 8,
                "VISIBLE_ADVANCED_ACCESS_CONTINUATION_CANDIDATE": 4,
                "VISIBLE_ADVANTAGE_EXPLOITATION_CANDIDATE": 3,
                "VISIBLE_ADVANTAGE_LOSS_OR_HANDOVER_CANDIDATE": 20,
                "VISIBLE_STATE_CHANGE_REVIEW_REQUIRED_CANDIDATE": 10,
                "VISIBLE_STATE_CHANGE_UNRESOLVED_NO_FOLLOW_UP_CANDIDATE": 5,
            },
            "state_change_function_is_opponent_organization_truth": False,
            "state_change_function_is_player_causal_credit": False,
            "state_change_function_is_value_model_output": False,
        }
    }

    tr = user_output_bundle._human_visible_state_function_lens(full, "tr")
    en = user_output_bundle._human_visible_state_function_lens(full, "en")

    joined_tr = " ".join(tr)
    joined_en = " ".join(en)
    assert "koruma-benzeri aynı takım devamı 50" in joined_tr
    assert "büyütme/ilerletme-benzeri görünür devam 12" in joined_tr
    assert "kullanma-benzeri görünür avantaj değerlendirme 3" in joined_tr
    assert "avantaj kaybı/rakibe geçiş 20" in joined_tr
    assert "CREATE=UNKNOWN" in joined_tr
    assert "DENY=UNKNOWN" in joined_tr
    assert "Oyuncu nedensel katkısı, rakip organizasyonu ve değer modeli yorumu bu kartın kapsamı dışındadır." in joined_tr

    assert "preserve-like same-team continuation 50" in joined_en
    assert "CREATE=UNKNOWN" in joined_en
    assert "DENY=UNKNOWN" in joined_en


def test_visible_state_function_lens_returns_empty_without_current_evidence() -> None:
    assert user_output_bundle._human_visible_state_function_lens({}, "tr") == []
    assert user_output_bundle._human_visible_state_function_lens(
        {"spatial_progression_evidence": {"status": "NOT_EVALUATED"}}, "en"
    ) == []


def test_mechanism_context_review_payload_binds_opponent_only_with_explicit_single_family():
    rich = {
        "m09_opponent_interaction_synthesis": {
            "status": "PASS",
            "profiles": [{
                "team_identity_candidate_id": "team_a",
                "reciprocal_same_family_comparisons": [{
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "opponent_team_identity_candidate_id": "team_b",
                    "self_visible_process_profile": {"eligible_process_n": 12},
                    "opponent_visible_process_profile": {"eligible_process_n": 9},
                }],
            }],
        }
    }
    bound = user_output_bundle._mechanism_context_review_payload(
        {}, rich, ["team_a"], "POSITIONAL_ATTACK_CANDIDATE", {}
    )
    assert bound["opponent_same_family_context"]["opponent_team_identity_candidate_id"] == "team_b"
    assert bound["opponent_same_family_context"]["self_visible_process_profile"]["eligible_process_n"] == 12

    ambiguous = user_output_bundle._mechanism_context_review_payload(
        {},
        rich,
        ["team_a"],
        None,
        {
            "provider_process_family_consensus": True,
            "provider_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
        },
    )
    assert ambiguous["opponent_same_family_context"] == {}


def test_player_function_cards_surface_match_local_function_context_without_quality_ranking() -> None:
    rich = {
        "player_score_state_process_participation": {
            "status": "PASS",
            "profiles": [
                {
                    "actor_identity_candidate_id": "a1",
                    "score_state_candidate": {"Alpha": 1, "Beta": 0},
                    "score_segment_start_second_candidate": 100.0,
                    "visible_process_participation_n": 9,
                    "shot_ending_process_participation_n": 2,
                    "player_exposure_admitted": False,
                    "player_rate_output_allowed": False,
                },
                {
                    "actor_identity_candidate_id": "a1",
                    "score_state_candidate": {"Alpha": 0, "Beta": 0},
                    "score_segment_start_second_candidate": 0.0,
                    "visible_process_participation_n": 3,
                    "shot_ending_process_participation_n": 0,
                    "player_exposure_admitted": False,
                    "player_rate_output_allowed": False,
                },
            ],
        },
        "constructs": {
            "C02": {
                "player_function_profiles": [
                    {
                        "actor_identity_candidate_id": "a1",
                        "actor_label": "Player One",
                        "team_identity_candidate_id": "team_a",
                        "team_label": "Alpha",
                        "process_participation_counts": {
                            "POSITIONAL_ATTACK_CANDIDATE": 12,
                            "COUNTERATTACK_CANDIDATE": 3,
                        },
                        "shot_ending_process_participation_counts": {
                            "POSITIONAL_ATTACK_CANDIDATE": 2,
                        },
                        "function_dimensions": {
                            "ACCESS": [
                                {"metric_key": "progressive_passes", "raw_value": 7},
                                {"metric_key": "passes_into_the_penalty_box", "raw_value": 4},
                            ],
                            "CREATION": [
                                {"metric_key": "chances_created", "raw_value": 2},
                            ],
                            "TERMINAL": [
                                {"metric_key": "shots", "raw_value": 1},
                                {"metric_key": "goals", "raw_value": 0},
                            ],
                            "RECOVERY_LOSS": [
                                {"metric_key": "ball_recoveries", "raw_value": 5},
                                {"metric_key": "lost_balls", "raw_value": 8},
                            ],
                            "PROCESS": {},
                        },
                        "profile_has_any_context": True,
                        "profile_is_quality_score": False,
                        "profile_is_tactical_role_truth": False,
                        "process_participation_is_causal_credit": False,
                        "per90_process_rate_admitted": False,
                        "claim_ceiling": "MATCH_LOCAL_OBSERVED_FUNCTION_PROFILE_ONLY",
                    },
                    {
                        "actor_identity_candidate_id": "a2",
                        "actor_label": "Player Two",
                        "team_identity_candidate_id": "team_a",
                        "team_label": "Alpha",
                        "process_participation_counts": {
                            "POSITIONAL_ATTACK_CANDIDATE": 5,
                        },
                        "shot_ending_process_participation_counts": {},
                        "function_dimensions": {"PROCESS": {}},
                        "profile_has_any_context": True,
                        "profile_is_quality_score": False,
                        "profile_is_tactical_role_truth": False,
                        "process_participation_is_causal_credit": False,
                        "per90_process_rate_admitted": False,
                        "claim_ceiling": "MATCH_LOCAL_OBSERVED_FUNCTION_PROFILE_ONLY",
                    },
                ]
            }
        }
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_aliases_raw": ["Alpha"]},
        ]
    }

    tr = user_output_bundle._human_player_function_cards(rich, identity, "tr", per_team_limit=2)
    en = user_output_bundle._human_player_function_cards(rich, identity, "en", per_team_limit=2)

    joined_tr = " ".join(tr)
    joined_en = " ".join(en)

    assert "Player One" in joined_tr
    assert "yerleşik hücum 12" in joined_tr
    assert "kontra atak 3" in joined_tr
    assert "şut bağlantılı süreç katılımı: yerleşik hücum 2" in joined_tr.lower()
    assert "progressive pass=7" in joined_tr
    assert "yaratılan şans=2" in joined_tr
    assert "top kazanımı=5" in joined_tr
    assert "top kaybı=8" in joined_tr
    assert "Skor-durumu bağlamı:" in joined_tr
    assert "Alpha 1 - Beta 0: 9 görünür süreç katılımı / 2 şut bağlantılı" in joined_tr
    assert "Alpha 0 - Beta 0: 3 görünür süreç katılımı / 0 şut bağlantılı" in joined_tr
    assert "kalite sıralaması" not in joined_tr.lower()
    assert "taktik rol gerçeği" not in joined_tr.lower()
    assert "nedensel katkı" in joined_tr.lower()
    assert "per-90" in joined_tr

    assert "Player One" in joined_en
    assert "positional attack 12" in joined_en
    assert "match-local function context" in joined_en.lower()


def test_player_function_cards_return_empty_without_profiles() -> None:
    assert user_output_bundle._human_player_function_cards({}, {}, "tr") == []


def test_player_mechanism_link_cards_surface_source_bound_actor_variant_context_only() -> None:
    graph = {
        "status": "REVIEW_REQUIRED",
        "cards": [
            {
                "card_index": 1,
                "classification": "MAIN_MECHANISM_CANDIDATE",
                "team_labels": ["Alpha"],
                "period_candidates": ["1"],
                "trace_grammar_tokens": ["LAYER[INTERCEPTION]", "LAYER[PASS]"],
                "resolved_variant_n": 4,
                "positive_visible_variant_n": 3,
                "negative_visible_variant_n": 1,
                "player_context": {"actor_identity_candidate_id": "a1"},
                "safe_finding_context": {
                    "score_state_candidate": {"Alpha": 0, "Beta": 1},
                },
                "source_mechanism_review_ref": "m1",
            },
            {
                "card_index": 2,
                "classification": "LIMITED_COMPARISON",
                "team_labels": ["Beta"],
                "period_candidates": ["2"],
                "trace_grammar_tokens": ["LAYER[DUEL]", "LAYER[PASS]"],
                "resolved_variant_n": 2,
                "positive_visible_variant_n": 1,
                "negative_visible_variant_n": 1,
                "player_context": {"actor_identity_candidate_id": "a2"},
                "safe_finding_context": {
                    "score_state_candidate": {"Alpha": 0, "Beta": 2},
                },
                "source_mechanism_review_ref": "m2",
            },
        ],
    }
    rich = {
        "constructs": {
            "C02": {
                "player_function_profiles": [
                    {"actor_identity_candidate_id": "a1", "actor_label": "Player One"},
                    {"actor_identity_candidate_id": "a2", "actor_label": "Player Two"},
                ]
            }
        }
    }
    identity = {
        "actor_identity_candidates": [
            {
                "actor_identity_candidate_id": "a1",
                "actor_aliases_raw": ["1. Player One (101)"],
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
                "validated_player_identity": True,
            },
            {
                "actor_identity_candidate_id": "a2",
                "actor_aliases_raw": ["2. Player Two (102)"],
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
                "validated_player_identity": True,
            },
        ]
    }

    tr = user_output_bundle._human_player_mechanism_link_cards(graph, rich, identity, "tr")
    en = user_output_bundle._human_player_mechanism_link_cards(graph, rich, identity, "en")

    joined_tr = " ".join(tr)
    joined_en = " ".join(en)
    assert "Player One" in joined_tr
    assert "pas arası → pas" in joined_tr
    assert "4 çözümlenmiş varyant; 3 olumlu / 1 olumsuz" in joined_tr
    assert "Alpha 0 - Beta 1" in joined_tr
    assert "ana mekanizma adayı" in joined_tr.lower()
    assert "Player Two" in joined_tr
    assert "sınırlı karşılaştırma" in joined_tr.lower()
    assert "nedensel katkı" in joined_tr.lower()
    assert "oyuncu niteliği" in joined_tr.lower()

    assert "Player One" in joined_en
    assert "4 resolved variants; 3 positive / 1 negative" in joined_en
    assert "source-bound mechanism link" in joined_en.lower()


def test_player_mechanism_link_cards_return_empty_without_actor_bound_cards() -> None:
    graph = {"status": "REVIEW_REQUIRED", "cards": [{"card_index": 1, "player_context": {}}]}
    assert user_output_bundle._human_player_mechanism_link_cards(graph, {}, {}, "tr") == []


def test_player_mechanism_link_cards_do_not_render_unvalidated_actor_label() -> None:
    graph = {
        "status": "REVIEW_REQUIRED",
        "cards": [{
            "card_index": 1,
            "classification": "MAIN_MECHANISM_CANDIDATE",
            "team_labels": ["Alpha"],
            "period_candidates": ["1"],
            "trace_grammar_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
            "resolved_variant_n": 4,
            "positive_visible_variant_n": 3,
            "negative_visible_variant_n": 1,
            "player_context": {"actor_identity_candidate_id": "unsafe"},
        }],
    }
    rich = {
        "constructs": {
            "C02": {
                "player_function_profiles": [{
                    "actor_identity_candidate_id": "unsafe",
                    "actor_label": "Wrong Plausible Name",
                }]
            }
        }
    }
    identity = {
        "actor_identity_candidates": [{
            "actor_identity_candidate_id": "unsafe",
            "actor_aliases_raw": ["99. Wrong Plausible Name (999999)"],
            "validated_player_identity": False,
        }]
    }

    assert user_output_bundle._human_player_mechanism_link_cards(
        graph, rich, identity, "tr"
    ) == []
