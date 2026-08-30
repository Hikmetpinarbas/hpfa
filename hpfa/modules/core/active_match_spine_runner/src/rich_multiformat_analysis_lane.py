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
    rows = _flatten_projection(projection)
    entity_views = _entity_views(rows)
    primitives = _primitive_metrics(features, entity_views)
    phase_states = _phase_state_candidates(features)
    c01 = _construct_c01(rows, features)
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
