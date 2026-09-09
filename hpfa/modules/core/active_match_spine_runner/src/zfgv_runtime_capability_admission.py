from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODULE_ID = "zfgv_runtime_capability_admission_v1"
ZFGV_OBSERVATION_MODEL = "MULTI_SURFACE_FOOTBALL_OBSERVATION_FABRIC"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("module_status") or "UNKNOWN").strip().upper()


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(item, dict) for item in value)


def build_runtime_capability_admission(out_dir: str | Path) -> dict[str, Any]:
    """Admit only observation capabilities that have positive current-run evidence.

    This is an observation-capability admission layer, not a truth promotion layer.
    It never creates event identity, metric values, construct truth, tactical truth,
    causal truth, possession truth or independent evidence votes.
    """
    output = Path(out_dir).expanduser().resolve(strict=False)

    trace = _load(output / "trackable_action_trace_candidates_lite_v1.json")
    identity = _load(output / "match_local_identity_candidates_lite_v1.json")
    geometry = _load(output / "visible_geometry_lens_lite_v1.json")
    xlsx = _load(output / "xlsx_surface_audit_lite_v1.json")
    routes = _load(output / "semantic_role_action_bundle_candidates_lite_v1.json")

    admitted: set[str] = set()
    evidence: dict[str, list[dict[str, Any]]] = {}
    review_hits: list[str] = []

    def admit(capability: str, source_artifact: str, reason: str, count: int | None = None) -> None:
        admitted.add(capability)
        row: dict[str, Any] = {
            "source_artifact": source_artifact,
            "admission_basis": reason,
            "admission_scope": "CURRENT_SINGLE_MATCH_OBSERVATION_CAPABILITY_ONLY",
        }
        if count is not None:
            row["visible_record_count"] = count
        evidence.setdefault(capability, []).append(row)

    trace_rows = trace.get("trackable_action_trace_candidates") or []
    if _status(trace) not in {"FAIL_CLOSED", "UNKNOWN"} and _nonempty_list(trace_rows):
        admit("ACTION_EVENT", "trackable_action_trace_candidates_lite_v1.json", "visible_trackable_action_candidates", len(trace_rows))
        temporal_rows = [
            row for row in trace_rows
            if isinstance(row, dict)
            and row.get("period_candidate") not in {None, ""}
            and (row.get("start_candidate") not in {None, ""} or row.get("end_candidate") not in {None, ""})
        ]
        if temporal_rows:
            admit("TEMPORAL", "trackable_action_trace_candidates_lite_v1.json", "period_and_candidate_time_present", len(temporal_rows))
    elif trace:
        review_hits.append("action_event_capability_not_admitted_from_trace")

    actor_rows = identity.get("actor_identity_candidates") or []
    team_rows = identity.get("team_identity_candidates") or []
    identity_count = sum(1 for row in [*actor_rows, *team_rows] if isinstance(row, dict)) if isinstance(actor_rows, list) and isinstance(team_rows, list) else 0
    if _status(identity) not in {"FAIL_CLOSED", "UNKNOWN"} and identity_count > 0:
        admit("ENTITY_ACTOR", "match_local_identity_candidates_lite_v1.json", "match_local_identity_candidates_present", identity_count)
    elif identity:
        review_hits.append("entity_actor_capability_not_admitted_from_identity")

    overall = geometry.get("overall_coordinate_surface") if isinstance(geometry.get("overall_coordinate_surface"), dict) else {}
    coordinate_count = overall.get("coordinate_point_count")
    if _status(geometry) not in {"FAIL_CLOSED", "UNKNOWN"} and _positive_int(coordinate_count):
        admit("SPATIAL", "visible_geometry_lens_lite_v1.json", "raw_provider_coordinate_points_present", int(coordinate_count))
    elif geometry:
        review_hits.append("spatial_capability_not_admitted_from_geometry")

    analyst_evidence = xlsx.get("analyst_evidence") if isinstance(xlsx.get("analyst_evidence"), dict) else {}
    visible_xlsx = analyst_evidence.get("visible_xlsx_surfaces")
    if _status(xlsx) not in {"FAIL_CLOSED", "UNKNOWN"} and _positive_int(visible_xlsx):
        admit("AGGREGATE_TABULAR", "xlsx_surface_audit_lite_v1.json", "visible_xlsx_aggregate_surfaces_present", int(visible_xlsx))
    elif xlsx:
        review_hits.append("aggregate_tabular_capability_not_admitted_from_xlsx")

    semantic_routes = routes.get("semantic_routes") or []
    if isinstance(semantic_routes, list) and _status(routes) not in {"FAIL_CLOSED", "UNKNOWN"}:
        route_map = {
            "PARTICIPATION_INTERVAL_ROUTE": "PROCESS_PARTICIPATION",
            "TERMINAL_OUTCOME_ROUTE": "OUTCOME_QUALIFIER",
            "REFERENCE_ROUTE": "RELATIONAL",
            "GOALKEEPER_OPPONENT_REFERENCE_ROUTE": "RELATIONAL",
            "DERIVED_CONSEQUENCE_ROUTE": "HPFA_DERIVED_INTELLIGENCE",
        }
        counts: dict[str, int] = {}
        for row in semantic_routes:
            if not isinstance(row, dict) or row.get("route_status") != "PASS":
                continue
            capability = route_map.get(str(row.get("semantic_route") or ""))
            if capability:
                counts[capability] = counts.get(capability, 0) + 1
        for capability, count in counts.items():
            admit(capability, "semantic_role_action_bundle_candidates_lite_v1.json", "admitted_non_action_semantic_route_present", count)
    elif routes:
        review_hits.append("non_action_capabilities_not_admitted_from_semantic_routes")

    required_artifacts = {
        "ACTION_EVENT": bool(trace),
        "ENTITY_ACTOR": bool(identity),
        "SPATIAL": bool(geometry),
        "AGGREGATE_TABULAR": bool(xlsx),
        "NON_ACTION_ROUTES": bool(routes),
    }
    evaluated = any(required_artifacts.values())
    return {
        "module_id": MODULE_ID,
        "status": "PASS" if evaluated else "NOT_EVALUATED_PREREQUISITE_MISSING",
        "observation_model": ZFGV_OBSERVATION_MODEL,
        "scope": "CURRENT_SINGLE_MATCH_ONLY",
        "runtime_capability_admission_evaluated": evaluated,
        "admitted_observation_capabilities": sorted(admitted),
        "capability_evidence": evidence,
        "source_artifact_presence": required_artifacts,
        "review_hits": sorted(set(review_hits)),
        "missing_capability_is_false_truth": False,
        "missing_capability_is_zero": False,
        "event_identity_created": False,
        "metric_value_output_allowed": False,
        "construct_truth_granted": False,
        "possession_truth": False,
        "tactical_truth": False,
        "causality_truth": False,
        "independent_evidence_vote_created": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }
