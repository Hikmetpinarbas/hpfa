from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from full_spine_runner import run_intelligence_chain
from rich_multiformat_analysis_lane import _construct_c01, _construct_c02, _construct_c03, _phase_state_candidates
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import build_composite_packet
from hpfa.modules.core.xlsx_entity_metric_row_projection_lite.src.xlsx_entity_metric_row_projection import _project_sheet


class Cell:
    def __init__(self, value=None, data_type="n", number_format=""):
        self.value = value
        self.data_type = data_type
        self.number_format = number_format


class Sheet:
    def __init__(self, rows):
        self.rows = rows
        self.max_row = len(rows)
        self.max_column = max(len(row) for row in rows)

    def cell(self, row, column):
        try:
            return self.rows[row - 1][column - 1]
        except IndexError:
            return Cell(None)


def _audit():
    return {
        "sheet_name": "Players",
        "sheet_state": "visible",
        "header_row_index": 1,
        "raw_columns": ["Player", "Team", "Progressive passes", "Shots"],
        "column_profiles": [
            {"raw_column": "Player", "normalized_column": "player", "identity_role_candidate": "player"},
            {"raw_column": "Team", "normalized_column": "team", "identity_role_candidate": "team"},
            {"raw_column": "Progressive passes", "normalized_column": "progressive_passes", "identity_role_candidate": None, "percent_header_candidate": False},
            {"raw_column": "Shots", "normalized_column": "shots", "identity_role_candidate": None, "percent_header_candidate": False},
        ],
    }


def test_xlsx_row_projection_preserves_identity_metric_alignment_and_zero():
    formula = Sheet([
        [Cell("Player", "s"), Cell("Team", "s"), Cell("Progressive passes", "s"), Cell("Shots", "s")],
        [Cell("P1", "s"), Cell("T1", "s"), Cell(0), Cell(3)],
    ])
    values = Sheet([
        [Cell("Player", "s"), Cell("Team", "s"), Cell("Progressive passes", "s"), Cell("Shots", "s")],
        [Cell("P1", "s"), Cell("T1", "s"), Cell(0), Cell(3)],
    ])
    result = _project_sheet(
        formula,
        values,
        _audit(),
        {"file_id": "file_generic", "relative_path": "players.xlsx", "source_sha256": "abc", "source_role": "PLAYER_SURFACE_CANDIDATE"},
        "msb_generic",
    )
    assert result["status"] == "PASS"
    row = result["rows"][0]
    assert row["identity_candidates"]["player_raw_candidate"] == "P1"
    assert row["identity_candidates"]["team_raw_candidate"] == "T1"
    assert row["metric_values"]["progressive_passes"]["raw_value"] == 0
    assert row["metric_values"]["progressive_passes"]["value_status"] == "OBSERVED"
    assert row["row_projection_is_canonical_event"] is False


def test_xlsx_row_projection_formula_without_cache_is_review_required():
    formula = Sheet([
        [Cell("Player", "s"), Cell("Team", "s"), Cell("Progressive passes", "s"), Cell("Shots", "s")],
        [Cell("P1", "s"), Cell("T1", "s"), Cell("=1+1", "f"), Cell(3)],
    ])
    values = Sheet([
        [Cell("Player", "s"), Cell("Team", "s"), Cell("Progressive passes", "s"), Cell("Shots", "s")],
        [Cell("P1", "s"), Cell("T1", "s"), Cell(None), Cell(3)],
    ])
    result = _project_sheet(
        formula,
        values,
        _audit(),
        {"file_id": "file_generic", "relative_path": "players.xlsx", "source_sha256": "abc", "source_role": "PLAYER_SURFACE_CANDIDATE"},
        "msb_generic",
    )
    assert result["status"] == "REVIEW_REQUIRED"
    metric = result["rows"][0]["metric_values"]["progressive_passes"]
    assert metric["raw_value"] is None
    assert metric["value_status"] == "NOT_ADMITTED_FORMULA_CACHE_MISSING"


def test_phase_state_candidates_are_explicitly_candidates_not_truth():
    features = {
        "episode_feature_vectors": [{
            "start_second_candidate": 100,
            "end_second_candidate": 160,
            "shot_candidate_count": 2,
            "turnover_candidate_count": 1,
            "recovery_candidate_count": 1,
            "eligible_action_zone_counts": {"FINAL_THIRD": 8},
            "action_family_counts": {"PASS": 20},
        }]
    }
    rows = _phase_state_candidates(features)
    assert rows[0]["labels"] == [
        "TERMINAL_ACTIVITY_CANDIDATE",
        "LOSS_TRANSITION_ACTIVITY_CANDIDATE",
        "RECOVERY_TRANSITION_ACTIVITY_CANDIDATE",
        "ADVANCED_ACCESS_ACTIVITY_CANDIDATE",
        "CIRCULATION_ACTIVITY_CANDIDATE",
    ]
    assert rows[0]["phase_truth"] is False
    assert rows[0]["tactical_truth"] is False


def test_c01_same_scope_aggregate_pair_can_enter_c4_without_fake_action_requirement():
    projection_rows = [{
        "row_projection_id": "xrp_1",
        "source_sha256": "same_provider_sha",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "identity_candidates": {"player_raw_candidate": "P1", "team_raw_candidate": "T1"},
        "metric_values": {
            "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 12, "value_status": "OBSERVED"},
            "shots": {"raw_metric_label": "Shots", "raw_value": 4, "value_status": "OBSERVED"},
        },
    }]
    features = {"episode_feature_vectors": [{"shot_candidate_count": 4}]}
    construct = _construct_c01(projection_rows, features)
    assert construct["status"] == "REVIEW_REQUIRED"
    assert construct["packet_candidate"] is not None
    candidate = construct["packet_candidate"]

    assert candidate["required_lenses"] == ["aggregate"]
    assert candidate["optional_lenses"] == ["action", "outcome", "context", "contradiction"]
    assert candidate["input_features"][0]["lens"] == "action"
    assert all(metric["lens"] == "aggregate" for metric in candidate["input_metrics"])
    assert len({metric["row_projection_id"] for metric in candidate["input_metrics"]}) == 1
    assert candidate["supporting_signals"][0]["relation_type"] == "SUPPORTS"
    assert candidate["supporting_signals"][0]["independent_support_vote"] is False
    assert candidate["supporting_signals"][0]["causal_truth"] is False

    packet = build_composite_packet(candidate)
    assert packet["status"] == "SMOKE_PASS"
    assert packet["packet_family"] == "progression"
    assert packet["independent_support_count"] == 0
    assert packet["nominal_ref_count_is_independent_support_count"] is False
    assert packet["claim_ceiling"] == "composite_candidate_only"

    chain = run_intelligence_chain(packet)
    assert chain["lens"]["lens_requirement_mode"] == "EXPLICIT_ZFGV"
    assert chain["lens"]["required_lenses"] == ["aggregate"]
    assert chain["lens"]["missing_required_lenses"] == []
    assert chain["lens"]["status"] == "SMOKE_PASS"
    assert construct["review_reason"] == "aggregate_pair_scope_aligned_same_provider_support_non_independent"


def test_c01_must_not_pair_progression_from_one_entity_with_terminal_output_from_another():
    projection_rows = [
        {
            "row_projection_id": "xrp_progression_p1",
            "source_sha256": "same_provider_sha",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "P1", "team_raw_candidate": "T1"},
            "metric_values": {
                "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 12, "value_status": "OBSERVED"},
            },
        },
        {
            "row_projection_id": "xrp_terminal_p2",
            "source_sha256": "same_provider_sha",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "P2", "team_raw_candidate": "T1"},
            "metric_values": {
                "shots": {"raw_metric_label": "Shots", "raw_value": 5, "value_status": "OBSERVED"},
            },
        },
    ]
    features = {"episode_feature_vectors": [{"shot_candidate_count": 9}]}
    construct = _construct_c01(projection_rows, features)

    assert construct["packet_candidate"] is None
    assert construct["status"] == "REVIEW_REQUIRED"
    assert construct["review_reason"] == "comparable_aggregate_scope_not_observed"
    assert construct["comparable_scope_pair_count"] == 0


def test_c01_scope_alignment_does_not_promote_same_provider_aggregate_to_independent_support():
    projection_rows = [{
        "row_projection_id": "xrp_2",
        "source_sha256": "same_provider_sha",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "identity_candidates": {"player_raw_candidate": "P2", "team_raw_candidate": "T2"},
        "metric_values": {
            "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 15, "value_status": "OBSERVED"},
            "shots": {"raw_metric_label": "Shots", "raw_value": 5, "value_status": "OBSERVED"},
        },
    }]
    construct = _construct_c01(projection_rows, {"episode_feature_vectors": [{"shot_candidate_count": 5}]})
    packet = build_composite_packet(construct["packet_candidate"])
    chain = run_intelligence_chain(packet)

    assert packet["independent_support_count"] == 0
    assert chain["fusion"]["independent_support_count"] == 0
    assert construct["aggregate_support_is_independent_vote"] is False


def _c02_identity():
    return {
        "module_id": "match_local_identity_candidates_lite_v1",
        "actor_identity_candidates": [
            {
                "actor_identity_candidate_id": "actor_kerem",
                "team_identity_candidate_id": "team_fener",
                "team_normalized_key": "fenerbahce",
                "actor_normalized_key": "kerem_akturkoglu",
                "actor_aliases_raw": ["7. Kerem Akturkoglu (737292)"],
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
            },
            {
                "actor_identity_candidate_id": "actor_guendouzi",
                "team_identity_candidate_id": "team_fener",
                "team_normalized_key": "fenerbahce",
                "actor_normalized_key": "matteo_guendouzi",
                "actor_aliases_raw": ["6. Matteo Guendouzi (562671)"],
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
            },
        ],
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "team_fener",
                "team_normalized_key": "fenerbahce",
                "team_aliases_raw": ["Fenerbahce (27041)"],
                "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            }
        ],
    }


def _c02_xlsx_rows():
    return [
        {
            "row_projection_id": "xrp_kerem",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "Kerem Akturkoglu", "team_raw_candidate": None},
            "metric_values": {
                "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 3, "value_status": "OBSERVED"},
                "xa": {"raw_metric_label": "xA", "raw_value": 0.85, "value_status": "OBSERVED"},
            },
        },
        {
            "row_projection_id": "xrp_guendouzi",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "Matteo Guendouzi", "team_raw_candidate": None},
            "metric_values": {
                "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 11, "value_status": "OBSERVED"},
                "xa": {"raw_metric_label": "xA", "raw_value": 0.37, "value_status": "OBSERVED"},
            },
        },
    ]


def _c02_process_payload():
    rows = []
    # Four positional attacks: two shot-ending. Kerem+Guendouzi together in two, both shot-ending.
    specs = [
        ("10", "20", True, ["actor_kerem", "actor_guendouzi"]),
        ("30", "40", True, ["actor_kerem", "actor_guendouzi"]),
        ("50", "60", False, ["actor_kerem"]),
        ("70", "80", False, ["actor_guendouzi"]),
    ]
    for idx, (start, end, shot, actors) in enumerate(specs, start=1):
        common = {
            "team_identity_candidate_id": "team_fener",
            "process_family_candidate": "POSITIONAL_ATTACKS",
            "period_candidate": "1",
            "start_candidate": start,
            "end_candidate": end,
            "episode_candidate_id": f"ep_{idx}",
            "shot_present_annotation_candidate": shot,
        }
        rows.append({
            **common,
            "process_participation_candidate_id": f"context_{idx}",
            "semantic_role": "CONTEXT_INTERVAL",
            "actor_identity_candidate_id": None,
        })
        for actor in actors:
            rows.append({
                **common,
                "process_participation_candidate_id": f"participant_{idx}_{actor}",
                "semantic_role": "PARTICIPATION_INTERVAL",
                "actor_identity_candidate_id": actor,
            })
    return {
        "module_id": "analyst_episode_process_participation_projection_v1",
        "status": "PASS",
        "process_participation_candidates": rows,
    }


def test_c02_combines_process_participation_outcome_and_xlsx_context():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["process_participation_consumed"] is True
    assert result["xlsx_actor_binding_count"] == 2
    dyad = result["representative_dyad_argument"]
    assert dyad["actor_labels"] == ["Matteo Guendouzi", "Kerem Akturkoglu"] or set(dyad["actor_labels"]) == {"Matteo Guendouzi", "Kerem Akturkoglu"}
    assert dyad["support_n"] == 2
    assert dyad["shot_ending_n"] == 2
    assert dyad["eligible_process_n"] == 4
    assert dyad["baseline_shot_ending_n"] == 2
    assert dyad["conditional_shot_frequency"] == 1.0
    assert dyad["match_local_baseline_shot_frequency"] == 0.5
    assert dyad["match_local_lift"] == 2.0
    assert dyad["xlsx_enriched_actor_count"] == 2
    assert dyad["association_is_causal_player_credit"] is False
    assert dyad["association_is_independent_evidence_vote"] is False


def test_c02_does_not_cross_bind_ambiguous_xlsx_player_rows():
    rows = _c02_xlsx_rows()
    rows.append(dict(rows[0], row_projection_id="xrp_kerem_duplicate"))
    result = _construct_c02(rows, _c02_identity(), _c02_process_payload())

    dyad = result["representative_dyad_argument"]
    assert result["xlsx_actor_binding_count"] == 1
    assert dyad["xlsx_enriched_actor_count"] == 1
    assert any("xlsx_player_row_ambiguous:kerem_akturkoglu" in hit for hit in result["xlsx_binding_review_hits"])


def test_c02_process_association_survives_without_xlsx_enrichment():
    result = _construct_c02([], _c02_identity(), _c02_process_payload())

    dyad = result["representative_dyad_argument"]
    assert result["xlsx_actor_binding_count"] == 0
    assert dyad["support_n"] == 2
    assert dyad["shot_ending_n"] == 2
    assert dyad["xlsx_enriched_actor_count"] == 0
    assert dyad["claim_ceiling"] == "MATCH_LOCAL_PROCESS_OUTCOME_ASSOCIATION_CANDIDATE_ONLY"



def test_c02_real_aggregate_role_can_bind_unique_xlsx_player_row():
    rows = _c02_xlsx_rows()
    for row in rows:
        row["source_role"] = "AGGREGATE_OR_TABULAR_SURFACE_CANDIDATE"
    result = _construct_c02(rows, _c02_identity(), _c02_process_payload())
    assert result["xlsx_actor_binding_count"] == 2
    assert result["representative_dyad_argument"]["xlsx_enriched_actor_count"] == 2


def test_c02_shot_specific_context_refines_same_interval_generic_context():
    payload = _c02_process_payload()
    generic = next(
        row for row in payload["process_participation_candidates"]
        if row["semantic_role"] == "CONTEXT_INTERVAL" and row["shot_present_annotation_candidate"] is True
    )
    generic["shot_present_annotation_candidate"] = False
    refined = dict(generic)
    refined["process_participation_candidate_id"] = generic["process_participation_candidate_id"] + "_shot"
    refined["shot_present_annotation_candidate"] = True
    payload["process_participation_candidates"].append(refined)
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), payload)
    profile = next(row for row in result["process_family_profiles"] if row["process_family_candidate"] == "POSITIONAL_ATTACKS")
    assert profile["shot_ending_n"] == 2
    assert result["representative_dyad_argument"]["shot_ending_n"] == 2

def test_c02_small_n_contract_does_not_coerce_not_target_annotation_into_resolved_non_shot():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    dyad = result["representative_dyad_argument"]
    contract = dyad["small_n_association_contract"]
    assert contract["present_target_annotated_n"] == 2
    assert contract["present_not_target_annotated_n"] == 0
    assert contract["absent_target_annotated_n"] == 0
    assert contract["absent_not_target_annotated_n"] == 2
    assert contract["present_non_shot_n"] is None
    assert contract["absent_non_shot_n"] is None
    assert contract["outcome_resolution_state"] == "OUTCOME_RESOLUTION_CAPABILITY_NOT_AVAILABLE"
    assert contract["exchangeability_admitted"] is False
    assert contract["dependency_state"] == "UNRESOLVED_MATCH_LOCAL_PROCESS_DEPENDENCE"
    assert contract["fisher_exact_state"] == "NOT_EVALUATED_OUTCOME_RESOLUTION_UNAVAILABLE"
    assert contract["permutation_state"] == "NOT_EVALUATED_OUTCOME_RESOLUTION_AND_EXCHANGEABILITY_UNAVAILABLE"
    assert contract["p_value_is_football_importance"] is False


def test_c02_epistemic_review_contract_preserves_claim_ceiling_and_exposes_review_actions():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    dyad = result["representative_dyad_argument"]
    review = dyad["epistemic_review_contract"]

    assert review["contract_version"] == "C02_ASSOCIATION_EPISTEMIC_REVIEW_V1"
    assert review["creates_new_evidence"] is False
    assert review["can_authorize_emit"] is False
    assert review["can_strengthen_claim_ceiling"] is False
    assert review["claim_ceiling"] == dyad["claim_ceiling"]
    assert review["review_target_refs"] == dyad["shot_process_refs"]
    assert review["review_target_without_association_refs"] == dyad["counterexample_shot_without_association_refs"]
    assert review["review_not_target_annotated_refs"] == dyad["counterexample_involved_without_shot_refs"]
    assert "admitted current surfaces or other admissible evidence" in review["analyst_action"]
    assert "match_local_process_dependence_may_reduce_effective_support" in review["alternative_explanations"]
    assert "dependency_resolution_collapses_support_into_shared_lineage" in review["falsifier_conditions"]
    assert result["epistemic_review_contract_creates_new_evidence"] is False
    assert result["epistemic_review_contract_can_authorize_emit"] is False


def test_c02_opportunity_normalized_evidence_anatomy_freezes_denominator_and_preserves_episode_spread():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    dyad = result["representative_dyad_argument"]
    anatomy = dyad["opportunity_normalized_evidence_anatomy"]
    assert anatomy["comparison_design_ref"] == "C02_PROCESS_FAMILY_OUTCOME_BLIND_ELIGIBILITY_V1"
    assert anatomy["denominator_state"] == "FAMILY_ELIGIBLE_PROCESS_N_FROZEN_BEFORE_OUTCOME_READ"
    assert anatomy["family_eligible_process_n"] == 4
    assert anatomy["association_involvement_n"] == 2
    assert anatomy["resolved_target_n"] == 2
    assert anatomy["resolved_non_target_n"] is None
    assert anatomy["unresolved_outcome_n"] is None
    assert anatomy["identification_state"] == "OUTCOME_RESOLUTION_CAPABILITY_NOT_AVAILABLE"
    assert anatomy["bound_transfer_state"] == "BOUND_NOT_TRANSFERABLE_TO_THIS_PROFILE"
    assert anatomy["supporting_episode_n"] == 2
    assert anatomy["episode_spread_is_independence_proof"] is False
    assert anatomy["lineage_group_n_is_effective_sample_size"] is False
    assert anatomy["counterexample_involved_without_target_refs"] == []


def test_full_spine_runs_sidecars_before_rich_multiformat_lane():
    source = (SRC / "full_spine_runner.py").read_text(encoding="utf-8")
    assert source.index("sidecar_report = run_sidecars(") < source.index("rich_report = run_rich_lane(")


def test_c03_builds_partial_order_process_development_and_anchor_path_without_tracking_claims():
    process = {
        "process_participation_candidates": [{
            "process_participation_candidate_id": "context_1",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": "10",
            "end_candidate": "30",
            "shot_present_annotation_candidate": True,
        }]
    }
    occurrences = {
        "occurrence_state_transition_projections": [
            {
                "action_occurrence_candidate_id": "occ_1",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["12"],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_1"],
                "transition_class_candidates": ["VISIBLE_CONTINUATION_CANDIDATE"],
                "provider_outcome_candidates": ["SUCCESS"],
                "supporting_spatial_transition_candidate_ids": ["sp_1"],
            },
            {
                "action_occurrence_candidate_id": "occ_2",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["20"],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_2"],
                "transition_class_candidates": ["VISIBLE_CONTINUATION_CANDIDATE"],
                "provider_outcome_candidates": ["SUCCESS"],
                "supporting_spatial_transition_candidate_ids": ["sp_2"],
            },
            {
                "action_occurrence_candidate_id": "occ_3",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["20"],
                "action_family_candidates": ["CARRY"],
                "actor_identity_candidate_ids": ["actor_2"],
                "transition_class_candidates": ["VISIBLE_CONTINUATION_CANDIDATE"],
                "provider_outcome_candidates": [],
                "supporting_spatial_transition_candidate_ids": ["sp_2"],
            },
        ]
    }
    spatial = {
        "spatial_transition_candidates": [
            {
                "spatial_transition_candidate_id": "sp_1",
                "occurrence_annotation_anchor_location_admitted": True,
                "provider_coordinate_anchor_x_candidate": 20.0,
                "provider_coordinate_anchor_y_candidate": 30.0,
                "provider_zone_candidates": ["MIDDLE_THIRD"],
            },
            {
                "spatial_transition_candidate_id": "sp_2",
                "occurrence_annotation_anchor_location_admitted": True,
                "provider_coordinate_anchor_x_candidate": 50.0,
                "provider_coordinate_anchor_y_candidate": 40.0,
                "provider_zone_candidates": ["FINAL_THIRD"],
            },
        ]
    }
    result = _construct_c03(process, occurrences, spatial)
    signature = result["signatures"][0]
    assert signature["process_interval_duration_candidate"] == 20.0
    assert signature["process_duration_basis"] == "PROVIDER_REVIEWED_PROCESS_CONTEXT_INTERVAL"
    assert signature["process_interval_duration_is_generic_action_duration"] is False
    assert signature["temporal_layer_n"] == 2
    assert signature["layers"][1]["occurrence_ids"] == ["occ_2", "occ_3"]
    assert signature["layers"][1]["action_family_candidates"] == ["CARRY", "PASS"]
    assert signature["layers"][1]["same_timestamp_internal_ordering_allowed"] is False
    assert signature["annotation_anchor_path_coverage_state"] == "COMPLETE_CONSECUTIVE_SINGLE_ANCHOR"
    assert signature["annotation_anchor_segment_n"] == 1
    assert round(signature["annotation_anchor_segment_distance_sum_provider_units_candidate"], 6) == round((1000) ** 0.5, 6)
    assert signature["annotation_anchor_path_is_physical_trajectory"] is False
    assert signature["annotation_anchor_distance_is_physical_travel_distance"] is False
    assert signature["tracking_truth"] is False
    assert result["physical_speed_claim_allowed"] is False


def test_c03_filters_occurrences_to_exact_team_period_and_process_interval():
    process = {
        "process_participation_candidates": [{
            "process_participation_candidate_id": "context_1",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "COUNTERATTACK_CANDIDATE",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": "10",
            "end_candidate": "20",
        }]
    }
    occurrences = {
        "occurrence_state_transition_projections": [
            {"action_occurrence_candidate_id": "inside", "team_identity_candidate_ids": ["team_a"], "period_candidates": ["1"], "start_candidates": ["15"], "action_family_candidates": ["PASS"], "supporting_spatial_transition_candidate_ids": []},
            {"action_occurrence_candidate_id": "outside_time", "team_identity_candidate_ids": ["team_a"], "period_candidates": ["1"], "start_candidates": ["25"], "action_family_candidates": ["SHOT"], "supporting_spatial_transition_candidate_ids": []},
            {"action_occurrence_candidate_id": "other_team", "team_identity_candidate_ids": ["team_b"], "period_candidates": ["1"], "start_candidates": ["15"], "action_family_candidates": ["SHOT"], "supporting_spatial_transition_candidate_ids": []},
            {"action_occurrence_candidate_id": "other_period", "team_identity_candidate_ids": ["team_a"], "period_candidates": ["2"], "start_candidates": ["15"], "action_family_candidates": ["SHOT"], "supporting_spatial_transition_candidate_ids": []},
        ]
    }
    result = _construct_c03(process, occurrences, {"spatial_transition_candidates": []})
    signature = result["signatures"][0]
    assert signature["visible_occurrence_n"] == 1
    assert signature["layers"][0]["occurrence_ids"] == ["inside"]
    assert signature["source_row_order_is_temporal_truth"] is False
    assert signature["annotation_anchor_path_coverage_state"] == "PARTIAL_OR_AMBIGUOUS"
