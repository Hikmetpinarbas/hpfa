from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from hpfa.modules.core.active_match_analyst_report_lite.src import report_lite
from hpfa.modules.core.triplex_source_alignment_adapter_lite.src import triplex_source_alignment_adapter as triplex
from hpfa.modules.core.active_match_spine_runner.src.metric_governance_bridge import run_metric_governance_bridge
from hpfa.modules.core.active_match_spine_runner.src.process_story_sidecar import write_process_story_sidecar

MODULE_ID = "active_match_orphan_capability_sidecars_v1"
PROCESS_STORY_DIAGNOSTIC_ARTIFACT = "active_match_process_story_sidecar_v1.json"
PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT = "active_match_process_story_sidecar_v1.txt"
SEMANTIC_ROUTE_ARTIFACT = "semantic_role_action_bundle_candidates_lite_v1.json"
ZFGV_NON_ACTION_ROUTES = {
    "CONTEXT_INTERVAL_ROUTE": "EXTERNAL_OR_MATCH_CONTEXT",
    "PARTICIPATION_INTERVAL_ROUTE": "PROCESS_PARTICIPATION",
    "DERIVED_CONSEQUENCE_ROUTE": "HPFA_DERIVED_CONSEQUENCE",
    "TERMINAL_OUTCOME_ROUTE": "OUTCOME_QUALIFIER",
    "REFERENCE_ROUTE": "RELATIONAL",
    "GOALKEEPER_OPPONENT_REFERENCE_ROUTE": "RELATIONAL",
}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _load_optional_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _zfgv_non_action_route_projection(output: Path) -> dict[str, Any]:
    """Expose already-routed non-action observations without promoting them to events.

    This closes an observability/orphan gap only. Context, participation,
    consequence, outcome and relation routes remain candidates with their upstream
    identity/dependency/time semantics. They do not become action instances,
    possession truth, tactical truth, causality or independent evidence votes.
    """
    payload = _load_optional_json(output / SEMANTIC_ROUTE_ARTIFACT)
    if not payload:
        return {
            "status": "NOT_EVALUATED_PREREQUISITE_MISSING",
            "source_artifact": SEMANTIC_ROUTE_ARTIFACT,
            "observation_route_record_count": 0,
            "route_counts": {},
            "capability_counts": {},
            "observation_refs": [],
            "event_instance_created": False,
            "action_identity_created": False,
            "possession_truth": False,
            "tactical_truth": False,
            "causality_truth": False,
            "independent_evidence_vote_created": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    routes = [
        row for row in (payload.get("semantic_routes") or [])
        if isinstance(row, dict)
        and row.get("semantic_route") in ZFGV_NON_ACTION_ROUTES
        and row.get("route_status") == "PASS"
    ]
    route_counts = Counter(str(row.get("semantic_route")) for row in routes)
    capability_counts = Counter(
        ZFGV_NON_ACTION_ROUTES[str(row.get("semantic_route"))]
        for row in routes
    )
    refs = [
        {
            "evidence_atom_id": row.get("evidence_atom_id"),
            "semantic_route": row.get("semantic_route"),
            "observation_capability": ZFGV_NON_ACTION_ROUTES[str(row.get("semantic_route"))],
            "source_role": row.get("source_role"),
            "semantic_role_candidate": row.get("semantic_role_candidate"),
            "team_identity_candidate_id": row.get("team_identity_candidate_id"),
            "actor_identity_candidate_id": row.get("actor_identity_candidate_id"),
            "claim_ceiling": row.get("claim_ceiling"),
        }
        for row in routes
    ]
    return {
        "status": "PASS" if routes else "REVIEW_REQUIRED",
        "source_artifact": SEMANTIC_ROUTE_ARTIFACT,
        "observation_route_record_count": len(routes),
        "route_counts": dict(sorted(route_counts.items())),
        "capability_counts": dict(sorted(capability_counts.items())),
        "observation_refs": refs,
        "event_instance_created": False,
        "action_identity_created": False,
        "possession_truth": False,
        "tactical_truth": False,
        "causality_truth": False,
        "independent_evidence_vote_created": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_story_diagnostic_projection(process_story: dict[str, Any]) -> dict[str, Any]:
    """Expose process-story metadata without upgrading diagnostics to publication authority.

    The parent contract owns the authority identity. Upstream diagnostic payloads may
    report their declaration for audit, but they cannot redirect publication authority
    or turn the mixed artifact inventory into user-facing evidence.
    """
    artifact_names = {
        Path(str(value)).name
        for value in process_story.get("current_invocation_artifacts") or []
        if str(value or "").strip()
    }
    return {
        "process_story_diagnostic_artifact_semantics": process_story.get("artifact_semantics", "UNKNOWN"),
        "process_story_diagnostic_user_facing_publication_authority": False,
        "process_story_publication_authority_artifact": PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT,
        "process_story_upstream_publication_authority_declaration_matches_contract": (
            process_story.get("publication_authority_artifact") == PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT
        ),
        "process_story_entity_story_count_diagnostic": process_story.get("entity_story_count", 0),
        "process_story_ready_assembly_item_count_diagnostic": process_story.get("ready_assembly_item_count", 0),
        "process_story_diagnostic_counts_are_publication_admission": False,
        "process_story_current_invocation_artifacts_are_publication_authority": False,
        "process_story_diagnostic_artifact": PROCESS_STORY_DIAGNOSTIC_ARTIFACT,
        "process_story_diagnostic_artifact_present_in_current_invocation": (
            PROCESS_STORY_DIAGNOSTIC_ARTIFACT in artifact_names
        ),
        "process_story_publication_authority_artifact_present_in_current_invocation": (
            PROCESS_STORY_PUBLICATION_AUTHORITY_ARTIFACT in artifact_names
        ),
    }


def run_sidecars(active_match_dir: str | Path, out_dir: str | Path, product_root: str | Path) -> dict[str, Any]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    artifacts: list[str] = []
    review_hits: list[str] = []
    hard_blocks: list[str] = []
    construct_path_blocked = False
    construct_path_block_reason: str | None = None

    try:
        baseline = report_lite.write_report(active_match_dir, output, root=product_root)
        baseline_status = baseline.get("status")
        engineering = baseline.get("engineering_evidence") or {}
        for key in ("out_json", "out_txt"):
            value = engineering.get(key)
            if value and Path(str(value)).is_file():
                artifacts.append(str(value))
    except Exception as exc:
        baseline = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
        baseline_status = "REVIEW_REQUIRED"
        review_hits.append(f"active_match_analyst_report_lite_sidecar_failed:{type(exc).__name__}")

    mapping_present = any((output / name).is_file() for name in triplex.MAPPING_FILES)
    if mapping_present:
        try:
            triplex_report = triplex.write_outputs(output, output, root=product_root)
            triplex_status = triplex_report.get("status")
            for value in (triplex_report.get("outputs") or {}).values():
                if value and Path(str(value)).is_file():
                    artifacts.append(str(value))
            if triplex_status != "PASS":
                review_hits.append("triplex_source_alignment_not_pass")
        except Exception as exc:
            triplex_report = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
            triplex_status = "REVIEW_REQUIRED"
            review_hits.append(f"triplex_source_alignment_sidecar_failed:{type(exc).__name__}")
    else:
        triplex_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "source_mapping_contract_or_audit_not_currently_produced",
            "fusion_admissible": False,
        }
        triplex_status = triplex_report["status"]

    try:
        metric_governance = run_metric_governance_bridge(output, product_root)
        metric_governance_status = metric_governance.get("status")
        for value in metric_governance.get("current_invocation_artifacts") or []:
            if value and Path(str(value)).is_file():
                artifacts.append(str(value))
        normalized_governance_status = str(metric_governance_status or "").upper()
        if normalized_governance_status == "FAIL_CLOSED":
            reasons = metric_governance.get("hard_block_hits") or []
            construct_path_block_reason = str(reasons[0]) if reasons else "metric_governance_fail_closed"
            hard_blocks.append(f"metric_governance_construct_path_blocked:{construct_path_block_reason}")
            construct_path_blocked = True
        elif normalized_governance_status != "SMOKE_PASS":
            review_hits.append(f"metric_governance_bridge_{str(metric_governance_status).casefold()}")
    except Exception as exc:
        metric_governance = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
        metric_governance_status = "REVIEW_REQUIRED"
        review_hits.append(f"metric_governance_bridge_sidecar_failed:{type(exc).__name__}")

    zfgv_non_action_routes = _zfgv_non_action_route_projection(output)
    if zfgv_non_action_routes.get("status") == "NOT_EVALUATED_PREREQUISITE_MISSING":
        review_hits.append("zfgv_non_action_routes_prerequisite_missing")

    # The process-story bridge consumes the reconstruction files produced earlier in
    # this same full-spine invocation. It never re-ingests the match and its failures
    # are scoped to the story lane, not promoted to unrelated product lanes.
    try:
        process_story = write_process_story_sidecar(output)
        process_story_status = process_story.get("status")
        for value in process_story.get("current_invocation_artifacts") or []:
            if value and Path(str(value)).is_file():
                artifacts.append(str(value))
        if str(process_story_status or "").upper() != "SMOKE_PASS":
            reason = process_story.get("story_path_block_reason") or "review_required"
            review_hits.append(f"process_story_sidecar_{str(process_story_status).casefold()}:{reason}")
    except Exception as exc:
        process_story = {
            "status": "REVIEW_REQUIRED",
            "story_path_blocked": True,
            "story_path_block_reason": f"process_story_sidecar_exception:{type(exc).__name__}",
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
        process_story_status = "REVIEW_REQUIRED"
        review_hits.append(f"process_story_sidecar_failed:{type(exc).__name__}")

    return {
        "module_id": MODULE_ID,
        # Scoped sidecar failures do not silently become whole-spine football truth
        # failures. They remain explicit review debt while unrelated lanes survive.
        "status": "REVIEW_REQUIRED" if hard_blocks or review_hits else "SMOKE_PASS",
        "active_match_analyst_report_lite_status": baseline_status,
        "triplex_source_alignment_status": triplex_status,
        "triplex_source_alignment_prerequisite_present": mapping_present,
        "metric_governance_bridge_status": metric_governance_status,
        "process_story_sidecar_status": process_story_status,
        "active_match_analyst_report_lite": baseline,
        "triplex_source_alignment": triplex_report,
        "metric_governance_bridge": metric_governance,
        "zfgv_non_action_observation_routes": zfgv_non_action_routes,
        "zfgv_non_action_routes_are_action_instances": False,
        "zfgv_non_action_routes_are_possession_truth": False,
        "process_story_sidecar": process_story,
        "process_story_runtime_bound": process_story.get("story_path_blocked") is False,
        **_process_story_diagnostic_projection(process_story),
        "construct_path_blocked": construct_path_blocked,
        "construct_path_block_reason": construct_path_block_reason,
        "hard_block_hits": _dedupe(hard_blocks),
        "review_hits": _dedupe(review_hits),
        "current_invocation_artifacts": sorted(set(artifacts)),
        "current_invocation_artifacts_are_publication_authority": False,
        "sidecar_outputs_are_primary_truth": False,
        "metric_value_output_allowed": False,
        "construct_truth": False,
        "process_story_is_tactical_plan_truth": False,
        "process_story_is_causality_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "production_release": False,
    }
