from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from full_spine_runner import run_intelligence_chain
from rich_multiformat_analysis_lane import _construct_c01, _construct_c02, _phase_state_candidates
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

def test_full_spine_runs_sidecars_before_rich_multiformat_lane():
    source = (SRC / "full_spine_runner.py").read_text(encoding="utf-8")
    assert source.index("sidecar_report = run_sidecars(") < source.index("rich_report = run_rich_lane(")
