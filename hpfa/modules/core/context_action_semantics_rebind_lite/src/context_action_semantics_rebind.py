from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "context_action_semantics_rebind_lite_v1"
MVC_MODULE_ID = "minimum_viable_context_lite_v1"
ROW_NUCLEUS_MODULE_ID = "row_nucleus_inventory_lite_v1"
CLAIM_CEILING = "REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE_ONLY"
OUTPUT_JSON = "context_action_semantics_rebind_lite_v1.json"
OUTPUT_TXT = "context_action_semantics_rebind_lite_v1.txt"
ANALYST_TXT = "context_action_semantics_rebind_analyst_audit_v1.txt"

ROLE_MAP = {
    "TEAM": "TEAM_SURFACE_CANDIDATE",
    "PLAYER": "PLAYER_SURFACE_CANDIDATE",
    "GOALKEEPER": "GOALKEEPER_SURFACE_CANDIDATE",
}

ACTION_ELIGIBILITY = {"ACTION_CANDIDATE_ELIGIBLE"}
NON_ACTION_ROLES = {
    "ATTRIBUTE_REFERENCE",
    "PARTICIPATION_INTERVAL",
    "CONTEXT_INTERVAL",
    "OPPONENT_ACTION_REFERENCE",
    "RECEIVED_ACTION_REFERENCE",
    "ADMINISTRATIVE_MARKER",
    "PERIOD_OR_META",
    "AGGREGATE_METRIC_LABEL",
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _norm(value: Any) -> str:
    return _clean(value).casefold()


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def provider_semantics_module(repo_root: Path):
    src = repo_root / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "src"
    ensure_module_path(src)
    import provider_label_value_semantics  # type: ignore

    return provider_label_value_semantics


def load_registry(repo_root: Path):
    module = provider_semantics_module(repo_root)
    path = (
        repo_root
        / "hpfa"
        / "modules"
        / "core"
        / "provider_label_value_semantics_lite"
        / "registry"
        / "sportsbase_label_semantics_seed_v1.json"
    )
    return module, module.load_registry(path)


def validate_output_root(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"semantic_rebind_input_unreadable:{source.name}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"semantic_rebind_input_malformed:{source.name}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"semantic_rebind_input_not_object:{source.name}")
    return payload


def _validate_inputs(mvc: dict[str, Any], row_nucleus: dict[str, Any]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []

    if mvc.get("module_id") != MVC_MODULE_ID:
        blocks.append("mvc_module_id_mismatch")
    if row_nucleus.get("module_id") != ROW_NUCLEUS_MODULE_ID:
        blocks.append("row_nucleus_module_id_mismatch")
    if mvc.get("canonical_event_count") != "UNKNOWN":
        blocks.append("mvc_canonical_event_count_claimed")
    if row_nucleus.get("canonical_event_count") != "UNKNOWN":
        blocks.append("row_nucleus_canonical_event_count_claimed")
    if mvc.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append("mvc_true_action_count_claimed")
    if row_nucleus.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append("row_nucleus_true_action_count_claimed")
    if mvc.get("production_release") is True or row_nucleus.get("production_release") is True:
        blocks.append("upstream_production_release_claimed")
    if mvc.get("time_admission_status") != "ADMITTED":
        blocks.append("mvc_time_not_admitted")
    if mvc.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("mvc_source_row_order_policy_breached")
    if mvc.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("mvc_same_time_policy_breached")

    binding = mvc.get("row_nucleus_context_binding") or {}
    if binding.get("enabled") is not True:
        blocks.append("row_nucleus_context_binding_missing")
    if binding.get("reflection_inflation_prevented") is not True:
        blocks.append("reflection_inflation_not_prevented")
    if mvc.get("context_occurrence_basis") != "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT":
        blocks.append("context_occurrence_basis_not_row_nucleus")

    contexts = mvc.get("context_candidates")
    nuclei = row_nucleus.get("row_nuclei")
    if not isinstance(contexts, list) or not contexts:
        blocks.append("context_candidates_empty_or_invalid")
        contexts = []
    if not isinstance(nuclei, list) or not nuclei:
        blocks.append("row_nuclei_empty_or_invalid")
        nuclei = []
    if mvc.get("context_candidate_count") != len(contexts):
        blocks.append("context_candidate_count_mismatch")
    if row_nucleus.get("row_nucleus_candidate_count") != len(nuclei):
        blocks.append("row_nucleus_candidate_count_mismatch")
    if len(contexts) != len(nuclei):
        blocks.append("row_nucleus_context_population_mismatch")

    if row_nucleus.get("status") == "FAIL_CLOSED":
        blocks.append("row_nucleus_upstream_fail_closed")
    elif row_nucleus.get("status") == "REVIEW_REQUIRED":
        reviews.append("row_nucleus_upstream_review_required")
    if mvc.get("status") == "FAIL_CLOSED":
        blocks.append("mvc_upstream_fail_closed")
    elif mvc.get("status") != "PASS":
        reviews.append(f"mvc_upstream_status_review:{mvc.get('status')}")

    return sorted(set(blocks)), sorted(set(reviews))


def _raw_label(nucleus: dict[str, Any]) -> str:
    resolved = nucleus.get("resolved_visible_fields") or {}
    return _clean(resolved.get("action") or resolved.get("code"))


def _goalkeeper_opponent_shot_reference_label(normalized_label: str) -> bool:
    if normalized_label in {"shots on target", "shots off target", "free kick shots"}:
        return True
    return normalized_label.startswith("opponent s ") and "shots on target" in normalized_label


def _semantic_record(
    *,
    context: dict[str, Any],
    nucleus: dict[str, Any],
    provider_module: Any,
    registry: dict[str, Any],
) -> dict[str, Any]:
    preserved = context.get("_preserved_unmapped") or {}
    nucleus_id = _clean(preserved.get("row_nucleus_candidate_id"))
    raw_role = _clean(nucleus.get("source_role"))
    provider_role = ROLE_MAP.get(raw_role, "UNKNOWN")
    raw_label = _raw_label(nucleus)

    classified = provider_module.classify_label(
        raw_label,
        source_format="row_nucleus",
        source_role=provider_role,
        registry=registry,
    )

    semantic_role = _clean(classified.get("semantic_role_candidate")) or "UNKNOWN_UNREVIEWED"
    action_family = _clean(classified.get("action_family_candidate")) or "UNKNOWN"
    downstream = _clean(classified.get("downstream_eligibility")) or "BLOCKED_UNKNOWN"
    review_status = _clean(classified.get("review_status")) or "REVIEW_REQUIRED"
    mapping_status = _clean(classified.get("mapping_status")) or "UNKNOWN_UNREVIEWED"

    action_occurrence_eligible = (
        semantic_role == "ACTION_ANCHOR"
        and downstream in ACTION_ELIGIBILITY
        and review_status == "REVIEWED_CANDIDATE"
        and mapping_status in {"EXACT_REVIEWED_CANDIDATE", "PREFIX_RULE_REVIEWED_CANDIDATE"}
    )

    non_action_context_or_reference = (
        not action_occurrence_eligible
        and (
            semantic_role in NON_ACTION_ROLES
            or downstream in {"REFERENCE_ONLY", "PARTICIPATION_ONLY", "CONTEXT_ONLY", "ADMIN_ONLY", "AGGREGATE_ONLY"}
        )
    )

    return {
        "context_id": _clean(context.get("context_id")),
        "row_nucleus_candidate_id": nucleus_id,
        "source_role": raw_role,
        "provider_source_role": provider_role,
        "raw_label": raw_label,
        "normalized_label": provider_module.normalize_label(raw_label),
        "provider_semantic_role_candidate": semantic_role,
        "provider_action_family_candidate": action_family,
        "provider_outcome_candidate": classified.get("outcome_candidate"),
        "provider_restart_type_candidate": classified.get("restart_type_candidate"),
        "provider_shot_result_candidate": classified.get("shot_result_candidate"),
        "provider_action_subtype_candidate": classified.get("action_subtype_candidate"),
        "provider_object_action_family_candidate": classified.get("object_action_family_candidate"),
        "provider_downstream_eligibility": downstream,
        "provider_semantics_mapping_status": mapping_status,
        "provider_semantics_rule_id": classified.get("rule_id"),
        "provider_semantics_review_status": review_status,
        "provider_semantics_confidence_tier": classified.get("confidence_tier"),
        "action_occurrence_eligible": action_occurrence_eligible,
        "non_action_context_or_reference": non_action_context_or_reference,
        "context_time_admission_status": context.get("time_admission_status"),
        "context_minute_candidate": context.get("football_minute_candidate"),
        "context_period_candidate": context.get("period"),
        "context_team_candidate": context.get("team_label"),
        "context_zone_candidate": context.get("zone_candidate"),
        "context_channel_candidate": context.get("channel_candidate"),
        "provider_semantics_is_validated_truth": False,
        "physical_action_truth": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_rebind(
    mvc: dict[str, Any],
    row_nucleus: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else repo_root_from_file()
    blocks, reviews = _validate_inputs(mvc, row_nucleus)
    contexts = mvc.get("context_candidates") if isinstance(mvc.get("context_candidates"), list) else []
    nuclei = row_nucleus.get("row_nuclei") if isinstance(row_nucleus.get("row_nuclei"), list) else []

    nucleus_by_id: dict[str, dict[str, Any]] = {}
    for index, nucleus in enumerate(nuclei):
        if not isinstance(nucleus, dict):
            blocks.append(f"row_nucleus_record_invalid:{index}")
            continue
        nucleus_id = _clean(nucleus.get("row_nucleus_candidate_id"))
        if not nucleus_id:
            blocks.append(f"row_nucleus_id_missing:{index}")
            continue
        if nucleus_id in nucleus_by_id:
            blocks.append(f"duplicate_row_nucleus_id:{nucleus_id}")
        nucleus_by_id[nucleus_id] = nucleus

    if blocks:
        return _fail_payload(blocks, reviews, len(contexts), len(nucleus_by_id))

    provider_module, registry = load_registry(root)
    records: list[dict[str, Any]] = []
    seen_context_ids: set[str] = set()
    seen_nucleus_ids: set[str] = set()

    for index, context in enumerate(contexts):
        if not isinstance(context, dict):
            blocks.append(f"context_record_invalid:{index}")
            continue
        context_id = _clean(context.get("context_id"))
        if not context_id:
            blocks.append(f"context_id_missing:{index}")
            continue
        if context_id in seen_context_ids:
            blocks.append(f"duplicate_context_id:{context_id}")
        seen_context_ids.add(context_id)

        preserved = context.get("_preserved_unmapped") or {}
        nucleus_id = _clean(preserved.get("row_nucleus_candidate_id"))
        nucleus = nucleus_by_id.get(nucleus_id)
        if not nucleus:
            blocks.append(f"context_row_nucleus_ref_invalid:{context_id}")
            continue
        if nucleus_id in seen_nucleus_ids:
            blocks.append(f"row_nucleus_semantic_assignment_duplicate:{nucleus_id}")
        seen_nucleus_ids.add(nucleus_id)
        records.append(
            _semantic_record(
                context=context,
                nucleus=nucleus,
                provider_module=provider_module,
                registry=registry,
            )
        )

    if set(nucleus_by_id) != seen_nucleus_ids:
        blocks.append("row_nucleus_semantic_assignment_coverage_mismatch")

    blocks = sorted(set(blocks))
    if blocks:
        return _fail_payload(blocks, reviews, len(contexts), len(nucleus_by_id))

    mapping_counts = Counter(row["provider_semantics_mapping_status"] for row in records)
    role_counts = Counter(row["provider_semantic_role_candidate"] for row in records)
    downstream_counts = Counter(row["provider_downstream_eligibility"] for row in records)
    action_family_counts = Counter(
        row["provider_action_family_candidate"]
        for row in records
        if row["action_occurrence_eligible"]
    )
    source_role_counts = Counter(row["source_role"] for row in records)

    reviewed_bound_count = sum(
        1 for row in records if row["provider_semantics_review_status"] == "REVIEWED_CANDIDATE"
    )
    action_eligible_count = sum(1 for row in records if row["action_occurrence_eligible"])
    non_action_count = sum(1 for row in records if row["non_action_context_or_reference"])
    unresolved_count = sum(
        1
        for row in records
        if row["provider_semantics_review_status"] != "REVIEWED_CANDIDATE"
        or row["provider_semantics_mapping_status"] in {
            "TOKEN_FALLBACK_REVIEW_REQUIRED",
            "CONFLICT_REVIEW_REQUIRED",
            "UNKNOWN_UNREVIEWED",
        }
    )

    team_goal_kick_length = [
        row
        for row in records
        if row["source_role"] == "TEAM"
        and row["normalized_label"].startswith("goal kicks ")
        and any(token in row["normalized_label"] for token in ("short", "medium", "long"))
    ]
    gk_goal_kicks = [
        row
        for row in records
        if row["source_role"] == "GOALKEEPER"
        and row.get("provider_restart_type_candidate") == "GOAL_KICK"
    ]
    lost_ball_rows = [row for row in records if row["normalized_label"].startswith("lost balls")]
    recovery_rows = [row for row in records if row["normalized_label"].startswith("ball recoveries")]
    reviewed_lost_ball_rows = [
        row for row in lost_ball_rows if row["provider_semantics_review_status"] == "REVIEWED_CANDIDATE"
    ]
    reviewed_recovery_rows = [
        row for row in recovery_rows if row["provider_semantics_review_status"] == "REVIEWED_CANDIDATE"
    ]
    gk_shot_reference_rows = [
        row
        for row in records
        if row["source_role"] == "GOALKEEPER"
        and _goalkeeper_opponent_shot_reference_label(row["normalized_label"])
    ]

    lost_ball_mismatches = [
        row
        for row in lost_ball_rows
        if not (
            row["provider_semantics_review_status"] == "REVIEWED_CANDIDATE"
            and row["provider_semantic_role_candidate"] == "ACTION_ANCHOR"
            and row["provider_action_family_candidate"] == "TURNOVER"
            and row["provider_downstream_eligibility"] == "ACTION_CANDIDATE_ELIGIBLE"
            and row["action_occurrence_eligible"] is True
        )
    ]
    recovery_mismatches = [
        row
        for row in recovery_rows
        if not (
            row["provider_semantics_review_status"] == "REVIEWED_CANDIDATE"
            and row["provider_semantic_role_candidate"] == "ACTION_ANCHOR"
            and row["provider_action_family_candidate"] == "RECOVERY"
            and row["provider_downstream_eligibility"] == "ACTION_CANDIDATE_ELIGIBLE"
            and row["action_occurrence_eligible"] is True
        )
    ]
    gk_shot_reference_mismatches = [
        row
        for row in gk_shot_reference_rows
        if not (
            row["provider_semantic_role_candidate"] == "OPPONENT_ACTION_REFERENCE"
            and row["provider_action_family_candidate"] == "SHOT"
            and row["provider_downstream_eligibility"] == "REFERENCE_ONLY"
            and row["action_occurrence_eligible"] is False
            and row["non_action_context_or_reference"] is True
        )
    ]

    collision_audit = {
        "team_goal_kick_length_record_count": len(team_goal_kick_length),
        "team_goal_kick_length_action_occurrence_eligible_count": sum(
            1 for row in team_goal_kick_length if row["action_occurrence_eligible"]
        ),
        "goalkeeper_goal_kick_record_count": len(gk_goal_kicks),
        "goalkeeper_goal_kick_action_occurrence_eligible_count": sum(
            1 for row in gk_goal_kicks if row["action_occurrence_eligible"]
        ),
        "lost_ball_record_count": len(lost_ball_rows),
        "lost_ball_reviewed_record_count": len(reviewed_lost_ball_rows),
        "lost_ball_turnover_candidate_count": sum(
            1
            for row in lost_ball_rows
            if row["provider_semantics_review_status"] == "REVIEWED_CANDIDATE"
            and row["provider_action_family_candidate"] == "TURNOVER"
            and row["action_occurrence_eligible"]
        ),
        "lost_ball_reconciliation_mismatch_count": len(lost_ball_mismatches),
        "ball_recovery_record_count": len(recovery_rows),
        "ball_recovery_reviewed_record_count": len(reviewed_recovery_rows),
        "ball_recovery_candidate_count": sum(
            1
            for row in recovery_rows
            if row["provider_semantics_review_status"] == "REVIEWED_CANDIDATE"
            and row["provider_action_family_candidate"] == "RECOVERY"
            and row["action_occurrence_eligible"]
        ),
        "ball_recovery_reconciliation_mismatch_count": len(recovery_mismatches),
        "goalkeeper_shot_reference_record_count": len(gk_shot_reference_rows),
        "goalkeeper_shot_reference_action_occurrence_eligible_count": sum(
            1 for row in gk_shot_reference_rows if row["action_occurrence_eligible"]
        ),
        "goalkeeper_shot_reference_routing_mismatch_count": len(gk_shot_reference_mismatches),
    }

    if collision_audit["team_goal_kick_length_action_occurrence_eligible_count"]:
        blocks.append("team_goal_kick_length_reference_promoted_to_action_occurrence")
    if collision_audit["goalkeeper_shot_reference_action_occurrence_eligible_count"]:
        blocks.append("goalkeeper_opponent_shot_reference_promoted_to_action_occurrence")
    if collision_audit["goalkeeper_shot_reference_routing_mismatch_count"]:
        blocks.append("goalkeeper_opponent_shot_reference_routing_incomplete")
    if team_goal_kick_length and collision_audit["team_goal_kick_length_record_count"] != sum(
        1 for row in team_goal_kick_length if row["non_action_context_or_reference"]
    ):
        blocks.append("team_goal_kick_length_reference_routing_incomplete")
    if collision_audit["lost_ball_reconciliation_mismatch_count"]:
        blocks.append("lost_ball_turnover_reconciliation_mismatch")
    if collision_audit["ball_recovery_reconciliation_mismatch_count"]:
        blocks.append("ball_recovery_reconciliation_mismatch")

    if unresolved_count:
        reviews.append("provider_semantics_unresolved_rows_visible")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "CONTEXT_ACTION_SEMANTICS_REBOUND" if not blocks else "CONTEXT_ACTION_SEMANTICS_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "input_context_count": len(contexts),
        "input_row_nucleus_count": len(nucleus_by_id),
        "context_action_semantic_records": records,
        "context_action_semantic_record_count": len(records),
        "context_semantic_assignment_complete": len(records) == len(contexts) == len(nucleus_by_id),
        "reviewed_provider_semantics_bound_count": reviewed_bound_count,
        "action_occurrence_eligible_count": action_eligible_count,
        "non_action_context_or_reference_count": non_action_count,
        "provider_semantics_unresolved_or_review_required_count": unresolved_count,
        "provider_semantics_mapping_status_counts": dict(sorted(mapping_counts.items())),
        "provider_semantic_role_counts": dict(sorted(role_counts.items())),
        "provider_downstream_eligibility_counts": dict(sorted(downstream_counts.items())),
        "eligible_action_family_candidate_counts": dict(sorted(action_family_counts.items())),
        "source_role_counts": dict(sorted(source_role_counts.items())),
        "semantic_collision_audit": collision_audit,
        "reflection_inflation_prevented": True,
        "context_occurrence_basis": "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT",
        "row_nucleus_is_action_occurrence_truth": False,
        "reference_participation_context_adds_action_volume": False,
        "review_limited_semantics_adds_action_volume": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "physical_action_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "production_release": False,
    }


def _fail_payload(blocks: list[str], reviews: list[str], context_count: int, nucleus_count: int) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "CONTEXT_ACTION_SEMANTICS_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "input_context_count": context_count,
        "input_row_nucleus_count": nucleus_count,
        "context_action_semantic_records": [],
        "context_action_semantic_record_count": 0,
        "context_semantic_assignment_complete": False,
        "reviewed_provider_semantics_bound_count": 0,
        "action_occurrence_eligible_count": 0,
        "non_action_context_or_reference_count": 0,
        "provider_semantics_unresolved_or_review_required_count": 0,
        "semantic_collision_audit": {},
        "reflection_inflation_prevented": False,
        "reference_participation_context_adds_action_volume": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "physical_action_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "production_release": False,
    }


def _summary_text(report: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA CONTEXT ACTION SEMANTICS REBIND LITE V1",
        "==============================================",
        f"status={report.get('status')}",
        f"input_context_count={report.get('input_context_count')}",
        f"reviewed_provider_semantics_bound_count={report.get('reviewed_provider_semantics_bound_count')}",
        f"action_occurrence_eligible_count={report.get('action_occurrence_eligible_count')}",
        f"non_action_context_or_reference_count={report.get('non_action_context_or_reference_count')}",
        f"provider_semantics_unresolved_or_review_required_count={report.get('provider_semantics_unresolved_or_review_required_count')}",
        f"eligible_action_family_candidate_counts={report.get('eligible_action_family_candidate_counts')}",
        f"semantic_collision_audit={report.get('semantic_collision_audit')}",
        f"hard_block_hits={report.get('hard_block_hits')}",
        f"review_hits={report.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "phase_truth=false",
        "rhythm_truth=false",
        "production_release=false",
        "",
    ])


def _analyst_text(report: dict[str, Any]) -> str:
    audit = report.get("semantic_collision_audit") or {}
    lines = [
        "HPFA ANALYST AUDIT — CONTEXT ACTION SEMANTICS REBIND",
        f"Visible context rows: {report.get('input_context_count', 0)}",
        f"Reviewed provider semantics bound: {report.get('reviewed_provider_semantics_bound_count', 0)}",
        f"Action-occurrence eligible rows: {report.get('action_occurrence_eligible_count', 0)}",
        f"Context/reference/participation rows kept out of action volume: {report.get('non_action_context_or_reference_count', 0)}",
        "",
        "Provider semantic collision checks:",
        f"- TEAM goal-kick-length references visible: {audit.get('team_goal_kick_length_record_count', 0)}; promoted to action occurrence: {audit.get('team_goal_kick_length_action_occurrence_eligible_count', 0)}",
        f"- GOALKEEPER goal-kick action anchors visible: {audit.get('goalkeeper_goal_kick_action_occurrence_eligible_count', 0)}",
        f"- Lost-ball reviewed rows: {audit.get('lost_ball_reviewed_record_count', 0)}; reconciliation mismatches: {audit.get('lost_ball_reconciliation_mismatch_count', 0)}",
        f"- Ball-recovery reviewed rows: {audit.get('ball_recovery_reviewed_record_count', 0)}; reconciliation mismatches: {audit.get('ball_recovery_reconciliation_mismatch_count', 0)}",
        f"- Goalkeeper opponent-shot reference labels visible: {audit.get('goalkeeper_shot_reference_record_count', 0)}; routing mismatches: {audit.get('goalkeeper_shot_reference_routing_mismatch_count', 0)}; promoted to action occurrence: {audit.get('goalkeeper_shot_reference_action_occurrence_eligible_count', 0)}",
        "",
        "Safe meaning: row-level context remains visible, but only reviewed action-anchor candidates may contribute to future action-volume analysis.",
        "This output does not establish physical action count, possession, sequence, phase, rhythm or tactical truth.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(input_dir).expanduser().resolve(strict=False)
    output = validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    mvc = _load_json(source / "minimum_viable_context_lite_v1.json")
    row_nucleus = _load_json(source / "row_nucleus_inventory_lite_v1.json")
    report = build_rebind(mvc, row_nucleus, repo_root=repo_root)
    report["outputs"] = {
        "json": str(output / OUTPUT_JSON),
        "summary": str(output / OUTPUT_TXT),
        "analyst": str(output / ANALYST_TXT),
    }
    (output / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / OUTPUT_TXT).write_text(_summary_text(report), encoding="utf-8")
    (output / ANALYST_TXT).write_text(_analyst_text(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Context Action Semantics Rebind Lite V1")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report = write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "input_context_count": report.get("input_context_count"),
        "action_occurrence_eligible_count": report.get("action_occurrence_eligible_count"),
        "non_action_context_or_reference_count": report.get("non_action_context_or_reference_count"),
        "provider_semantics_unresolved_or_review_required_count": report.get("provider_semantics_unresolved_or_review_required_count"),
        "semantic_collision_audit": report.get("semantic_collision_audit"),
        "hard_block_hits": report.get("hard_block_hits"),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
