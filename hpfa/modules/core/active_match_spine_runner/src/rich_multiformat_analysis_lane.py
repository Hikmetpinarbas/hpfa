from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from hpfa.modules.core.multiformat_file_inventory_lite.src import multiformat_file_inventory as inventory
from hpfa.modules.core.xlsx_surface_reader_lite.src.xlsx_surface_reader import native_reader as xlsx
from hpfa.modules.core.xlsx_entity_metric_row_projection_lite.src.xlsx_entity_metric_row_projection import build_projection

MODULE_ID = "rich_multiformat_analysis_lattice_v1"
OUTPUT_JSON = "rich_multiformat_analysis_lattice_v1.json"
OUTPUT_TXT = "rich_multiformat_analysis_lattice_v1.txt"
XLSX_AUDIT_JSON = "xlsx_surface_audit_lite_v1.json"
XLSX_AUDIT_TXT = "xlsx_surface_audit_lite_v1.txt"
XLSX_AUDIT_ANALYST = "xlsx_surface_analyst_audit_lite_v1.txt"
XLSX_PROJECTION_JSON = "xlsx_entity_metric_row_projection_lite_v1.json"
XLSX_PROJECTION_TXT = "xlsx_entity_metric_row_projection_lite_v1.txt"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot(root: Path) -> str:
    records = []
    if root.is_dir():
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if path.is_file():
                records.append((path.relative_to(root).as_posix(), path.stat().st_size, _hash_file(path)))
    return hashlib.sha256(json.dumps(records, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _flatten_projection(projection: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for file_row in projection.get("files", []) or []
        for sheet in file_row.get("sheets", []) or []
        for row in sheet.get("rows", []) or []
        if isinstance(row, dict)
    ]


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
        role = str(row.get("source_role") or "").upper()
        if "GOALKEEPER" in role:
            goalkeepers.append(compact)
        elif identity.get("player_raw_candidate") not in (None, ""):
            players.append(compact)
        elif identity.get("team_raw_candidate") not in (None, "") or "TEAM" in role:
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


def _progression_pool_p02(
    features: dict[str, Any],
    temporal: dict[str, Any],
    episode: dict[str, Any] | None = None,
    consequence: dict[str, Any] | None = None,
    semantics: dict[str, Any] | None = None,
    identities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project current episode/temporal outputs into a claim-bounded P02 pool.

    This is a projection, not a new occurrence, sequence or reasoning engine.
    Route/directness fields remain not evaluated until an ordered coordinate
    chain is explicitly bound.
    """
    episode = episode or {}
    consequence = consequence or {}
    semantics = semantics or {}
    identities = identities or {}
    temporal_by_episode = {
        str(row.get("episode_candidate_id")): row
        for row in (temporal.get("temporal_episode_signatures") or [])
        if isinstance(row, dict) and row.get("episode_candidate_id")
    }
    episode_by_id = {
        str(row.get("episode_candidate_id")): row
        for row in (episode.get("episode_candidates") or [])
        if isinstance(row, dict) and row.get("episode_candidate_id")
    }
    time_layer_by_id = {
        str(row.get("episode_time_layer_candidate_id")): row
        for row in (episode.get("episode_time_layer_candidates") or [])
        if isinstance(row, dict) and row.get("episode_time_layer_candidate_id")
    }
    consequence_records = [
        row
        for row in (consequence.get("trackable_action_consequence_candidates") or [])
        if isinstance(row, dict)
    ]
    team_identity_alias_map: dict[str, str] = {}
    ambiguous_team_aliases: set[str] = set()
    for candidate in identities.get("team_identity_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("decision_state") or "") != "TEAM_IDENTITY_CANDIDATE_BOUND":
            continue
        team_id = str(candidate.get("team_identity_candidate_id") or "")
        if not team_id:
            continue
        for alias in candidate.get("team_aliases_raw") or []:
            key = str(alias or "").strip().casefold()
            if not key:
                continue
            if key in team_identity_alias_map and team_identity_alias_map[key] != team_id:
                ambiguous_team_aliases.add(key)
                team_identity_alias_map.pop(key, None)
                continue
            if key not in ambiguous_team_aliases:
                team_identity_alias_map[key] = team_id

    semantic_by_context = {
        str(row.get("context_id")): row
        for row in (semantics.get("context_action_semantic_records") or [])
        if isinstance(row, dict) and row.get("context_id")
    }
    finding_atoms: list[dict[str, Any]] = []
    pool_items: list[dict[str, Any]] = []
    team_pool_items: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []

    for card in features.get("episode_feature_vectors") or []:
        if not isinstance(card, dict):
            continue
        episode_id = str(card.get("episode_candidate_id") or "")
        if not episode_id:
            continue
        feature_id = str(card.get("episode_feature_vector_id") or f"efv:{episode_id}")
        temporal_row = temporal_by_episode.get(episode_id) or {}
        temporal_id = str(temporal_row.get("temporal_episode_signature_id") or "")
        dependency_root = f"episode_feature:{episode_id}"
        atom_ids: list[str] = []

        def add_atom(kind: str, value: Any, unit: str, semantic_role: str) -> None:
            atom_id = f"fa_p02:{episode_id}:{kind}"
            atom_ids.append(atom_id)
            finding_atoms.append({
                "finding_atom_id": atom_id,
                "producer_module_id": MODULE_ID,
                "producer_output_id": feature_id,
                "source_ref_ids": [feature_id] + ([temporal_id] if temporal_id else []),
                "surface_ref_ids": ["episode_feature_vector_lite_v1"] + (["temporal_episode_signature_lite_v1"] if temporal_id else []),
                "observation_ref_ids": list(card.get("context_refs") or []),
                "dependency_root": dependency_root,
                "provenance_root": "episode_feature_vector_lite_v1",
                "observation_family": "PROCESS/PARTICIPATION",
                "semantic_role": semantic_role,
                "epistemic_state": "DERIVED_OBSERVATION",
                "claim_ceiling": "P02_EPISODE_DESCRIPTIVE_CANDIDATE_ONLY",
                "provider_semantics_status": "PRESERVED_UPSTREAM",
                "pool_candidates": ["P02_PROGRESSION"],
                "scale": "MEZZO",
                "game_dimensions": ["TIME", "ACTION", "PROCESS", "CONTEXT"],
                "episode_candidate_id": episode_id,
                "period_candidate": card.get("period_candidate"),
                "value": value,
                "unit": unit,
                "dependency_state": "DEPENDENT_OR_PARTIAL_LINEAGE",
                "independent_support_vote": False,
                "uncertainty_state": "VISIBLE_CANDIDATE_ONLY",
                "transformation_state": "SEMANTICALLY_ENRICHED",
                "transformation_id": f"p02_projection:{episode_id}",
                "information_delta_class": "ENRICHED",
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            })

        duration = card.get("duration_seconds_candidate")
        eligible_actions = int(card.get("eligible_action_candidate_count") or 0)
        same_time_layers = int(card.get("same_time_unordered_layer_count") or 0)
        zone_counts = dict(card.get("eligible_action_zone_counts") or {})
        channel_counts = dict(card.get("eligible_action_channel_counts") or {})
        family_counts = dict(card.get("action_family_counts") or {})
        shot_count = int(card.get("shot_candidate_count") or 0)
        turnover_count = int(card.get("turnover_candidate_count") or 0)
        recovery_count = int(card.get("recovery_candidate_count") or 0)

        add_atom("duration", duration, "seconds_candidate", "EPISODE_DURATION_CANDIDATE")
        add_atom("action_station_burden", eligible_actions, "action_station_candidate_count", "ACTION_STATION_BURDEN_CANDIDATE")
        add_atom("zone_distribution", zone_counts, "candidate_count_by_zone", "ZONE_DISTRIBUTION_CANDIDATE")
        add_atom("channel_distribution", channel_counts, "candidate_count_by_channel", "CHANNEL_DISTRIBUTION_CANDIDATE")
        add_atom(
            "terminal_activity",
            {"shot": shot_count, "turnover": turnover_count, "recovery": recovery_count},
            "candidate_counts",
            "VISIBLE_TERMINAL_AND_TRANSITION_ACTIVITY_CANDIDATE",
        )
        if temporal_row:
            add_atom(
                "temporal_change",
                {
                    "comparison_status": temporal_row.get("comparison_status"),
                    "eligible_action_rate_delta_per_minute": temporal_row.get("eligible_action_rate_delta_per_minute"),
                    "zone_share_shift_candidate": temporal_row.get("zone_share_shift_candidate"),
                    "channel_share_shift_candidate": temporal_row.get("channel_share_shift_candidate"),
                },
                "temporal_signature_candidate",
                "TEMPORAL_COMPARISON_CANDIDATE",
            )

        final_third_count = int(zone_counts.get("FINAL_THIRD") or zone_counts.get("final_third") or 0)

        episode_row = episode_by_id.get(episode_id) or {}
        ordered_layers = [
            time_layer_by_id.get(str(layer_ref))
            for layer_ref in (episode_row.get("time_layer_refs") or [])
        ]
        ordered_layers = [row for row in ordered_layers if isinstance(row, dict)]

        zone_station_path: list[dict[str, Any]] = []
        zone_transition_candidates: list[dict[str, Any]] = []
        for layer in ordered_layers:
            eligible_zone_counts = {
                str(key): int(value or 0)
                for key, value in (layer.get("eligible_action_zone_candidate_counts") or {}).items()
                if str(key) not in {"", "UNKNOWN_ZONE"} and int(value or 0) > 0
            }
            unique_zones = sorted(eligible_zone_counts)
            if len(unique_zones) != 1:
                continue
            zone_station_path.append({
                "time_layer_ref": layer.get("episode_time_layer_candidate_id"),
                "second_candidate": layer.get("second_candidate"),
                "zone_candidate": unique_zones[0],
                "same_time_unordered": bool(layer.get("same_time_unordered")),
                "internal_order_asserted": False,
            })

        for left, right in zip(zone_station_path, zone_station_path[1:]):
            if left.get("second_candidate") == right.get("second_candidate"):
                continue
            zone_transition_candidates.append({
                "from_zone": left.get("zone_candidate"),
                "to_zone": right.get("zone_candidate"),
                "from_second_candidate": left.get("second_candidate"),
                "to_second_candidate": right.get("second_candidate"),
                "same_timestamp_transition": False,
                "transition_is_physical_trajectory_truth": False,
            })

        compressed_zone_stations: list[str] = []
        for station in zone_station_path:
            zone = str(station.get("zone_candidate") or "")
            if not zone:
                continue
            if not compressed_zone_stations or compressed_zone_stations[-1] != zone:
                compressed_zone_stations.append(zone)

        start_zone_candidate = compressed_zone_stations[0] if compressed_zone_stations else None
        end_zone_candidate = compressed_zone_stations[-1] if compressed_zone_stations else None
        zone_order = {"DEFENSIVE_THIRD": 0, "MIDDLE_THIRD": 1, "FINAL_THIRD": 2}
        zone_advancement_steps = None
        if start_zone_candidate in zone_order and end_zone_candidate in zone_order:
            zone_advancement_steps = zone_order[end_zone_candidate] - zone_order[start_zone_candidate]

        occurrence_summary_by_id: dict[str, dict[str, Any]] = {}
        episode_start = card.get("start_second_candidate")
        episode_end = card.get("end_second_candidate")
        episode_period = str(card.get("period_candidate") or "")
        if isinstance(episode_start, (int, float)) and isinstance(episode_end, (int, float)):
            for record in consequence_records:
                if str(record.get("period_candidate") or "") != episode_period:
                    continue
                try:
                    anchor_second = float(record.get("anchor_start_candidate"))
                except (TypeError, ValueError):
                    continue
                if anchor_second < float(episode_start) or anchor_second > float(episode_end):
                    continue
                occurrence_ids = [
                    str(value)
                    for value in (record.get("supporting_action_occurrence_candidate_ids") or [])
                    if str(value).strip()
                ]
                for occurrence_id in occurrence_ids:
                    summary = occurrence_summary_by_id.setdefault(
                        occurrence_id,
                        {
                            "visible_follow_up": False,
                            "terminal_support_visible": False,
                            "opponent_follow_up_visible": False,
                            "same_team_follow_up_visible": False,
                            "consequence_candidate_ids": set(),
                        },
                    )
                    if record.get("occurrence_visible_consequence_support") is True or record.get("visible_follow_up_trace_ids"):
                        summary["visible_follow_up"] = True
                    if record.get("terminal_outcome_support_visible") is True:
                        summary["terminal_support_visible"] = True
                    signals = {str(value) for value in (record.get("consequence_signal_candidates") or [])}
                    if "OPPONENT_FOLLOW_UP_VISIBLE" in signals:
                        summary["opponent_follow_up_visible"] = True
                    if "SAME_TEAM_FOLLOW_UP_VISIBLE" in signals:
                        summary["same_team_follow_up_visible"] = True
                    candidate_id = str(record.get("trackable_action_consequence_candidate_id") or "")
                    if candidate_id:
                        summary["consequence_candidate_ids"].add(candidate_id)

        occurrence_ids = sorted(occurrence_summary_by_id)
        visible_follow_up_occurrence_ids = sorted(
            occurrence_id
            for occurrence_id, summary in occurrence_summary_by_id.items()
            if summary["visible_follow_up"]
        )
        terminal_support_occurrence_ids = sorted(
            occurrence_id
            for occurrence_id, summary in occurrence_summary_by_id.items()
            if summary["terminal_support_visible"]
        )
        opponent_follow_up_occurrence_ids = sorted(
            occurrence_id
            for occurrence_id, summary in occurrence_summary_by_id.items()
            if summary["opponent_follow_up_visible"]
        )
        same_team_follow_up_occurrence_ids = sorted(
            occurrence_id
            for occurrence_id, summary in occurrence_summary_by_id.items()
            if summary["same_team_follow_up_visible"]
        )

        action_rate = None
        if isinstance(duration, (int, float)) and duration > 0:
            action_rate = round(eligible_actions / float(duration), 6)

        pool_status = "DEGRADED"
        unresolved = [
            "ordered_coordinate_chain_not_bound",
            "actor_station_identity_not_bound",
            "relation_station_identity_not_bound",
            "opponent_response_not_bound_at_p02_projection_stage",
        ]
        if not compressed_zone_stations:
            unresolved.append("start_end_zone_transition_not_bound")
        if not occurrence_ids:
            unresolved.append("occurrence_consequence_binding_not_available_for_episode")
        if not opponent_follow_up_occurrence_ids:
            unresolved.append("visible_opponent_follow_up_not_resolved_for_episode")
        pool_item_id = f"p02:{episode_id}"
        team_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for context_ref in card.get("context_refs") or []:
            semantic_row = semantic_by_context.get(str(context_ref))
            if not isinstance(semantic_row, dict):
                continue
            if semantic_row.get("action_occurrence_eligible") is not True:
                continue
            team_candidate = str(semantic_row.get("context_team_candidate") or "").strip()
            if team_candidate.casefold() in {"", "unknown", "none", "null", "unknown_team"}:
                continue
            team_rows[team_candidate].append(semantic_row)

        for team_candidate, rows_for_team in sorted(team_rows.items()):
            team_family_counts = Counter(
                str(row.get("provider_action_family_candidate") or "UNKNOWN")
                for row in rows_for_team
            )
            team_zone_counts = Counter(
                str(row.get("context_zone_candidate") or "UNKNOWN_ZONE")
                for row in rows_for_team
            )
            team_channel_counts = Counter(
                str(row.get("context_channel_candidate") or "UNKNOWN_CHANNEL")
                for row in rows_for_team
            )
            team_context_refs = sorted(
                str(row.get("context_id"))
                for row in rows_for_team
                if row.get("context_id")
            )
            team_dependency_root = f"episode_team_feature:{episode_id}:{team_candidate}"
            team_identity_candidate_id = team_identity_alias_map.get(team_candidate.casefold())

            team_consequence_summary_by_occurrence: dict[str, dict[str, Any]] = {}
            if team_identity_candidate_id and isinstance(episode_start, (int, float)) and isinstance(episode_end, (int, float)):
                for record in consequence_records:
                    if str(record.get("period_candidate") or "") != episode_period:
                        continue
                    if str(record.get("team_identity_candidate_id") or "") != team_identity_candidate_id:
                        continue
                    try:
                        anchor_second = float(record.get("anchor_start_candidate"))
                    except (TypeError, ValueError):
                        continue
                    if anchor_second < float(episode_start) or anchor_second > float(episode_end):
                        continue
                    for occurrence_id in [
                        str(value)
                        for value in (record.get("supporting_action_occurrence_candidate_ids") or [])
                        if str(value).strip()
                    ]:
                        summary = team_consequence_summary_by_occurrence.setdefault(
                            occurrence_id,
                            {
                                "visible_follow_up": False,
                                "terminal_support_visible": False,
                                "opponent_follow_up_visible": False,
                                "same_team_follow_up_visible": False,
                            },
                        )
                        if record.get("occurrence_visible_consequence_support") is True or record.get("visible_follow_up_trace_ids"):
                            summary["visible_follow_up"] = True
                        if record.get("terminal_outcome_support_visible") is True:
                            summary["terminal_support_visible"] = True
                        signals = {str(value) for value in (record.get("consequence_signal_candidates") or [])}
                        if "OPPONENT_FOLLOW_UP_VISIBLE" in signals:
                            summary["opponent_follow_up_visible"] = True
                        if "SAME_TEAM_FOLLOW_UP_VISIBLE" in signals:
                            summary["same_team_follow_up_visible"] = True

            team_occurrence_ids = sorted(team_consequence_summary_by_occurrence)
            team_visible_follow_up_ids = sorted(
                oid for oid, summary in team_consequence_summary_by_occurrence.items()
                if summary["visible_follow_up"]
            )
            team_terminal_support_ids = sorted(
                oid for oid, summary in team_consequence_summary_by_occurrence.items()
                if summary["terminal_support_visible"]
            )
            team_opponent_follow_up_ids = sorted(
                oid for oid, summary in team_consequence_summary_by_occurrence.items()
                if summary["opponent_follow_up_visible"]
            )

            team_zone_station_path: list[dict[str, Any]] = []
            for layer in ordered_layers:
                team_layer_zones = sorted({
                    str(semantic_by_context[str(context_ref)].get("context_zone_candidate") or "")
                    for context_ref in (layer.get("context_refs") or [])
                    if str(context_ref) in semantic_by_context
                    and semantic_by_context[str(context_ref)].get("action_occurrence_eligible") is True
                    and str(semantic_by_context[str(context_ref)].get("context_team_candidate") or "").strip() == team_candidate
                    and str(semantic_by_context[str(context_ref)].get("context_zone_candidate") or "").strip()
                    not in {"", "UNKNOWN_ZONE"}
                })
                if len(team_layer_zones) != 1:
                    continue
                team_zone_station_path.append({
                    "time_layer_ref": layer.get("episode_time_layer_candidate_id"),
                    "second_candidate": layer.get("second_candidate"),
                    "zone_candidate": team_layer_zones[0],
                    "same_time_unordered": bool(layer.get("same_time_unordered")),
                    "internal_order_asserted": False,
                })

            team_compressed_zones: list[str] = []
            for station in team_zone_station_path:
                zone = str(station.get("zone_candidate") or "")
                if zone and (not team_compressed_zones or team_compressed_zones[-1] != zone):
                    team_compressed_zones.append(zone)
            team_start_zone = team_compressed_zones[0] if team_compressed_zones else None
            team_end_zone = team_compressed_zones[-1] if team_compressed_zones else None
            team_zone_advancement_steps = None
            if team_start_zone in zone_order and team_end_zone in zone_order:
                team_zone_advancement_steps = zone_order[team_end_zone] - zone_order[team_start_zone]

            team_transition_candidates: list[dict[str, Any]] = []
            for left, right in zip(team_zone_station_path, team_zone_station_path[1:]):
                if left.get("second_candidate") == right.get("second_candidate"):
                    continue
                team_transition_candidates.append({
                    "from_zone": left.get("zone_candidate"),
                    "to_zone": right.get("zone_candidate"),
                    "from_second_candidate": left.get("second_candidate"),
                    "to_second_candidate": right.get("second_candidate"),
                    "same_timestamp_transition": False,
                    "transition_is_physical_trajectory_truth": False,
                })

            team_unresolved = ["game_state_not_bound"]
            if not team_identity_candidate_id:
                team_unresolved.append("team_identity_candidate_not_bound")
            elif not team_occurrence_ids:
                team_unresolved.append("team_specific_occurrence_consequence_not_visible_in_episode")
            if not team_opponent_follow_up_ids:
                team_unresolved.append("team_specific_visible_opponent_follow_up_not_resolved")
            if not team_compressed_zones:
                team_unresolved.append("team_specific_ordered_zone_path_not_bound")

            team_item_id = f"p02_team:{episode_id}:{hashlib.sha256(team_candidate.encode('utf-8')).hexdigest()[:12]}"
            team_pool_items.append({
                "pool_item_id": team_item_id,
                "parent_pool_item_id": pool_item_id,
                "pool_id": "P02_PROGRESSION",
                "pool_version": "v1-pilot",
                "pool_stage": "SPECIALIZED",
                "team_candidate": team_candidate,
                "team_identity_candidate_id": team_identity_candidate_id,
                "episode_candidate_id": episode_id,
                "input_finding_atom_ids": atom_ids,
                "input_context_refs": team_context_refs,
                "dependency_roots": [dependency_root, team_dependency_root],
                "football_question_id": "P02_TEAM_VISIBLE_PROGRESSION_PROCESS",
                "construct_id": "P02_TEAM_PROCESS_SIGNATURE_PARTIAL",
                "construct_definition": "Team-specific visible progression-relevant composition inside one analyst episode.",
                "estimand": "team_episode_process_signature_candidate",
                "eligible_population_definition": "reviewed action-occurrence-eligible semantic contexts assigned to the team inside the episode",
                "numerator": None,
                "denominator": len(rows_for_team),
                "unit": "team_episode_candidate",
                "scale": "MEZZO",
                "dimensions": ["TEAM", "TIME", "SPACE", "ACTION", "PROCESS", "CONTEXT"],
                "visible_observation_summary": {
                    "eligible_action_candidate_count": len(rows_for_team),
                    "occurrence_bound_consequence_occurrence_count": len(team_occurrence_ids),
                    "visible_follow_up_occurrence_count": len(team_visible_follow_up_ids),
                    "terminal_support_occurrence_count": len(team_terminal_support_ids),
                    "opponent_follow_up_visible_occurrence_count": len(team_opponent_follow_up_ids),
                    "action_family_counts": dict(sorted(team_family_counts.items())),
                    "zone_counts": dict(sorted(team_zone_counts.items())),
                    "channel_counts": dict(sorted(team_channel_counts.items())),
                    "shot_candidate_count": int(team_family_counts.get("SHOT", 0)),
                    "turnover_candidate_count": int(team_family_counts.get("TURNOVER", 0)),
                    "recovery_candidate_count": int(team_family_counts.get("RECOVERY", 0)),
                },
                "process_signature_fields": {
                    "team_specific_zone_station_path": team_compressed_zones,
                    "team_specific_zone_station_count_candidate": len(team_compressed_zones) if team_compressed_zones else None,
                    "team_specific_zone_transition_candidates": team_transition_candidates,
                    "team_specific_start_zone": team_start_zone,
                    "team_specific_end_zone": team_end_zone,
                    "team_specific_zone_advancement_steps_candidate": team_zone_advancement_steps,
                    "team_specific_route_evaluability": "ZONE_STATION_PATH_ONLY" if team_compressed_zones else "NOT_EVALUATED",
                    "team_specific_visible_path_length_proxy": None,
                    "team_specific_directness_proxy": None,
                    "team_specific_occurrence_ids": team_occurrence_ids,
                    "team_specific_visible_follow_up_occurrence_ids": team_visible_follow_up_ids,
                    "team_specific_terminal_support_occurrence_ids": team_terminal_support_ids,
                    "team_specific_opponent_follow_up_occurrence_ids": team_opponent_follow_up_ids,
                    "occurrence_consequence_binding_is_causal_truth": False,
                    "opponent_follow_up_is_tactical_response_truth": False,
                },
                "support_refs": team_context_refs,
                "counterevidence_refs": [],
                "dependency_challenge_refs": [],
                "non_support_refs": [],
                "unresolved_refs": team_unresolved,
                "comparison_admission_status": "NOT_EVALUATED",
                "pool_status": "DEGRADED",
                "downstream_admission": "REVIEW_BOUNDED_POOL_ITEM",
                "claim_ceiling": "P02_TEAM_EPISODE_DESCRIPTIVE_CANDIDATE_ONLY",
                "independent_support_vote": False,
                "team_share_is_possession_or_control_truth": False,
                "zone_distribution_is_route_truth": False,
                "production_release": False,
            })

        pool_items.append({
            "pool_item_id": pool_item_id,
            "pool_id": "P02_PROGRESSION",
            "pool_version": "v1-pilot",
            "pool_stage": "SPECIALIZED",
            "input_finding_atom_ids": atom_ids,
            "input_pool_item_ids": [],
            "dependency_roots": [dependency_root],
            "football_question_id": "P02_VISIBLE_PROGRESSION_PROCESS",
            "construct_id": "P02_PROCESS_SIGNATURE_PARTIAL",
            "construct_definition": "Visible episode-level progression-relevant process description without route truth.",
            "estimand": "episode_process_signature_candidate",
            "eligible_population_definition": "reviewed episode feature vectors produced by the current episode lane",
            "numerator": None,
            "denominator": None,
            "unit": "episode_candidate",
            "scale": "MEZZO",
            "dimensions": ["TIME", "SPACE", "ACTION", "PROCESS", "CONTEXT", "OUTCOME"],
            "phase_family": None,
            "process_stage": "PROGRESSION_RELEVANT_EPISODE",
            "temporal_role": "EPISODE",
            "comparison_context": {
                "period_candidate": card.get("period_candidate"),
                "feature_readiness": card.get("feature_readiness"),
            },
            "context_completeness": "PARTIAL",
            "opponent_context": (
                "VISIBLE_OPPONENT_FOLLOW_UP_CANDIDATE"
                if opponent_follow_up_occurrence_ids
                else "UNRESOLVED_VISIBLE_OPPONENT_RESPONSE"
            ),
            "game_state": "NOT_EVALUATED",
            "visible_observation_summary": {
                "duration_seconds_candidate": duration,
                "occurrence_bound_consequence_occurrence_count": len(occurrence_ids),
                "visible_follow_up_occurrence_count": len(visible_follow_up_occurrence_ids),
                "terminal_support_occurrence_count": len(terminal_support_occurrence_ids),
                "opponent_follow_up_visible_occurrence_count": len(opponent_follow_up_occurrence_ids),
                "same_team_follow_up_visible_occurrence_count": len(same_team_follow_up_occurrence_ids),
                "start_zone_candidate": start_zone_candidate,
                "end_zone_candidate": end_zone_candidate,
                "zone_advancement_steps_candidate": zone_advancement_steps,
                "zone_station_path_candidate": compressed_zone_stations,
                "zone_transition_candidate_count": len(zone_transition_candidates),
                "action_station_candidate_count": eligible_actions,
                "same_time_unordered_layer_count": same_time_layers,
                "action_family_counts": family_counts,
                "zone_counts": zone_counts,
                "channel_counts": channel_counts,
                "final_third_activity_candidate_count": final_third_count,
                "shot_candidate_count": shot_count,
                "turnover_candidate_count": turnover_count,
                "recovery_candidate_count": recovery_count,
                "eligible_action_rate_per_second_candidate": action_rate,
            },
            "process_signature_fields": {
                "route_evaluability": "NOT_EVALUATED",
                "visible_path_length_proxy": None,
                "directness_proxy": None,
                "net_goalward_progression": None,
                "net_lateral_displacement": None,
                "start_zone_candidate": start_zone_candidate,
                "end_zone_candidate": end_zone_candidate,
                "zone_advancement_steps_candidate": zone_advancement_steps,
                "zone_station_path_candidate": compressed_zone_stations,
                "zone_transition_candidates": zone_transition_candidates,
                "action_station_count_candidate": eligible_actions,
                "actor_station_count_candidate": None,
                "relation_station_count_candidate": None,
                "zone_station_count_candidate": len(compressed_zone_stations) if compressed_zone_stations else None,
                "same_time_unordered_layer_count": same_time_layers,
                "advanced_access_activity_candidate": final_third_count > 0,
                "occurrence_ids": occurrence_ids,
                "visible_follow_up_occurrence_ids": visible_follow_up_occurrence_ids,
                "terminal_support_occurrence_ids": terminal_support_occurrence_ids,
                "opponent_follow_up_occurrence_ids": opponent_follow_up_occurrence_ids,
                "same_team_follow_up_occurrence_ids": same_team_follow_up_occurrence_ids,
                "occurrence_consequence_binding_is_causal_truth": False,
                "opponent_follow_up_is_tactical_response_truth": False,
            },
            "station_type": "ACTION_STATION",
            "route_family": "NOT_EVALUATED",
            "branch_family": "NOT_EVALUATED",
            "support_refs": atom_ids,
            "counterevidence_refs": [],
            "dependency_challenge_refs": [],
            "non_support_refs": [],
            "unresolved_refs": unresolved,
            "comparison_admission_status": "NOT_EVALUATED",
            "reconstruction_status": "DEGRADED",
            "information_delta_counts": {
                "preserved": len(atom_ids),
                "collapsed": 0,
                "enriched": len(atom_ids),
                "degraded": len(unresolved),
                "lost": 0,
                "invented": 0,
                "ambiguous": 0,
            },
            "lost_atom_refs": [],
            "invented_semantics_hits": [],
            "collapsed_reflection_count": 0,
            "preserved_atom_count": len(atom_ids),
            "enriched_field_count": len(atom_ids),
            "pool_status": pool_status,
            "downstream_admission": "REVIEW_BOUNDED_POOL_ITEM",
            "claim_ceiling": "P02_EPISODE_DESCRIPTIVE_CANDIDATE_ONLY",
            "forbidden_inferences": [
                "TACTICAL_TRUTH",
                "COACH_INTENTION",
                "DOMINANCE_TRUTH",
                "CONTROL_TRUTH",
                "PHYSICAL_TRAJECTORY_TRUTH",
                "CAUSAL_TRUTH",
            ],
            "withdrawal_conditions": ["upstream_episode_feature_vector_invalidated"],
            "pool_coverage": {
                "duration_available": duration is not None,
                "occurrence_consequence_binding_available": bool(occurrence_ids),
                "visible_follow_up_available": bool(visible_follow_up_occurrence_ids),
                "opponent_follow_up_visible": bool(opponent_follow_up_occurrence_ids),
                "action_station_available": True,
                "zone_distribution_available": bool(zone_counts),
                "channel_distribution_available": bool(channel_counts),
                "zone_station_path_available": bool(compressed_zone_stations),
                "zone_transition_available": bool(zone_transition_candidates),
                "route_available": False,
            },
            "missing_required_dimensions": [],
            "missing_optional_dimensions": unresolved,
            "recurring_gap_signatures": unresolved,
            "maintenance_debt_candidates": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        })
        ledger.append({
            "transformation_id": f"p02_projection:{episode_id}",
            "operation_type": "ROUTE_TO_POOL",
            "input_artifact_ids": [feature_id] + ([temporal_id] if temporal_id else []),
            "input_atom_ids": atom_ids,
            "output_pool_item_ids": [pool_item_id],
            "information_delta_class": "ENRICHED_WITH_EXPLICIT_DEGRADATION",
            "preserved_atom_refs": atom_ids,
            "collapsed_atom_refs": [],
            "excluded_atom_refs": [],
            "lost_atom_refs": [],
            "invented_semantics_hits": [],
            "claim_ceiling_before": card.get("claim_ceiling"),
            "claim_ceiling_after": "P02_EPISODE_DESCRIPTIVE_CANDIDATE_ONLY",
            "production_release": False,
        })

    return {
        "module_id": "progression_pool_p02_projection_v1",
        "status": "DEGRADED" if pool_items else "NOT_EVALUATED",
        "decision": "P02_PARTIAL_PROJECTION_AVAILABLE" if pool_items else "P02_NOT_EVALUATED",
        "finding_atom_candidate_count": len(finding_atoms),
        "finding_atom_candidates": finding_atoms,
        "p02_pool_item_count": len(pool_items),
        "p02_pool_items": pool_items,
        "p02_team_pool_item_count": len(team_pool_items),
        "p02_team_pool_items": team_pool_items,
        "transformation_ledger_count": len(ledger),
        "transformation_ledger": ledger,
        "comparison_candidates": [],
        "route_metric_evaluable_count": 0,
        "route_metric_not_evaluable_count": len(pool_items),
        "invented_semantics_count": 0,
        "lost_atom_count": 0,
        "pool_item_is_new_evidence_vote": False,
        "same_timestamp_is_total_order": False,
        "coordinate_is_tracking": False,
        "absence_is_counterevidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _metric_refs(rows: list[dict[str, Any]], terms: tuple[str, ...], limit: int = 20) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for row in rows:
        for key, metric in (row.get("metric_values") or {}).items():
            if not isinstance(metric, dict) or metric.get("value_status") != "OBSERVED":
                continue
            key_text = str(key).casefold()
            raw_label = str(metric.get("raw_metric_label") or "").casefold()
            if not any(term in key_text or term in raw_label for term in terms):
                continue
            refs.append({
                "metric_id": f"{row.get('row_projection_id')}:{key}",
                "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
                "raw_metric_label": metric.get("raw_metric_label"),
                "raw_value": metric.get("raw_value"),
                "entity_candidate": (row.get("identity_candidates") or {}).get("player_raw_candidate") or (row.get("identity_candidates") or {}).get("team_raw_candidate"),
                "provenance_root": str(row.get("source_sha256") or "xlsx_unknown"),
                "dependency_group": "same_provider_xlsx_aggregate",
                "independence_group": None,
                "independent_support_vote": False,
                "metric_truth": False,
            })
            if len(refs) >= limit:
                return refs
    return refs


def _construct_c01(rows: list[dict[str, Any]], features: dict[str, Any]) -> dict[str, Any]:
    progression = _metric_refs(rows, ("progressive", "progression", "final_third", "final third", "penalty_area", "penalty area", "box"))
    terminal = _metric_refs(rows, ("shot", "xg", "goal", "chance"))
    shot_total = sum(int(card.get("shot_candidate_count") or 0) for card in (features.get("episode_feature_vectors") or []) if isinstance(card, dict))
    occurrence_ref = {
        "feature_id": "c01_visible_terminal_episode_surface",
        "source_surface": "episode_feature_vector_lite_v1",
        "shot_candidate_count": shot_total,
        "provenance_root": "episode_feature_vector_lite_v1",
        "dependency_group": "episode_feature_action_population",
        "independence_group": None,
        "independent_support_vote": False,
    }
    packet_candidate = None
    if progression and (terminal or shot_total > 0):
        metrics = [progression[0]] + ([terminal[0]] if terminal else [])
        packet_candidate = {
            "packet_family": "progression",
            "input_features": [occurrence_ref],
            "input_windows": [],
            "input_sequences": [],
            "input_metrics": metrics,
            "supporting_signals": [],
            "contradicting_signals": [],
            "claim_ceiling": "composite_candidate_only",
            "blocked_language_families": ["tactical_truth", "dominance_truth", "control_truth"],
        }
    state = "REVIEW_REQUIRED"
    if not progression:
        reason = "aggregate_progression_surface_not_observed"
    elif not terminal and shot_total <= 0:
        reason = "terminal_surface_not_observed"
    else:
        reason = "occurrence_progression_semantics_not_yet_admitted_same_provider_support_non_independent"
    return {
        "construct_id": "C01_PROGRESSION_VOLUME_VS_TERMINAL_CONVERSION",
        "status": state,
        "question": "Visible progression/access production and terminal production appear together on admitted surfaces?",
        "progression_aggregate_ref_count": len(progression),
        "terminal_aggregate_ref_count": len(terminal),
        "visible_shot_candidate_count": shot_total,
        "progression_metric_refs": progression,
        "terminal_metric_refs": terminal,
        "packet_candidate": packet_candidate,
        "review_reason": reason,
        "aggregate_support_is_independent_vote": False,
        "construct_truth": False,
        "claim_ceiling": "CONSTRUCT_EVIDENCE_CANDIDATE_ONLY",
    }


def _render_txt(payload: dict[str, Any]) -> str:
    entity = payload.get("entity_views") or {}
    c01 = payload.get("constructs", {}).get("C01") or {}
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
        f"C01_visible_shot_candidate_count={c01.get('visible_shot_candidate_count')}",
        f"C01_review_reason={c01.get('review_reason')}",
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
    episode = _load_json(output / "analyst_episode_locator_lite_v1.json")
    consequence = _load_json(output / "trackable_action_consequence_candidates_lite_v1.json")
    semantics = _load_json(output / "context_action_semantics_rebind_lite_v1.json")
    identities = _load_json(output / "match_local_identity_candidates_lite_v1.json")
    rows = _flatten_projection(projection)
    entity_views = _entity_views(rows)
    primitives = _primitive_metrics(features, entity_views)
    phase_states = _phase_state_candidates(features)
    c01 = _construct_c01(rows, features)
    p02 = _progression_pool_p02(features, temporal, episode, consequence, semantics, identities)
    if c01.get("status") == "REVIEW_REQUIRED":
        review_hits.append("C01_progression_terminal_construct_review_required")

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
        "constructs": {"C01": c01},
        "progression_pool_p02": p02,
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
                "P02_progression_pool_items": p02.get("p02_pool_items") or [],
                "P02_progression_team_pool_items": p02.get("p02_team_pool_items") or [],
            },
            "MACRO": {
                "team_view_candidates": entity_views.get("team_view_candidates"),
                "action_family_candidate_counts": features.get("eligible_action_family_candidate_counts") or {},
                "metric_label_observation_counts": entity_views.get("metric_label_observation_counts") or {},
                "constructs": {"C01": {key: value for key, value in c01.items() if key not in {"progression_metric_refs", "terminal_metric_refs", "packet_candidate"}}},
            },
        },
        "entity_views": entity_views,
        "c4_packet_candidates": packet_candidates,
        "p02_pool_item_count": p02.get("p02_pool_item_count", 0),
        "p02_team_pool_item_count": p02.get("p02_team_pool_item_count", 0),
        "p02_finding_atom_candidate_count": p02.get("finding_atom_candidate_count", 0),
        "p02_route_metric_evaluable_count": p02.get("route_metric_evaluable_count", 0),
        "p02_route_metric_not_evaluable_count": p02.get("route_metric_not_evaluable_count", 0),
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
