from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from hpfa.modules.core.multiformat_file_inventory_lite.src import multiformat_file_inventory as inventory
from hpfa.modules.core.xlsx_surface_reader_lite.src.xlsx_surface_reader import native_reader as xlsx
from hpfa.modules.core.xlsx_entity_metric_row_projection_lite.src.xlsx_entity_metric_row_projection import build_projection
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.supported_sequence_grammar_alignment_projection import build_supported_sequence_grammar_alignment
from hpfa.modules.core.active_match_spine_runner.src.shared_surface_snapshot_contract import surface_snapshot_id

MODULE_ID = "rich_multiformat_analysis_lattice_v1"
OUTPUT_JSON = "rich_multiformat_analysis_lattice_v1.json"
OUTPUT_TXT = "rich_multiformat_analysis_lattice_v1.txt"
XLSX_AUDIT_JSON = "xlsx_surface_audit_lite_v1.json"
XLSX_AUDIT_TXT = "xlsx_surface_audit_lite_v1.txt"
XLSX_AUDIT_ANALYST = "xlsx_surface_analyst_audit_lite_v1.txt"
XLSX_PROJECTION_JSON = "xlsx_entity_metric_row_projection_lite_v1.json"
XLSX_PROJECTION_TXT = "xlsx_entity_metric_row_projection_lite_v1.txt"
IDENTITY_JSON = "match_local_identity_candidates_lite_v1.json"
PROCESS_PARTICIPATION_JSON = "analyst_episode_process_participation_projection_v1.json"
OCCURRENCE_STATE_TRANSITION_JSON = "occurrence_state_transition_projection_v1.json"
SPATIAL_TRANSITION_JSON = "spatial_transition_candidate_lite_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _snapshot(root: Path) -> str:
    """Use the canonical shared ACTIVE_MATCH content snapshot contract."""
    return surface_snapshot_id(root)


def _flatten_projection(projection: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for file_row in projection.get("files", []) or []
        for sheet in file_row.get("sheets", []) or []
        for row in sheet.get("rows", []) or []
        if isinstance(row, dict)
    ]


_GOALKEEPER_SCHEMA_SIGNALS = frozenset({
    "shots_faced",
    "shots_on_target_faced",
    "shots_saved",
    "goals_conceded",
    "sweeping_actions",
    "penalties_saved",
})


def _xlsx_entity_role_candidate(row: dict[str, Any]) -> str:
    role = str(row.get("source_role") or "").upper()
    if "GOALKEEPER" in role:
        return "GOALKEEPER"
    if "TEAM" in role:
        return "TEAM"
    metric_keys = {
        str(key).strip().casefold()
        for key in (row.get("metric_values") or {})
        if str(key).strip()
    }
    if metric_keys.intersection(_GOALKEEPER_SCHEMA_SIGNALS):
        return "GOALKEEPER"
    identity = row.get("identity_candidates") or {}
    if identity.get("player_raw_candidate") not in (None, ""):
        return "PLAYER"
    if identity.get("team_raw_candidate") not in (None, ""):
        return "TEAM"
    return "UNRESOLVED"


def _entity_views(rows: list[dict[str, Any]]) -> dict[str, Any]:
    players: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    goalkeepers: list[dict[str, Any]] = []
    metric_label_counts: Counter[str] = Counter()
    observed_metric_cell_count = 0
    for row in rows:
        identity = row.get("identity_candidates") or {}
        observed_metrics = {
            key: value
            for key, value in (row.get("metric_values") or {}).items()
            if isinstance(value, dict) and value.get("value_status") == "OBSERVED"
        }
        for key in observed_metrics:
            metric_label_counts[str(key)] += 1
        observed_metric_cell_count += len(observed_metrics)
        compact = {
            "row_projection_id": row.get("row_projection_id"),
            "source_role": row.get("source_role"),
            "player_raw_candidate": identity.get("player_raw_candidate"),
            "team_raw_candidate": identity.get("team_raw_candidate"),
            "position_raw_candidate": identity.get("position_raw_candidate"),
            "minutes_raw_candidate": identity.get("minutes_raw_candidate"),
            "metric_values": observed_metrics,
            "validated_identity": False,
            "metric_truth": False,
        }
        entity_role = _xlsx_entity_role_candidate(row)
        compact["entity_role_candidate"] = entity_role
        if entity_role == "GOALKEEPER":
            goalkeepers.append(compact)
        elif entity_role == "PLAYER":
            players.append(compact)
        elif entity_role == "TEAM":
            teams.append(compact)
    return {
        "player_view_candidates": players,
        "team_view_candidates": teams,
        "goalkeeper_view_candidates": goalkeepers,
        "observed_metric_cell_count": observed_metric_cell_count,
        "metric_label_observation_counts": dict(metric_label_counts.most_common()),
        "player_identity_truth": False,
        "team_identity_truth": False,
    }


def _primitive_metrics(features: dict[str, Any], entity_views: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    total = features.get("total_eligible_action_candidate_count")
    if total is not None:
        values.append({
            "metric_id": "primitive_visible_action_candidate_volume",
            "value": total,
            "unit": "candidate_count",
            "construct": "visible_action_surface",
            "source_surface": "episode_feature_vector_lite_v1",
            "denominator": "eligible_action_candidate_population",
            "dependency_group": "episode_feature_action_population",
            "provenance_root": "episode_feature_vector_lite_v1",
            "independent_support_vote": False,
            "claim_ceiling": "VISIBLE_CANDIDATE_VOLUME_ONLY",
        })
    for family, value in sorted((features.get("eligible_action_family_candidate_counts") or {}).items()):
        values.append({
            "metric_id": f"primitive_action_family_{str(family).casefold()}",
            "value": value,
            "unit": "candidate_count",
            "construct": "action_family_volume",
            "source_surface": "episode_feature_vector_lite_v1",
            "denominator": "eligible_action_candidate_population",
            "dependency_group": "episode_feature_action_population",
            "provenance_root": "episode_feature_vector_lite_v1",
            "independent_support_vote": False,
            "claim_ceiling": "ACTION_FAMILY_CANDIDATE_ONLY",
        })
    values.append({
        "metric_id": "primitive_xlsx_observed_metric_cell_volume",
        "value": entity_views.get("observed_metric_cell_count", 0),
        "unit": "observed_metric_cell_count",
        "construct": "aggregate_surface_coverage",
        "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
        "denominator": "visible_xlsx_projected_rows",
        "dependency_group": "same_provider_aggregate_surface",
        "provenance_root": "xlsx_entity_metric_row_projection_lite_v1",
        "independent_support_vote": False,
        "claim_ceiling": "AGGREGATE_CELL_SURFACE_ONLY",
    })
    return values


CANONICAL_SIX_PHASES = (
    "ESTABLISHED_ATTACK",
    "ATTACKING_TRANSITION",
    "ATTACKING_SET_PIECE",
    "ESTABLISHED_DEFENCE",
    "DEFENSIVE_TRANSITION",
    "DEFENSIVE_SET_PIECE",
)


def _football_ontology_contract() -> dict[str, Any]:
    return {
        "canonical_six_phases": list(CANONICAL_SIX_PHASES),
        "phase_is_evaluation": False,
        "phase_is_outcome": False,
        "success_failure_is_phase": False,
        "efficiency_inefficiency_is_phase": False,
        "set_piece_is_open_play_subtype": False,
        "attacking_set_piece_reciprocal_phase": "DEFENSIVE_SET_PIECE",
        "defensive_set_piece_reciprocal_phase": "ATTACKING_SET_PIECE",
        "observation_dimensions": [
            "ACTOR", "ACTION", "TIME", "SPACE", "ZONE", "ROLE", "RELATION",
            "TEAM", "OPPONENT", "PROCESS", "PHASE", "CONSEQUENCE", "CONTEXT",
        ],
        "scale_axis": [
            "ACTION", "INDIVIDUAL", "DYAD_TRIAD", "FUNCTIONAL_GROUP",
            "TEAM", "TWO_TEAM_INTERACTION", "MATCH",
        ],
        "evaluation_dimensions": [
            "OUTCOME", "SUCCESS_FAILURE", "EFFICIENCY_INEFFICIENCY",
            "RECURRENCE", "VARIATION", "DEVIATION",
        ],
        "restart_phase_contract": {
            "restart_types": [
                "CORNER_KICK", "FREE_KICK", "THROW_IN", "PENALTY_KICK",
                "GOAL_KICK", "KICK_OFF", "OTHER_RESTART",
            ],
            "attacking_phase": "ATTACKING_SET_PIECE",
            "defending_phase": "DEFENSIVE_SET_PIECE",
            "restart_event_is_not_phase": True,
            "restart_type_is_not_routine_truth": True,
            "delivery_is_not_full_set_piece_process": True,
            "set_piece_process_requires_visible_continuation": True,
            "second_action_requires_observed_followup": True,
            "routine_design_requires_tracking_or_video": True,
            "marking_scheme_requires_tracking_or_video": True,
            "off_ball_movement_requires_tracking_or_video": True,
        },
        "role_contract": {
            "provider_position_is_not_functional_role_truth": True,
            "functional_role_requires_observed_task_distribution": True,
            "functional_role_is_match_contextual": True,
            "role_label_is_not_coach_intention": True,
            "event_only_role_evidence_dimensions": [
                "ACTION_FAMILY_DISTRIBUTION",
                "ZONE_DISTRIBUTION",
                "PROCESS_PARTICIPATION",
                "RELATION_PARTICIPATION",
                "TEAM_SHARE_CONTEXT",
            ],
            "single_match_role_output": "FUNCTIONAL_ROLE_CANDIDATE_ONLY",
            "season_role_classifier_truth": False,
        },
        "opponent_interaction_contract": {
            "same_time_counterpart_is_not_reaction_truth": True,
            "reaction_requires_admitted_order_or_visible_consequence_chain": True,
            "team_a_action_should_be_read_against_team_b_response_when_observable": True,
            "reciprocal_phase_pairing_required": True,
            "interaction_chain": [
                "TEAM_A_ACTION",
                "TEAM_B_VISIBLE_RESPONSE",
                "TEAM_A_COUNTER_RESPONSE_IF_OBSERVED",
                "VISIBLE_CONSEQUENCE",
            ],
            "no_visible_response_is_not_no_response_truth": True,
        },
        "external_donor_adaptation_contract": {
            "provider_normalization": {
                "reference_projects": ["PySport/kloppy", "ML-KULeuven/socceraction"],
                "provider_schema_is_not_canonical_football_truth": True,
                "normalize_at_boundary_not_inside_constructs": True,
                "coordinate_system_requires_explicit_admission": True,
                "orientation_requires_explicit_admission": True,
                "provider_event_type_requires_semantic_mapping": True,
            },
            "action_state_consequence": {
                "reference_projects": ["ML-KULeuven/socceraction", "statsbomb/open-data"],
                "action_value_model_is_not_observation_truth": True,
                "model_output_requires_model_source_version": True,
                "state_transition_requires_admitted_action_identity": True,
                "visible_consequence_preferred_over_inferred_intention": True,
            },
            "tracking_boundary": {
                "reference_projects": ["metrica-sports/sample-data", "SkillCorner/opendata", "Friends-of-Tracking-Data-FoTD/LaurieOnTracking"],
                "tracking_is_optional_not_required_dependency": True,
                "event_coordinate_is_not_tracking": True,
                "pitch_control_requires_tracking_or_equivalent_spatiotemporal_observation": True,
                "velocity_acceleration_requires_tracking_or_equivalent_spatiotemporal_observation": True,
                "team_shape_compactness_requires_tracking_or_video": True,
            },
            "adoption_policy": "ADAPT_IDEA_NOT_CODE_UNLESS_LICENSE_AND_PRODUCT_GAP_ARE_EXPLICITLY_ADMITTED",
        },
        "metric_argument_contract": {
            "opaque_single_score_allowed": False,
            "construct_axes_remain_separate": True,
            "eligible_denominator_required_for_rate_claim": True,
            "aggregate_decomposition_is_not_independent_support": True,
            "micro_macro_reconciliation_requires_estimand_alignment": True,
            "progression_argument_axes": [
                "VOLUME",
                "EXECUTION",
                "SPATIAL_ROUTE",
                "SEQUENCE_CONTINUATION",
                "VISIBLE_CONSEQUENCE",
                "REPEATABILITY",
                "OPPONENT_RESPONSE",
                "FAILURE_COST",
            ],
            "context_ratios_are_not_conditional_conversion_without_sequence_identity": True,
        },
        "truth_locks": [
            "ACTIVITY_LABEL_IS_NOT_PHASE_TRUTH",
            "PHASE_IS_NOT_SUCCESS_FAILURE",
            "PHASE_IS_NOT_EFFICIENCY",
            "POSITION_IS_NOT_OBSERVED_FUNCTIONAL_ROLE",
            "SAME_TIMESTAMP_IS_NOT_REACTION_ORDER",
            "COORDINATE_IS_NOT_TRACKING",
        ],
        "claim_ceiling": "ONTOLOGY_CONTRACT_ONLY_PHASE_REQUIRES_SEPARATE_ADMISSION",
    }


def _phase_state_candidates(features: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    cards = features.get("episode_feature_vectors") or []
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            continue
        labels: list[str] = []
        shots = int(card.get("shot_candidate_count") or 0)
        turnovers = int(card.get("turnover_candidate_count") or 0)
        recoveries = int(card.get("recovery_candidate_count") or 0)
        zones = card.get("eligible_action_zone_counts") or {}
        families = card.get("action_family_counts") or {}
        final_third = int(zones.get("FINAL_THIRD") or zones.get("final_third") or 0)
        passes = int(families.get("PASS") or families.get("pass") or 0)
        if shots:
            labels.append("TERMINAL_ACTIVITY_CANDIDATE")
        if turnovers:
            labels.append("LOSS_TRANSITION_ACTIVITY_CANDIDATE")
        if recoveries:
            labels.append("RECOVERY_TRANSITION_ACTIVITY_CANDIDATE")
        if final_third:
            labels.append("ADVANCED_ACCESS_ACTIVITY_CANDIDATE")
        if passes:
            labels.append("CIRCULATION_ACTIVITY_CANDIDATE")
        if not labels:
            labels.append("UNRESOLVED_ACTIVITY_STATE")
        result.append({
            "phase_state_candidate_id": f"psc_{index:04d}",
            "episode_index": index,
            "start_second_candidate": card.get("start_second_candidate"),
            "end_second_candidate": card.get("end_second_candidate"),
            "labels": labels,
            "support": {
                "shot_candidate_count": shots,
                "turnover_candidate_count": turnovers,
                "recovery_candidate_count": recoveries,
                "final_third_action_candidate_count": final_third,
                "pass_candidate_count": passes,
            },
            "activity_labels_are_phase_labels": False,
            "phase_admission_status": "NOT_EVALUATED",
            "phase_truth": False,
            "possession_truth": False,
            "tactical_truth": False,
            "claim_ceiling": "EPISODE_ACTIVITY_STATE_CANDIDATE_ONLY",
        })
    return result


def _metric_refs(rows: list[dict[str, Any]], terms: tuple[str, ...], limit: int = 20) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for row in rows:
        identity = row.get("identity_candidates") or {}
        row_projection_id = str(row.get("row_projection_id") or "").strip()
        for key, metric in (row.get("metric_values") or {}).items():
            if not isinstance(metric, dict) or metric.get("value_status") != "OBSERVED":
                continue
            key_text = str(key).casefold()
            raw_label = str(metric.get("raw_metric_label") or "").casefold()
            if not any(term in key_text or term in raw_label for term in terms):
                continue
            player_candidate = identity.get("player_raw_candidate")
            team_candidate = identity.get("team_raw_candidate")
            refs.append({
                "metric_id": f"{row_projection_id}:{key}",
                "row_projection_id": row_projection_id,
                "source_role": row.get("source_role"),
                "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
                "raw_metric_label": metric.get("raw_metric_label"),
                "raw_value": metric.get("raw_value"),
                "player_candidate": player_candidate,
                "team_candidate": team_candidate,
                "entity_candidate": player_candidate or team_candidate,
                "provenance_root": str(row.get("source_sha256") or "xlsx_unknown"),
                "dependency_group": "same_provider_xlsx_aggregate",
                "independence_group": None,
                "independent_support_vote": False,
                "metric_truth": False,
                "lens": "aggregate",
            })
            if len(refs) >= limit:
                return refs
    return refs


def _comparable_aggregate_pairs(
    progression: list[dict[str, Any]],
    terminal: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    terminal_by_row: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ref in terminal:
        row_id = str(ref.get("row_projection_id") or "").strip()
        if row_id:
            terminal_by_row[row_id].append(ref)

    pairs: list[dict[str, Any]] = []
    for progression_ref in progression:
        row_id = str(progression_ref.get("row_projection_id") or "").strip()
        if not row_id:
            continue
        for terminal_ref in terminal_by_row.get(row_id, []):
            if progression_ref.get("metric_id") == terminal_ref.get("metric_id"):
                continue
            pairs.append({
                "row_projection_id": row_id,
                "source_role": progression_ref.get("source_role"),
                "player_candidate": progression_ref.get("player_candidate"),
                "team_candidate": progression_ref.get("team_candidate"),
                "progression_metric": progression_ref,
                "terminal_metric": terminal_ref,
                "same_row_scope": True,
                "same_provider_surface": True,
                "independent_support_vote": False,
            })
    return pairs


def _construct_c01(rows: list[dict[str, Any]], features: dict[str, Any]) -> dict[str, Any]:
    progression = _metric_refs(rows, ("progressive", "progression", "final_third", "final third", "penalty_area", "penalty area", "box"))
    terminal = _metric_refs(rows, ("shot", "xg", "goal", "chance"))
    comparable_pairs = _comparable_aggregate_pairs(progression, terminal)
    shot_total = sum(int(card.get("shot_candidate_count") or 0) for card in (features.get("episode_feature_vectors") or []) if isinstance(card, dict))
    occurrence_ref = {
        "feature_id": "c01_visible_terminal_episode_surface",
        "source_surface": "episode_feature_vector_lite_v1",
        "shot_candidate_count": shot_total,
        "provenance_root": "episode_feature_vector_lite_v1",
        "dependency_group": "episode_feature_action_population",
        "independence_group": None,
        "independent_support_vote": False,
        "lens": "action",
    }

    packet_candidate = None
    if comparable_pairs:
        pair = comparable_pairs[0]
        metrics = [pair["progression_metric"], pair["terminal_metric"]]
        relation_signal = {
            "signal_id": "c01_same_scope_progression_terminal_alignment_candidate",
            "source_surface": "HPFA_DERIVED_FROM_SAME_ROW_AGGREGATE",
            "evidence_derivation_role": "DERIVED_FROM_COMPARABLE_AGGREGATE_PAIR_CANDIDATE",
            "evidence_role": "same_scope_progression_terminal_alignment_candidate",
            "relation_type": "SUPPORTS",
            "source_refs": [str(metric.get("metric_id")) for metric in metrics],
            "row_projection_id": pair.get("row_projection_id"),
            "player_candidate": pair.get("player_candidate"),
            "team_candidate": pair.get("team_candidate"),
            "provenance_root": str(pair["progression_metric"].get("provenance_root") or "c01_same_row_aggregate"),
            "dependency_group": "c01_same_row_aggregate_relation",
            "independence_group": None,
            "independent_support_vote": False,
            "causal_truth": False,
            "tactical_truth_candidate_admitted": False,
        }
        packet_candidate = {
            "source_construct_id": "C01_PROGRESSION_VOLUME_VS_TERMINAL_CONVERSION",
            "packet_family": "progression",
            "input_features": [occurrence_ref],
            "input_windows": [],
            "input_sequences": [],
            "input_metrics": metrics,
            "supporting_signals": [relation_signal],
            "contradicting_signals": [],
            "required_lenses": ["aggregate"],
            "optional_lenses": ["action", "outcome", "context", "contradiction"],
            "claim_ceiling": "composite_candidate_only",
            "blocked_language_families": ["tactical_truth", "dominance_truth", "control_truth"],
        }

    if not progression:
        reason = "aggregate_progression_surface_not_observed"
    elif not terminal:
        reason = "terminal_surface_not_observed"
    elif not comparable_pairs:
        reason = "comparable_aggregate_scope_not_observed"
    else:
        reason = "aggregate_pair_scope_aligned_same_provider_support_non_independent"

    return {
        "construct_id": "C01_PROGRESSION_VOLUME_VS_TERMINAL_CONVERSION",
        "status": "REVIEW_REQUIRED",
        "question": "Visible progression/access production and terminal production appear together on comparable admitted aggregate scope?",
        "progression_aggregate_ref_count": len(progression),
        "terminal_aggregate_ref_count": len(terminal),
        "comparable_scope_pair_count": len(comparable_pairs),
        "visible_shot_candidate_count": shot_total,
        "progression_metric_refs": progression,
        "terminal_metric_refs": terminal,
        "comparable_scope_pairs": comparable_pairs,
        "packet_candidate": packet_candidate,
        "review_reason": reason,
        "aggregate_support_is_independent_vote": False,
        "action_surface_is_optional_context": True,
        "cross_entity_aggregate_pairing_allowed": False,
        "construct_truth": False,
        "claim_ceiling": "CONSTRUCT_EVIDENCE_CANDIDATE_ONLY",
    }



def _normalize_identity_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", " ".join(str(value or "").split()).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text)).strip("_")


def _display_subject(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    text = re.sub(r"^\d+\.\s+", "", text)
    text = re.sub(r"\s+\(\d+\)$", "", text)
    return text or "UNKNOWN"


def _actor_xlsx_bindings(
    rows: list[dict[str, Any]],
    identity_payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Bind match-local actor candidates to one unique XLSX player row by normalized name."""
    reviews: list[str] = []
    xlsx_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        identity = row.get("identity_candidates") or {}
        raw_player = identity.get("player_raw_candidate")
        if raw_player in (None, ""):
            continue
        key = _normalize_identity_text(raw_player)
        if key:
            xlsx_by_name[key].append(row)

    actors = [
        row for row in (identity_payload.get("actor_identity_candidates") or [])
        if isinstance(row, dict)
        and str(row.get("decision_state") or "") == "ACTOR_IDENTITY_CANDIDATE_BOUND"
        and row.get("actor_identity_candidate_id")
        and row.get("actor_normalized_key")
    ]
    actor_key_counts = Counter(str(row.get("actor_normalized_key") or "") for row in actors)
    teams = {
        str(row.get("team_identity_candidate_id") or ""): row
        for row in (identity_payload.get("team_identity_candidates") or [])
        if isinstance(row, dict) and row.get("team_identity_candidate_id")
    }
    bindings: dict[str, dict[str, Any]] = {}
    for actor in actors:
        actor_id = str(actor.get("actor_identity_candidate_id"))
        actor_key = str(actor.get("actor_normalized_key"))
        if actor_key_counts[actor_key] != 1:
            reviews.append(f"xlsx_actor_name_ambiguous_in_match:{actor_key}")
            continue
        xlsx_rows = xlsx_by_name.get(actor_key, [])
        if len(xlsx_rows) != 1:
            if len(xlsx_rows) > 1:
                reviews.append(f"xlsx_player_row_ambiguous:{actor_key}")
            continue
        xlsx_row = xlsx_rows[0]
        xlsx_team = _normalize_identity_text((xlsx_row.get("identity_candidates") or {}).get("team_raw_candidate"))
        actor_team_key = str(actor.get("team_normalized_key") or "")
        if xlsx_team and actor_team_key and xlsx_team != actor_team_key:
            reviews.append(f"xlsx_actor_team_mismatch:{actor_key}")
            continue
        team = teams.get(str(actor.get("team_identity_candidate_id") or "")) or {}
        aliases = list(actor.get("actor_aliases_raw") or [])
        team_aliases = list(team.get("team_aliases_raw") or [])
        bindings[actor_id] = {
            "actor_identity_candidate_id": actor_id,
            "actor_label": _display_subject(aliases[0] if aliases else actor_key),
            "team_identity_candidate_id": actor.get("team_identity_candidate_id"),
            "team_label": _display_subject(team_aliases[0] if team_aliases else actor_team_key),
            "xlsx_row_projection_id": xlsx_row.get("row_projection_id"),
            "xlsx_row": xlsx_row,
            "binding_state": "MATCH_LOCAL_UNIQUE_NAME_XLSX_ROW_CANDIDATE_BOUND",
            "validated_global_player_identity": False,
            "xlsx_row_is_action_identity": False,
        }
    return bindings, sorted(set(reviews))


def _selected_xlsx_metric_context(row: dict[str, Any]) -> list[dict[str, Any]]:
    terms = (
        "progressive pass",
        "final third entr",
        "passes into the penalty box",
        "open passes received in the final third",
        "actions in opponent",
        "chances created",
        "xa",
        "xg",
    )
    result: list[dict[str, Any]] = []
    for key, metric in (row.get("metric_values") or {}).items():
        if not isinstance(metric, dict) or metric.get("value_status") != "OBSERVED":
            continue
        haystack = f"{key} {metric.get('raw_metric_label') or ''}".casefold().replace("_", " ")
        if not any(term in haystack for term in terms):
            continue
        result.append({
            "metric_key": str(key),
            "raw_metric_label": metric.get("raw_metric_label"),
            "raw_value": metric.get("raw_value"),
            "row_projection_id": row.get("row_projection_id"),
            "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
            "independent_support_vote": False,
            "metric_truth": False,
        })
        if len(result) >= 8:
            break
    return result


def _process_interval_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("team_identity_candidate_id") or ""),
        str(row.get("process_family_candidate") or ""),
        str(row.get("period_candidate") or ""),
        str(row.get("start_candidate") or ""),
        str(row.get("end_candidate") or ""),
    )


def _association_epistemic_review_contract(
    *,
    shot_rows: list[dict[str, Any]],
    not_target_rows: list[dict[str, Any]],
    shot_without: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project review instructions from admitted association evidence without creating evidence."""
    return {
        "contract_version": "C02_ASSOCIATION_EPISTEMIC_REVIEW_V1",
        "creates_new_evidence": False,
        "can_authorize_emit": False,
        "can_strengthen_claim_ceiling": False,
        "alternative_explanations": [
            "shared_process_participation_or_role_exposure",
            "score_state_or_opponent_mode_not_resolved_here",
            "provider_annotation_coverage_or_semantic_resolution_may_shift_target_counts",
            "match_local_process_dependence_may_reduce_effective_support",
        ],
        "falsifier_conditions": [
            "target_outcome_semantic_withdrawn_or_reclassified",
            "actor_or_dyad_identity_binding_invalidated",
            "outcome_resolution_materially_changes_target_or_non_target_counts",
            "dependency_resolution_collapses_support_into_shared_lineage",
        ],
        "withdrawal_conditions": [
            "comparison_eligibility_is_no_longer_outcome_blind",
            "supporting_process_reference_is_invalidated",
            "target_outcome_semantic_is_not_admitted",
            "association_identity_binding_is_not_admitted",
        ],
        "review_target_refs": [row["process_ref"] for row in shot_rows],
        "review_not_target_annotated_refs": [row["process_ref"] for row in not_target_rows],
        "review_target_without_association_refs": [row["process_ref"] for row in shot_without],
        "analyst_action": (
            "Review target-annotated, target-without-association, and not-target-annotated "
            "process refs against admitted current surfaces or other admissible evidence before any "
            "player-quality, causal, tactical-plan, or physical-mechanism interpretation."
        ),
        "claim_ceiling": "MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY",
    }


def _c02_observation_capability_profile() -> dict[str, Any]:
    """Describe what the current C02 source can and cannot resolve for its target outcome."""
    required = [
        "PROCESS_CONTEXT_INTERVAL",
        "PROCESS_PARTICIPATION",
        "TARGET_OUTCOME_POSITIVE_ANNOTATION",
        "TARGET_OUTCOME_NEGATIVE_RESOLUTION",
    ]
    admitted = [
        "PROCESS_CONTEXT_INTERVAL",
        "PROCESS_PARTICIPATION",
        "TARGET_OUTCOME_POSITIVE_ANNOTATION",
    ]
    missing = ["TARGET_OUTCOME_NEGATIVE_RESOLUTION"]
    return {
        "profile_version": "C02_OBSERVATION_CAPABILITY_COVERAGE_V1",
        "applicability_state": "ELIGIBLE",
        "required_capabilities": required,
        "admitted_capabilities": admitted,
        "missing_required_capabilities": missing,
        "capability_state": "PARTIALLY_ADMITTED",
        "observation_window_state": "UNRESOLVED_FOR_TARGET_NEGATIVE_RESOLUTION",
        "instance_observation_state": "PARTIALLY_OBSERVED",
        "coverage_state": "PARTIALLY_OBSERVABLE",
        "negative_claim_admission_state": "BLOCKED_NEGATIVE_OUTCOME_NOT_RESOLVABLE",
        "not_target_annotation_is_negative_outcome_truth": False,
        "absence_is_counterevidence": False,
        "creates_new_evidence": False,
        "can_authorize_emit": False,
        "can_strengthen_claim_ceiling": False,
        "claim_ceiling": "MATCH_LOCAL_OBSERVATION_CAPABILITY_AND_COVERAGE_DESCRIPTION_ONLY",
    }


def _association_record(
    *,
    association_type: str,
    actor_ids: tuple[str, ...],
    process_rows: list[dict[str, Any]],
    baseline_shot_n: int,
    baseline_n: int,
    actor_bindings: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    actor_set = set(actor_ids)
    involved = [row for row in process_rows if actor_set.issubset(set(row["actor_ids"]))]
    shot_rows = [row for row in involved if row["shot_present"]]
    no_shot_rows = [row for row in involved if not row["shot_present"]]
    shot_without = [
        row for row in process_rows
        if row["shot_present"] and not actor_set.issubset(set(row["actor_ids"]))
    ]
    no_shot_without = [
        row for row in process_rows
        if not row["shot_present"] and not actor_set.issubset(set(row["actor_ids"]))
    ]
    support_n = len(involved)
    shot_n = len(shot_rows)
    unresolved_n = len(no_shot_rows)
    rate = (shot_n / support_n) if support_n else None
    baseline = (baseline_shot_n / baseline_n) if baseline_n else None
    lift = (rate / baseline) if rate is not None and baseline not in (None, 0) else None
    eligible_episode_refs = sorted({
        str(row.get("episode_ref")) for row in involved if row.get("episode_ref")
    })
    positive_episode_refs = sorted({
        str(row.get("episode_ref")) for row in shot_rows if row.get("episode_ref")
    })
    bound = [actor_bindings.get(actor_id) for actor_id in actor_ids]
    labels = [
        (item or {}).get("actor_label") or actor_id
        for actor_id, item in zip(actor_ids, bound)
    ]
    xlsx_context = []
    for actor_id, item in zip(actor_ids, bound):
        if not item:
            continue
        xlsx_context.append({
            "actor_identity_candidate_id": actor_id,
            "actor_label": item.get("actor_label"),
            "xlsx_binding_state": item.get("binding_state"),
            "xlsx_row_projection_id": item.get("xlsx_row_projection_id"),
            "metrics": _selected_xlsx_metric_context(item.get("xlsx_row") or {}),
        })
    return {
        "association_type": association_type,
        "actor_identity_candidate_ids": list(actor_ids),
        "actor_labels": labels,
        "support_n": support_n,
        "eligible_n": support_n,
        "shot_ending_n": shot_n,
        "visible_target_annotation_k": shot_n,
        "target_outcome_unresolved_u": unresolved_n,
        "observed_visible_target_annotation_frequency": rate,
        "observed_rate_semantics": "VISIBLE_TARGET_ANNOTATION_FREQUENCY_NOT_RESOLVED_OUTCOME_RATE",
        "not_target_annotated_n": len(no_shot_rows),
        "involved_without_target_annotation_refs": [row["process_ref"] for row in no_shot_rows],
        "not_target_annotated_is_resolved_non_target": False,
        "legacy_non_shot_fields_deprecation_state": "DEPRECATED_COMPATIBILITY_ONLY",
        "legacy_non_shot_fields_are_resolved_non_target": False,
        "non_shot_n": len(no_shot_rows),
        "conditional_shot_frequency": rate,
        "conditional_shot_frequency_semantics": "LEGACY_ALIAS_VISIBLE_TARGET_ANNOTATION_FREQUENCY",
        "match_local_baseline_shot_frequency": baseline,
        "baseline_frequency_semantics": "VISIBLE_TARGET_ANNOTATION_FREQUENCY_AMONG_FAMILY_ELIGIBLE_UNITS",
        "match_local_lift": lift,
        "descriptive_lift": lift,
        "descriptive_lift_semantics": "VISIBLE_ANNOTATION_FREQUENCY_RATIO_MATCH_LOCAL_NOT_EFFECT_SIZE",
        "eligible_episode_refs": eligible_episode_refs,
        "eligible_episode_spread": len(eligible_episode_refs),
        "positive_episode_refs": positive_episode_refs,
        "positive_episode_spread": len(positive_episode_refs),
        "eligible_episode_spread_is_independence_proof": False,
        "positive_episode_spread_is_independence_proof": False,
        "process_refs": [row["process_ref"] for row in involved],
        "shot_process_refs": [row["process_ref"] for row in shot_rows],
        "counterexample_involved_without_shot_refs": [row["process_ref"] for row in no_shot_rows],
        "counterexample_shot_without_association_refs": [row["process_ref"] for row in shot_without],
        "opportunity_normalized_evidence_anatomy": {
            "comparison_design_ref": "C02_PROCESS_FAMILY_OUTCOME_BLIND_ELIGIBILITY_V1",
            "target_outcome_semantic": "PROVIDER_REVIEWED_SHOT_PRESENT_ANNOTATION_CANDIDATE",
            "denominator_state": "FAMILY_ELIGIBLE_PROCESS_N_FROZEN_BEFORE_OUTCOME_READ",
            "family_eligible_process_n": None,
            "association_involvement_n": support_n,
            "resolved_target_n": shot_n,
            "resolved_non_target_n": None,
            "unresolved_outcome_n": None,
            "right_censored_n": None,
            "identification_state": "OUTCOME_RESOLUTION_CAPABILITY_NOT_AVAILABLE",
            "lower_bound": None,
            "upper_bound": None,
            "identification_source_ref": None,
            "bound_transfer_state": "BOUND_NOT_TRANSFERABLE_TO_THIS_PROFILE",
            "supporting_episode_refs": sorted({
                str(row.get("episode_ref")) for row in involved if row.get("episode_ref")
            }),
            "supporting_episode_n": len({
                str(row.get("episode_ref")) for row in involved if row.get("episode_ref")
            }),
            "dependency_state": "UNRESOLVED_MATCH_LOCAL_PROCESS_DEPENDENCE",
            "bounded_lineage_group_refs": [],
            "lineage_group_n": None,
            "not_target_annotated_involvement_refs": [row["process_ref"] for row in no_shot_rows],
            "counterexample_involved_without_target_refs": [],
            "counterexample_target_without_association_refs": [row["process_ref"] for row in shot_without],
            "episode_spread_is_independence_proof": False,
            "lineage_group_n_is_effective_sample_size": False,
        },
        "observation_capability_coverage_profile": _c02_observation_capability_profile(),
        "epistemic_review_contract": _association_epistemic_review_contract(
            shot_rows=shot_rows,
            not_target_rows=no_shot_rows,
            shot_without=shot_without,
        ),
        "small_n_association_contract": {
            "observation_unit": "ADMITTED_PROVIDER_REVIEWED_PROCESS_CONTEXT_INTERVAL",
            "target_outcome_semantic": "PROVIDER_REVIEWED_SHOT_PRESENT_ANNOTATION_CANDIDATE",
            "present_target_annotated_n": shot_n,
            "present_not_target_annotated_n": len(no_shot_rows),
            "absent_target_annotated_n": len(shot_without),
            "absent_not_target_annotated_n": len(no_shot_without),
            "present_non_shot_n": None,
            "absent_non_shot_n": None,
            "outcome_resolution_state": "OUTCOME_RESOLUTION_CAPABILITY_NOT_AVAILABLE",
            "exchangeability_admitted": False,
            "dependency_state": "UNRESOLVED_MATCH_LOCAL_PROCESS_DEPENDENCE",
            "fisher_exact_state": "NOT_EVALUATED_OUTCOME_RESOLUTION_UNAVAILABLE",
            "permutation_state": "NOT_EVALUATED_OUTCOME_RESOLUTION_AND_EXCHANGEABILITY_UNAVAILABLE",
            "p_value_is_football_importance": False,
        },
        "xlsx_actor_context": xlsx_context,
        "xlsx_enriched_actor_count": len(xlsx_context),
        "association_is_causal_player_credit": False,
        "association_is_independent_evidence_vote": False,
        "lift_is_probability": False,
        "outcome_must_not_define_its_own_eligible_denominator": True,
        "minimum_support_threshold_is_evidence_strength_truth": False,
        "shrunk_rate_is_observed_rate": False,
        "no_p_value_eliminates_selection_multiplicity_risk": False,
        "ranked_extreme_is_stable_signal": False,
        "exact_computation_is_valid_football_inference": False,
        "cluster_aware_is_assumption_free": False,
        "claim_ceiling": "MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY",
    }


def _c02_packet_candidate(candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    """Bind one C02 analyst-attention profile to the existing governed C4 chain.

    The packet creates no new evidence and deliberately admits no independent support.
    Absence of a visible target annotation is not promoted to contradiction or resolved
    negative outcome. The outer packet ceiling stays at the composite-builder contract;
    the C02-specific ceiling is preserved inside the evidence profile.
    """
    if not isinstance(candidate, dict):
        return None
    process_refs = sorted({
        str(value).strip()
        for value in (candidate.get("process_refs") or [])
        if str(value).strip()
    })
    if len(process_refs) < 2:
        return None

    positive_refs = {
        str(value).strip()
        for value in (candidate.get("shot_process_refs") or [])
        if str(value).strip()
    }
    actor_ids = tuple(str(value) for value in (candidate.get("actor_identity_candidate_ids") or []))
    association_type = str(candidate.get("association_type") or "UNRESOLVED")
    team_id = str(candidate.get("team_identity_candidate_id") or "UNKNOWN")
    family = str(candidate.get("process_family_candidate") or "UNKNOWN")
    profile_seed = "|".join([association_type, team_id, family, *actor_ids])
    profile_id = "c02_profile_" + hashlib.sha256(profile_seed.encode("utf-8")).hexdigest()[:24]
    dependency_group = f"c02:{team_id}:{family}"

    sequence_records = [
        {
            "sequence_id": process_ref,
            "source_surface": "analyst_episode_process_participation_projection_v1",
            "lenses": ["actor", "process", "outcome", "context"],
            "visible_target_annotation_candidate": process_ref in positive_refs,
            "not_target_annotation_is_resolved_non_target": False,
            "provenance_root": "analyst_episode_process_participation_projection_v1",
            "dependency_group": dependency_group,
            "independence_group": None,
            "independent_support_vote": False,
        }
        for process_ref in process_refs
    ]
    profile_feature = {
        "feature_id": profile_id,
        "source_surface": "rich_multiformat_analysis_lattice_v1",
        "lenses": ["actor", "process", "outcome", "context", "derived"],
        "association_type": association_type,
        "actor_identity_candidate_ids": list(actor_ids),
        "actor_labels": list(candidate.get("actor_labels") or []),
        "team_identity_candidate_id": candidate.get("team_identity_candidate_id"),
        "process_family_candidate": candidate.get("process_family_candidate"),
        "eligibility_contract": "C02_PROCESS_FAMILY_OUTCOME_BLIND_ELIGIBILITY_V1",
        "eligible_n": candidate.get("eligible_n"),
        "visible_target_annotation_k": candidate.get("visible_target_annotation_k"),
        "target_outcome_unresolved_u": candidate.get("target_outcome_unresolved_u"),
        "observed_visible_target_annotation_frequency": candidate.get("observed_visible_target_annotation_frequency"),
        "descriptive_lift": candidate.get("descriptive_lift"),
        "eligible_episode_spread": candidate.get("eligible_episode_spread"),
        "positive_episode_spread": candidate.get("positive_episode_spread"),
        "selection_scope": candidate.get("selection_scope"),
        "selection_candidate_pool_n": candidate.get("selection_candidate_pool_n"),
        "selection_rank": candidate.get("selection_rank"),
        "selection_is_posthoc_attention_ranking": True,
        "selection_is_stable_signal": False,
        "association_claim_ceiling": "MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY",
        "association_is_causal_player_credit": False,
        "target_annotation_absence_is_counterevidence": False,
        "outcome_must_not_define_its_own_eligible_denominator": True,
        "no_p_value_eliminates_selection_multiplicity_risk": False,
        "ranked_extreme_is_stable_signal": False,
        "provenance_root": "rich_multiformat_analysis_lattice_v1",
        "dependency_group": dependency_group,
        "independence_group": None,
        "independent_support_vote": False,
    }
    signal = {
        "signal_id": profile_id + ":visible_association",
        "source_surface": "HPFA_DERIVED_FROM_C02_ADMITTED_PROCESS_PARTICIPATION",
        "evidence_derivation_role": "DESCRIPTIVE_VISIBLE_ASSOCIATION_PROFILE",
        "evidence_role": "analyst_attention_visible_association_candidate",
        "relation_type": "SUPPORTS",
        "source_refs": process_refs,
        "lenses": ["actor", "process", "outcome", "derived"],
        "provenance_root": "analyst_episode_process_participation_projection_v1",
        "dependency_group": dependency_group,
        "independence_group": None,
        "independent_support_vote": False,
        "causal_truth": False,
        "quality_truth": False,
        "statistical_significance_truth": False,
    }
    return {
        "source_construct_id": "C02_PROCESS_PARTICIPANT_OUTCOME_ASSOCIATION",
        "packet_family": "production_consequence",
        "input_features": [profile_feature],
        "input_windows": [],
        "input_sequences": sequence_records,
        "input_metrics": [],
        "supporting_signals": [signal],
        "contradicting_signals": [],
        "required_lenses": ["actor", "process", "outcome", "context"],
        "optional_lenses": ["derived", "aggregate", "contradiction", "opponent"],
        "claim_ceiling": "composite_candidate_only",
        "blocked_language_families": [
            "causal_truth",
            "quality_truth",
            "tactical_truth",
            "coach_intention",
            "future_expectation",
            "population_effect",
            "statistical_significance",
        ],
    }


def _construct_c02(
    rows: list[dict[str, Any]],
    identity_payload: dict[str, Any],
    process_payload: dict[str, Any],
) -> dict[str, Any]:
    """Compose process participation + visible shot outcome + XLSX aggregate context."""
    if str(process_payload.get("status") or "").upper() == "FAIL_CLOSED":
        return {
            "construct_id": "C02_PROCESS_PARTICIPANT_OUTCOME_ASSOCIATION",
            "status": "REVIEW_REQUIRED",
            "review_reason": "process_participation_upstream_fail_closed",
            "argument_candidates": [],
            "claim_ceiling": "MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY",
        }

    actor_bindings, binding_reviews = _actor_xlsx_bindings(rows, identity_payload)
    raw = [
        row for row in (process_payload.get("process_participation_candidates") or [])
        if isinstance(row, dict)
    ]
    contexts: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    participants: dict[tuple[str, str, str, str, str], set[str]] = defaultdict(set)
    for row in raw:
        key = _process_interval_key(row)
        role = str(row.get("semantic_role") or "")
        if role == "CONTEXT_INTERVAL":
            existing = contexts.get(key)
            if existing is None or (
                existing.get("shot_present_annotation_candidate") is not True
                and row.get("shot_present_annotation_candidate") is True
            ):
                contexts[key] = row
        elif role == "PARTICIPATION_INTERVAL":
            actor_id = str(row.get("actor_identity_candidate_id") or "").strip()
            if actor_id:
                participants[key].add(actor_id)

    family_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for key, context in contexts.items():
        team_id, family, _, _, _ = key
        if not team_id or not family:
            continue
        family_rows[(team_id, family)].append({
            "process_ref": str(context.get("process_participation_candidate_id") or ""),
            "episode_ref": context.get("episode_candidate_id"),
            "shot_present": context.get("shot_present_annotation_candidate") is True,
            "actor_ids": sorted(participants.get(key, set())),
            "period_candidate": context.get("period_candidate"),
            "start_candidate": context.get("start_candidate"),
            "end_candidate": context.get("end_candidate"),
        })

    family_profiles: list[dict[str, Any]] = []
    all_actor_candidates: list[dict[str, Any]] = []
    all_dyad_candidates: list[dict[str, Any]] = []
    identity_actors = {
        str(row.get("actor_identity_candidate_id") or ""): row
        for row in (identity_payload.get("actor_identity_candidates") or [])
        if isinstance(row, dict) and row.get("actor_identity_candidate_id")
    }
    identity_teams = {
        str(row.get("team_identity_candidate_id") or ""): row
        for row in (identity_payload.get("team_identity_candidates") or [])
        if isinstance(row, dict) and row.get("team_identity_candidate_id")
    }

    for (team_id, family), process_rows in sorted(family_rows.items()):
        eligible_n = len(process_rows)
        shot_n = sum(row["shot_present"] for row in process_rows)
        if not eligible_n:
            continue
        actor_ids = sorted({actor for row in process_rows for actor in row["actor_ids"]})
        actor_candidates = [
            _association_record(
                association_type="ACTOR",
                actor_ids=(actor_id,),
                process_rows=process_rows,
                baseline_shot_n=shot_n,
                baseline_n=eligible_n,
                actor_bindings=actor_bindings,
            )
            for actor_id in actor_ids
        ]
        dyad_ids = sorted({
            tuple(pair)
            for row in process_rows
            for pair in combinations(sorted(row["actor_ids"]), 2)
        })
        dyad_candidates = [
            _association_record(
                association_type="DYAD",
                actor_ids=pair,
                process_rows=process_rows,
                baseline_shot_n=shot_n,
                baseline_n=eligible_n,
                actor_bindings=actor_bindings,
            )
            for pair in dyad_ids
        ]
        actor_candidates = [row for row in actor_candidates if row["support_n"] > 0]
        dyad_candidates = [row for row in dyad_candidates if row["support_n"] > 0]

        def decorate(candidate: dict[str, Any]) -> dict[str, Any]:
            out = dict(candidate)
            out["team_identity_candidate_id"] = team_id
            out["process_family_candidate"] = family
            out["eligible_process_n"] = eligible_n
            out["baseline_shot_ending_n"] = shot_n
            out["baseline_not_target_annotated_n"] = eligible_n - shot_n
            out["baseline_not_target_annotated_is_resolved_non_target"] = False
            out["baseline_non_shot_n"] = eligible_n - shot_n
            anatomy = out.get("opportunity_normalized_evidence_anatomy")
            if isinstance(anatomy, dict):
                anatomy["family_eligible_process_n"] = eligible_n
            small_n = out.get("small_n_association_contract")
            if isinstance(small_n, dict):
                small_n["family_eligible_process_n"] = eligible_n
            return out

        actor_candidates = [decorate(row) for row in actor_candidates]
        dyad_candidates = [decorate(row) for row in dyad_candidates]
        all_actor_candidates.extend(actor_candidates)
        all_dyad_candidates.extend(dyad_candidates)
        team = identity_teams.get(team_id) or {}
        family_profiles.append({
            "team_identity_candidate_id": team_id,
            "team_label": _display_subject((team.get("team_aliases_raw") or [team_id])[0]),
            "process_family_candidate": family,
            "eligible_process_n": eligible_n,
            "shot_ending_n": shot_n,
            "not_target_annotated_n": eligible_n - shot_n,
            "not_target_annotated_is_resolved_non_target": False,
            "legacy_non_shot_fields_deprecation_state": "DEPRECATED_COMPATIBILITY_ONLY",
            "legacy_non_shot_fields_are_resolved_non_target": False,
            "non_shot_n": eligible_n - shot_n,
            "shot_ending_frequency": shot_n / eligible_n,
            "observation_capability_coverage_profile": _c02_observation_capability_profile(),
            "process_refs": [row["process_ref"] for row in process_rows],
            "actor_candidate_count": len(actor_candidates),
            "dyad_candidate_count": len(dyad_candidates),
        })

    def priority(row: dict[str, Any]) -> tuple[Any, ...]:
        lift = row.get("match_local_lift")
        return (
            -int(row.get("shot_ending_n") or 0),
            -int(row.get("support_n") or 0),
            -(float(lift) if isinstance(lift, (int, float)) else -1.0),
            tuple(str(value) for value in row.get("actor_labels") or []),
        )

    all_actor_candidates.sort(key=priority)
    all_dyad_candidates.sort(key=priority)
    for rank, row in enumerate(all_actor_candidates, start=1):
        row["selection_scope"] = "ALL_C02_ACTOR_CANDIDATES_CURRENT_MATCH"
        row["selection_candidate_pool_n"] = len(all_actor_candidates)
        row["selection_rank"] = rank
        row["selection_is_posthoc_attention_ranking"] = True
        row["selection_is_stable_signal"] = False
        row["no_p_value_eliminates_selection_multiplicity_risk"] = False
    for rank, row in enumerate(all_dyad_candidates, start=1):
        row["selection_scope"] = "ALL_C02_DYAD_CANDIDATES_CURRENT_MATCH"
        row["selection_candidate_pool_n"] = len(all_dyad_candidates)
        row["selection_rank"] = rank
        row["selection_is_posthoc_attention_ranking"] = True
        row["selection_is_stable_signal"] = False
        row["no_p_value_eliminates_selection_multiplicity_risk"] = False
    representative_actor = all_actor_candidates[0] if all_actor_candidates else None
    representative_dyad = all_dyad_candidates[0] if all_dyad_candidates else None
    packet_candidates = [
        packet
        for packet in (
            _c02_packet_candidate(representative_actor),
            _c02_packet_candidate(representative_dyad),
        )
        if packet is not None
    ]

    return {
        "construct_id": "C02_PROCESS_PARTICIPANT_OUTCOME_ASSOCIATION",
        "status": "REVIEW_REQUIRED" if family_profiles else "NOT_APPLICABLE",
        "review_reason": (
            "match_local_process_outcome_association_candidates_available"
            if family_profiles
            else "process_context_intervals_not_available"
        ),
        "process_family_profiles": family_profiles,
        "actor_argument_candidates": all_actor_candidates,
        "dyad_argument_candidates": all_dyad_candidates,
        "argument_candidate_count": len(all_actor_candidates) + len(all_dyad_candidates),
        "representative_actor_argument": representative_actor,
        "representative_dyad_argument": representative_dyad,
        "packet_candidates": packet_candidates,
        "packet_candidate_count": len(packet_candidates),
        "packet_candidates_create_new_evidence": False,
        "packet_candidates_admit_independent_support": False,
        "packet_candidates_can_authorize_emit": False,
        "xlsx_actor_binding_count": len(actor_bindings),
        "xlsx_binding_review_hits": binding_reviews,
        "process_participation_consumed": bool(raw),
        "observation_capability_coverage_profile": _c02_observation_capability_profile(),
        "unit_of_analysis": "ADMITTED_PROVIDER_REVIEWED_PROCESS_CONTEXT_INTERVAL",
        "association_statistics": [
            "SUPPORT_N",
            "CONDITIONAL_SHOT_FREQUENCY",
            "MATCH_LOCAL_BASELINE_SHOT_FREQUENCY",
            "MATCH_LOCAL_LIFT",
        ],
        "correlation_is_causality": False,
        "player_participation_is_causal_credit": False,
        "xlsx_aggregate_is_action_identity": False,
        "association_candidate_is_independent_support": False,
        "epistemic_review_contract_version": "C02_ASSOCIATION_EPISTEMIC_REVIEW_V1",
        "epistemic_review_contract_creates_new_evidence": False,
        "epistemic_review_contract_can_authorize_emit": False,
        "selection_scope_actor_candidate_count": len(all_actor_candidates),
        "selection_scope_dyad_candidate_count": len(all_dyad_candidates),
        "selection_is_posthoc_attention_ranking": True,
        "no_p_value_eliminates_selection_multiplicity_risk": False,
        "ranked_extreme_is_stable_signal": False,
        "outcome_must_not_define_its_own_eligible_denominator": True,
        "minimum_support_threshold_is_evidence_strength_truth": False,
        "shrunk_rate_is_observed_rate": False,
        "exact_computation_is_valid_football_inference": False,
        "cluster_aware_is_assumption_free": False,
        "claim_ceiling": "MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY",
        "c4_bridge_state": "DEFERRED_UNTIL_PROCESS_ASSOCIATION_ARGUMENT_FAMILY_IS_EXPLICITLY_ADMITTED",
    }



def _as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _construct_c03(
    process_payload: dict[str, Any],
    occurrence_transition_payload: dict[str, Any],
    spatial_payload: dict[str, Any],
) -> dict[str, Any]:
    """Compose process intervals with admitted occurrence layers and annotation-anchor path candidates."""
    process_rows = [
        row for row in (process_payload.get("process_participation_candidates") or [])
        if isinstance(row, dict) and row.get("semantic_role") == "CONTEXT_INTERVAL"
    ]
    occurrence_rows = [
        row for row in (occurrence_transition_payload.get("occurrence_state_transition_projections") or [])
        if isinstance(row, dict)
    ]
    spatial_rows = [
        row for row in (spatial_payload.get("spatial_transition_candidates") or [])
        if isinstance(row, dict)
    ]
    spatial_by_id = {
        str(row.get("spatial_transition_candidate_id")): row
        for row in spatial_rows
        if row.get("spatial_transition_candidate_id")
    }
    signatures: list[dict[str, Any]] = []

    for process in process_rows:
        start = _as_number(process.get("start_candidate"))
        end = _as_number(process.get("end_candidate"))
        if start is None or end is None or end < start:
            continue
        team_id = str(process.get("team_identity_candidate_id") or "")
        period = str(process.get("period_candidate") or "")

        matched: list[tuple[float, dict[str, Any]]] = []
        for occurrence in occurrence_rows:
            teams = {str(v) for v in (occurrence.get("team_identity_candidate_ids") or [])}
            periods = {str(v) for v in (occurrence.get("period_candidates") or [])}
            times = sorted({
                value for value in (_as_number(v) for v in (occurrence.get("start_candidates") or []))
                if value is not None
            })
            if team_id and team_id not in teams:
                continue
            if period and period not in periods:
                continue
            for timestamp in times:
                if start <= timestamp <= end:
                    matched.append((timestamp, occurrence))
                    break

        layer_map: dict[float, list[dict[str, Any]]] = defaultdict(list)
        for timestamp, occurrence in matched:
            layer_map[timestamp].append(occurrence)

        layers: list[dict[str, Any]] = []
        for timestamp in sorted(layer_map):
            rows = layer_map[timestamp]
            anchor_pairs: set[tuple[float, float]] = set()
            spatial_ids: set[str] = set()
            zones: set[str] = set()
            for occurrence in rows:
                for sid in occurrence.get("supporting_spatial_transition_candidate_ids") or []:
                    sid_text = str(sid)
                    spatial = spatial_by_id.get(sid_text)
                    if spatial is None:
                        continue
                    spatial_ids.add(sid_text)
                    zones.update(str(v) for v in (spatial.get("provider_zone_candidates") or []) if v)
                    if not spatial.get("occurrence_annotation_anchor_location_admitted"):
                        continue
                    x = _as_number(spatial.get("provider_coordinate_anchor_x_candidate"))
                    y = _as_number(spatial.get("provider_coordinate_anchor_y_candidate"))
                    if x is not None and y is not None:
                        anchor_pairs.add((x, y))
            layers.append({
                "timestamp_candidate": timestamp,
                "occurrence_ids": sorted({
                    str(row.get("action_occurrence_candidate_id"))
                    for row in rows if row.get("action_occurrence_candidate_id")
                }),
                "action_family_candidates": sorted({
                    str(value)
                    for row in rows
                    for value in (row.get("action_family_candidates") or [])
                    if value
                }),
                "actor_identity_candidate_ids": sorted({
                    str(value)
                    for row in rows
                    for value in (row.get("actor_identity_candidate_ids") or [])
                    if value
                }),
                "transition_class_candidates": sorted({
                    str(value)
                    for row in rows
                    for value in (row.get("transition_class_candidates") or [])
                    if value
                }),
                "provider_outcome_candidates": sorted({
                    str(value)
                    for row in rows
                    for value in (row.get("provider_outcome_candidates") or [])
                    if value
                }),
                "primary_consequence_candidates": sorted({
                    str(value)
                    for row in rows
                    for value in (row.get("primary_consequence_candidates") or [])
                    if value
                }),
                "provider_zone_candidates": sorted(zones),
                "supporting_spatial_transition_candidate_ids": sorted(spatial_ids),
                "admitted_annotation_anchor_candidates": [
                    {"x": x, "y": y} for x, y in sorted(anchor_pairs)
                ],
                "same_timestamp_internal_ordering_allowed": False,
            })

        segments: list[dict[str, Any]] = []
        for left, right in zip(layers, layers[1:]):
            left_anchors = left["admitted_annotation_anchor_candidates"]
            right_anchors = right["admitted_annotation_anchor_candidates"]
            if len(left_anchors) != 1 or len(right_anchors) != 1:
                continue
            ax, ay = left_anchors[0]["x"], left_anchors[0]["y"]
            bx, by = right_anchors[0]["x"], right_anchors[0]["y"]
            dx, dy = bx - ax, by - ay
            segments.append({
                "from_timestamp_candidate": left["timestamp_candidate"],
                "to_timestamp_candidate": right["timestamp_candidate"],
                "delta_x_provider_coordinate_candidate": dx,
                "delta_y_provider_coordinate_candidate": dy,
                "annotation_anchor_distance_provider_units_candidate": (dx * dx + dy * dy) ** 0.5,
                "physical_distance_truth": False,
                "physical_speed_truth": False,
            })

        complete_path = bool(layers) and len(segments) == max(0, len(layers) - 1) and all(
            len(layer["admitted_annotation_anchor_candidates"]) == 1 for layer in layers
        )
        cumulative = sum(
            segment["annotation_anchor_distance_provider_units_candidate"] for segment in segments
        )
        net = None
        directness = None
        if complete_path and len(layers) >= 2:
            first = layers[0]["admitted_annotation_anchor_candidates"][0]
            last = layers[-1]["admitted_annotation_anchor_candidates"][0]
            dx, dy = last["x"] - first["x"], last["y"] - first["y"]
            net = (dx * dx + dy * dy) ** 0.5
            if cumulative > 0:
                directness = net / cumulative

        action_family_layer_counts: Counter[str] = Counter()
        unique_actor_ids: set[str] = set()
        zone_layer_path_candidates: list[list[str]] = []
        transition_classes: set[str] = set()
        provider_outcomes: set[str] = set()
        primary_consequences: set[str] = set()
        for layer in layers:
            for family_value in layer.get("action_family_candidates") or []:
                action_family_layer_counts[str(family_value)] += 1
            unique_actor_ids.update(str(value) for value in (layer.get("actor_identity_candidate_ids") or []) if value)
            zone_layer_path_candidates.append([
                str(value) for value in (layer.get("provider_zone_candidates") or []) if value
            ])
            transition_classes.update(
                str(value) for value in (layer.get("transition_class_candidates") or []) if value
            )
            provider_outcomes.update(
                str(value) for value in (layer.get("provider_outcome_candidates") or []) if value
            )
            primary_consequences.update(
                str(value) for value in (layer.get("primary_consequence_candidates") or []) if value
            )
        start_zone_candidates = zone_layer_path_candidates[0] if zone_layer_path_candidates else []
        end_zone_candidates = zone_layer_path_candidates[-1] if zone_layer_path_candidates else []
        zone_transition_candidates = []
        for left_layer, right_layer in zip(layers, layers[1:]):
            left_zones = [str(v) for v in (left_layer.get("provider_zone_candidates") or []) if v]
            right_zones = [str(v) for v in (right_layer.get("provider_zone_candidates") or []) if v]
            if len(left_zones) != 1 or len(right_zones) != 1:
                continue
            if left_zones[0] == right_zones[0]:
                continue
            zone_transition_candidates.append({
                "from_zone_candidate": left_zones[0],
                "to_zone_candidate": right_zones[0],
                "from_timestamp_candidate": left_layer.get("timestamp_candidate"),
                "to_timestamp_candidate": right_layer.get("timestamp_candidate"),
                "ordering_basis": "STRICTLY_ORDERED_TEMPORAL_LAYERS",
                "progression_truth": False,
                "line_break_truth": False,
                "physical_ball_path_truth": False,
            })
        pass_layer_n = int(action_family_layer_counts.get("PASS", 0))
        carry_layer_n = int(action_family_layer_counts.get("CARRY", 0))
        pass_carry_total = pass_layer_n + carry_layer_n
        pass_carry_mix = {
            "pass_layer_n": pass_layer_n,
            "carry_layer_n": carry_layer_n,
            "eligible_pass_carry_family_layer_n": pass_carry_total,
            "pass_share_candidate": (pass_layer_n / pass_carry_total) if pass_carry_total else None,
            "carry_share_candidate": (carry_layer_n / pass_carry_total) if pass_carry_total else None,
            "denominator_basis": "ACTION_FAMILY_PRESENCE_PER_TEMPORAL_LAYER",
            "physical_touch_count_truth": False,
        }

        on_ball_families = {"PASS", "CARRY", "DRIBBLE", "SHOT", "RESTART"}
        on_ball_layers = [
            layer for layer in layers
            if on_ball_families.intersection(set(layer.get("action_family_candidates") or []))
        ]
        on_ball_family_layer_counts = {
            family: int(action_family_layer_counts.get(family, 0))
            for family in sorted(on_ball_families)
            if action_family_layer_counts.get(family, 0)
        }
        actor_family_layer_counts: Counter[tuple[str, str]] = Counter()
        unresolved_actor_family_layer_n = 0
        for layer in on_ball_layers:
            layer_pairs: set[tuple[str, str]] = set()
            layer_unresolved = False
            for occurrence_id in layer.get("occurrence_ids") or []:
                matched_occurrence_rows = [
                    row for _, row in matched
                    if str(row.get("action_occurrence_candidate_id") or "") == str(occurrence_id)
                ]
                for occurrence_row in matched_occurrence_rows:
                    actors = [str(value) for value in (occurrence_row.get("actor_identity_candidate_ids") or []) if value]
                    families = [str(value) for value in (occurrence_row.get("action_family_candidates") or []) if value and str(value) in on_ball_families]
                    if len(actors) == 1 and len(families) == 1:
                        layer_pairs.add((actors[0], families[0]))
                    elif actors or families:
                        layer_unresolved = True
            for pair in layer_pairs:
                actor_family_layer_counts[pair] += 1
            if layer_unresolved:
                unresolved_actor_family_layer_n += 1

        on_ball_profile = {
            "visible_on_ball_temporal_layer_n": len(on_ball_layers),
            "visible_on_ball_family_layer_counts": on_ball_family_layer_counts,
            "visible_on_ball_actor_candidate_n": len({
                str(actor_id)
                for layer in on_ball_layers
                for actor_id in (layer.get("actor_identity_candidate_ids") or [])
                if actor_id
            }),
            "actor_family_temporal_layer_participation_candidates": [
                {
                    "actor_identity_candidate_id": actor_id,
                    "action_family_candidate": family,
                    "temporal_layer_n": count,
                    "eligible_on_ball_temporal_layer_n": len(on_ball_layers),
                    "temporal_layer_share_candidate": (count / len(on_ball_layers)) if on_ball_layers else None,
                    "causal_process_credit_truth": False,
                    "physical_touch_count_truth": False,
                }
                for (actor_id, family), count in sorted(actor_family_layer_counts.items())
            ],
            "actor_family_unresolved_temporal_layer_n": unresolved_actor_family_layer_n,
            "actor_family_binding_basis": "UNAMBIGUOUS_OCCURRENCE_LEVEL_ACTOR_AND_ON_BALL_FAMILY_WITH_TEMPORAL_LAYER_DEDUP",
            "actor_family_participation_is_causal_process_credit": False,
            "eligible_family_basis": sorted(on_ball_families),
            "same_timestamp_multi_family_is_not_multiple_touch_truth": True,
            "temporal_layer_is_not_physical_touch": True,
            "event_coordinate_is_not_ball_trajectory": True,
            "absence_of_family_is_not_absence_of_physical_action": True,
            "claim_ceiling": "VISIBLE_ON_BALL_EVENT_FAMILY_PROFILE_CANDIDATE_ONLY",
        }

        signatures.append({
            "process_development_signature_id": "pds_" + hashlib.sha256(
                "|".join([
                    str(process.get("process_participation_candidate_id") or ""),
                    team_id, period, str(start), str(end),
                ]).encode("utf-8")
            ).hexdigest()[:24],
            "process_ref": process.get("process_participation_candidate_id"),
            "process_family_candidate": process.get("process_family_candidate"),
            "team_identity_candidate_id": process.get("team_identity_candidate_id"),
            "period_candidate": process.get("period_candidate"),
            "process_start_candidate": start,
            "process_end_candidate": end,
            "process_interval_duration_candidate": end - start,
            "process_duration_basis": "PROVIDER_REVIEWED_PROCESS_CONTEXT_INTERVAL",
            "shot_present_annotation_candidate": process.get("shot_present_annotation_candidate") is True,
            "visible_occurrence_n": len({row.get("action_occurrence_candidate_id") for _, row in matched if row.get("action_occurrence_candidate_id")}),
            "temporal_layer_n": len(layers),
            "unique_actor_candidate_n": len(unique_actor_ids),
            "unique_actor_identity_candidate_ids": sorted(unique_actor_ids),
            "action_family_layer_counts": dict(sorted(action_family_layer_counts.items())),
            "pass_carry_layer_mix": pass_carry_mix,
            "visible_on_ball_profile": on_ball_profile,
            "process_start_zone_candidates": start_zone_candidates,
            "process_end_zone_candidates": end_zone_candidates,
            "zone_layer_path_candidates": zone_layer_path_candidates,
            "visible_zone_transition_candidate_n": len(zone_transition_candidates),
            "visible_zone_transition_candidates": zone_transition_candidates,
            "zone_transition_is_progression_truth": False,
            "zone_transition_is_line_break_truth": False,
            "transition_class_candidates_observed": sorted(transition_classes),
            "provider_outcome_candidates_observed": sorted(provider_outcomes),
            "primary_consequence_candidates_observed": sorted(primary_consequences),
            "visible_loss_transition_candidate_present": bool(primary_consequences & {
                "OPPONENT_HANDOVER_CANDIDATE",
                "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
            }),
            "visible_recovery_transition_candidate_present": bool(primary_consequences & {
                "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE",
                "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE",
            }),
            "loss_recovery_visibility_basis": "EXPLICIT_ADMITTED_PRIMARY_CONSEQUENCE_CANDIDATES",
            "visible_terminal_annotation_candidate_present": process.get("shot_present_annotation_candidate") is True,
            "process_morphology_basis": "ADMITTED_TEMPORAL_LAYER_SUMMARY_NOT_PHYSICAL_TRAJECTORY_OR_PHASE_TRUTH",
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "layers": layers,
            "annotation_anchor_segments": segments,
            "annotation_anchor_segment_n": len(segments),
            "annotation_anchor_path_coverage_state": (
                "COMPLETE_CONSECUTIVE_SINGLE_ANCHOR"
                if complete_path and len(layers) >= 2
                else "PARTIAL_OR_AMBIGUOUS"
            ),
            "annotation_anchor_segment_distance_sum_provider_units_candidate": cumulative if segments else None,
            "annotation_anchor_net_displacement_provider_units_candidate": net,
            "annotation_anchor_path_directness_candidate": directness,
            "annotation_anchor_path_is_physical_trajectory": False,
            "annotation_anchor_distance_is_physical_travel_distance": False,
            "process_interval_duration_is_generic_action_duration": False,
            "tracking_truth": False,
            "video_truth": False,
            "team_shape_truth": False,
            "off_ball_geometry_truth": False,
            "coach_intention_truth": False,
            "claim_ceiling": "MATCH_LOCAL_VISIBLE_PROCESS_DEVELOPMENT_SIGNATURE_CANDIDATE_ONLY",
        })

    process_motif_family_candidates: list[dict[str, Any]] = []
    motif_members: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    def _motif_length_bucket(value: Any) -> str:
        n = int(value or 0)
        if n <= 2:
            return "SHORT_0_2_LAYERS"
        if n <= 5:
            return "MEDIUM_3_5_LAYERS"
        return "LONG_6_PLUS_LAYERS"

    def _motif_pass_carry_style(signature: dict[str, Any]) -> str:
        value = _as_number((signature.get("pass_carry_layer_mix") or {}).get("pass_share_candidate"))
        if value is None:
            return "NO_PASS_CARRY_BASIS"
        if value >= 0.85:
            return "PASS_DOMINANT"
        if value >= 0.50:
            return "MIXED_PASS_CARRY"
        return "CARRY_DOMINANT"

    def _motif_action_presence(signature: dict[str, Any]) -> tuple[str, ...]:
        excluded = {"SHOT", "GOAL", "TURNOVER", "RECOVERY"}
        return tuple(sorted(
            str(family)
            for family, count in (signature.get("action_family_layer_counts") or {}).items()
            if count and str(family) not in excluded
        ))

    def _motif_route_hint(signature: dict[str, Any]) -> str:
        starts = [str(v) for v in (signature.get("process_start_zone_candidates") or []) if v]
        ends = [str(v) for v in (signature.get("process_end_zone_candidates") or []) if v]
        if len(starts) == 1 and len(ends) == 1:
            return f"{starts[0]}->{ends[0]}"
        return "NO_UNAMBIGUOUS_ROUTE_HINT"

    for signature in signatures:
        team_id = str(signature.get("team_identity_candidate_id") or "")
        family_id = str(signature.get("process_family_candidate") or "UNKNOWN")
        if not team_id:
            continue
        morphology = {
            "length_bucket": _motif_length_bucket(signature.get("temporal_layer_n")),
            "action_family_presence": list(_motif_action_presence(signature)),
            "pass_carry_style": _motif_pass_carry_style(signature),
            "route_hint": _motif_route_hint(signature),
        }
        morphology_key = json.dumps(morphology, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        motif_members[(team_id, family_id, morphology_key)].append(signature)

    for (team_id, family_id, morphology_key), rows in sorted(motif_members.items()):
        morphology = json.loads(morphology_key)
        shot_n = sum(row.get("shot_present_annotation_candidate") is True for row in rows)
        loss_n = sum(bool(row.get("visible_loss_transition_candidate_present")) for row in rows)
        recovery_n = sum(bool(row.get("visible_recovery_transition_candidate_present")) for row in rows)
        periods = sorted({str(row.get("period_candidate") or "") for row in rows if row.get("period_candidate")})
        durations = [_as_number(row.get("process_interval_duration_candidate")) for row in rows]
        durations = [v for v in durations if v is not None]
        actor_spreads = [_as_number(row.get("unique_actor_candidate_n")) for row in rows]
        actor_spreads = [v for v in actor_spreads if v is not None]
        temporal_layers = [_as_number(row.get("temporal_layer_n")) for row in rows]
        temporal_layers = [v for v in temporal_layers if v is not None]
        representative = max(
            rows,
            key=lambda row: (
                int(row.get("temporal_layer_n") or 0),
                int(row.get("unique_actor_candidate_n") or 0),
                float(row.get("process_interval_duration_candidate") or 0.0),
            ),
        )
        motif_id = "pmf_" + hashlib.sha256(
            f"{team_id}|{family_id}|{morphology_key}".encode()
        ).hexdigest()[:24]

        def _variant_context(row: dict[str, Any]) -> str:
            shot = row.get("shot_present_annotation_candidate") is True
            loss = bool(row.get("visible_loss_transition_candidate_present"))
            recovery = bool(row.get("visible_recovery_transition_candidate_present"))
            if shot and loss:
                return "SHOT_AND_LOSS_VISIBLE"
            if shot:
                return "SHOT_LINKED"
            if loss:
                return "LOSS_LINKED"
            if recovery:
                return "RECOVERY_LINKED"
            return "OTHER_VISIBLE"

        synthetic_variants = []
        variant_context_by_id: dict[str, str] = {}
        for row in rows:
            variant_id = str(row.get("process_development_signature_id") or "")
            if not variant_id:
                continue
            layer_refs = [f"{variant_id}:L{idx}" for idx, _ in enumerate(row.get("layers") or [])]
            node_records = []
            for idx, layer in enumerate(row.get("layers") or []):
                node_records.append({
                    "time_layer_ref": layer_refs[idx],
                    "action_family_candidates": [str(v) for v in (layer.get("action_family_candidates") or []) if v],
                })
            edge_relations = [
                {
                    "from_time_layer_ref": layer_refs[idx],
                    "to_time_layer_ref": layer_refs[idx + 1],
                    "relation": "BEFORE_CONFIRMED",
                }
                for idx in range(max(0, len(layer_refs) - 1))
            ]
            synthetic_variants.append({
                "partial_order_occurrence_variant_id": variant_id,
                "time_layer_refs": layer_refs,
                "node_records": node_records,
                "edge_relations": edge_relations,
            })
            variant_context_by_id[variant_id] = _variant_context(row)

        synthetic_pairs = []
        for left, right in combinations(synthetic_variants, 2):
            left_id = str(left.get("partial_order_occurrence_variant_id") or "")
            right_id = str(right.get("partial_order_occurrence_variant_id") or "")
            left_context = variant_context_by_id.get(left_id, "OTHER_VISIBLE")
            right_context = variant_context_by_id.get(right_id, "OTHER_VISIBLE")
            if left_context == right_context:
                continue
            synthetic_pairs.append({
                "partial_order_similarity_pair_id": "motif_pair_" + hashlib.sha256(
                    f"{motif_id}|{left_id}|{right_id}".encode()
                ).hexdigest()[:24],
                "left_variant_ref": left_id,
                "right_variant_ref": right_id,
                "comparison_eligible": True,
                "comparison_eligibility_state": "SAME_OUTCOME_INDEPENDENT_MOTIF_DIFFERENT_VISIBLE_VARIANT_CONTEXT",
                "outcome_used_in_similarity_decision": False,
            })

        divergence_alignment = None
        divergence_candidates = []
        if len(synthetic_variants) >= 2 and synthetic_pairs:
            alignment_report = build_supported_sequence_grammar_alignment({
                "partial_order_occurrence_variants": synthetic_variants,
                "dependency_aware_partial_order_similarity_pairs": synthetic_pairs,
                "dependency_aware_partial_order_similarity_status": "PASS",
                "outcome_used_in_similarity_decision": False,
                "same_timestamp_internal_ordering_allowed": False,
                "source_row_order_is_temporal_truth": False,
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            })
            divergence_candidates = [
                row for row in (alignment_report.get("supported_sequence_grammar_alignments") or [])
                if isinstance(row, dict) and row.get("first_supported_grammar_divergence") is not None
            ]
            if divergence_candidates:
                divergence_candidates.sort(key=lambda row: (
                    float(row.get("grammar_edit_distance_normalized") or 999.0),
                    -float(row.get("common_core_symmetric_coverage") or 0.0),
                    str(row.get("supported_sequence_grammar_alignment_id") or ""),
                ))
                chosen = divergence_candidates[0]
                left_id = str(chosen.get("left_variant_ref") or "")
                right_id = str(chosen.get("right_variant_ref") or "")
                divergence_alignment = {
                    "alignment_ref": chosen.get("supported_sequence_grammar_alignment_id"),
                    "left_process_development_signature_id": left_id,
                    "right_process_development_signature_id": right_id,
                    "left_variant_context": variant_context_by_id.get(left_id),
                    "right_variant_context": variant_context_by_id.get(right_id),
                    "supported_common_core_tokens": chosen.get("supported_common_core_tokens") or [],
                    "supported_common_core_layer_count": chosen.get("supported_common_core_layer_count"),
                    "common_core_symmetric_coverage": chosen.get("common_core_symmetric_coverage"),
                    "grammar_edit_distance": chosen.get("grammar_edit_distance"),
                    "grammar_edit_distance_normalized": chosen.get("grammar_edit_distance_normalized"),
                    "first_supported_grammar_divergence": chosen.get("first_supported_grammar_divergence"),
                    "contrast_pair_selected_within_outcome_independent_motif": True,
                    "contrast_pair_outcome_context_is_not_similarity_basis": True,
                    "first_divergence_is_causal_breakpoint_truth": False,
                    "first_divergence_is_tactical_failure_truth": False,
                    "claim_ceiling": "MATCH_LOCAL_VISIBLE_GRAMMAR_DIVERGENCE_CANDIDATE_ONLY",
                }

        process_motif_family_candidates.append({
            "process_motif_family_candidate_id": motif_id,
            "team_identity_candidate_id": team_id,
            "process_family_candidate": family_id,
            "morphology_signature": morphology,
            "member_process_n": len(rows),
            "recurring_motif_candidate": len(rows) >= 2,
            "period_spread_candidates": periods,
            "shot_variant_n": shot_n,
            "non_shot_variant_n": len(rows) - shot_n,
            "visible_loss_variant_n": loss_n,
            "visible_recovery_variant_n": recovery_n,
            "mean_duration_candidate": (sum(durations) / len(durations)) if durations else None,
            "mean_actor_spread_candidate": (sum(actor_spreads) / len(actor_spreads)) if actor_spreads else None,
            "mean_temporal_layer_n": (sum(temporal_layers) / len(temporal_layers)) if temporal_layers else None,
            "representative_process_development_signature_id": representative.get("process_development_signature_id"),
            "representative_process_start_candidate": representative.get("process_start_candidate"),
            "representative_process_end_candidate": representative.get("process_end_candidate"),
            "representative_start_zone_candidates": representative.get("process_start_zone_candidates") or [],
            "representative_end_zone_candidates": representative.get("process_end_zone_candidates") or [],
            "outcome_fields_participate_in_motif_identity": False,
            "same_motif_outcomes_are_variant_context_only": True,
            "member_variant_context_counts": dict(sorted(Counter(variant_context_by_id.values()).items())),
            "divergent_variant_contrast_pair_candidate_n": len(divergence_candidates),
            "representative_first_supported_grammar_divergence": divergence_alignment,
            "motif_similarity_basis": "EXACT_MATCH_ON_OUTCOME_INDEPENDENT_VISIBLE_MORPHOLOGY_SIGNATURE",
            "motif_is_tactical_pattern_truth": False,
            "motif_is_coach_intention_truth": False,
            "motif_is_physical_trajectory_truth": False,
            "claim_ceiling": "MATCH_LOCAL_RECURRING_VISIBLE_PROCESS_MOTIF_CANDIDATE_ONLY",
        })

    motif_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for motif in process_motif_family_candidates:
        motif_index[(
            str(motif.get("team_identity_candidate_id") or ""),
            str(motif.get("process_family_candidate") or ""),
        )].append(motif)
    for rows in motif_index.values():
        rows.sort(key=lambda row: (-int(row.get("member_process_n") or 0), str(row.get("process_motif_family_candidate_id") or "")))

    team_process_profiles: list[dict[str, Any]] = []
    by_team_family: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for signature in signatures:
        team_id = str(signature.get("team_identity_candidate_id") or "")
        family_id = str(signature.get("process_family_candidate") or "UNKNOWN")
        if team_id:
            by_team_family[(team_id, family_id)].append(signature)

    for (team_id, family_id), team_rows in sorted(by_team_family.items()):
        shot_n = sum(row.get("shot_present_annotation_candidate") is True for row in team_rows)
        loss_n = sum(bool(row.get("visible_loss_transition_candidate_present")) for row in team_rows)
        recovery_n = sum(bool(row.get("visible_recovery_transition_candidate_present")) for row in team_rows)
        actor_values = [
            int(row.get("unique_actor_candidate_n") or 0)
            for row in team_rows
            if row.get("unique_actor_candidate_n") is not None
        ]
        layer_values = [
            int(row.get("temporal_layer_n") or 0)
            for row in team_rows
            if row.get("temporal_layer_n") is not None
        ]
        team_process_profiles.append({
            "team_identity_candidate_id": team_id,
            "process_family_candidate": family_id,
            "eligible_process_n": len(team_rows),
            "shot_ending_process_n": shot_n,
            "shot_ending_share_candidate": shot_n / len(team_rows),
            "visible_loss_process_n": loss_n,
            "visible_loss_share_candidate": loss_n / len(team_rows),
            "visible_recovery_process_n": recovery_n,
            "visible_recovery_share_candidate": recovery_n / len(team_rows),
            "mean_actor_spread_candidate": (sum(actor_values) / len(actor_values)) if actor_values else None,
            "mean_temporal_layer_n": (sum(layer_values) / len(layer_values)) if layer_values else None,
            "denominator_basis": "MATCH_LOCAL_ADMITTED_PROCESS_FAMILY_INTERVALS_FOR_TEAM",
            "profile_is_team_quality_truth": False,
            "profile_is_opponent_response_truth": False,
            "profile_is_independent_support": False,
            "claim_ceiling": "MATCH_LOCAL_TEAM_PROCESS_PROFILE_CANDIDATE_ONLY",
        })

    team_ids = sorted({str(row.get("team_identity_candidate_id") or "") for row in signatures if row.get("team_identity_candidate_id")})
    reciprocal_team_process_comparisons: list[dict[str, Any]] = []
    if len(team_ids) == 2:
        team_a, team_b = team_ids
        families = sorted({str(row.get("process_family_candidate") or "UNKNOWN") for row in signatures})
        profile_index = {
            (row["team_identity_candidate_id"], row["process_family_candidate"]): row
            for row in team_process_profiles
        }
        for family_id in families:
            a = profile_index.get((team_a, family_id))
            b = profile_index.get((team_b, family_id))
            if not a or not b:
                continue
            reciprocal_team_process_comparisons.append({
                "process_family_candidate": family_id,
                "team_a_identity_candidate_id": team_a,
                "team_b_identity_candidate_id": team_b,
                "team_a_profile": a,
                "team_b_profile": b,
                "comparison_basis": "SAME_MATCH_SAME_PROCESS_FAMILY_DESCRIPTIVE_PROFILE",
                "difference_is_opponent_response_truth": False,
                "difference_is_tactical_superiority_truth": False,
                "difference_is_causal_truth": False,
                "independent_support_created": False,
                "claim_ceiling": "MATCH_LOCAL_RECIPROCAL_TEAM_PROCESS_COMPARISON_CANDIDATE_ONLY",
            })

    six_phase_team_matrix: list[dict[str, Any]] = []
    if len(team_ids) == 2:
        profile_index = {
            (row["team_identity_candidate_id"], row["process_family_candidate"]): row
            for row in team_process_profiles
        }
        phase_specs = (
            ("ESTABLISHED_ATTACK", "ATTACK", "POSITIONAL_ATTACK_CANDIDATE", "ESTABLISHED_DEFENCE"),
            ("ATTACKING_TRANSITION", "ATTACK", "COUNTERATTACK_CANDIDATE", "DEFENSIVE_TRANSITION"),
            ("ATTACKING_SET_PIECE", "ATTACK", "SET_PIECE_ATTACK_CANDIDATE", "DEFENSIVE_SET_PIECE"),
            ("ESTABLISHED_DEFENCE", "DEFENCE", "POSITIONAL_ATTACK_CANDIDATE", "ESTABLISHED_ATTACK"),
            ("DEFENSIVE_TRANSITION", "DEFENCE", "COUNTERATTACK_CANDIDATE", "ATTACKING_TRANSITION"),
            ("DEFENSIVE_SET_PIECE", "DEFENCE", "SET_PIECE_ATTACK_CANDIDATE", "ATTACKING_SET_PIECE"),
        )
        for team_id in team_ids:
            opponent_id = team_ids[1] if team_id == team_ids[0] else team_ids[0]
            for phase_slot, perspective, family_id, reciprocal_slot in phase_specs:
                source_team_id = team_id if perspective == "ATTACK" else opponent_id
                profile = profile_index.get((source_team_id, family_id))
                observed = isinstance(profile, dict)
                source_rows = by_team_family.get((source_team_id, family_id), [])

                def _mean_signature(key: str) -> float | None:
                    values = [_as_number(row.get(key)) for row in source_rows]
                    observed_values = [value for value in values if value is not None]
                    return (sum(observed_values) / len(observed_values)) if observed_values else None

                start_zone_counts: Counter[str] = Counter()
                end_zone_counts: Counter[str] = Counter()
                for signature in source_rows:
                    start_zones = [str(v) for v in (signature.get("process_start_zone_candidates") or []) if v]
                    end_zones = [str(v) for v in (signature.get("process_end_zone_candidates") or []) if v]
                    if len(start_zones) == 1:
                        start_zone_counts[start_zones[0]] += 1
                    if len(end_zones) == 1:
                        end_zone_counts[end_zones[0]] += 1

                shot_rows = [row for row in source_rows if row.get("shot_present_annotation_candidate") is True]
                non_shot_rows = [row for row in source_rows if row.get("shot_present_annotation_candidate") is not True]
                loss_rows = [row for row in source_rows if row.get("visible_loss_transition_candidate_present")]

                def _representative(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
                    if not rows:
                        return None
                    row = max(
                        rows,
                        key=lambda item: (
                            int(item.get("temporal_layer_n") or 0),
                            int(item.get("unique_actor_candidate_n") or 0),
                            float(item.get("process_interval_duration_candidate") or 0.0),
                        ),
                    )
                    return {
                        "process_development_signature_id": row.get("process_development_signature_id"),
                        "period_candidate": row.get("period_candidate"),
                        "process_start_candidate": row.get("process_start_candidate"),
                        "process_end_candidate": row.get("process_end_candidate"),
                        "duration_candidate": row.get("process_interval_duration_candidate"),
                        "temporal_layer_n": row.get("temporal_layer_n"),
                        "unique_actor_candidate_n": row.get("unique_actor_candidate_n"),
                        "start_zone_candidates": row.get("process_start_zone_candidates") or [],
                        "end_zone_candidates": row.get("process_end_zone_candidates") or [],
                        "action_family_layer_counts": row.get("action_family_layer_counts") or {},
                        "pass_carry_layer_mix": row.get("pass_carry_layer_mix") or {},
                        "visible_zone_transition_candidate_n": row.get("visible_zone_transition_candidate_n"),
                        "visible_loss_transition_candidate_present": bool(row.get("visible_loss_transition_candidate_present")),
                        "visible_recovery_transition_candidate_present": bool(row.get("visible_recovery_transition_candidate_present")),
                        "shot_present_annotation_candidate": row.get("shot_present_annotation_candidate") is True,
                        "replay_is_physical_trajectory_truth": False,
                    }

                six_phase_team_matrix.append({
                    "team_identity_candidate_id": team_id,
                    "opponent_team_identity_candidate_id": opponent_id,
                    "canonical_phase_slot": phase_slot,
                    "reciprocal_phase_slot": reciprocal_slot,
                    "perspective": perspective,
                    "source_process_family_candidate": family_id,
                    "source_process_profile_team_identity_candidate_id": source_team_id,
                    "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE" if observed else "UNOBSERVABLE_WITH_CURRENT_DATA",
                    "eligible_process_n": int(profile.get("eligible_process_n") or 0) if observed else None,
                    "shot_ending_process_n": int(profile.get("shot_ending_process_n") or 0) if observed else None,
                    "visible_loss_process_n": int(profile.get("visible_loss_process_n") or 0) if observed else None,
                    "visible_recovery_process_n": int(profile.get("visible_recovery_process_n") or 0) if observed else None,
                    "shot_ending_share_candidate": profile.get("shot_ending_share_candidate") if observed else None,
                    "visible_loss_share_candidate": profile.get("visible_loss_share_candidate") if observed else None,
                    "visible_recovery_share_candidate": profile.get("visible_recovery_share_candidate") if observed else None,
                    "mean_actor_spread_candidate": profile.get("mean_actor_spread_candidate") if observed else None,
                    "mean_temporal_layer_n": profile.get("mean_temporal_layer_n") if observed else None,
                    "mean_duration_candidate": _mean_signature("process_interval_duration_candidate") if observed else None,
                    "mean_visible_zone_transition_candidate_n": _mean_signature("visible_zone_transition_candidate_n") if observed else None,
                    "single_start_zone_process_n": sum(start_zone_counts.values()) if observed else None,
                    "single_start_zone_distribution": dict(sorted(start_zone_counts.items())) if observed else {},
                    "single_end_zone_process_n": sum(end_zone_counts.values()) if observed else None,
                    "single_end_zone_distribution": dict(sorted(end_zone_counts.items())) if observed else {},
                    "shot_variant_n": len(shot_rows) if observed else None,
                    "non_shot_variant_n": len(non_shot_rows) if observed else None,
                    "loss_variant_n": len(loss_rows) if observed else None,
                    "representative_shot_process": _representative(shot_rows) if observed else None,
                    "representative_non_shot_process": _representative(non_shot_rows) if observed else None,
                    "representative_loss_process": _representative(loss_rows) if observed else None,
                    "anatomy_basis": "ADMITTED_MATCH_LOCAL_PROCESS_DEVELOPMENT_SIGNATURES",
                    "anatomy_is_physical_trajectory_truth": False,
                    "recurring_process_motif_family_count": sum(
                        bool(row.get("recurring_motif_candidate")) for row in motif_index.get((source_team_id, family_id), [])
                    ),
                    "recurring_process_motif_covered_process_n": sum(
                        int(row.get("member_process_n") or 0)
                        for row in motif_index.get((source_team_id, family_id), [])
                        if row.get("recurring_motif_candidate")
                    ),
                    "top_recurring_process_motifs": [
                        dict(row) for row in motif_index.get((source_team_id, family_id), [])
                        if row.get("recurring_motif_candidate")
                    ][:3],
                    "metric_semantics": (
                        "OWN_VISIBLE_PROCESS_PROFILE" if perspective == "ATTACK"
                        else "OPPONENT_VISIBLE_PROCESS_EXPOSURE_PROFILE"
                    ),
                    "defensive_exposure_is_defensive_success_truth": False,
                    "opponent_visible_loss_is_forced_turnover_truth": False,
                    "opponent_non_shot_is_shot_prevention_truth": False,
                    "phase_slot_is_observed_phase_truth": False,
                    "phase_admission_status": "NOT_EVALUATED",
                    "independent_support_created": False,
                    "claim_ceiling": "MATCH_LOCAL_SIX_PHASE_DIRECTIONAL_PROCESS_SURFACE_ONLY",
                })

    variant_context_profiles: list[dict[str, Any]] = []
    by_team_family_variant: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for signature in signatures:
        team_id = str(signature.get("team_identity_candidate_id") or "")
        family_id = str(signature.get("process_family_candidate") or "UNKNOWN")
        if team_id:
            by_team_family_variant[(team_id, family_id)].append(signature)

    for (team_id, family_id), family_rows in sorted(by_team_family_variant.items()):
        shot_rows = [row for row in family_rows if row.get("shot_present_annotation_candidate") is True]
        non_shot_rows = [row for row in family_rows if row.get("shot_present_annotation_candidate") is not True]
        if not shot_rows or not non_shot_rows:
            continue

        def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
            values = [_as_number(row.get(key)) for row in rows]
            observed = [value for value in values if value is not None]
            return (sum(observed) / len(observed)) if observed else None

        def _mix_mean(rows: list[dict[str, Any]], key: str) -> float | None:
            values = [_as_number((row.get("pass_carry_layer_mix") or {}).get(key)) for row in rows]
            observed = [value for value in values if value is not None]
            return (sum(observed) / len(observed)) if observed else None

        shot_n, non_shot_n = len(shot_rows), len(non_shot_rows)
        variant_context_profiles.append({
            "team_identity_candidate_id": team_id,
            "process_family_candidate": family_id,
            "shot_ending_process_n": shot_n,
            "non_shot_process_n": non_shot_n,
            "eligible_process_n": len(family_rows),
            "shot_ending_share_candidate": shot_n / len(family_rows),
            "shot_ending_mean_duration_candidate": _mean(shot_rows, "process_interval_duration_candidate"),
            "non_shot_mean_duration_candidate": _mean(non_shot_rows, "process_interval_duration_candidate"),
            "shot_ending_mean_actor_spread_candidate": _mean(shot_rows, "unique_actor_candidate_n"),
            "non_shot_mean_actor_spread_candidate": _mean(non_shot_rows, "unique_actor_candidate_n"),
            "shot_ending_mean_temporal_layer_n": _mean(shot_rows, "temporal_layer_n"),
            "non_shot_mean_temporal_layer_n": _mean(non_shot_rows, "temporal_layer_n"),
            "shot_ending_mean_pass_share_candidate": _mix_mean(shot_rows, "pass_share_candidate"),
            "non_shot_mean_pass_share_candidate": _mix_mean(non_shot_rows, "pass_share_candidate"),
            "shot_ending_mean_carry_share_candidate": _mix_mean(shot_rows, "carry_share_candidate"),
            "non_shot_mean_carry_share_candidate": _mix_mean(non_shot_rows, "carry_share_candidate"),
            "shot_ending_visible_loss_n": sum(bool(row.get("visible_loss_transition_candidate_present")) for row in shot_rows),
            "non_shot_visible_loss_n": sum(bool(row.get("visible_loss_transition_candidate_present")) for row in non_shot_rows),
            "shot_ending_visible_recovery_n": sum(bool(row.get("visible_recovery_transition_candidate_present")) for row in shot_rows),
            "non_shot_visible_recovery_n": sum(bool(row.get("visible_recovery_transition_candidate_present")) for row in non_shot_rows),
            "comparison_basis": "SAME_TEAM_SAME_PROCESS_FAMILY_SHOT_ENDING_VS_NON_SHOT_VISIBLE_VARIANTS",
            "cross_team_variant_pooling_allowed": False,
            "comparison_is_descriptive_not_causal": True,
            "shot_ending_is_success_truth": False,
            "non_shot_is_failure_truth": False,
            "difference_is_tactical_mechanism_truth": False,
            "independent_support_created": False,
            "claim_ceiling": "MATCH_LOCAL_VISIBLE_PROCESS_VARIANT_CONTEXT_DESCRIPTION_ONLY",
        })

    return {
        "construct_id": "C03_PROCESS_DEVELOPMENT_SIGNATURE",
        "status": "REVIEW_REQUIRED" if signatures else "NOT_APPLICABLE",
        "signature_count": len(signatures),
        "signatures": signatures,
        "process_motif_family_candidate_count": len(process_motif_family_candidates),
        "recurring_process_motif_family_candidate_count": sum(
            bool(row.get("recurring_motif_candidate")) for row in process_motif_family_candidates
        ),
        "recurring_process_motif_covered_process_n": sum(
            int(row.get("member_process_n") or 0)
            for row in process_motif_family_candidates
            if row.get("recurring_motif_candidate")
        ),
        "process_motif_family_candidates": process_motif_family_candidates,
        "process_motif_identity_uses_outcome": False,
        "team_process_profile_count": len(team_process_profiles),
        "team_process_profiles": team_process_profiles,
        "reciprocal_team_process_comparison_count": len(reciprocal_team_process_comparisons),
        "reciprocal_team_process_comparisons": reciprocal_team_process_comparisons,
        "six_phase_team_matrix_expected_direction_count": 12 if len(team_ids) == 2 else 0,
        "six_phase_team_matrix_direction_count": len(six_phase_team_matrix),
        "six_phase_team_matrix_visible_direction_count": sum(
            row.get("observation_state") == "VISIBLE_PROCESS_PROFILE_AVAILABLE" for row in six_phase_team_matrix
        ),
        "six_phase_team_matrix": six_phase_team_matrix,
        "six_phase_team_matrix_is_phase_truth": False,
        "six_phase_team_matrix_is_tactical_superiority_truth": False,
        "team_process_profiles_create_independent_support": False,
        "reciprocal_team_process_comparison_is_opponent_response_truth": False,
        "variant_context_profile_count": len(variant_context_profiles),
        "variant_context_profiles": variant_context_profiles,
        "variant_context_comparison_creates_independent_support": False,
        "variant_context_shot_ending_is_success_truth": False,
        "variant_context_non_shot_is_failure_truth": False,
        "unit_of_analysis": "ADMITTED_PROVIDER_REVIEWED_PROCESS_CONTEXT_INTERVAL",
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "coordinate_path_is_tracking_truth": False,
        "process_morphology_is_phase_truth": False,
        "process_morphology_is_possession_truth": False,
        "process_morphology_is_tactical_plan_truth": False,
        "physical_speed_claim_allowed": False,
        "off_ball_geometry_claim_allowed": False,
        "claim_ceiling": "MATCH_LOCAL_VISIBLE_PROCESS_DEVELOPMENT_SIGNATURE_CANDIDATE_ONLY",
    }


COMPOSITION_FAMILY_SPECS = (
    ("ACTION_OUTCOME_COMPOSITION", "actions", ("actions_successful", "actions_unsuccessful")),
    ("CHALLENGE_OUTCOME_COMPOSITION", "challenges", ("challenges_won", "challenges_unsuccessful")),
    ("FINAL_THIRD_ENTRY_MODE_COMPOSITION", "final_third_entries", ("final_third_entries_through_pass", "final_third_entries_through_carry")),
    ("BALL_LOSS_MODE_COMPOSITION", "lost_balls", ("lost_balls_after_passes", "individual_ball_losses")),
    ("RECEPTION_DEPTH_COMPOSITION", "open_passes_received", ("open_passes_received_in_the_first_third", "open_passes_received_in_the_central_third", "open_passes_received_in_the_final_third")),
    ("SHOT_ORIGIN_COMPOSITION", "shots", ("shots_from_the_penalty_area", "shots_from_outside_the_penalty_area")),
)


def _observed_metric_number(row: dict[str, Any], metric_key: str) -> float | None:
    metric = (row.get("metric_values") or {}).get(metric_key)
    if not isinstance(metric, dict) or metric.get("value_status") != "OBSERVED":
        return None
    return _as_number(metric.get("raw_value"))


def _construct_c04(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Expose algebraically closed XLSX total+composition families without scalar quality scoring."""
    profiles: list[dict[str, Any]] = []
    family_audit: dict[str, dict[str, int]] = {
        family_id: {"eligible_complete_n": 0, "closed_n": 0, "mismatch_n": 0}
        for family_id, _, _ in COMPOSITION_FAMILY_SPECS
    }
    residual_profiles: list[dict[str, Any]] = []
    tolerance = 1e-6

    for row in rows:
        identity = row.get("identity_candidates") or {}
        row_id = str(row.get("row_projection_id") or "").strip()
        if not row_id:
            continue
        entity = identity.get("player_raw_candidate") or identity.get("team_raw_candidate")
        for family_id, total_key, component_keys in COMPOSITION_FAMILY_SPECS:
            total = _observed_metric_number(row, total_key)
            components = {key: _observed_metric_number(row, key) for key in component_keys}
            if total is None or any(value is None for value in components.values()):
                continue
            family_audit[family_id]["eligible_complete_n"] += 1
            component_sum = sum(float(value) for value in components.values() if value is not None)
            delta = total - component_sum
            closed = abs(delta) <= tolerance
            family_audit[family_id]["closed_n" if closed else "mismatch_n"] += 1
            shares = None
            balance = None
            if closed and total > 0:
                shares = {key: float(value) / total for key, value in components.items() if value is not None}
                if len(component_keys) == 2:
                    first, second = component_keys
                    balance = (float(components[first]) - float(components[second])) / total
            profiles.append({
                "composition_profile_id": "xcp_" + hashlib.sha256(
                    f"{row_id}|{family_id}".encode("utf-8")
                ).hexdigest()[:24],
                "row_projection_id": row_id,
                "entity_candidate": entity,
                "player_candidate": identity.get("player_raw_candidate"),
                "team_candidate": identity.get("team_raw_candidate"),
                "family_id": family_id,
                "total_metric_key": total_key,
                "component_metric_keys": list(component_keys),
                "total_value": total,
                "component_values": components,
                "component_sum": component_sum,
                "closure_delta": delta,
                "closure_state": "IDENTITY_OBSERVED_WITHIN_TOLERANCE" if closed else "DEFINITION_OR_DATA_MISMATCH_REVIEW",
                "composition_shares": shares,
                "component_balance_index_candidate": balance,
                "component_balance_has_quality_direction": False,
                "total_exposure_preserved_separately": True,
                "percentage_columns_are_independent_indicators": False,
                "derived_composition_adds_independent_evidence": False,
                "aggregate_row_is_action_identity": False,
                "claim_ceiling": "MATCH_LOCAL_XLSX_AGGREGATE_COMPOSITION_DESCRIPTION_ONLY",
            })

        xgt = _observed_metric_number(row, "xgt_xg_while_player_is_on_the_pitch")
        xgopp = _observed_metric_number(row, "xgopp_opponent_s_xg_while_player_is_on_the_pitch")
        nxg = _observed_metric_number(row, "nxg_net_xg_difference_between_xgt_and_xgopp")
        if None not in (xgt, xgopp, nxg):
            expected = float(xgt) - float(xgopp)
            delta = float(nxg) - expected
            residual_profiles.append({
                "residual_profile_id": "xrp_ctx_" + hashlib.sha256(row_id.encode("utf-8")).hexdigest()[:24],
                "row_projection_id": row_id,
                "entity_candidate": entity,
                "xgt": xgt,
                "xgopp": xgopp,
                "nxg_observed": nxg,
                "nxg_recomputed": expected,
                "closure_delta": delta,
                "closure_state": "IDENTITY_OBSERVED_WITHIN_TOLERANCE" if abs(delta) <= tolerance else "DEFINITION_OR_DATA_MISMATCH_REVIEW",
                "provider_model_output_context_only": True,
                "player_causal_contribution_truth": False,
                "player_quality_truth": False,
                "claim_ceiling": "PROVIDER_MODEL_MATCH_CONTEXT_RESIDUAL_ONLY",
            })

    closed_profiles = [row for row in profiles if row["closure_state"] == "IDENTITY_OBSERVED_WITHIN_TOLERANCE"]
    return {
        "construct_id": "C04_XLSX_COMPOSITION_TOTAL_INTELLIGENCE",
        "status": "REVIEW_REQUIRED" if profiles or residual_profiles else "NOT_APPLICABLE",
        "composition_profile_count": len(profiles),
        "closed_composition_profile_count": len(closed_profiles),
        "composition_profiles": profiles,
        "family_closure_audit": family_audit,
        "model_context_residual_profile_count": len(residual_profiles),
        "model_context_residual_profiles": residual_profiles,
        "total_exposure_and_composition_are_separate_axes": True,
        "no_scalar_player_quality_score_created": True,
        "aggregate_is_not_action_identity": True,
        "composition_is_not_independent_evidence": True,
        "claim_ceiling": "MATCH_LOCAL_XLSX_AGGREGATE_COMPOSITION_AND_MODEL_CONTEXT_DESCRIPTION_ONLY",
    }


def _render_txt(payload: dict[str, Any]) -> str:
    entity = payload.get("entity_views") or {}
    c01 = payload.get("constructs", {}).get("C01") or {}
    c02 = payload.get("constructs", {}).get("C02") or {}
    c03 = payload.get("constructs", {}).get("C03") or {}
    c04 = payload.get("constructs", {}).get("C04") or {}
    lines = [
        "HPFA RICH MULTIFORMAT ANALYSIS LATTICE V1",
        "==========================================",
        f"status={payload.get('status')}",
        f"inventory_status={payload.get('inventory_status')}",
        f"xlsx_audit_status={payload.get('xlsx_audit_status')}",
        f"xlsx_projection_status={payload.get('xlsx_projection_status')}",
        f"xlsx_projected_row_count={payload.get('xlsx_projected_row_count')}",
        f"primitive_metric_count={len(payload.get('primitive_metrics') or [])}",
        f"phase_state_candidate_count={len(payload.get('phase_state_candidates') or [])}",
        f"player_view_candidate_count={len(entity.get('player_view_candidates') or [])}",
        f"team_view_candidate_count={len(entity.get('team_view_candidates') or [])}",
        f"goalkeeper_view_candidate_count={len(entity.get('goalkeeper_view_candidates') or [])}",
        f"C01_status={c01.get('status')}",
        f"C01_progression_aggregate_ref_count={c01.get('progression_aggregate_ref_count')}",
        f"C01_terminal_aggregate_ref_count={c01.get('terminal_aggregate_ref_count')}",
        f"C01_comparable_scope_pair_count={c01.get('comparable_scope_pair_count')}",
        f"C01_visible_shot_candidate_count={c01.get('visible_shot_candidate_count')}",
        f"C01_review_reason={c01.get('review_reason')}",
        f"C02_status={c02.get('status')}",
        f"C02_argument_candidate_count={c02.get('argument_candidate_count')}",
        f"C02_xlsx_actor_binding_count={c02.get('xlsx_actor_binding_count')}",
        f"C02_review_reason={c02.get('review_reason')}",
        f"C03_status={c03.get('status')}",
        f"C03_signature_count={c03.get('signature_count')}",
        f"C04_status={c04.get('status')}",
        f"C04_closed_composition_profile_count={c04.get('closed_composition_profile_count')}",
        f"C04_model_context_residual_profile_count={c04.get('model_context_residual_profile_count')}",
        f"hard_block_hits={payload.get('hard_block_hits') or []}",
        f"review_hits={payload.get('review_hits') or []}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "phase_truth=false",
        "possession_truth=false",
        "sequence_truth=false",
        "tactical_truth=false",
        "production_release=false",
        "",
    ]
    return "\n".join(lines)


def run_rich_lane(
    active_match_dir: str | Path,
    out_dir: str | Path,
    *,
    expected_snapshot_id: str | None,
    match_surface_binding_id: str | None,
) -> dict[str, Any]:
    active_match = Path(active_match_dir).expanduser().resolve(strict=False)
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    before = _snapshot(active_match)
    if expected_snapshot_id and before != expected_snapshot_id:
        hard_blocks.append("active_match_surface_snapshot_mismatch_before_rich_multiformat_lane")

    inventory_report = inventory.build_inventory(active_match) if not hard_blocks else {}
    if inventory_report.get("status") == "FAIL_CLOSED":
        hard_blocks.append("multiformat_inventory_fail_closed")
    elif inventory_report.get("status") == "REVIEW_REQUIRED":
        review_hits.append("multiformat_inventory_review_required")

    xlsx_audit = xlsx.build_xlsx_surface_audit(active_match, inventory_report) if inventory_report else {}
    if xlsx_audit.get("status") == "FAIL_CLOSED":
        hard_blocks.append("xlsx_surface_audit_fail_closed")
    elif xlsx_audit.get("status") == "REVIEW_REQUIRED":
        review_hits.append("xlsx_surface_audit_review_required")

    projection = build_projection(
        active_match,
        inventory_report,
        xlsx_audit,
        match_surface_binding_id=match_surface_binding_id,
    ) if xlsx_audit else {}
    if projection.get("status") == "FAIL_CLOSED":
        hard_blocks.append("xlsx_entity_metric_projection_fail_closed")
    elif projection.get("status") == "REVIEW_REQUIRED":
        review_hits.append("xlsx_entity_metric_projection_review_required")

    after = _snapshot(active_match)
    if expected_snapshot_id and after != expected_snapshot_id:
        hard_blocks.append("active_match_surface_snapshot_mismatch_after_rich_multiformat_lane")

    features = _load_json(output / "episode_feature_vector_lite_v1.json")
    temporal = _load_json(output / "temporal_episode_signature_lite_v1.json")
    rows = _flatten_projection(projection)
    entity_views = _entity_views(rows)
    primitives = _primitive_metrics(features, entity_views)
    phase_states = _phase_state_candidates(features)
    c01 = _construct_c01(rows, features)
    if c01.get("status") == "REVIEW_REQUIRED":
        review_hits.append("C01_progression_terminal_construct_review_required")

    identity_payload = _load_json(output / IDENTITY_JSON)
    process_participation_payload = _load_json(output / PROCESS_PARTICIPATION_JSON)
    c02 = _construct_c02(rows, identity_payload, process_participation_payload)
    if c02.get("status") == "REVIEW_REQUIRED":
        review_hits.append("C02_process_participant_outcome_association_review_available")

    occurrence_transition_payload = _load_json(output / OCCURRENCE_STATE_TRANSITION_JSON)
    spatial_transition_payload = _load_json(output / SPATIAL_TRANSITION_JSON)
    c03 = _construct_c03(process_participation_payload, occurrence_transition_payload, spatial_transition_payload)
    if c03.get("status") == "REVIEW_REQUIRED":
        review_hits.append("C03_process_development_signature_review_available")

    c04 = _construct_c04(rows)
    if c04.get("status") == "REVIEW_REQUIRED":
        review_hits.append("C04_xlsx_composition_total_intelligence_review_available")

    packet_candidates = [c01["packet_candidate"]] if c01.get("packet_candidate") else []
    packet_candidates.extend(
        row for row in (c02.get("packet_candidates") or []) if isinstance(row, dict)
    )
    status = "FAIL_CLOSED" if hard_blocks else "REVIEW_REQUIRED" if review_hits else "SMOKE_PASS"
    payload = {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "BLOCK_RICH_LANE" if hard_blocks else "RICH_LATTICE_AVAILABLE_FOR_C4",
        "input_surface_snapshot_id": before,
        "surface_snapshot_bound": bool(not expected_snapshot_id or after == expected_snapshot_id),
        "inventory_status": inventory_report.get("status"),
        "xlsx_audit_status": xlsx_audit.get("status"),
        "xlsx_projection_status": projection.get("status"),
        "xlsx_projected_row_count": projection.get("row_projection_count", 0),
        "multiformat_inventory": inventory_report,
        "xlsx_surface_audit": xlsx_audit,
        "xlsx_entity_metric_projection": projection,
        "primitive_metrics": primitives,
        "football_ontology_contract": _football_ontology_contract(),
        "constructs": {"C01": c01, "C02": c02, "C03": c03, "C04": c04},
        "phase_state_candidates": phase_states,
        "analysis_lattice": {
            "MICRO": {
                "player_view_candidates": entity_views.get("player_view_candidates"),
                "goalkeeper_view_candidates": entity_views.get("goalkeeper_view_candidates"),
                "primitive_metrics": primitives,
            },
            "MEZZO": {
                "episode_feature_vectors": features.get("episode_feature_vectors") or [],
                "phase_state_candidates": phase_states,
                "temporal_episode_signatures": temporal.get("temporal_episode_signatures") or temporal.get("episode_signatures") or [],
                "process_development_signatures": c03.get("signatures") or [],
            },
            "MACRO": {
                "team_view_candidates": entity_views.get("team_view_candidates"),
                "action_family_candidate_counts": features.get("eligible_action_family_candidate_counts") or {},
                "metric_label_observation_counts": entity_views.get("metric_label_observation_counts") or {},
                "constructs": {
                    "C01": {key: value for key, value in c01.items() if key not in {"progression_metric_refs", "terminal_metric_refs", "comparable_scope_pairs", "packet_candidate"}},
                    "C02": {key: value for key, value in c02.items() if key not in {"actor_argument_candidates", "dyad_argument_candidates", "process_family_profiles", "packet_candidates"}},
                    "C03": {key: value for key, value in c03.items() if key != "signatures"},
                    "C04": {key: value for key, value in c04.items() if key not in {"composition_profiles", "model_context_residual_profiles"}},
                },
            },
        },
        "entity_views": entity_views,
        "c4_packet_candidates": packet_candidates,
        "hard_block_hits": list(dict.fromkeys(hard_blocks)),
        "review_hits": list(dict.fromkeys(review_hits)),
        "format_fusion_is_independent_evidence_vote": False,
        "xlsx_row_projection_is_event_truth": False,
        "construct_truth": False,
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    paths = {
        "lattice_json": output / OUTPUT_JSON,
        "lattice_txt": output / OUTPUT_TXT,
        "xlsx_audit_json": output / XLSX_AUDIT_JSON,
        "xlsx_audit_txt": output / XLSX_AUDIT_TXT,
        "xlsx_audit_analyst": output / XLSX_AUDIT_ANALYST,
        "xlsx_projection_json": output / XLSX_PROJECTION_JSON,
        "xlsx_projection_txt": output / XLSX_PROJECTION_TXT,
    }
    paths["xlsx_audit_json"].write_text(json.dumps(xlsx_audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["xlsx_audit_txt"].write_text(xlsx.render_summary(xlsx_audit), encoding="utf-8")
    paths["xlsx_audit_analyst"].write_text(xlsx.render_analyst(xlsx_audit), encoding="utf-8")
    paths["xlsx_projection_json"].write_text(json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["xlsx_projection_txt"].write_text(
        "\n".join([
            "HPFA XLSX ENTITY-METRIC ROW PROJECTION V1",
            f"status={projection.get('status')}",
            f"xlsx_file_count={projection.get('xlsx_file_count')}",
            f"row_projection_count={projection.get('row_projection_count')}",
            f"hard_block_hits={projection.get('hard_block_hits') or []}",
            f"review_hits={projection.get('review_hits') or []}",
            "canonical_event_count=UNKNOWN",
            "true_action_count=UNKNOWN",
            "production_release=false",
            "",
        ]),
        encoding="utf-8",
    )
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    payload["current_invocation_artifacts"] = [str(path) for path in paths.values()]
    paths["lattice_json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["lattice_txt"].write_text(_render_txt(payload), encoding="utf-8")
    return payload
