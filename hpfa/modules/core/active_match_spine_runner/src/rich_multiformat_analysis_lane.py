from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from hpfa.modules.core.match_local_identity_candidates_lite.src.match_local_identity_candidates import _normalize as normalize_match_local_identity_candidate
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
MATCH_LOCAL_IDENTITY_JSON = "match_local_identity_candidates_lite_v1.json"
MATCH_LOCAL_IDENTITY_MODULE_ID = "match_local_identity_candidates_lite_v1"
TRACKABLE_TRACE_JSON = "trackable_action_trace_candidates_lite_v1.json"
TRACKABLE_TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"


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


def _strict_nonnegative_count(value: Any) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


def _positive_numeric_observation(metric: Any) -> int | float | None:
    if not isinstance(metric, dict) or metric.get("value_status") != "OBSERVED":
        return None
    if metric.get("value_kind") != "number":
        return None
    raw_value = metric.get("raw_value")
    if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool):
        return None
    numeric_value = float(raw_value)
    if not math.isfinite(numeric_value) or numeric_value <= 0:
        return None
    return raw_value


def _flatten_projection(projection: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for file_row in projection.get("files", []) or []
        for sheet in file_row.get("sheets", []) or []
        for row in sheet.get("rows", []) or []
        if isinstance(row, dict)
    ]


def _identity_candidate_index(identity_payload: dict[str, Any], binding_id: str | None) -> dict[str, Any]:
    empty = {
        "input_state": "IDENTITY_CANDIDATE_INPUT_UNAVAILABLE",
        "actor_by_key": {},
        "team_by_key": {},
    }
    if not isinstance(identity_payload, dict) or not identity_payload:
        return empty
    if identity_payload.get("module_id") != MATCH_LOCAL_IDENTITY_MODULE_ID:
        return {**empty, "input_state": "IDENTITY_CANDIDATE_MODULE_MISMATCH_REVIEW_REQUIRED"}
    if str(identity_payload.get("status") or identity_payload.get("module_status") or "") == "FAIL_CLOSED":
        return {**empty, "input_state": "IDENTITY_CANDIDATE_INPUT_FAIL_CLOSED"}
    payload_binding_id = str(identity_payload.get("match_surface_binding_id") or "").strip()
    expected_binding_id = str(binding_id or "").strip()
    if not expected_binding_id or payload_binding_id != expected_binding_id:
        return {**empty, "input_state": "IDENTITY_CANDIDATE_BINDING_MISMATCH_REVIEW_REQUIRED"}

    actor_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in identity_payload.get("actor_identity_candidates") or []:
        if not isinstance(candidate, dict) or candidate.get("decision_state") != "ACTOR_IDENTITY_CANDIDATE_BOUND":
            continue
        if candidate.get("match_surface_binding_id") != expected_binding_id:
            continue
        team_key = str(candidate.get("team_normalized_key") or "").strip()
        actor_key = str(candidate.get("actor_normalized_key") or "").strip()
        candidate_id = str(candidate.get("actor_identity_candidate_id") or "").strip()
        team_candidate_id = str(candidate.get("team_identity_candidate_id") or "").strip()
        if team_key and actor_key and candidate_id and team_candidate_id:
            actor_by_key[(team_key, actor_key)].append({
                "actor_identity_candidate_id": candidate_id,
                "team_identity_candidate_id": team_candidate_id,
                "team_normalized_key": team_key,
                "actor_normalized_key": actor_key,
            })

    team_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in identity_payload.get("team_identity_candidates") or []:
        if not isinstance(candidate, dict) or candidate.get("decision_state") != "TEAM_IDENTITY_CANDIDATE_BOUND":
            continue
        if candidate.get("match_surface_binding_id") != expected_binding_id:
            continue
        team_key = str(candidate.get("team_normalized_key") or "").strip()
        candidate_id = str(candidate.get("team_identity_candidate_id") or "").strip()
        if team_key and candidate_id:
            team_by_key[team_key].append({
                "team_identity_candidate_id": candidate_id,
                "team_normalized_key": team_key,
            })
    return {
        "input_state": "MATCH_LOCAL_IDENTITY_CANDIDATES_AVAILABLE",
        "actor_by_key": dict(actor_by_key),
        "team_by_key": dict(team_by_key),
    }


def _trace_candidate_index(trace_payload: dict[str, Any], binding_id: str | None) -> dict[str, Any]:
    empty = {
        "input_state": "TRACE_CANDIDATE_INPUT_UNAVAILABLE",
        "actor_by_identity_candidate_ids": {},
        "review_bound": False,
    }
    if not isinstance(trace_payload, dict) or not trace_payload:
        return empty
    if trace_payload.get("module_id") != TRACKABLE_TRACE_MODULE_ID:
        return {**empty, "input_state": "TRACE_CANDIDATE_MODULE_MISMATCH_REVIEW_REQUIRED"}
    status = str(trace_payload.get("status") or trace_payload.get("module_status") or "")
    if status not in {"PASS", "REVIEW_REQUIRED"}:
        return {**empty, "input_state": "TRACE_CANDIDATE_INPUT_NOT_ADMISSIBLE_REVIEW_REQUIRED"}
    expected_binding_id = str(binding_id or "").strip()
    payload_binding_id = str(trace_payload.get("match_surface_binding_id") or "").strip()
    if not expected_binding_id or payload_binding_id != expected_binding_id:
        return {**empty, "input_state": "TRACE_CANDIDATE_BINDING_MISMATCH_REVIEW_REQUIRED"}
    if (
        trace_payload.get("canonical_event_count") != "UNKNOWN"
        or trace_payload.get("true_action_count") != "UNKNOWN"
        or trace_payload.get("production_release") is True
        or trace_payload.get("trackable_action_candidate_is_event_truth") is True
        or trace_payload.get("physical_action_identity_truth") is True
        or trace_payload.get("trace_count_is_physical_action_count") is True
        or trace_payload.get("claim_allowed") is True
    ):
        return {**empty, "input_state": "TRACE_CANDIDATE_CLAIM_BOUNDARY_MISMATCH_REVIEW_REQUIRED"}

    actor_by_identity_candidate_ids: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in trace_payload.get("trackable_action_trace_candidates") or []:
        if not isinstance(row, dict):
            continue
        if row.get("match_surface_binding_id") != expected_binding_id:
            continue
        trace_id = str(row.get("trackable_action_trace_candidate_id") or "").strip()
        team_candidate_id = str(row.get("team_identity_candidate_id") or "").strip()
        actor_candidate_id = str(row.get("actor_identity_candidate_id") or "").strip()
        if not trace_id or not team_candidate_id or not actor_candidate_id:
            continue
        if (
            row.get("trackable_action_candidate_is_event_truth") is True
            or row.get("physical_action_identity_truth") is True
            or row.get("event_instance_allowed") is True
            or row.get("validated_event_identity") is True
            or row.get("count_value_output_allowed") is True
            or row.get("trace_count_is_physical_action_count") is True
        ):
            return {**empty, "input_state": "TRACE_CANDIDATE_ROW_CLAIM_BOUNDARY_MISMATCH_REVIEW_REQUIRED"}
        actor_by_identity_candidate_ids[(team_candidate_id, actor_candidate_id)].append({
            "trackable_action_trace_candidate_id": trace_id,
            "team_identity_candidate_id": team_candidate_id,
            "actor_identity_candidate_id": actor_candidate_id,
            "source_role": row.get("source_role"),
            "action_family_candidates": list(row.get("action_family_candidates") or []),
        })
    return {
        "input_state": "TRACKABLE_ACTION_TRACE_CANDIDATES_AVAILABLE",
        "actor_by_identity_candidate_ids": dict(actor_by_identity_candidate_ids),
        "review_bound": status == "REVIEW_REQUIRED",
    }


def _entity_views(
    rows: list[dict[str, Any]],
    identity_payload: dict[str, Any] | None = None,
    trace_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    players: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    goalkeepers: list[dict[str, Any]] = []
    metric_label_counts: Counter[str] = Counter()
    observed_metric_cell_count = 0
    aggregate_support_lineage_incomplete_candidate_count = 0
    aggregate_support_identity_candidate_link_count = 0
    aggregate_support_identity_relation_review_required_count = 0
    aggregate_support_trace_cohort_context_link_count = 0
    aggregate_support_trace_candidate_ref_count = 0
    aggregate_support_trace_relation_review_required_count = 0
    binding_ids = {
        str(row.get("match_surface_binding_id") or "").strip()
        for row in rows
        if str(row.get("match_surface_binding_id") or "").strip()
    }
    common_binding_id = next(iter(binding_ids)) if len(binding_ids) == 1 else None
    identity_index = _identity_candidate_index(identity_payload or {}, common_binding_id)
    trace_index = _trace_candidate_index(trace_payload or {}, common_binding_id)
    if identity_index["input_state"].endswith("REVIEW_REQUIRED"):
        aggregate_support_identity_relation_review_required_count += 1
    if trace_index["input_state"].endswith("REVIEW_REQUIRED") or trace_index.get("review_bound"):
        aggregate_support_trace_relation_review_required_count += 1

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
        aggregate_support_lineage = {
            "row_projection_id": row.get("row_projection_id"),
            "file_id": row.get("file_id"),
            "relative_path": row.get("relative_path"),
            "source_sha256": row.get("source_sha256"),
            "source_role": row.get("source_role"),
            "sheet_name": row.get("sheet_name"),
            "source_row_number": row.get("source_row_number"),
            "match_surface_binding_id": row.get("match_surface_binding_id"),
        }
        required_text = (
            "row_projection_id",
            "file_id",
            "relative_path",
            "source_sha256",
            "source_role",
            "sheet_name",
            "match_surface_binding_id",
        )
        lineage_complete = all(str(aggregate_support_lineage.get(key) or "").strip() for key in required_text)
        source_row_number = aggregate_support_lineage.get("source_row_number")
        lineage_complete = bool(
            lineage_complete
            and isinstance(source_row_number, int)
            and not isinstance(source_row_number, bool)
            and source_row_number > 0
        )
        if not lineage_complete:
            aggregate_support_lineage_incomplete_candidate_count += 1

        role = str(row.get("source_role") or "").upper()
        team_key = normalize_match_local_identity_candidate(identity.get("team_raw_candidate")) or None
        actor_key = normalize_match_local_identity_candidate(identity.get("player_raw_candidate")) or None
        relation_ref: dict[str, Any] | None = None
        relation_state = "XLSX_ROW_PROJECTION_CANDIDATE_ONLY"
        relation_basis: list[str] = []
        if lineage_complete and identity_index["input_state"] == "MATCH_LOCAL_IDENTITY_CANDIDATES_AVAILABLE":
            candidates: list[dict[str, Any]] = []
            if "GOALKEEPER" in role or identity.get("player_raw_candidate") not in (None, ""):
                if team_key and actor_key:
                    candidates = list(identity_index["actor_by_key"].get((team_key, actor_key), []))
                    relation_basis = [
                        "same_match_surface_binding_id",
                        "bound_match_local_actor_identity_candidate",
                        "normalized_team_and_actor_candidate_match",
                    ]
            elif team_key:
                candidates = list(identity_index["team_by_key"].get(team_key, []))
                relation_basis = [
                    "same_match_surface_binding_id",
                    "bound_match_local_team_identity_candidate",
                    "normalized_team_candidate_match",
                ]
            if len(candidates) == 1:
                relation_ref = candidates[0]
                relation_state = "MATCH_LOCAL_IDENTITY_CANDIDATE_LINK_ONLY"
                aggregate_support_identity_candidate_link_count += 1
            elif len(candidates) > 1:
                relation_state = "IDENTITY_CANDIDATE_AMBIGUOUS_REVIEW_REQUIRED"
                aggregate_support_identity_relation_review_required_count += 1

        trace_context_refs: list[dict[str, Any]] = []
        trace_context_state = "TRACE_CANDIDATE_CONTEXT_UNAVAILABLE"
        trace_context_basis: list[str] = []
        if (
            relation_ref is not None
            and "actor_identity_candidate_id" in relation_ref
            and trace_index["input_state"] == "TRACKABLE_ACTION_TRACE_CANDIDATES_AVAILABLE"
        ):
            trace_context_refs = list(
                trace_index["actor_by_identity_candidate_ids"].get(
                    (
                        str(relation_ref.get("team_identity_candidate_id") or "").strip(),
                        str(relation_ref.get("actor_identity_candidate_id") or "").strip(),
                    ),
                    [],
                )
            )
            if trace_context_refs:
                trace_context_state = (
                    "TRACE_CANDIDATE_COHORT_CONTEXT_REVIEW_BOUND"
                    if trace_index.get("review_bound")
                    else "TRACE_CANDIDATE_COHORT_CONTEXT_ONLY"
                )
                trace_context_basis = [
                    "same_match_surface_binding_id",
                    "same_bound_team_identity_candidate_id",
                    "same_bound_actor_identity_candidate_id",
                    "trackable_trace_candidate_claim_boundary_preserved",
                ]
                aggregate_support_trace_cohort_context_link_count += 1
                aggregate_support_trace_candidate_ref_count += len(trace_context_refs)
            else:
                trace_context_state = "NO_COMPATIBLE_TRACE_CANDIDATE_CONTEXT"

        compact = {
            "row_projection_id": row.get("row_projection_id"),
            "source_role": row.get("source_role"),
            "player_raw_candidate": identity.get("player_raw_candidate"),
            "team_raw_candidate": identity.get("team_raw_candidate"),
            "position_raw_candidate": identity.get("position_raw_candidate"),
            "minutes_raw_candidate": identity.get("minutes_raw_candidate"),
            "metric_values": observed_metrics,
            "aggregate_support_lineage": aggregate_support_lineage,
            "aggregate_support_lineage_complete": lineage_complete,
            "aggregate_support_attachment_state": (
                "PROVENANCE_INCOMPLETE_REVIEW_REQUIRED"
                if not lineage_complete
                else relation_state
            ),
            "aggregate_support_match_local_identity_candidate_ref": relation_ref,
            "aggregate_support_identity_relation_basis": relation_basis,
            "aggregate_support_identity_relation_is_candidate_only": relation_ref is not None,
            "aggregate_support_identity_relation_is_identity_truth": False,
            "aggregate_support_identity_relation_is_action_trace_attachment": False,
            "aggregate_support_trace_context_state": trace_context_state,
            "aggregate_support_trackable_trace_candidate_refs": trace_context_refs,
            "aggregate_support_trace_context_basis": trace_context_basis,
            "aggregate_support_trace_relation_is_cohort_context_only": bool(trace_context_refs),
            "aggregate_support_trace_relation_is_review_bound": bool(trace_context_refs and trace_index.get("review_bound")),
            "aggregate_support_trace_relation_is_individual_action_support": False,
            "aggregate_support_trace_relation_is_action_trace_identity": False,
            "aggregate_support_trace_relation_is_physical_action_truth": False,
            "aggregate_support_is_timeline_identity": False,
            "aggregate_support_is_event_truth": False,
            "aggregate_support_is_independent_vote": False,
            "validated_identity": False,
            "metric_truth": False,
        }
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
        "aggregate_support_lineage_incomplete_candidate_count": aggregate_support_lineage_incomplete_candidate_count,
        "aggregate_support_identity_candidate_link_count": aggregate_support_identity_candidate_link_count,
        "aggregate_support_identity_relation_review_required_count": aggregate_support_identity_relation_review_required_count,
        "aggregate_support_identity_relation_input_state": identity_index["input_state"],
        "aggregate_support_trace_cohort_context_link_count": aggregate_support_trace_cohort_context_link_count,
        "aggregate_support_trace_candidate_ref_count": aggregate_support_trace_candidate_ref_count,
        "aggregate_support_trace_relation_review_required_count": aggregate_support_trace_relation_review_required_count,
        "aggregate_support_trace_relation_input_state": trace_index["input_state"],
        "aggregate_support_trace_relation_review_bound": bool(trace_index.get("review_bound")),
        "aggregate_support_attachment_is_match_local_identity_truth": False,
        "aggregate_support_attachment_is_action_trace_identity": False,
        "aggregate_support_trace_relation_is_individual_action_support": False,
        "aggregate_support_trace_relation_is_physical_action_truth": False,
        "aggregate_support_attachment_is_timeline_identity_truth": False,
        "aggregate_support_attachment_is_timeline_identity": False,
        "aggregate_support_attachment_is_independent_vote": False,
        "player_identity_truth": False,
        "team_identity_truth": False,
    }


def _primitive_metrics(features: dict[str, Any], entity_views: dict[str, Any]) -> dict[str, Any]:
    values: list[dict[str, Any]] = []
    invalid_count_fields: list[str] = []

    raw_total = features.get("total_eligible_action_candidate_count")
    total = None if raw_total is None else _strict_nonnegative_count(raw_total)
    if raw_total is not None and total is None:
        invalid_count_fields.append("total_eligible_action_candidate_count")
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

    raw_family_counts = features.get("eligible_action_family_candidate_counts")
    admitted_family_counts: dict[str, int] = {}
    family_invalid = False
    if raw_family_counts is not None and not isinstance(raw_family_counts, dict):
        invalid_count_fields.append("eligible_action_family_candidate_counts")
        family_invalid = True
    elif isinstance(raw_family_counts, dict):
        for family, raw_value in sorted(raw_family_counts.items(), key=lambda item: str(item[0])):
            value = _strict_nonnegative_count(raw_value)
            if value is None:
                invalid_count_fields.append(f"eligible_action_family_candidate_counts.{family}")
                family_invalid = True
            else:
                admitted_family_counts[str(family)] = value
    if family_invalid:
        admitted_family_counts = {}
    else:
        for family, value in sorted(admitted_family_counts.items()):
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
    return {
        "metrics": values,
        "count_contract_review_required": bool(invalid_count_fields),
        "invalid_count_fields": sorted(invalid_count_fields),
        "admitted_action_family_candidate_counts": admitted_family_counts,
    }


def _phase_state_candidates(features: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    cards = features.get("episode_feature_vectors") or []
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            continue
        zones = card.get("eligible_action_zone_counts")
        families = card.get("action_family_counts")
        zones = zones if isinstance(zones, dict) else {}
        families = families if isinstance(families, dict) else {}
        raw_counts = {
            "shot_candidate_count": card.get("shot_candidate_count", 0),
            "turnover_candidate_count": card.get("turnover_candidate_count", 0),
            "recovery_candidate_count": card.get("recovery_candidate_count", 0),
            "final_third_action_candidate_count": zones.get("FINAL_THIRD", zones.get("final_third", 0)),
            "pass_candidate_count": families.get("PASS", families.get("pass", 0)),
        }
        counts = {key: _strict_nonnegative_count(value) for key, value in raw_counts.items()}
        invalid_fields = sorted(key for key, value in counts.items() if value is None)
        count_contract_review_required = bool(invalid_fields)
        support = {key: (0 if value is None else value) for key, value in counts.items()}

        labels: list[str] = []
        if not count_contract_review_required:
            if support["shot_candidate_count"]:
                labels.append("TERMINAL_ACTIVITY_CANDIDATE")
            if support["turnover_candidate_count"]:
                labels.append("LOSS_TRANSITION_ACTIVITY_CANDIDATE")
            if support["recovery_candidate_count"]:
                labels.append("RECOVERY_TRANSITION_ACTIVITY_CANDIDATE")
            if support["final_third_action_candidate_count"]:
                labels.append("ADVANCED_ACCESS_ACTIVITY_CANDIDATE")
            if support["pass_candidate_count"]:
                labels.append("CIRCULATION_ACTIVITY_CANDIDATE")
        if not labels:
            labels.append("UNRESOLVED_ACTIVITY_STATE")
        result.append({
            "phase_state_candidate_id": f"psc_{index:04d}",
            "episode_index": index,
            "start_second_candidate": card.get("start_second_candidate"),
            "end_second_candidate": card.get("end_second_candidate"),
            "labels": labels,
            "support": support,
            "count_contract_review_required": count_contract_review_required,
            "invalid_count_fields": invalid_fields,
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
            admitted_value = _positive_numeric_observation(metric)
            if admitted_value is None:
                continue
            refs.append({
                "metric_id": f"{row.get('row_projection_id')}:{key}",
                "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
                "raw_metric_label": metric.get("raw_metric_label"),
                "raw_value": admitted_value,
                "value_kind": "number",
                "positive_numeric_support_only": True,
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
    shot_values: list[int] = []
    invalid_shot_count_episode_indices: list[int] = []
    for index, card in enumerate(features.get("episode_feature_vectors") or []):
        if not isinstance(card, dict):
            continue
        value = _strict_nonnegative_count(card.get("shot_candidate_count", 0))
        if value is None:
            invalid_shot_count_episode_indices.append(index)
        else:
            shot_values.append(value)
    count_contract_review_required = bool(invalid_shot_count_episode_indices)
    shot_total = sum(shot_values) if not count_contract_review_required else 0
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
    if not count_contract_review_required and progression and (terminal or shot_total > 0):
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
    if count_contract_review_required:
        reason = "episode_feature_shot_count_contract_invalid"
    elif not progression:
        reason = "positive_numeric_aggregate_progression_surface_not_observed"
    elif not terminal and shot_total <= 0:
        reason = "positive_numeric_terminal_surface_not_observed"
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
        "count_contract_review_required": count_contract_review_required,
        "invalid_shot_count_episode_indices": invalid_shot_count_episode_indices,
        "xlsx_metric_support_requires_observed_positive_numeric_value": True,
        "xlsx_zero_metric_value_is_production_support": False,
        "xlsx_nonnumeric_metric_value_is_production_support": False,
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
        f"primitive_count_contract_review_required={payload.get('primitive_count_contract_review_required')}",
        f"primitive_invalid_count_fields={payload.get('primitive_invalid_count_fields') or []}",
        f"phase_state_candidate_count={len(payload.get('phase_state_candidates') or [])}",
        f"player_view_candidate_count={len(entity.get('player_view_candidates') or [])}",
        f"team_view_candidate_count={len(entity.get('team_view_candidates') or [])}",
        f"goalkeeper_view_candidate_count={len(entity.get('goalkeeper_view_candidates') or [])}",
        f"aggregate_support_lineage_incomplete_candidate_count={entity.get('aggregate_support_lineage_incomplete_candidate_count')}",
        f"aggregate_support_identity_candidate_link_count={entity.get('aggregate_support_identity_candidate_link_count')}",
        f"aggregate_support_identity_relation_review_required_count={entity.get('aggregate_support_identity_relation_review_required_count')}",
        f"aggregate_support_identity_relation_input_state={entity.get('aggregate_support_identity_relation_input_state')}",
        f"aggregate_support_trace_cohort_context_link_count={entity.get('aggregate_support_trace_cohort_context_link_count')}",
        f"aggregate_support_trace_candidate_ref_count={entity.get('aggregate_support_trace_candidate_ref_count')}",
        f"aggregate_support_trace_relation_review_required_count={entity.get('aggregate_support_trace_relation_review_required_count')}",
        f"aggregate_support_trace_relation_input_state={entity.get('aggregate_support_trace_relation_input_state')}",
        f"aggregate_support_trace_relation_review_bound={entity.get('aggregate_support_trace_relation_review_bound')}",
        f"C01_status={c01.get('status')}",
        f"C01_progression_aggregate_ref_count={c01.get('progression_aggregate_ref_count')}",
        f"C01_terminal_aggregate_ref_count={c01.get('terminal_aggregate_ref_count')}",
        f"C01_visible_shot_candidate_count={c01.get('visible_shot_candidate_count')}",
        f"C01_review_reason={c01.get('review_reason')}",
        f"hard_block_hits={payload.get('hard_block_hits') or []}",
        f"review_hits={payload.get('review_hits') or []}",
        "aggregate_support_attachment_is_match_local_identity_truth=false",
        "aggregate_support_attachment_is_action_trace_identity=false",
        "aggregate_support_trace_relation_is_individual_action_support=false",
        "aggregate_support_trace_relation_is_physical_action_truth=false",
        "aggregate_support_attachment_is_timeline_identity=false",
        "aggregate_support_attachment_is_independent_vote=false",
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
    match_local_identity = _load_json(output / MATCH_LOCAL_IDENTITY_JSON)
    trackable_traces = _load_json(output / TRACKABLE_TRACE_JSON)
    rows = _flatten_projection(projection)
    entity_views = _entity_views(rows, match_local_identity, trackable_traces)
    if entity_views.get("aggregate_support_lineage_incomplete_candidate_count"):
        review_hits.append("xlsx_entity_view_aggregate_support_lineage_incomplete")
    if entity_views.get("aggregate_support_identity_relation_review_required_count"):
        review_hits.append("xlsx_entity_view_match_local_identity_relation_review_required")
    if entity_views.get("aggregate_support_trace_relation_review_required_count"):
        review_hits.append("xlsx_entity_view_trackable_trace_relation_review_required")
    primitive_projection = _primitive_metrics(features, entity_views)
    primitives = primitive_projection["metrics"]
    admitted_action_family_counts = primitive_projection["admitted_action_family_candidate_counts"]
    if primitive_projection.get("count_contract_review_required") is True:
        review_hits.append("episode_feature_primitive_count_contract_review_required")
    phase_states = _phase_state_candidates(features)
    if any(item.get("count_contract_review_required") is True for item in phase_states):
        review_hits.append("episode_feature_count_contract_review_required")
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
        "primitive_count_contract_review_required": primitive_projection["count_contract_review_required"],
        "primitive_invalid_count_fields": primitive_projection["invalid_count_fields"],
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
                "action_family_candidate_counts": admitted_action_family_counts,
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
        "aggregate_support_attachment_is_match_local_identity_truth": False,
        "aggregate_support_attachment_is_action_trace_identity": False,
        "aggregate_support_trace_relation_is_individual_action_support": False,
        "aggregate_support_trace_relation_is_physical_action_truth": False,
        "aggregate_support_attachment_is_timeline_identity": False,
        "aggregate_support_attachment_is_independent_vote": False,
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
