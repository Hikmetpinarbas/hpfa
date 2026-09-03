from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "professional_finding_candidate_lite_v1"
RECIPROCAL_MODULE_ID = "reciprocal_process_chain_lite_v1"
ROBUSTNESS_MODULE_ID = "process_robustness_lens_lite_v1"
METRIC_MODULE_ID = "process_metric_profile_lite_v1"
RECONCILIATION_MODULE_ID = "match_reconciliation_ledger_lite_v2"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "professional_finding_candidate_lite_v1.json"
OUTPUT_TXT = "professional_finding_candidate_lite_v1.txt"
ANALYST_TXT = "professional_finding_candidate_analyst_audit_v1.txt"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _signature_text(signature: dict[str, Any]) -> str:
    anchor = "+".join(signature.get("anchor_action_families") or ["UNKNOWN"])
    response = "+".join(signature.get("response_action_families") or ["UNKNOWN"])
    return f"{anchor} -> {response}"


def build_professional_finding_candidates(
    reciprocal_payload: dict[str, Any],
    robustness_payload: dict[str, Any],
    metric_payload: dict[str, Any],
    reconciliation_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build auditable analyst argument candidates, not released final findings.

    Every sentence carries explicit supporting chain/episode/player/metric references,
    counterevidence, unresolved alternative explanations and withdrawal conditions.
    Final claim output stays closed while counter-search/statistical/calibration debts
    remain open.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    expected = (
        ("reciprocal", reciprocal_payload, RECIPROCAL_MODULE_ID),
        ("robustness", robustness_payload, ROBUSTNESS_MODULE_ID),
        ("metric", metric_payload, METRIC_MODULE_ID),
        ("reconciliation", reconciliation_payload, RECONCILIATION_MODULE_ID),
    )
    for label, payload, module_id in expected:
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

    profiles = reciprocal_payload.get("process_variant_profiles") or []
    findings = reciprocal_payload.get("defeasible_process_finding_inputs") or []
    robustness_rows = robustness_payload.get("process_robustness_rows") or []
    metric_rows = metric_payload.get("process_metric_rows") or []
    reconciliation_edges = reconciliation_payload.get("reciprocal_consistency_edges") or []

    robustness_by_profile = {
        _clean(row.get("process_variant_profile_candidate_id")): row
        for row in robustness_rows if isinstance(row, dict) and _clean(row.get("process_variant_profile_candidate_id"))
    }
    metric_by_profile = {
        _clean(row.get("process_variant_profile_candidate_id")): row
        for row in metric_rows if isinstance(row, dict) and _clean(row.get("process_variant_profile_candidate_id"))
    }
    finding_by_chain = {
        _clean(row.get("reciprocal_process_chain_candidate_id")): row
        for row in findings if isinstance(row, dict) and _clean(row.get("reciprocal_process_chain_candidate_id"))
    }
    edge_by_chain = {
        _clean(row.get("reciprocal_process_chain_candidate_id")): row
        for row in reconciliation_edges if isinstance(row, dict) and _clean(row.get("reciprocal_process_chain_candidate_id"))
    }

    rows: list[dict[str, Any]] = []
    if not blocks:
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            profile_id = _clean(profile.get("process_variant_profile_candidate_id"))
            robustness = robustness_by_profile.get(profile_id) or {}
            metric = metric_by_profile.get(profile_id) or {}
            repeat_count = int(profile.get("visible_repeat_count_candidate") or 0)
            if repeat_count <= 1:
                continue
            signature = profile.get("process_family_signature_candidate") or {}
            signature_text = _signature_text(signature)
            chain_ids = [
                _clean(value) for value in (profile.get("reciprocal_process_chain_candidate_ids") or []) if _clean(value)
            ]
            episode_scopes = profile.get("episode_scope_candidates") or []
            episode_ids = sorted({
                _clean(value)
                for scope in episode_scopes if isinstance(scope, dict)
                for value in (
                    scope.get("anchor_episode_candidate_id"),
                    scope.get("response_episode_candidate_id"),
                    scope.get("counter_response_episode_candidate_id"),
                )
                if _clean(value) and _clean(value) != "NO_VISIBLE_COUNTER_RESPONSE"
            })
            actor_ids: set[str] = set()
            role_actor_ids: dict[str, set[str]] = {"anchor": set(), "response": set(), "counter_response": set()}
            for chain_id in chain_ids:
                edge = edge_by_chain.get(chain_id) or {}
                roles = edge.get("roles") if isinstance(edge, dict) else {}
                roles = roles if isinstance(roles, dict) else {}
                for role in role_actor_ids:
                    role_row = roles.get(role) if isinstance(roles.get(role), dict) else {}
                    ids = {
                        _clean(actor) for actor in (role_row.get("actor_identity_candidate_ids") or []) if _clean(actor)
                    }
                    role_actor_ids[role].update(ids)
                    actor_ids.update(ids)

            direct_counter_ids: set[str] = set()
            dependent_support_ids: set[str] = set()
            for chain_id in chain_ids:
                finding = finding_by_chain.get(chain_id) or {}
                direct_counter_ids.update(
                    _clean(value) for value in (finding.get("counterevidence_chain_ids") or []) if _clean(value)
                )
                dependent_support_ids.update(
                    _clean(value) for value in (finding.get("dependent_support_chain_ids") or []) if _clean(value)
                )

            incomplete = int(profile.get("incomplete_episode_binding_count") or 0)
            unique_scopes = int(profile.get("unique_episode_scope_count_candidate") or 0)
            outcomes = int(profile.get("distinct_visible_outcome_signature_count_candidate") or 0)
            segment_state = robustness.get("segment_only_falsifier_state_candidate")
            if incomplete:
                state = "BLOCKED_INCOMPLETE_EPISODE_BINDING"
                safe_sentence = (
                    f"Within this match, the visible {signature_text} process-family signature appeared {repeat_count} times, "
                    f"but at least one repeat lacks complete admitted episode binding; do not generalize the repeat beyond local process visibility."
                )
            elif segment_state == "SEGMENT_ONLY_RISK_PRESENT":
                state = "FRAGILE_LOCAL_REPEAT_ONLY"
                safe_sentence = (
                    f"Within this match, the visible {signature_text} process-family signature appeared {repeat_count} times but remained confined to one admitted episode scope; treat it as a local repeat, not a match-wide pattern."
                )
            elif outcomes > 1:
                state = "QUALIFIED_MULTI_EPISODE_REPEAT_WITH_OUTCOME_VARIATION"
                safe_sentence = (
                    f"Within this match, the visible {signature_text} process-family signature appeared {repeat_count} times across {unique_scopes} admitted episode scopes and produced {outcomes} visible outcome signatures; this supports repeated process visibility but not a stable tactical tendency or predictable outcome."
                )
            else:
                state = "QUALIFIED_MULTI_EPISODE_REPEAT_SAME_VISIBLE_OUTCOME"
                safe_sentence = (
                    f"Within this match, the visible {signature_text} process-family signature appeared {repeat_count} times across {unique_scopes} admitted episode scopes with one visible outcome signature; this remains match-local descriptive evidence, not recurrence or tactical truth."
                )

            alternative_explanations = [
                {
                    "type": "PLAYER_CONCENTRATION",
                    "state": robustness.get("player_outlier_search_state_candidate"),
                    "max_anchor_actor_chain_presence_share_candidate": robustness.get("max_anchor_actor_chain_presence_share_candidate"),
                    "threshold_policy": "NOT_CALIBRATED",
                },
                {
                    "type": "SEGMENT_CONCENTRATION",
                    "state": segment_state,
                    "segment_concentration_share_candidate": robustness.get("segment_concentration_share_candidate"),
                },
                {
                    "type": "OPPONENT_SYMMETRY",
                    "state": robustness.get("opponent_symmetry_falsifier_state_candidate"),
                },
                {
                    "type": "TRACE_DEPENDENCY",
                    "state": "MEASURED_NOT_INDEPENDENCE_TRUTH",
                    "trace_membership_uniqueness_ratio_candidate": robustness.get("trace_membership_uniqueness_ratio_candidate"),
                },
                {
                    "type": "CONTEXT_DEPENDENCE",
                    "state": "NOT_EVALUATED_V1",
                },
                {
                    "type": "THRESHOLD_SENSITIVITY",
                    "state": "NOT_EVALUATED_V1",
                },
                {
                    "type": "VIDEO_TRACKING_ALTERNATIVE",
                    "state": "REQUIRES_VIDEO_OR_TRACKING_FOR_OFF_BALL_TACTICAL_EXPLANATION",
                },
            ]

            metric_refs = {
                key: value for key, value in metric.items()
                if key.startswith("M_PROCESS_")
            }
            rows.append({
                "professional_finding_candidate_id": "pfc_" + _digest(profile_id)[:24],
                "finding_state_candidate": state,
                "process_variant_profile_candidate_id": profile_id,
                "process_family_signature_candidate": signature,
                "safe_analyst_sentence_candidate": safe_sentence,
                "support": {
                    "visible_repeat_count_candidate": repeat_count,
                    "unique_episode_scope_count_candidate": unique_scopes,
                    "supporting_reciprocal_process_chain_candidate_ids": chain_ids,
                    "supporting_episode_candidate_ids": episode_ids,
                    "supporting_actor_identity_candidate_ids": sorted(actor_ids),
                    "anchor_actor_identity_candidate_ids": sorted(role_actor_ids["anchor"]),
                    "response_actor_identity_candidate_ids": sorted(role_actor_ids["response"]),
                    "counter_response_actor_identity_candidate_ids": sorted(role_actor_ids["counter_response"]),
                    "dependent_support_chain_ids": sorted(dependent_support_ids),
                    "metric_candidate_values": metric_refs,
                },
                "counterevidence": {
                    "direct_visible_outcome_counterevidence_chain_ids": sorted(direct_counter_ids),
                    "visible_outcome_signature_count_candidate": outcomes,
                    "visible_outcome_normalized_entropy_candidate": robustness.get("visible_outcome_normalized_entropy_candidate"),
                    "segment_only_falsifier_state_candidate": segment_state,
                    "opponent_symmetry_falsifier_state_candidate": robustness.get("opponent_symmetry_falsifier_state_candidate"),
                    "leave_one_episode_scope_out_repeat_survives_candidate": robustness.get("leave_one_episode_scope_out_repeat_survives_candidate"),
                    "leave_top_anchor_actor_out_repeat_survives_candidate": robustness.get("leave_top_anchor_actor_out_repeat_survives_candidate"),
                },
                "alternative_explanations": alternative_explanations,
                "uncertainty": {
                    "episode_binding_incomplete_count": incomplete,
                    "composite_metric_calibrated": False,
                    "statistical_significance_tested": False,
                    "cross_match_reference_corpus_available": False,
                    "alternative_explanation_search_complete": False,
                },
                "claim_ceiling": CLAIM_CEILING,
                "withdrawal_condition": (
                    "Withdraw or downgrade if reciprocal process eligibility, episode binding, actor/team reconciliation, visible outcome signature, reflection control, temporal ordering, or supporting metric inputs are invalidated."
                ),
                "forbidden_inference": [
                    "stable tactical pattern",
                    "coach intention",
                    "causal effectiveness",
                    "expected outcome probability",
                    "possession dominance",
                    "team shape",
                    "off-ball mechanism truth",
                ],
                "professional_finding_emitted": False,
                "claim_output_allowed": False,
            })

    status = "FAIL_CLOSED" if blocks else "REVIEW_REQUIRED"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "PROFESSIONAL_FINDING_CANDIDATES_BUILT_REVIEW_REQUIRED" if not blocks else "PROFESSIONAL_FINDING_CANDIDATES_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "professional_finding_candidates": rows if not blocks else [],
        "professional_finding_candidate_count": len(rows) if not blocks else 0,
        "blocked_incomplete_episode_binding_candidate_count": sum(
            row.get("finding_state_candidate") == "BLOCKED_INCOMPLETE_EPISODE_BINDING" for row in rows
        ) if not blocks else 0,
        "fragile_local_repeat_candidate_count": sum(
            row.get("finding_state_candidate") == "FRAGILE_LOCAL_REPEAT_ONLY" for row in rows
        ) if not blocks else 0,
        "qualified_multi_episode_candidate_count": sum(
            str(row.get("finding_state_candidate") or "").startswith("QUALIFIED_MULTI_EPISODE") for row in rows
        ) if not blocks else 0,
        "claim_output_allowed_count": 0,
        "professional_finding_emitted_count": 0,
        "alternative_explanation_search_complete": False,
        "statistical_significance_tested": False,
        "cross_match_reference_corpus_available": False,
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
        "HPFA PROFESSIONAL FINDING CANDIDATE LITE V1",
        f"status={payload.get('status')}",
        f"professional_finding_candidate_count={payload.get('professional_finding_candidate_count', 0)}",
        f"qualified_multi_episode_candidate_count={payload.get('qualified_multi_episode_candidate_count', 0)}",
        f"fragile_local_repeat_candidate_count={payload.get('fragile_local_repeat_candidate_count', 0)}",
        f"blocked_incomplete_episode_binding_candidate_count={payload.get('blocked_incomplete_episode_binding_candidate_count', 0)}",
        "claim_output_allowed_count=0",
        "professional_finding_emitted_count=0",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    ranked = sorted(
        payload.get("professional_finding_candidates") or [],
        key=lambda row: int((row.get("support") or {}).get("visible_repeat_count_candidate") or 0),
        reverse=True,
    )
    lines = [
        "HPFA ANALYST AUDIT — PROFESSIONAL FINDING CANDIDATES",
        "Safe sentences below are evidence-bearing analyst candidates. Final finding release remains closed while alternative-explanation/statistical/calibration debts remain open.",
    ]
    for row in ranked[:25]:
        lines.append(f"- [{row.get('finding_state_candidate')}] {row.get('safe_analyst_sentence_candidate')}")
    lines.extend([
        "No candidate is released as stable tactical pattern, causality, expected outcome probability, coach intention or production truth.",
        "",
    ])
    analyst_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
