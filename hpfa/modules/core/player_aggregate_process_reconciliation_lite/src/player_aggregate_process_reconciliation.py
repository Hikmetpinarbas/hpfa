from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from hpfa.modules.core.match_local_identity_candidates_lite.src.match_local_identity_candidates import _normalize as normalize_identity_key

MODULE_ID = "player_aggregate_process_reconciliation_lite_v1"
XLSX_MODULE_ID = "xlsx_entity_metric_row_projection_lite_v1"
IDENTITY_MODULE_ID = "match_local_identity_candidates_lite_v1"
RECONCILIATION_MODULE_ID = "match_reconciliation_ledger_lite_v2"
GEOMETRY_MODULE_ID = "visible_geometry_lens_lite_v1"
CLAIM_CEILING = "MATCH_LOCAL_PLAYER_AGGREGATE_PROCESS_RECONCILIATION_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "player_aggregate_process_reconciliation_lite_v1.json"
OUTPUT_TXT = "player_aggregate_process_reconciliation_lite_v1.txt"
ANALYST_TXT = "player_aggregate_process_reconciliation_analyst_audit_v1.txt"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _validate(payload: dict[str, Any], expected: str, label: str, blocks: list[str], reviews: list[str]) -> None:
    if payload.get("module_id") != expected:
        blocks.append(f"{label}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{label}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append(f"{label}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{label}_production_release_claimed")
    if _status(payload.get("status") or payload.get("module_status")) == "FAIL_CLOSED" or payload.get("hard_block_hits"):
        blocks.append(f"{label}_input_fail_closed")
    elif _status(payload.get("status") or payload.get("module_status")) == "REVIEW_REQUIRED":
        reviews.append(f"{label}_upstream_review_required")


def _flatten_xlsx_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for file_row in payload.get("files") or []:
        if not isinstance(file_row, dict):
            continue
        for sheet in file_row.get("sheets") or []:
            if not isinstance(sheet, dict):
                continue
            for row in sheet.get("rows") or []:
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def _numeric_metric_candidates(row: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    values = row.get("metric_values") or {}
    if not isinstance(values, dict):
        return out
    for metric_key, value in sorted(values.items()):
        if not isinstance(value, dict):
            continue
        raw = value.get("raw_value")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        if value.get("value_status") != "OBSERVED":
            continue
        out.append({
            "metric_key": metric_key,
            "raw_metric_label": value.get("raw_metric_label"),
            "raw_value": raw,
            "number_format": value.get("number_format"),
            "percent_header_candidate": value.get("percent_header_candidate") is True,
            "metric_truth": False,
            "source_row_projection_id": row.get("row_projection_id"),
        })
    return out


def build_player_aggregate_process_reconciliation(
    xlsx_payload: dict[str, Any],
    identity_payload: dict[str, Any],
    reconciliation_payload: dict[str, Any],
    geometry_payload: dict[str, Any],
) -> dict[str, Any]:
    """Attach aggregate XLSX support to existing match-local actor candidates.

    XLSX never creates actor identity, event identity, process membership or metric
    construct truth. The bridge requires an existing unique match-local actor and an
    exact normalized player+team candidate match before attaching aggregate rows.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    for label, payload, expected in (
        ("xlsx", xlsx_payload, XLSX_MODULE_ID),
        ("identity", identity_payload, IDENTITY_MODULE_ID),
        ("reconciliation", reconciliation_payload, RECONCILIATION_MODULE_ID),
        ("geometry", geometry_payload, GEOMETRY_MODULE_ID),
    ):
        _validate(payload, expected, label, blocks, reviews)

    actors = identity_payload.get("actor_identity_candidates") or []
    teams = identity_payload.get("team_identity_candidates") or []
    if not isinstance(actors, list) or not isinstance(teams, list):
        blocks.append("identity_collections_invalid")
        actors, teams = [], []
    team_by_id = {
        _clean(row.get("team_identity_candidate_id")): row
        for row in teams if isinstance(row, dict) and _clean(row.get("team_identity_candidate_id"))
    }
    actors_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in actors:
        if not isinstance(row, dict):
            continue
        key = _clean(row.get("actor_normalized_key"))
        if key:
            actors_by_key[key].append(row)

    process_by_actor = {
        _clean(row.get("actor_identity_candidate_id")): row
        for row in (reconciliation_payload.get("player_process_membership_rows") or [])
        if isinstance(row, dict) and _clean(row.get("actor_identity_candidate_id"))
    }
    geometry_by_actor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in geometry_payload.get("player_period_geometry_rows") or []:
        if isinstance(row, dict) and _clean(row.get("actor_identity_candidate_id")):
            geometry_by_actor[_clean(row.get("actor_identity_candidate_id"))].append(row)

    actor_dossiers: dict[str, dict[str, Any]] = {}
    unmatched_rows: list[str] = []
    ambiguous_rows: list[str] = []
    team_mismatch_rows: list[str] = []
    bound_xlsx_rows = 0

    if not blocks:
        for row in _flatten_xlsx_rows(xlsx_payload):
            identity = row.get("identity_candidates") or {}
            raw_player = _clean(identity.get("player_raw_candidate"))
            raw_team = _clean(identity.get("team_raw_candidate"))
            if not raw_player:
                continue
            player_key = normalize_identity_key(raw_player)
            team_key = normalize_identity_key(raw_team) if raw_team else ""
            candidates = actors_by_key.get(player_key, [])
            matched: list[dict[str, Any]] = []
            for actor in candidates:
                actor_team_key = _clean(actor.get("team_normalized_key"))
                if not actor_team_key:
                    team_row = team_by_id.get(_clean(actor.get("team_identity_candidate_id"))) or {}
                    actor_team_key = _clean(team_row.get("team_normalized_key"))
                if team_key and actor_team_key and team_key != actor_team_key:
                    continue
                matched.append(actor)
            row_id = _clean(row.get("row_projection_id")) or "UNKNOWN_XLSX_ROW"
            if not matched:
                if candidates:
                    team_mismatch_rows.append(row_id)
                else:
                    unmatched_rows.append(row_id)
                continue
            if len(matched) != 1:
                ambiguous_rows.append(row_id)
                continue

            actor = matched[0]
            actor_id = _clean(actor.get("actor_identity_candidate_id"))
            dossier = actor_dossiers.setdefault(actor_id, {
                "actor_identity_candidate_id": actor_id,
                "actor_normalized_key_candidate": actor.get("actor_normalized_key"),
                "team_identity_candidate_id": actor.get("team_identity_candidate_id"),
                "team_normalized_key_candidate": actor.get("team_normalized_key"),
                "validated_player_identity": False,
                "aggregate_binding_state_candidate": "EXACT_NORMALIZED_PLAYER_AND_TEAM_MATCH_LOCAL_CANDIDATE",
                "aggregate_rows": [],
                "aggregate_numeric_metric_candidates": [],
            })
            dossier["aggregate_rows"].append({
                "row_projection_id": row.get("row_projection_id"),
                "sheet_name": row.get("sheet_name"),
                "source_row_number": row.get("source_row_number"),
                "source_sha256": row.get("source_sha256"),
                "player_raw_candidate": raw_player,
                "team_raw_candidate": raw_team or None,
                "position_raw_candidate": identity.get("position_raw_candidate"),
                "minutes_raw_candidate": identity.get("minutes_raw_candidate"),
                "xlsx_validated_identity": row.get("validated_identity") is True,
            })
            dossier["aggregate_numeric_metric_candidates"].extend(_numeric_metric_candidates(row))
            bound_xlsx_rows += 1

    dossiers: list[dict[str, Any]] = []
    for actor_id in sorted(actor_dossiers):
        dossier = actor_dossiers[actor_id]
        process = process_by_actor.get(actor_id)
        dossier["visible_process_membership_state_candidate"] = (
            "VISIBLE_RECIPROCAL_PROCESS_MEMBERSHIP_CANDIDATE"
            if process else "NO_VISIBLE_RECIPROCAL_PROCESS_MEMBERSHIP_CANDIDATE"
        )
        dossier["unique_process_candidate_count"] = int((process or {}).get("unique_process_candidate_count") or 0)
        dossier["unique_episode_candidate_count"] = int((process or {}).get("unique_episode_candidate_count") or 0)
        dossier["role_membership_counts"] = (process or {}).get("role_membership_counts") or {}
        dossier["visible_process_membership_share_of_team_candidate"] = (process or {}).get("visible_process_membership_share_of_team_candidate")
        dossier["process_membership_share_is_quality_truth"] = False
        dossier["period_geometry_candidates"] = geometry_by_actor.get(actor_id, [])
        dossier["aggregate_numeric_metric_candidate_count"] = len(dossier["aggregate_numeric_metric_candidates"])
        dossier["aggregate_metrics_are_validated_constructs"] = False
        dossier["aggregate_metrics_are_independent_event_evidence"] = False
        dossier["claim_ceiling"] = CLAIM_CEILING
        dossiers.append(dossier)

    if unmatched_rows:
        reviews.append(f"xlsx_player_rows_unmatched:{len(unmatched_rows)}")
    if ambiguous_rows:
        reviews.append(f"xlsx_player_rows_ambiguous:{len(ambiguous_rows)}")
    if team_mismatch_rows:
        reviews.append(f"xlsx_player_rows_team_mismatch:{len(team_mismatch_rows)}")

    xlsx_player_rows = sum(
        1 for row in _flatten_xlsx_rows(xlsx_payload)
        if _clean((row.get("identity_candidates") or {}).get("player_raw_candidate"))
    )
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "PLAYER_AGGREGATE_PROCESS_RECONCILIATION_BUILT" if not blocks else "PLAYER_AGGREGATE_PROCESS_RECONCILIATION_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "player_dossiers": dossiers if not blocks else [],
        "player_dossier_count": len(dossiers) if not blocks else 0,
        "xlsx_player_row_count": xlsx_player_rows if not blocks else 0,
        "xlsx_player_row_bound_count": bound_xlsx_rows if not blocks else 0,
        "xlsx_player_row_unmatched_count": len(unmatched_rows) if not blocks else 0,
        "xlsx_player_row_ambiguous_count": len(ambiguous_rows) if not blocks else 0,
        "xlsx_player_row_team_mismatch_count": len(team_mismatch_rows) if not blocks else 0,
        "players_with_visible_process_membership_count": sum(
            row.get("visible_process_membership_state_candidate") == "VISIBLE_RECIPROCAL_PROCESS_MEMBERSHIP_CANDIDATE"
            for row in dossiers
        ) if not blocks else 0,
        "players_with_period_geometry_count": sum(bool(row.get("period_geometry_candidates")) for row in dossiers) if not blocks else 0,
        "normalization_contract_source": "match_local_identity_candidates_lite_v1",
        "xlsx_creates_player_identity": False,
        "xlsx_creates_event_identity": False,
        "aggregate_metric_truth": False,
        "player_quality_truth": False,
        "tactical_role_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    analyst_path = output / ANALYST_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text("\n".join([
        "HPFA PLAYER AGGREGATE ↔ PROCESS RECONCILIATION LITE V1",
        f"status={payload.get('status')}",
        f"xlsx_player_row_count={payload.get('xlsx_player_row_count', 0)}",
        f"xlsx_player_row_bound_count={payload.get('xlsx_player_row_bound_count', 0)}",
        f"player_dossier_count={payload.get('player_dossier_count', 0)}",
        f"players_with_visible_process_membership_count={payload.get('players_with_visible_process_membership_count', 0)}",
        "validated_player_identity=false",
        "aggregate_metric_truth=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    lines = [
        "HPFA ANALYST AUDIT — PLAYER AGGREGATE ↔ PROCESS",
        "Aggregate XLSX rows are attached only to existing unique match-local player+team candidates; they do not create identity or event truth.",
    ]
    for row in payload.get("player_dossiers") or []:
        lines.append(
            f"- {row.get('actor_normalized_key_candidate')}: aggregate_rows={len(row.get('aggregate_rows') or [])} "
            f"numeric_metrics={row.get('aggregate_numeric_metric_candidate_count')} "
            f"visible_processes={row.get('unique_process_candidate_count')} "
            f"visible_episodes={row.get('unique_episode_candidate_count')} roles={row.get('role_membership_counts')}"
        )
    lines.extend([
        "Aggregate values remain provider/tabular observations, not validated constructs or independent confirmation of event evidence.",
        "",
    ])
    analyst_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
