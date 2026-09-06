from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "process_metric_profile_lite_v1"
ROBUSTNESS_MODULE_ID = "process_robustness_lens_lite_v1"
ACTIVITY_MODULE_ID = "team_episode_activity_lens_lite_v1"
RECIPROCAL_MODULE_ID = "reciprocal_process_chain_lite_v1"
CLAIM_CEILING = "MATCH_LOCAL_PROCESS_AND_VISIBLE_ACTIVITY_METRIC_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "process_metric_profile_lite_v1.json"
OUTPUT_TXT = "process_metric_profile_lite_v1.txt"
ANALYST_TXT = "process_metric_profile_analyst_audit_v1.txt"
GOVERNANCE_CONTRACT = "process_metric_profile_lite_v1.json"

METRIC_DEFINITIONS = [
    {"metric_id": "M_PROCESS_REPEAT_POPULATION_SHARE_CANDIDATE", "construct": "visible same-signature process frequency within eligible reciprocal population", "formula": "visible_repeat_count_candidate / eligible_reciprocal_population_count", "dependency_group": "RECIPROCAL_PROCESS_SIGNATURE_DEPENDENT", "interpretation": "match-local descriptive share only"},
    {"metric_id": "M_PROCESS_EPISODE_DISPERSION_CANDIDATE", "construct": "spread across admitted episode scopes", "formula": "unique_episode_scope_count_candidate / visible_repeat_count_candidate", "dependency_group": "EPISODE_BINDING_DEPENDENT", "interpretation": "descriptive spread, not recurrence truth"},
    {"metric_id": "M_PROCESS_SEGMENT_CONCENTRATION_CANDIDATE", "construct": "largest single episode-scope concentration", "formula": "max_chain_count_in_one_episode_scope / visible_repeat_count_candidate", "dependency_group": "EPISODE_BINDING_DEPENDENT", "interpretation": "segment-locality falsifier surface"},
    {"metric_id": "M_PROCESS_ANCHOR_ACTOR_CONCENTRATION_CANDIDATE", "construct": "maximum anchor-actor presence", "formula": "max_anchor_actor_chain_presence_count / visible_repeat_count_candidate", "dependency_group": "PLAYER_PROCESS_MEMBERSHIP_DEPENDENT", "interpretation": "participation concentration only"},
    {"metric_id": "M_PROCESS_TRACE_MEMBERSHIP_UNIQUENESS_CANDIDATE", "construct": "unique trace IDs relative to trace memberships", "formula": "unique_supporting_trace_count / supporting_trace_membership_count", "dependency_group": "TRACE_DEPENDENCY_GROUP", "interpretation": "trace-reuse descriptor, not independence truth"},
    {"metric_id": "M_PROCESS_VISIBLE_OUTCOME_ENTROPY_CANDIDATE", "construct": "visible outcome-signature dispersion", "formula": "Shannon_entropy(outcome_counts) / log(distinct_outcome_count)", "dependency_group": "VISIBLE_OUTCOME_SIGNATURE_DEPENDENT", "interpretation": "outcome diversity, not success probability"},
    {"metric_id": "M_PROCESS_RECURRENCE_SURFACE_ROBUSTNESS_COMPOSITE_CANDIDATE", "construct": "uncalibrated analyst ranking over spread and dependence surfaces", "formula": "mean(episode_dispersion, 1-anchor_actor_concentration, trace_membership_uniqueness)", "dependency_group": "COMPOSITE_DEPENDENT_SAME_PROCESS_EVIDENCE", "interpretation": "ranking candidate only"},
    {"metric_id": "M_TEAM_VISIBLE_FINAL_THIRD_ACTION_SHARE_CANDIDATE", "construct": "reviewed final-third visible eligible action density", "formula": "FINAL_THIRD_count / known_team_eligible_action_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "not territorial control"},
    {"metric_id": "M_TEAM_VISIBLE_SHOT_ACTION_SHARE_CANDIDATE", "construct": "reviewed shot-family visible eligible action density", "formula": "SHOT_count / known_team_eligible_action_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "not canonical shot count or finishing quality"},
    {"metric_id": "M_TEAM_VISIBLE_SHOT_PER_FINAL_THIRD_ACTION_CANDIDATE", "construct": "terminal density inside final-third visible surface", "formula": "SHOT_count / FINAL_THIRD_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "not conversion probability"},
    {"metric_id": "M_TEAM_VISIBLE_TERMINAL_TO_PASS_RATIO_CANDIDATE", "construct": "reviewed shot-family signal relative to reviewed pass-family signal", "formula": "SHOT_count / PASS_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "not attacking efficiency truth"},
    {"metric_id": "M_TEAM_VISIBLE_CARRY_DRIBBLE_ACTION_SHARE_CANDIDATE", "construct": "reviewed carry+dribble visible density", "formula": "(CARRY_count + DRIBBLE_count) / known_team_eligible_action_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "on-ball action density, not progression quality"},
    {"metric_id": "M_TEAM_VISIBLE_DUEL_TACKLE_ACTION_SHARE_CANDIDATE", "construct": "reviewed duel+tackle visible density", "formula": "(DUEL_count + TACKLE_count) / known_team_eligible_action_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "contact-action density, not pressure geometry"},
    {"metric_id": "M_TEAM_VISIBLE_LOSS_ACTION_SHARE_CANDIDATE", "construct": "reviewed turnover visible density", "formula": "TURNOVER_count / known_team_eligible_action_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "visible turnover density, not possession-loss rate truth"},
    {"metric_id": "M_TEAM_VISIBLE_RECOVERY_INTERCEPTION_SHARE_CANDIDATE", "construct": "reviewed recovery+interception visible density", "formula": "(RECOVERY_count + INTERCEPTION_count) / known_team_eligible_action_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "visible regain-action density, not pressing effectiveness"},
    {"metric_id": "M_TEAM_VISIBLE_RESTART_ACTION_SHARE_CANDIDATE", "construct": "reviewed restart visible density", "formula": "RESTART_count / known_team_eligible_action_count", "dependency_group": "KNOWN_TEAM_REVIEWED_ACTIVITY_SURFACE", "interpretation": "restart surface only"},
]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _ratio(num: int | float, den: int | float) -> float | None:
    return round(float(num) / float(den), 6) if den else None


def build_process_metric_profile(robustness_payload: dict[str, Any], activity_payload: dict[str, Any], reciprocal_payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    for label, payload, module_id in (
        ("robustness", robustness_payload, ROBUSTNESS_MODULE_ID),
        ("activity", activity_payload, ACTIVITY_MODULE_ID),
        ("reciprocal", reciprocal_payload, RECIPROCAL_MODULE_ID),
    ):
        if payload.get("module_id") != module_id:
            blocks.append(f"{label}_module_id_mismatch")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{label}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
            blocks.append(f"{label}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{label}_production_release_claimed")
        if _status(payload.get("status")) == "FAIL_CLOSED" or payload.get("hard_block_hits"):
            blocks.append(f"{label}_input_fail_closed")
        if _status(payload.get("status")) == "REVIEW_REQUIRED":
            reviews.append(f"{label}_upstream_review_required")
    if activity_payload.get("activity_signal_family_source") != "REVIEWED_PROVIDER_SEMANTICS":
        blocks.append("activity_family_source_not_reviewed_provider_semantics")

    eligible_population = int(reciprocal_payload.get("eligible_reciprocal_population_count") or 0)
    process_rows: list[dict[str, Any]] = []
    if not blocks:
        for row in robustness_payload.get("process_robustness_rows") or []:
            if not isinstance(row, dict):
                continue
            repeat_count = int(row.get("visible_repeat_count_candidate") or 0)
            process_rows.append({
                "process_variant_profile_candidate_id": row.get("process_variant_profile_candidate_id"),
                "process_family_signature_candidate": row.get("process_family_signature_candidate"),
                "M_PROCESS_REPEAT_POPULATION_SHARE_CANDIDATE": _ratio(repeat_count, eligible_population),
                "M_PROCESS_EPISODE_DISPERSION_CANDIDATE": row.get("episode_scope_dispersion_ratio_candidate"),
                "M_PROCESS_SEGMENT_CONCENTRATION_CANDIDATE": row.get("segment_concentration_share_candidate"),
                "M_PROCESS_ANCHOR_ACTOR_CONCENTRATION_CANDIDATE": row.get("max_anchor_actor_chain_presence_share_candidate"),
                "M_PROCESS_TRACE_MEMBERSHIP_UNIQUENESS_CANDIDATE": row.get("trace_membership_uniqueness_ratio_candidate"),
                "M_PROCESS_VISIBLE_OUTCOME_ENTROPY_CANDIDATE": row.get("visible_outcome_normalized_entropy_candidate"),
                "M_PROCESS_RECURRENCE_SURFACE_ROBUSTNESS_COMPOSITE_CANDIDATE": row.get("recurrence_surface_robustness_composite_candidate"),
                "metric_eligibility_state": "REVIEW_REQUIRED_INCOMPLETE_EPISODE_BINDING" if int(row.get("incomplete_episode_binding_count") or 0) else "MATCH_LOCAL_CANDIDATE_ELIGIBLE",
                "composite_is_calibrated": False,
                "statistical_significance_tested": False,
                "stable_pattern_truth": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    team_acc: dict[str, dict[str, Any]] = defaultdict(lambda: {"known": 0, "family": Counter(), "zone": Counter(), "team_name": None})
    if not blocks:
        for row in activity_payload.get("team_episode_activity_rows") or []:
            if not isinstance(row, dict):
                continue
            team_id = _clean(row.get("team_identity_candidate_id"))
            if not team_id:
                continue
            acc = team_acc[team_id]
            acc["team_name"] = row.get("team_normalized_key_candidate")
            acc["known"] += int(row.get("known_team_eligible_action_candidate_count") or 0)
            acc["family"].update(row.get("action_family_candidate_counts") or {})
            acc["zone"].update(row.get("zone_candidate_counts") or {})

    team_rows: list[dict[str, Any]] = []
    for team_id, acc in sorted(team_acc.items()):
        known = int(acc["known"])
        family = acc["family"]
        passes = int(family.get("PASS", 0))
        shots = int(family.get("SHOT", 0))
        carry_dribble = int(family.get("CARRY", 0)) + int(family.get("DRIBBLE", 0))
        duel_tackle = int(family.get("DUEL", 0)) + int(family.get("TACKLE", 0))
        losses = int(family.get("TURNOVER", 0))
        regains = int(family.get("RECOVERY", 0)) + int(family.get("INTERCEPTION", 0))
        restarts = int(family.get("RESTART", 0))
        final_third = int(acc["zone"].get("FINAL_THIRD", 0))
        team_rows.append({
            "team_identity_candidate_id": team_id,
            "team_normalized_key_candidate": acc["team_name"],
            "known_team_eligible_action_candidate_count": known,
            "visible_pass_family_candidate_count": passes,
            "visible_shot_family_candidate_count": shots,
            "visible_carry_dribble_family_candidate_count": carry_dribble,
            "visible_duel_tackle_family_candidate_count": duel_tackle,
            "visible_loss_family_candidate_count": losses,
            "visible_recovery_interception_family_candidate_count": regains,
            "visible_restart_family_candidate_count": restarts,
            "visible_final_third_zone_candidate_count": final_third,
            "M_TEAM_VISIBLE_FINAL_THIRD_ACTION_SHARE_CANDIDATE": _ratio(final_third, known),
            "M_TEAM_VISIBLE_SHOT_ACTION_SHARE_CANDIDATE": _ratio(shots, known),
            "M_TEAM_VISIBLE_SHOT_PER_FINAL_THIRD_ACTION_CANDIDATE": _ratio(shots, final_third),
            "M_TEAM_VISIBLE_TERMINAL_TO_PASS_RATIO_CANDIDATE": _ratio(shots, passes),
            "M_TEAM_VISIBLE_PASS_ACTION_SHARE_CANDIDATE": _ratio(passes, known),
            "M_TEAM_VISIBLE_CARRY_DRIBBLE_ACTION_SHARE_CANDIDATE": _ratio(carry_dribble, known),
            "M_TEAM_VISIBLE_DUEL_TACKLE_ACTION_SHARE_CANDIDATE": _ratio(duel_tackle, known),
            "M_TEAM_VISIBLE_LOSS_ACTION_SHARE_CANDIDATE": _ratio(losses, known),
            "M_TEAM_VISIBLE_RECOVERY_INTERCEPTION_SHARE_CANDIDATE": _ratio(regains, known),
            "M_TEAM_VISIBLE_RESTART_ACTION_SHARE_CANDIDATE": _ratio(restarts, known),
            "team_metric_family_source": "REVIEWED_PROVIDER_SEMANTICS",
            "team_metric_surface_is_possession_or_control_truth": False,
            "terminal_ratio_is_finishing_quality_or_conversion_probability": False,
            "final_third_share_is_territorial_control_truth": False,
            "duel_tackle_share_is_pressure_geometry_truth": False,
            "recovery_interception_share_is_pressing_effectiveness_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "PROCESS_AND_TEAM_METRIC_PROFILE_BUILT" if not blocks else "PROCESS_AND_TEAM_METRIC_PROFILE_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "metric_governance_contract": GOVERNANCE_CONTRACT,
        "metric_definitions": METRIC_DEFINITIONS,
        "metric_definition_count": len(METRIC_DEFINITIONS),
        "process_metric_rows": process_rows if not blocks else [],
        "process_metric_row_count": len(process_rows) if not blocks else 0,
        "team_visible_activity_metric_rows": team_rows if not blocks else [],
        "team_visible_activity_metric_row_count": len(team_rows) if not blocks else 0,
        "eligible_reciprocal_population_count": eligible_population if not blocks else 0,
        "composite_metrics_are_calibrated": False,
        "reference_corpus_available": False,
        "cross_match_calibration_available": False,
        "statistical_significance_tested": False,
        "null_model_evaluated": False,
        "threshold_sensitivity_evaluated": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "causal_truth": False,
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
        "HPFA PROCESS METRIC PROFILE LITE V1",
        f"status={payload.get('status')}",
        f"metric_definition_count={payload.get('metric_definition_count', 0)}",
        f"process_metric_row_count={payload.get('process_metric_row_count', 0)}",
        f"team_visible_activity_metric_row_count={payload.get('team_visible_activity_metric_row_count', 0)}",
        "team_metric_family_source=REVIEWED_PROVIDER_SEMANTICS",
        "composite_metrics_are_calibrated=false",
        "statistical_significance_tested=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    lines = [
        "HPFA ANALYST AUDIT — PROCESS + TEAM VISIBLE METRICS",
        "Team funnel ratios use reviewed action families on one known-team eligible surface; process composites are match-local, dependent and uncalibrated.",
    ]
    for row in payload.get("team_visible_activity_metric_rows") or []:
        lines.append(
            f"- {row.get('team_normalized_key_candidate') or row.get('team_identity_candidate_id')}: "
            f"final_third_share={row.get('M_TEAM_VISIBLE_FINAL_THIRD_ACTION_SHARE_CANDIDATE')} "
            f"shot_share={row.get('M_TEAM_VISIBLE_SHOT_ACTION_SHARE_CANDIDATE')} "
            f"shot_per_final_third={row.get('M_TEAM_VISIBLE_SHOT_PER_FINAL_THIRD_ACTION_CANDIDATE')} "
            f"terminal_to_pass={row.get('M_TEAM_VISIBLE_TERMINAL_TO_PASS_RATIO_CANDIDATE')} "
            f"carry_dribble_share={row.get('M_TEAM_VISIBLE_CARRY_DRIBBLE_ACTION_SHARE_CANDIDATE')} "
            f"duel_tackle_share={row.get('M_TEAM_VISIBLE_DUEL_TACKLE_ACTION_SHARE_CANDIDATE')}"
        )
    lines.extend([
        "These ratios are not possession, attacking efficiency, finishing quality, territorial control, pressure geometry, probability or tactical truth.",
        "",
    ])
    analyst_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
