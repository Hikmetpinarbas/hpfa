from __future__ import annotations

import argparse
import json
from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.comparable_outcome_counterevidence_projection import (
    build_comparable_outcome_counterevidence,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.grammar_stable_variant_feature_delta_projection import (
    build_grammar_stable_variant_feature_delta,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.observable_process_variant_binding_projection import (
    build_observable_process_variant_binding,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.process_participation_variant_context_adapter import (
    apply_process_context_to_comparison,
    apply_process_participation_context,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.puzzle_finding_contract_adapter import (
    build_puzzle_finding_contract,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_admission_projection import (
    build_safe_finding_admission,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_occurrence_consequence_burden_adapter import (
    apply_occurrence_consequence_burden_to_admission,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_variant_feature_challenge_adapter import (
    apply_variant_feature_challenge_to_admission,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.supported_sequence_grammar_alignment_projection import (
    build_supported_sequence_grammar_alignment,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.variant_feature_challenge_projection import (
    build_variant_feature_challenge_projection,
)

OUTPUT_NAME = "safe_finding_admission_projection_v1.json"
FEATURE_DELTA_NAME = "grammar_stable_variant_feature_delta_projection_v1.json"
PROCESS_VARIANT_NAME = "observable_process_variant_binding_projection_v1.json"
GRAMMAR_ALIGNMENT_NAME = "supported_sequence_grammar_alignment_projection_v1.json"
PROCESS_PARTICIPATION_NAME = "analyst_episode_process_participation_projection_v1.json"
OCCURRENCE_CONSEQUENCE_NAME = "occurrence_consequence_projection_v1.json"
OCCURRENCE_STATE_TRANSITION_NAME = "occurrence_state_transition_projection_v1.json"
CHALLENGE_NAME = "variant_feature_challenge_projection_v1.json"
PUZZLE_FINDING_NAME = "puzzle_finding_contract_projection_v1.json"
RICH_MULTIFORMAT_NAME = "rich_multiformat_analysis_lattice_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _bind_counterevidence_projection(source_payload: dict, projection: dict) -> dict:
    source_payload["comparable_outcome_counterevidence_status"] = projection.get("status")
    source_payload["comparable_outcome_counterevidence_records"] = list(
        projection.get("comparable_outcome_counterevidence_records") or []
    )
    source_payload["comparable_outcome_counterevidence_record_count"] = int(
        projection.get("comparable_outcome_counterevidence_record_count") or 0
    )
    source_payload["comparable_outcome_contrast_state_counts"] = dict(
        projection.get("comparable_outcome_contrast_state_counts") or {}
    )
    source_payload["comparison_eligible_outcome_record_count"] = int(
        projection.get("comparison_eligible_record_count") or 0
    )
    source_payload["comparable_counterevidence_candidate_count"] = int(
        projection.get("comparable_counterevidence_candidate_count") or 0
    )
    source_payload["canonical_evidence_classification_applied"] = (
        projection.get("canonical_evidence_classification_applied") is True
    )
    source_payload["canonical_evidence_direction_classes"] = list(
        projection.get("canonical_evidence_direction_classes") or []
    )
    source_payload["legacy_canonical_evidence_direction_counts"] = dict(
        projection.get("legacy_canonical_evidence_direction_counts") or {}
    )
    source_payload["branch_canonical_evidence_direction_counts"] = dict(
        projection.get("branch_canonical_evidence_direction_counts") or {}
    )
    source_payload["legacy_dependency_challenge_record_count"] = int(
        projection.get("legacy_dependency_challenge_record_count") or 0
    )
    source_payload["claim_target_denominator_binding_applied"] = (
        projection.get("claim_target_denominator_binding_applied") is True
    )
    source_payload["legacy_denominator_binding_state_counts"] = dict(
        projection.get("legacy_denominator_binding_state_counts") or {}
    )
    source_payload["branch_denominator_binding_state_counts"] = dict(
        projection.get("branch_denominator_binding_state_counts") or {}
    )
    source_payload["pair_record_is_eligible_denominator"] = False
    source_payload["pair_count_is_eligible_denominator"] = False
    source_payload["eligible_denominator_is_independent_evidence_count"] = False
    source_payload["falsification_invalidation_contract_applied"] = (
        projection.get("falsification_invalidation_contract_applied") is True
    )
    source_payload["falsifier_is_invalidator"] = False
    source_payload["invalidator_is_falsifier"] = False
    source_payload["invalidator_is_counterevidence"] = False
    source_payload["invalidator_makes_claim_false"] = False
    source_payload["dependency_challenge_is_evidence_direction"] = False
    source_payload["dependency_challenge_changes_evidence_direction"] = False
    source_payload["non_support_is_counterevidence"] = False
    source_payload["unresolved_is_failure"] = False
    source_payload["counterevidence_independent_support_count"] = 0
    source_payload["counterevidence_is_independent_support"] = False
    source_payload["comparable_outcome_counterevidence_claim_ceiling"] = projection.get("claim_ceiling")
    source_payload["outcome_difference_is_failure_cause_truth"] = False
    source_payload["outcome_difference_is_tactical_pattern_truth"] = False
    source_payload["absence_is_counterevidence"] = False
    source_payload["safe_finding_handoff_candidates"] = list(
        projection.get("safe_finding_handoff_candidates") or []
    )
    source_payload["safe_finding_handoff_candidate_count"] = int(
        projection.get("safe_finding_handoff_candidate_count") or 0
    )
    source_payload["safe_finding_handoff_finding_status_counts"] = dict(
        projection.get("safe_finding_handoff_finding_status_counts") or {}
    )
    source_payload["professional_finding_emitted_count"] = int(
        projection.get("professional_finding_emitted_count") or 0
    )
    source_payload["safe_finding_handoff_professional_emit_allowed"] = False
    source_payload["safe_finding_handoff_claim_ceiling"] = projection.get(
        "safe_finding_handoff_claim_ceiling"
    )
    source_payload["counterexample_pair_count_is_independent_evidence_count"] = False
    source_payload["canonical_event_count"] = "UNKNOWN"
    source_payload["true_action_count"] = "UNKNOWN"
    source_payload["production_release"] = False
    return source_payload


def _missing_sequence_puzzle_contract() -> dict:
    return {
        "module_id": "puzzle_finding_contract_adapter_v1",
        "status": "FAIL_CLOSED",
        "puzzle_finding_contract_version": "PUZZLE_FINDING_V1",
        "puzzle_findings": [],
        "puzzle_finding_count": 0,
        "puzzle_finding_status_counts": {},
        "bound_puzzle_ids": [],
        "safe_finding_handoff_consumed": False,
        "safe_finding_admission_consumed": False,
        "discovery_recomputed": False,
        "comparison_recomputed": False,
        "falsification_recomputed": False,
        "creates_new_evidence": False,
        "creates_new_finding": False,
        "cross_mechanism_fusion_performed": False,
        "mechanism_candidate_emitted": False,
        "game_state_conditioning_ready": False,
        "hard_block_hits": ["sequence_payload_missing_or_invalid"],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": "MATCH_LOCAL_PUZZLE_FINDING_CONTRACT_CANDIDATE_ONLY",
    }




def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _branch_preoutcome_context_enrichment(
    source_payload: dict,
    admission_payload: dict,
    rich_multiformat_payload: dict | None,
    process_participation_payload: dict | None,
) -> dict:
    branch_maps = {
        str(row.get("comparable_set_id") or "").strip(): row
        for row in (source_payload.get("anchor_centered_sequence_branch_maps") or [])
        if isinstance(row, dict) and str(row.get("comparable_set_id") or "").strip()
    }
    handoffs = {
        str(row.get("safe_finding_handoff_candidate_id") or "").strip(): row
        for row in (source_payload.get("safe_finding_handoff_candidates") or [])
        if isinstance(row, dict)
        and str(row.get("safe_finding_handoff_candidate_id") or "").strip()
    }

    rich = rich_multiformat_payload if isinstance(rich_multiformat_payload, dict) else {}
    game_profiles = (
        (rich.get("game_state_process_mix_context") or {}).get("profiles") or []
    )

    process_intervals = []
    if isinstance(process_participation_payload, dict):
        for row in process_participation_payload.get("process_participation_candidates") or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("semantic_role") or "") != "CONTEXT_INTERVAL":
                continue
            team_id = str(row.get("team_identity_candidate_id") or "").strip()
            period = str(row.get("period_candidate") or "").strip()
            family = str(row.get("process_family_candidate") or "").strip()
            start = _as_float(row.get("start_candidate"))
            end = _as_float(row.get("end_candidate"))
            if team_id and period and family and start is not None and end is not None:
                process_intervals.append(
                    {
                        "team_identity_candidate_id": team_id,
                        "period_candidate": period,
                        "process_family_candidate": family,
                        "start_candidate": start,
                        "end_candidate": end,
                    }
                )

    profiles_by_handoff: dict[str, dict] = {}
    state_counts: dict[str, int] = {}

    for decision in admission_payload.get("safe_finding_admission_decisions") or []:
        if not isinstance(decision, dict):
            continue
        handoff_ref = str(
            decision.get("source_safe_finding_handoff_ref") or ""
        ).strip()
        handoff = handoffs.get(handoff_ref)
        if not handoff:
            continue
        comparable_ref = str(handoff.get("source_comparable_set_id") or "").strip()
        branch_map = branch_maps.get(comparable_ref)
        if not branch_map:
            profiles_by_handoff[handoff_ref] = {
                "state": "BRANCH_COMPARABLE_SET_NOT_BOUND",
                "source_comparable_set_id": comparable_ref or None,
                "branch_comparison_context_complete": False,
                "creates_new_evidence": False,
                "creates_independent_support": False,
                "can_change_safe_finding_decision": False,
                "can_authorize_emit": False,
            }
            state_counts["BRANCH_COMPARABLE_SET_NOT_BOUND"] = (
                state_counts.get("BRANCH_COMPARABLE_SET_NOT_BOUND", 0) + 1
            )
            continue

        team_id = str(branch_map.get("team_identity_candidate_id") or "").strip()
        period = str(branch_map.get("period_candidate") or "").strip()
        anchor_time = _as_float(branch_map.get("anchor_time_candidate"))
        anchor_actions = dict(branch_map.get("anchor_action_family_counts") or {})

        matching_game = []
        if team_id and anchor_time is not None:
            for profile in game_profiles:
                if not isinstance(profile, dict):
                    continue
                if str(profile.get("team_identity_candidate_id") or "").strip() != team_id:
                    continue
                start = _as_float(profile.get("segment_start_second_candidate"))
                end = _as_float(profile.get("segment_end_second_candidate"))
                if start is None or end is None:
                    continue
                if start <= anchor_time < end or (start == end == anchor_time):
                    matching_game.append(profile)

        game_states = {
            tuple(sorted((profile.get("score_state_candidate") or {}).items()))
            for profile in matching_game
        }
        game_state_unique = len(game_states) == 1 and len(matching_game) >= 1
        game_state_value = (
            dict(next(iter(game_states))) if game_state_unique else None
        )
        game_binding_state = (
            "SINGLE_SCORE_STATE_SEGMENT_MATCH"
            if game_state_unique
            else (
                "MULTIPLE_SCORE_STATE_SEGMENTS_REVIEW_REQUIRED"
                if matching_game
                else "NO_SCORE_STATE_SEGMENT_MATCH"
            )
        )

        process_families = set()
        if team_id and period and anchor_time is not None:
            for interval in process_intervals:
                if interval["team_identity_candidate_id"] != team_id:
                    continue
                if interval["period_candidate"] != period:
                    continue
                if interval["start_candidate"] <= anchor_time <= interval["end_candidate"]:
                    process_families.add(interval["process_family_candidate"])
        process_binding_state = (
            "SINGLE_PROVIDER_PROCESS_FAMILY_MATCH"
            if len(process_families) == 1
            else (
                "MULTIPLE_PROVIDER_PROCESS_FAMILIES_REVIEW_REQUIRED"
                if len(process_families) > 1
                else "NO_PROVIDER_PROCESS_INTERVAL_MATCH"
            )
        )

        dimensions = ["TEAM", "PERIOD", "SHARED_VISIBLE_ANCHOR", "ANCHOR_ACTION_FAMILY"]
        if game_state_unique:
            dimensions.append("SCORE_STATE")
        if len(process_families) == 1:
            dimensions.append("PROVIDER_REVIEWED_PROCESS_FAMILY")

        if game_state_unique and len(process_families) == 1:
            state = "PRE_BRANCH_CONTEXT_ENRICHED_GAME_STATE_AND_PROCESS"
        elif game_state_unique or len(process_families) == 1:
            state = "PRE_BRANCH_CONTEXT_ENRICHED_PARTIAL"
        else:
            state = "BASE_SHARED_ANCHOR_CONTEXT_ONLY"

        profile = {
            "state": state,
            "source_comparable_set_id": comparable_ref,
            "team_identity_candidate_id": team_id or None,
            "period_candidate": period or None,
            "shared_anchor_time_candidate": anchor_time,
            "anchor_action_family_counts": anchor_actions,
            "pre_branch_context_dimensions": dimensions,
            "game_state_binding_state": game_binding_state,
            "score_state_candidate": game_state_value,
            "provider_process_binding_state": process_binding_state,
            "provider_process_family_candidates": sorted(process_families),
            "context_is_pre_outcome_only": True,
            "outcome_used_in_context_enrichment": False,
            "consequence_used_in_context_enrichment": False,
            "branch_comparison_context_complete": False,
            "context_enrichment_can_resolve_global_context_completeness": False,
            "creates_new_evidence": False,
            "creates_independent_support": False,
            "can_change_safe_finding_decision": False,
            "can_authorize_emit": False,
        }
        profiles_by_handoff[handoff_ref] = profile
        state_counts[state] = state_counts.get(state, 0) + 1

    return {
        "status": "PASS" if profiles_by_handoff else "NOT_AVAILABLE",
        "profile_count": len(profiles_by_handoff),
        "state_counts": dict(sorted(state_counts.items())),
        "profiles_by_handoff_ref": profiles_by_handoff,
        "enrichment_is_pre_outcome_only": True,
        "enrichment_resolves_branch_context_completeness": False,
        "creates_new_evidence": False,
        "creates_independent_support": False,
        "can_change_safe_finding_decision": False,
        "can_authorize_emit": False,
    }


def _attach_branch_preoutcome_context_to_decisions(
    admission_payload: dict,
    enrichment: dict,
) -> dict:
    profiles = enrichment.get("profiles_by_handoff_ref") or {}
    for row in admission_payload.get("safe_finding_admission_decisions") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("source_safe_finding_handoff_ref") or "").strip()
        if ref in profiles:
            row["branch_preoutcome_context_enrichment"] = profiles[ref]
            row["branch_preoutcome_context_enrichment_can_change_decision"] = False
            row["branch_preoutcome_context_enrichment_can_authorize_emit"] = False
    admission_payload["branch_preoutcome_context_enrichment"] = {
        key: value
        for key, value in enrichment.items()
        if key != "profiles_by_handoff_ref"
    }
    return admission_payload


def _context_coverage_decomposition(
    source_payload: dict,
    admission_payload: dict,
    rich_multiformat_payload: dict | None,
) -> dict:
    handoff_context_by_ref: dict[str, str] = {}
    for handoff in source_payload.get("safe_finding_handoff_candidates") or []:
        if not isinstance(handoff, dict):
            continue
        ref = str(handoff.get("safe_finding_handoff_candidate_id") or "").strip()
        suff = handoff.get("evidence_sufficiency") or {}
        dimensions = suff.get("dimensions") or {}
        context = dimensions.get("context_coverage") or {}
        state = str(context.get("state") or "").strip()
        if ref and state:
            handoff_context_by_ref[ref] = state

    branch_states: dict[str, int] = {}
    for row in admission_payload.get("safe_finding_admission_decisions") or []:
        if not isinstance(row, dict):
            continue
        source_ref = str(row.get("source_safe_finding_handoff_ref") or "").strip()
        state = str(row.get("context_coverage_state") or "").strip()
        if not state:
            state = handoff_context_by_ref.get(source_ref, "UNKNOWN")
        branch_states[state] = branch_states.get(state, 0) + 1

    process_states = dict(source_payload.get("process_comparison_context_state_counts") or {})
    rich = rich_multiformat_payload if isinstance(rich_multiformat_payload, dict) else {}
    descriptive_surfaces = {
        "game_state_context_status": (rich.get("game_state_context") or {}).get("status"),
        "game_state_process_mix_context_status": (rich.get("game_state_process_mix_context") or {}).get("status"),
        "loss_next_opponent_process_context_status": (rich.get("loss_next_opponent_process_context") or {}).get("status"),
        "recovery_next_process_context_status": (rich.get("recovery_next_process_context") or {}).get("status"),
        "set_piece_process_consequence_context_status": (rich.get("set_piece_process_consequence_context") or {}).get("status"),
        "counterattack_next_process_context_status": (rich.get("counterattack_next_process_context") or {}).get("status"),
    }
    descriptive_available = any(
        value in {"PASS", "REVIEW_REQUIRED"}
        for value in descriptive_surfaces.values()
    )

    return {
        "branch_comparison_context_state_counts": branch_states,
        "provider_reviewed_process_comparison_context_consumed": (
            source_payload.get("process_comparison_context_consumed") is True
        ),
        "provider_reviewed_process_context_state_counts": process_states,
        "rich_descriptive_context_available": descriptive_available,
        "rich_descriptive_context_surface_statuses": descriptive_surfaces,
        "rich_descriptive_context_resolves_branch_comparison_completeness": False,
        "rich_descriptive_context_creates_independent_support": False,
        "context_blocker_scope": "BRANCH_COMPARISON_CONTEXT_COMPLETENESS_NOT_GLOBAL_CONTEXT_ABSENCE",
        "can_change_safe_finding_decision": False,
        "can_authorize_emit": False,
    }


def runtime_write_outputs(sequence_json: str | Path, out_dir: str | Path) -> dict:
    source_path = Path(sequence_json).expanduser().resolve()
    output = Path(out_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    source_payload = _load(source_path)
    feature_delta_path = output / FEATURE_DELTA_NAME
    process_variant_path = output / PROCESS_VARIANT_NAME
    grammar_alignment_path = output / GRAMMAR_ALIGNMENT_NAME
    process_participation_path = output / PROCESS_PARTICIPATION_NAME
    occurrence_consequence_path = output / OCCURRENCE_CONSEQUENCE_NAME
    occurrence_state_transition_path = output / OCCURRENCE_STATE_TRANSITION_NAME
    challenge_path = output / CHALLENGE_NAME
    puzzle_finding_path = output / PUZZLE_FINDING_NAME
    rich_multiformat_path = output / RICH_MULTIFORMAT_NAME

    feature_delta_payload = _load(feature_delta_path)
    process_variant_payload = _load(process_variant_path)
    grammar_alignment_payload = _load(grammar_alignment_path)
    process_participation_payload = _load(process_participation_path)
    occurrence_consequence_payload = _load(occurrence_consequence_path)
    occurrence_state_transition_payload = _load(occurrence_state_transition_path)
    rich_multiformat_payload = _load(rich_multiformat_path)
    challenge_payload: dict | None = None
    process_context_counterevidence_recomputed = False
    process_context_counterevidence_fail_closed = False
    process_context_downstream_recomputed = False
    process_context_downstream_recompute_fail_closed = False
    stale_process_variant_surface_reused = False

    if source_payload and process_participation_payload and occurrence_consequence_payload:
        source_payload = apply_process_context_to_comparison(
            source_payload,
            process_participation_payload,
            occurrence_consequence_payload,
            occurrence_state_transition_payload,
        )
        if source_payload.get("process_comparison_context_consumed") is True:
            counterevidence_projection = build_comparable_outcome_counterevidence(source_payload)
            if counterevidence_projection.get("status") == "FAIL_CLOSED":
                process_context_counterevidence_fail_closed = True
            else:
                source_payload = _bind_counterevidence_projection(
                    source_payload,
                    counterevidence_projection,
                )
                process_context_counterevidence_recomputed = True
                _write(source_path, source_payload)

                if not occurrence_state_transition_payload:
                    process_context_downstream_recompute_fail_closed = True
                else:
                    grammar_alignment_payload = build_supported_sequence_grammar_alignment(source_payload)
                    if grammar_alignment_payload.get("status") == "FAIL_CLOSED":
                        process_context_downstream_recompute_fail_closed = True
                    else:
                        _write(grammar_alignment_path, grammar_alignment_payload)
                        process_variant_payload = build_observable_process_variant_binding(
                            source_payload,
                            grammar_alignment_payload,
                        )
                        if process_variant_payload.get("status") == "FAIL_CLOSED":
                            process_context_downstream_recompute_fail_closed = True
                        else:
                            _write(process_variant_path, process_variant_payload)
                            feature_delta_payload = build_grammar_stable_variant_feature_delta(
                                source_payload,
                                process_variant_payload,
                                occurrence_state_transition_payload,
                                occurrence_consequence_payload,
                            )
                            if feature_delta_payload.get("status") == "FAIL_CLOSED":
                                process_context_downstream_recompute_fail_closed = True
                            else:
                                _write(feature_delta_path, feature_delta_payload)
                                process_context_downstream_recomputed = True
        elif process_variant_payload:
            stale_process_variant_surface_reused = True

    if (
        source_payload
        and feature_delta_payload
        and not process_context_downstream_recompute_fail_closed
    ):
        feature_delta_payload = apply_process_participation_context(
            source_payload,
            feature_delta_payload,
            process_participation_payload or None,
            occurrence_consequence_payload or None,
        )
        _write(feature_delta_path, feature_delta_payload)

    if (
        feature_delta_payload
        and process_variant_payload
        and not process_context_downstream_recompute_fail_closed
    ):
        challenge_payload = build_variant_feature_challenge_projection(
            feature_delta_payload,
            process_variant_payload,
        )
        _write(challenge_path, challenge_payload)

    if not source_payload:
        result = {
            "status": "FAIL_CLOSED",
            "safe_finding_admission_decisions": [],
            "safe_finding_admission_decision_count": 0,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
            "hard_block_hits": ["sequence_payload_missing_or_invalid"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    elif process_context_counterevidence_fail_closed:
        result = {
            "status": "FAIL_CLOSED",
            "safe_finding_admission_decisions": [],
            "safe_finding_admission_decision_count": 0,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
            "hard_block_hits": ["process_context_counterevidence_recompute_fail_closed"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    elif process_context_downstream_recompute_fail_closed:
        result = {
            "status": "FAIL_CLOSED",
            "safe_finding_admission_decisions": [],
            "safe_finding_admission_decision_count": 0,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
            "hard_block_hits": ["process_context_downstream_recompute_fail_closed"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    else:
        base_admission = build_safe_finding_admission(source_payload)
        result = apply_variant_feature_challenge_to_admission(
            source_payload,
            base_admission,
            challenge_payload,
            process_variant_payload or None,
        )
        result = apply_occurrence_consequence_burden_to_admission(
            source_payload,
            result,
            process_variant_payload or None,
            occurrence_consequence_payload or None,
        )

    branch_preoutcome_context_enrichment = _branch_preoutcome_context_enrichment(
        source_payload,
        result,
        rich_multiformat_payload or None,
        process_participation_payload or None,
    ) if source_payload else {
        "status": "NOT_AVAILABLE",
        "profile_count": 0,
        "state_counts": {},
        "profiles_by_handoff_ref": {},
        "enrichment_is_pre_outcome_only": True,
        "enrichment_resolves_branch_context_completeness": False,
        "creates_new_evidence": False,
        "creates_independent_support": False,
        "can_change_safe_finding_decision": False,
        "can_authorize_emit": False,
    }
    result = _attach_branch_preoutcome_context_to_decisions(
        result,
        branch_preoutcome_context_enrichment,
    )

    if source_payload:
        if rich_multiformat_payload:
            puzzle_finding_payload = build_puzzle_finding_contract(
                source_payload,
                result,
                rich_multiformat_payload,
            )
        else:
            puzzle_finding_payload = build_puzzle_finding_contract(
                source_payload,
                result,
            )
    else:
        puzzle_finding_payload = _missing_sequence_puzzle_contract()
    _write(puzzle_finding_path, puzzle_finding_payload)

    result["puzzle_finding_contract_status"] = puzzle_finding_payload.get("status")
    result["puzzle_finding_contract_version"] = puzzle_finding_payload.get(
        "puzzle_finding_contract_version"
    )
    result["puzzle_finding_count"] = int(
        puzzle_finding_payload.get("puzzle_finding_count") or 0
    )
    result["puzzle_finding_status_counts"] = dict(
        puzzle_finding_payload.get("puzzle_finding_status_counts") or {}
    )
    result["puzzle_finding_bound_puzzle_ids"] = list(
        puzzle_finding_payload.get("bound_puzzle_ids") or []
    )
    result["puzzle_finding_contract_creates_new_evidence"] = False
    result["puzzle_finding_contract_creates_new_finding"] = False
    result["cross_mechanism_fusion_performed"] = False
    result["mechanism_candidate_emitted"] = False
    result["context_coverage_decomposition"] = _context_coverage_decomposition(
        source_payload,
        result,
        rich_multiformat_payload or None,
    )

    target = output / OUTPUT_NAME
    _write(target, result)
    result["output"] = str(target)
    result["puzzle_finding_contract_output"] = str(puzzle_finding_path)
    result["source_sequence_json"] = str(source_path)
    result["source_feature_delta_json"] = (
        str(feature_delta_path) if feature_delta_path.is_file() else None
    )
    result["source_process_variant_json"] = (
        str(process_variant_path) if process_variant_path.is_file() else None
    )
    result["source_supported_sequence_grammar_alignment_json"] = (
        str(grammar_alignment_path) if grammar_alignment_path.is_file() else None
    )
    result["source_process_participation_json"] = (
        str(process_participation_path) if process_participation_path.is_file() else None
    )
    result["source_occurrence_consequence_json"] = (
        str(occurrence_consequence_path) if occurrence_consequence_path.is_file() else None
    )
    result["source_occurrence_state_transition_json"] = (
        str(occurrence_state_transition_path) if occurrence_state_transition_path.is_file() else None
    )
    result["source_variant_feature_challenge_json"] = (
        str(challenge_path) if challenge_path.is_file() else None
    )
    result["variant_feature_challenge_materialized"] = challenge_path.is_file()
    result["process_participation_context_enrichment_consumed"] = bool(
        feature_delta_payload.get("process_participation_context_enrichment_consumed")
    ) if feature_delta_payload else False
    result["process_participation_context_binding_state"] = (
        feature_delta_payload.get("process_participation_context_binding_state")
        if feature_delta_payload
        else "NOT_AVAILABLE"
    )
    result["process_context_feature_difference_appended_count"] = int(
        feature_delta_payload.get("process_context_feature_difference_appended_count") or 0
    ) if feature_delta_payload else 0
    result["process_comparison_context_consumed"] = source_payload.get(
        "process_comparison_context_consumed"
    ) is True if source_payload else False
    result["process_comparison_context_binding_state"] = (
        source_payload.get("process_comparison_context_binding_state")
        if source_payload
        else "NOT_AVAILABLE"
    )
    result["process_comparison_context_lowered_pair_count"] = int(
        source_payload.get("process_comparison_context_lowered_pair_count") or 0
    ) if source_payload else 0
    result["process_context_counterevidence_recomputed"] = process_context_counterevidence_recomputed
    result["process_context_downstream_recomputed"] = process_context_downstream_recomputed
    result["process_context_stale_process_variant_surface_reused"] = stale_process_variant_surface_reused
    result["context_aligned_grammar_alignment_status"] = grammar_alignment_payload.get("status") if grammar_alignment_payload else None
    result["context_aligned_grammar_alignment_count"] = int(
        grammar_alignment_payload.get("supported_sequence_grammar_alignment_count") or 0
    ) if grammar_alignment_payload else 0
    result["context_aligned_process_variant_status"] = process_variant_payload.get("status") if process_variant_payload else None
    result["context_aligned_process_variant_binding_count"] = int(
        process_variant_payload.get("observable_process_variant_binding_count") or 0
    ) if process_variant_payload else 0
    result["context_aligned_process_variant_family_count"] = int(
        process_variant_payload.get("observable_process_variant_family_count") or 0
    ) if process_variant_payload else 0
    result["context_aligned_visible_outcome_variation_family_count"] = int(
        process_variant_payload.get("grammar_stable_visible_outcome_variation_family_count") or 0
    ) if process_variant_payload else 0
    result["context_aligned_feature_delta_status"] = feature_delta_payload.get("status") if feature_delta_payload else None
    result["context_aligned_feature_delta_record_count"] = int(
        feature_delta_payload.get("grammar_stable_variant_feature_delta_record_count") or 0
    ) if feature_delta_payload else 0
    result["process_context_can_create_new_pair"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA compact Safe Finding admission micro-gear")
    parser.add_argument("--sequence-json", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = runtime_write_outputs(args.sequence_json, args.out_dir)
    print(json.dumps({
        "status": result.get("status"),
        "safe_finding_admission_decision_count": result.get("safe_finding_admission_decision_count"),
        "finding_status_counts": result.get("finding_status_counts") or {},
        "professional_finding_emitted_count": result.get("professional_finding_emitted_count"),
        "claim_output_allowed_count": result.get("claim_output_allowed_count"),
        "puzzle_finding_contract_status": result.get("puzzle_finding_contract_status"),
        "puzzle_finding_count": result.get("puzzle_finding_count", 0),
        "puzzle_finding_status_counts": result.get("puzzle_finding_status_counts") or {},
        "puzzle_finding_bound_puzzle_ids": result.get("puzzle_finding_bound_puzzle_ids") or [],
        "variant_feature_challenge_consumed": result.get("variant_feature_challenge_consumed"),
        "variant_feature_challenge_materialized": result.get("variant_feature_challenge_materialized"),
        "occurrence_consequence_observation_burden_consumed": result.get(
            "occurrence_consequence_observation_burden_consumed"
        ),
        "process_participation_context_enrichment_consumed": result.get(
            "process_participation_context_enrichment_consumed"
        ),
        "process_participation_context_binding_state": result.get(
            "process_participation_context_binding_state"
        ),
        "process_context_feature_difference_appended_count": result.get(
            "process_context_feature_difference_appended_count", 0
        ),
        "process_comparison_context_consumed": result.get("process_comparison_context_consumed"),
        "process_comparison_context_binding_state": result.get(
            "process_comparison_context_binding_state"
        ),
        "process_comparison_context_lowered_pair_count": result.get(
            "process_comparison_context_lowered_pair_count", 0
        ),
        "process_context_counterevidence_recomputed": result.get(
            "process_context_counterevidence_recomputed"
        ),
        "process_context_downstream_recomputed": result.get(
            "process_context_downstream_recomputed"
        ),
        "process_context_stale_process_variant_surface_reused": result.get(
            "process_context_stale_process_variant_surface_reused"
        ),
        "context_aligned_grammar_alignment_count": result.get(
            "context_aligned_grammar_alignment_count", 0
        ),
        "context_aligned_process_variant_binding_count": result.get(
            "context_aligned_process_variant_binding_count", 0
        ),
        "context_aligned_process_variant_family_count": result.get(
            "context_aligned_process_variant_family_count", 0
        ),
        "context_aligned_visible_outcome_variation_family_count": result.get(
            "context_aligned_visible_outcome_variation_family_count", 0
        ),
        "cross_mechanism_fusion_performed": result.get("cross_mechanism_fusion_performed"),
        "mechanism_candidate_emitted": result.get("mechanism_candidate_emitted"),
        "hard_block_hits": result.get("hard_block_hits") or [],
        "review_hits": result.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "output": result.get("output"),
        "puzzle_finding_contract_output": result.get("puzzle_finding_contract_output"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if result.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())