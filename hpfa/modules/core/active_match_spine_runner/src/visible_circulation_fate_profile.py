from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


MODULE_ID = "visible_circulation_fate_profile_v1"
CLAIM_CEILING = "MATCH_LOCAL_VISIBLE_CIRCULATION_FATE_PROFILE_CANDIDATE_ONLY"


def build_visible_circulation_fate_profile(
    process_signatures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Describe what visible consequences follow processes containing PASS/CARRY circulation.

    This surface is descriptive and match-local. It does not classify circulation as
    tactically good/bad, sterile/productive, possession-dominant, causal, or coach-intended.
    """
    eligible: list[dict[str, Any]] = []
    for row in process_signatures:
        if not isinstance(row, dict):
            continue
        counts = row.get("action_family_layer_counts") or {}
        pass_n = int(counts.get("PASS") or 0)
        carry_n = int(counts.get("CARRY") or 0)
        if pass_n + carry_n <= 0:
            continue

        shot = row.get("shot_present_annotation_candidate") is True
        loss = bool(row.get("visible_loss_transition_candidate_present"))
        recovery = bool(row.get("visible_recovery_transition_candidate_present"))
        if shot and loss:
            fate = "SHOT_AND_LOSS_VISIBLE"
        elif shot:
            fate = "SHOT_LINKED_VISIBLE"
        elif loss:
            fate = "LOSS_LINKED_VISIBLE"
        elif recovery:
            fate = "RECOVERY_LINKED_VISIBLE"
        else:
            fate = "OTHER_VISIBLE_OR_UNRESOLVED"

        eligible.append({
            "process_development_signature_id": row.get("process_development_signature_id"),
            "team_identity_candidate_id": row.get("team_identity_candidate_id"),
            "process_family_candidate": row.get("process_family_candidate"),
            "period_candidate": row.get("period_candidate"),
            "process_start_candidate": row.get("process_start_candidate"),
            "process_end_candidate": row.get("process_end_candidate"),
            "pass_layer_n": pass_n,
            "carry_layer_n": carry_n,
            "circulation_layer_n": pass_n + carry_n,
            "visible_fate_candidate": fate,
            "shot_linked_visible": shot,
            "loss_linked_visible": loss,
            "recovery_linked_visible": recovery,
            "fate_is_productivity_truth": False,
            "fate_is_sterility_truth": False,
            "fate_is_tactical_quality_truth": False,
            "fate_is_causal_truth": False,
        })

    by_team_family: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        team = str(row.get("team_identity_candidate_id") or "UNKNOWN_TEAM")
        family = str(row.get("process_family_candidate") or "UNKNOWN_PROCESS_FAMILY")
        by_team_family[(team, family)].append(row)

    profiles: list[dict[str, Any]] = []
    for (team, family), rows in sorted(by_team_family.items()):
        fate_counts = Counter(str(row.get("visible_fate_candidate") or "UNKNOWN") for row in rows)
        denominator = len(rows)
        profiles.append({
            "team_identity_candidate_id": team,
            "process_family_candidate": family,
            "eligible_circulation_process_n": denominator,
            "visible_fate_counts": dict(sorted(fate_counts.items())),
            "visible_fate_shares": {
                key: round(value / denominator, 6) if denominator else None
                for key, value in sorted(fate_counts.items())
            },
            "denominator": "VISIBLE_PROCESS_SIGNATURES_WITH_PASS_OR_CARRY_LAYER",
            "sterile_productive_binary_emitted": False,
            "tactical_quality_score_emitted": False,
            "causal_contribution_emitted": False,
        })

    global_counts = Counter(str(row.get("visible_fate_candidate") or "UNKNOWN") for row in eligible)
    status = "PASS" if eligible else "NOT_AVAILABLE"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "binding_state": "VISIBLE_PASS_CARRY_PROCESS_TO_VISIBLE_FATE_CONTEXT",
        "eligible_circulation_process_n": len(eligible),
        "visible_fate_counts": dict(sorted(global_counts.items())),
        "profiles": profiles,
        "rows": eligible,
        "claim_ceiling": CLAIM_CEILING,
        "denominator": "VISIBLE_PROCESS_SIGNATURES_WITH_PASS_OR_CARRY_LAYER",
        "sterile_productive_binary_emitted": False,
        "circulation_is_possession_truth": False,
        "circulation_fate_is_tactical_quality_truth": False,
        "circulation_fate_is_causal_truth": False,
        "coach_intention_truth": False,
        "creates_independent_support": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
