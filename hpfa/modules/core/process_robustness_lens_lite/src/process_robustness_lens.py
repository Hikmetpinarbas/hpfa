from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "process_robustness_lens_lite_v1"
RECIPROCAL_MODULE_ID = "reciprocal_process_chain_lite_v1"
RECONCILIATION_MODULE_ID = "match_reconciliation_ledger_lite_v2"
CLAIM_CEILING = "MATCH_LOCAL_PROCESS_ROBUSTNESS_AND_FALSIFIER_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "process_robustness_lens_lite_v1.json"
OUTPUT_TXT = "process_robustness_lens_lite_v1.txt"
ANALYST_TXT = "process_robustness_lens_analyst_audit_v1.txt"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _episode_scope(chain: dict[str, Any]) -> tuple[str, str, str] | None:
    anchor = _clean(chain.get("anchor_episode_candidate_id"))
    response = _clean(chain.get("response_episode_candidate_id"))
    counter_visible = bool(chain.get("counter_response_visible"))
    counter = _clean(chain.get("counter_response_episode_candidate_id"))
    if not anchor or not response or (counter_visible and not counter):
        return None
    return anchor, response, counter if counter_visible else "NO_VISIBLE_COUNTER_RESPONSE"


def _normalized_entropy(counts: list[int]) -> float:
    total = sum(counts)
    positive = [count for count in counts if count > 0]
    if total <= 0 or len(positive) <= 1:
        return 0.0
    probs = [count / total for count in positive]
    entropy = -sum(p * math.log(p) for p in probs)
    return entropy / math.log(len(positive))


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build_process_robustness_lens(
    reciprocal_payload: dict[str, Any],
    reconciliation_payload: dict[str, Any],
) -> dict[str, Any]:
    """Measure match-local repeat robustness without promoting repeat to pattern truth.

    The lens evaluates exact, observable dependence surfaces: episode concentration,
    actor concentration, anchor-team symmetry, trace-membership reuse and visible
    outcome dispersion. Equal-weight composites are explicitly uncalibrated and
    exist only as analyst-ranking candidates.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    if reciprocal_payload.get("module_id") != RECIPROCAL_MODULE_ID:
        blocks.append("reciprocal_module_id_mismatch")
    if reconciliation_payload.get("module_id") != RECONCILIATION_MODULE_ID:
        blocks.append("reconciliation_module_id_mismatch")
    for label, payload in (("reciprocal", reciprocal_payload), ("reconciliation", reconciliation_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{label}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
            blocks.append(f"{label}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{label}_production_release_claimed")
        if _status(payload.get("status")) == "FAIL_CLOSED" or payload.get("hard_block_hits"):
            blocks.append(f"{label}_input_fail_closed")

    chains = reciprocal_payload.get("reciprocal_process_chain_candidates") or []
    profiles = reciprocal_payload.get("process_variant_profiles") or []
    edges = reconciliation_payload.get("reciprocal_consistency_edges") or []
    if not isinstance(chains, list):
        blocks.append("reciprocal_chain_collection_invalid")
        chains = []
    if not isinstance(profiles, list):
        blocks.append("process_variant_profile_collection_invalid")
        profiles = []
    if not isinstance(edges, list):
        blocks.append("reconciliation_edge_collection_invalid")
        edges = []

    chain_by_id = {
        _clean(row.get("reciprocal_process_chain_candidate_id")): row
        for row in chains if isinstance(row, dict) and _clean(row.get("reciprocal_process_chain_candidate_id"))
    }
    edge_by_chain = {
        _clean(row.get("reciprocal_process_chain_candidate_id")): row
        for row in edges if isinstance(row, dict) and _clean(row.get("reciprocal_process_chain_candidate_id"))
    }

    rows: list[dict[str, Any]] = []
    if not blocks:
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            chain_ids = [
                _clean(value)
                for value in (profile.get("reciprocal_process_chain_candidate_ids") or [])
                if _clean(value)
            ]
            group = [chain_by_id[chain_id] for chain_id in chain_ids if chain_id in chain_by_id]
            if len(group) != len(chain_ids):
                reviews.append(
                    f"profile_chain_lookup_incomplete:{profile.get('process_variant_profile_candidate_id')}"
                )
            repeat_count = len(group)
            complete_scopes = [_episode_scope(chain) for chain in group]
            incomplete_count = sum(scope is None for scope in complete_scopes)
            complete_scope_counter = Counter(scope for scope in complete_scopes if scope is not None)
            unique_scope_count = len(complete_scope_counter)
            max_scope_count = max(complete_scope_counter.values(), default=0)
            segment_concentration = (
                max_scope_count / repeat_count if repeat_count else None
            )

            if repeat_count <= 1:
                segment_state = "NOT_APPLICABLE_SINGLE_INSTANCE"
            elif incomplete_count:
                segment_state = "REVIEW_REQUIRED_INCOMPLETE_EPISODE_BINDING"
            elif unique_scope_count <= 1:
                segment_state = "SEGMENT_ONLY_RISK_PRESENT"
            else:
                segment_state = "NOT_SINGLE_EPISODE_ONLY_VISIBLE"

            leave_one_scope_out_survives = False
            if repeat_count > 1 and incomplete_count == 0 and unique_scope_count >= 2:
                leave_one_scope_out_survives = True
                for removed_scope in complete_scope_counter:
                    remaining = [
                        chain for chain in group
                        if _episode_scope(chain) != removed_scope
                    ]
                    remaining_scopes = {
                        _episode_scope(chain) for chain in remaining if _episode_scope(chain) is not None
                    }
                    if len(remaining) < 2 or len(remaining_scopes) < 2:
                        leave_one_scope_out_survives = False
                        break

            anchor_team_counts = Counter(_clean(chain.get("anchor_team_identity_candidate_id")) for chain in group)
            anchor_team_counts.pop("", None)
            opponent_symmetry_state = (
                "VISIBLE_BOTH_ANCHOR_SIDES"
                if len(anchor_team_counts) >= 2
                else "ONE_ANCHOR_SIDE_ONLY_VISIBLE"
            )

            anchor_actor_presence: Counter[str] = Counter()
            any_role_actor_presence: Counter[str] = Counter()
            chain_anchor_actors: dict[str, set[str]] = {}
            total_trace_memberships = 0
            unique_trace_ids: set[str] = set()
            for chain in group:
                chain_id = _clean(chain.get("reciprocal_process_chain_candidate_id"))
                edge = edge_by_chain.get(chain_id) or {}
                roles = edge.get("roles") if isinstance(edge, dict) else {}
                roles = roles if isinstance(roles, dict) else {}
                anchor_role = roles.get("anchor") if isinstance(roles.get("anchor"), dict) else {}
                anchor_actors = {
                    _clean(actor) for actor in (anchor_role.get("actor_identity_candidate_ids") or []) if _clean(actor)
                }
                chain_anchor_actors[chain_id] = anchor_actors
                for actor in anchor_actors:
                    anchor_actor_presence[actor] += 1
                all_actors: set[str] = set()
                for role_row in roles.values():
                    if not isinstance(role_row, dict):
                        continue
                    all_actors.update(
                        _clean(actor)
                        for actor in (role_row.get("actor_identity_candidate_ids") or [])
                        if _clean(actor)
                    )
                for actor in all_actors:
                    any_role_actor_presence[actor] += 1

                trace_ids = {
                    _clean(trace_id)
                    for trace_id in (chain.get("supporting_trackable_action_trace_candidate_ids") or [])
                    if _clean(trace_id)
                }
                total_trace_memberships += len(trace_ids)
                unique_trace_ids.update(trace_ids)

            top_anchor_actor_id = None
            top_anchor_actor_count = 0
            if anchor_actor_presence:
                top_anchor_actor_id, top_anchor_actor_count = sorted(
                    anchor_actor_presence.items(), key=lambda item: (-item[1], item[0])
                )[0]
            max_anchor_actor_share = (
                top_anchor_actor_count / repeat_count if repeat_count else None
            )
            max_any_role_actor_share = (
                max(any_role_actor_presence.values(), default=0) / repeat_count
                if repeat_count else None
            )

            leave_top_anchor_actor_out_survives = False
            if repeat_count > 1 and top_anchor_actor_id:
                remaining = [
                    chain for chain in group
                    if top_anchor_actor_id not in chain_anchor_actors.get(
                        _clean(chain.get("reciprocal_process_chain_candidate_id")), set()
                    )
                ]
                remaining_scopes = {
                    _episode_scope(chain) for chain in remaining if _episode_scope(chain) is not None
                }
                leave_top_anchor_actor_out_survives = (
                    len(remaining) >= 2 and len(remaining_scopes) >= 2
                )

            trace_membership_uniqueness = (
                len(unique_trace_ids) / total_trace_memberships
                if total_trace_memberships else None
            )

            outcome_profile = profile.get("visible_outcome_profile_candidate") or []
            outcome_counts = [
                int(row.get("chain_count_candidate") or 0)
                for row in outcome_profile if isinstance(row, dict)
            ]
            outcome_entropy = _normalized_entropy(outcome_counts)
            max_outcome_share = (
                max(outcome_counts, default=0) / sum(outcome_counts)
                if sum(outcome_counts) else None
            )

            episode_dispersion = (
                unique_scope_count / repeat_count if repeat_count else None
            )
            actor_independence = (
                1.0 - max_anchor_actor_share
                if max_anchor_actor_share is not None else None
            )
            components = [
                value for value in (
                    episode_dispersion,
                    actor_independence,
                    trace_membership_uniqueness,
                ) if value is not None
            ]
            robustness_composite = _mean(components)

            rows.append({
                "process_variant_profile_candidate_id": profile.get("process_variant_profile_candidate_id"),
                "process_family_signature_candidate": profile.get("process_family_signature_candidate"),
                "visible_repeat_count_candidate": repeat_count,
                "unique_episode_scope_count_candidate": unique_scope_count,
                "incomplete_episode_binding_count": incomplete_count,
                "segment_only_falsifier_state_candidate": segment_state,
                "segment_concentration_share_candidate": (
                    round(segment_concentration, 6) if segment_concentration is not None else None
                ),
                "leave_one_episode_scope_out_repeat_survives_candidate": leave_one_scope_out_survives,
                "anchor_team_occurrence_counts_candidate": dict(sorted(anchor_team_counts.items())),
                "opponent_symmetry_falsifier_state_candidate": opponent_symmetry_state,
                "top_anchor_actor_identity_candidate_id": top_anchor_actor_id,
                "top_anchor_actor_chain_presence_count_candidate": top_anchor_actor_count,
                "max_anchor_actor_chain_presence_share_candidate": (
                    round(max_anchor_actor_share, 6) if max_anchor_actor_share is not None else None
                ),
                "max_any_role_actor_chain_presence_share_candidate": (
                    round(max_any_role_actor_share, 6) if max_any_role_actor_share is not None else None
                ),
                "player_outlier_search_state_candidate": (
                    "EVALUATED_VISIBLE_ACTOR_CONCENTRATION"
                    if repeat_count > 1 and anchor_actor_presence
                    else "NOT_APPLICABLE_OR_NO_ACTOR_MEMBERSHIP"
                ),
                "leave_top_anchor_actor_out_repeat_survives_candidate": leave_top_anchor_actor_out_survives,
                "supporting_trace_membership_count_candidate": total_trace_memberships,
                "supporting_unique_trace_candidate_count": len(unique_trace_ids),
                "trace_membership_uniqueness_ratio_candidate": (
                    round(trace_membership_uniqueness, 6)
                    if trace_membership_uniqueness is not None else None
                ),
                "trace_uniqueness_is_independent_evidence_truth": False,
                "distinct_visible_outcome_signature_count_candidate": len(outcome_counts),
                "visible_outcome_normalized_entropy_candidate": round(outcome_entropy, 6),
                "max_visible_outcome_share_candidate": (
                    round(max_outcome_share, 6) if max_outcome_share is not None else None
                ),
                "episode_scope_dispersion_ratio_candidate": (
                    round(episode_dispersion, 6) if episode_dispersion is not None else None
                ),
                "anchor_actor_independence_candidate": (
                    round(actor_independence, 6) if actor_independence is not None else None
                ),
                "recurrence_surface_robustness_composite_candidate": (
                    round(robustness_composite, 6) if robustness_composite is not None else None
                ),
                "recurrence_surface_robustness_formula": "mean(episode_scope_dispersion_ratio_candidate, anchor_actor_independence_candidate, trace_membership_uniqueness_ratio_candidate)",
                "recurrence_surface_robustness_weighting": "EQUAL_WEIGHT_UNCALIBRATED",
                "recurrence_surface_robustness_is_pattern_truth": False,
                "outcome_entropy_is_success_probability_truth": False,
                "evaluated_falsifier_families": ["SEGMENT_ONLY", "PLAYER_OUTLIER", "OPPONENT_SYMMETRY"],
                "pending_falsifier_families": [
                    "CONTEXT_DEPENDENCE",
                    "THRESHOLD_SENSITIVITY",
                    "FAILED_TRACE_SUPPORT",
                    "DUPLICATE_REFLECTION_RISK",
                    "ALTERNATIVE_EXPLANATION",
                ],
                "claim_ceiling": CLAIM_CEILING,
            })

    repeated_rows = [row for row in rows if int(row.get("visible_repeat_count_candidate") or 0) > 1]
    if _status(reciprocal_payload.get("status")) == "REVIEW_REQUIRED":
        reviews.append("reciprocal_upstream_review_required")
    if _status(reconciliation_payload.get("status")) == "REVIEW_REQUIRED":
        reviews.append("reconciliation_upstream_review_required")

    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "PROCESS_ROBUSTNESS_LENS_BUILT" if not blocks else "PROCESS_ROBUSTNESS_LENS_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "process_robustness_rows": rows if not blocks else [],
        "process_robustness_row_count": len(rows) if not blocks else 0,
        "repeated_process_robustness_row_count": len(repeated_rows) if not blocks else 0,
        "segment_only_risk_profile_count": sum(
            row.get("segment_only_falsifier_state_candidate") == "SEGMENT_ONLY_RISK_PRESENT"
            for row in repeated_rows
        ) if not blocks else 0,
        "leave_one_episode_scope_out_survives_profile_count": sum(
            row.get("leave_one_episode_scope_out_repeat_survives_candidate") is True
            for row in repeated_rows
        ) if not blocks else 0,
        "leave_top_anchor_actor_out_survives_profile_count": sum(
            row.get("leave_top_anchor_actor_out_repeat_survives_candidate") is True
            for row in repeated_rows
        ) if not blocks else 0,
        "both_anchor_sides_visible_profile_count": sum(
            row.get("opponent_symmetry_falsifier_state_candidate") == "VISIBLE_BOTH_ANCHOR_SIDES"
            for row in repeated_rows
        ) if not blocks else 0,
        "composite_metric_is_calibrated": False,
        "statistical_significance_tested": False,
        "stable_pattern_truth": False,
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
        "HPFA PROCESS ROBUSTNESS LENS LITE V1",
        f"status={payload.get('status')}",
        f"process_robustness_row_count={payload.get('process_robustness_row_count', 0)}",
        f"repeated_process_robustness_row_count={payload.get('repeated_process_robustness_row_count', 0)}",
        f"segment_only_risk_profile_count={payload.get('segment_only_risk_profile_count', 0)}",
        f"leave_one_episode_scope_out_survives_profile_count={payload.get('leave_one_episode_scope_out_survives_profile_count', 0)}",
        f"leave_top_anchor_actor_out_survives_profile_count={payload.get('leave_top_anchor_actor_out_survives_profile_count', 0)}",
        f"both_anchor_sides_visible_profile_count={payload.get('both_anchor_sides_visible_profile_count', 0)}",
        "composite_metric_is_calibrated=false",
        "stable_pattern_truth=false",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    ranked = sorted(
        payload.get("process_robustness_rows") or [],
        key=lambda row: (
            int(row.get("visible_repeat_count_candidate") or 0),
            float(row.get("recurrence_surface_robustness_composite_candidate") or 0.0),
        ),
        reverse=True,
    )
    lines = [
        "HPFA ANALYST AUDIT — MATCH-LOCAL PROCESS ROBUSTNESS",
        "Repeat robustness combines episode dispersion, anchor-actor independence and trace-membership uniqueness with equal uncalibrated weight. It is a ranking candidate, not pattern truth.",
    ]
    for row in ranked[:20]:
        lines.append(
            f"- {row.get('process_family_signature_candidate')} repeat={row.get('visible_repeat_count_candidate')} "
            f"episodes={row.get('unique_episode_scope_count_candidate')} robustness={row.get('recurrence_surface_robustness_composite_candidate')} "
            f"outcome_entropy={row.get('visible_outcome_normalized_entropy_candidate')} segment={row.get('segment_only_falsifier_state_candidate')}"
        )
    lines.extend([
        "Do not read the composite as statistical significance, stable tactical pattern, success probability or causality.",
        "",
    ])
    analyst_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
