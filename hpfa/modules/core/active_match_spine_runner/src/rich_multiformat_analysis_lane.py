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
    return surface_snapshot_id(root)


def _flatten_projection(projection: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for file_row in projection.get("files", []) or []
        for sheet in file_row.get("sheets", []) or []
        for row in sheet.get("rows", []) or []
        if isinstance(row, dict)
    ]


_GOALKEEPER_SCHEMA_SIGNALS = frozenset({"shots_faced", "shots_on_target_faced", "shots_saved", "goals_conceded", "sweeping_actions", "penalties_saved"})

def _xlsx_entity_role_candidate(row: dict[str, Any]) -> str:
    # Infer aggregate entity role from schema/content, never filenames or names.
    role = str(row.get("source_role") or "").upper()
    if "GOALKEEPER" in role:
        return "GOALKEEPER"
    if "TEAM" in role:
        return "TEAM"
    metric_keys = {str(key).strip().casefold() for key in (row.get("metric_values") or {}) if str(key).strip()}
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
        "claim_ceiling": "MATCH_LOCAL_PROCESS_OUTCOME_ASSOCIATION_CANDIDATE_ONLY",
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
    rate = (shot_n / support_n) if support_n else None
    baseline = (baseline_shot_n / baseline_n) if baseline_n else None
    lift = (rate / baseline) if rate is not None and baseline not in (None, 0) else None
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
        "shot_ending_n": shot_n,
        "not_target_annotated_n": len(no_shot_rows),
        "involved_without_target_annotation_refs": [row["process_ref"] for row in no_shot_rows],
        "not_target_annotated_is_resolved_non_target": False,
        "legacy_non_shot_fields_deprecation_state": "DEPRECATED_COMPATIBILITY_ONLY",
        "legacy_non_shot_fields_are_resolved_non_target": False,
        "non_shot_n": len(no_shot_rows),
        "conditional_shot_frequency": rate,
        "match_local_baseline_shot_frequency": baseline,
        "match_local_lift": lift,
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
        "claim_ceiling": "MATCH_LOCAL_PROCESS_OUTCOME_ASSOCIATION_CANDIDATE_ONLY",
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
            "claim_ceiling": "MATCH_LOCAL_PROCESS_OUTCOME_ASSOCIATION_CANDIDATE_ONLY",
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
    representative_actor = all_actor_candidates[0] if all_actor_candidates else None
    representative_dyad = all_dyad_candidates[0] if all_dyad_candidates else None

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
        "claim_ceiling": "MATCH_LOCAL_PROCESS_OUTCOME_ASSOCIATION_CANDIDATE_ONLY",
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
            "process_start_zone_candidates": start_zone_candidates,
            "process_end_zone_candidates": end_zone_candidates,
            "zone_layer_path_candidates": zone_layer_path_candidates,
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

    return {
        "construct_id": "C03_PROCESS_DEVELOPMENT_SIGNATURE",
        "status": "REVIEW_REQUIRED" if signatures else "NOT_APPLICABLE",
        "signature_count": len(signatures),
        "signatures": signatures,
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
                    "C02": {key: value for key, value in c02.items() if key not in {"actor_argument_candidates", "dyad_argument_candidates", "process_family_profiles"}},
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
