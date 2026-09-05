from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

MODULE_ID = "football_episode_boundary_candidate_v1"
UPSTREAM_MODULE_ID = "analyst_episode_locator_lite_v1"
CLAIM_CEILING = "FOOTBALL_EPISODE_BOUNDARY_CANDIDATE_ONLY"
DEFAULT_GAP_SECONDS = 8.0


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fail(reason: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "FOOTBALL_EPISODE_INPUT_REJECTED",
        "football_episode_candidates": [],
        "football_episode_candidate_count": 0,
        "episode_recurrence_change_candidates": [],
        "episode_recurrence_change_candidate_count": 0,
        "visible_outcome_counterevidence_pair_count": 0,
        "hard_block_hits": [reason],
        "review_hits": [],
        "claim_ceiling": CLAIM_CEILING,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "episode_is_possession_truth": False,
        "episode_is_sequence_truth": False,
        "episode_is_phase_truth": False,
        "episode_is_tactical_truth": False,
        "episode_is_causal_truth": False,
        "recurrence_candidate_is_stable_pattern_truth": False,
        "outcome_variation_candidate_is_tactical_change_truth": False,
        "counterevidence_candidate_is_causal_falsification_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _visible_time_layer_family_sequence(segment: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Preserve only positive-time ordering between distinct visible time layers.

    Rows sharing the same timestamp are folded into one unordered family-count bucket.
    Absolute timestamps and source-row order are deliberately excluded so recurrence
    grouping uses visible process order without inventing same-time chronology.
    """
    sequence: list[dict[str, int]] = []
    current_second: float | None = None
    current_counts: dict[str, int] = {}

    def flush() -> None:
        nonlocal current_counts
        if current_second is not None:
            sequence.append(dict(sorted(current_counts.items())))
        current_counts = {}

    for row in segment:
        second = float(row.get("second_candidate"))
        if current_second is None:
            current_second = second
        elif second != current_second:
            flush()
            current_second = second
        for family, count in (row.get("eligible_action_family_counts") or {}).items():
            family_key = str(family)
            current_counts[family_key] = current_counts.get(family_key, 0) + int(count)

    flush()
    return sequence


def _recurrence_change_surface(fine: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group only exact visible episode composition candidates.

    The signature deliberately excludes visible outcome so the same admitted visible
    composition can preserve outcome variation as a counterevidence/change surface.
    Pairwise contrasts are dependent same-match projections only; they are not
    independent evidence votes, causal falsification or tactical truth.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in fine:
        signature = _clean(row.get("visible_process_composition_signature_candidate"))
        if signature:
            grouped[signature].append(row)

    surface: list[dict[str, Any]] = []
    for signature, rows in sorted(grouped.items()):
        if len(rows) < 2:
            continue
        outcome_distribution: dict[str, int] = {}
        for row in rows:
            outcome = _clean(row.get("visible_outcome_candidate")) or "UNKNOWN_VISIBLE_OUTCOME"
            outcome_distribution[outcome] = outcome_distribution.get(outcome, 0) + 1

        contrast_pairs: list[dict[str, Any]] = []
        for left_index, left in enumerate(rows):
            left_outcome = _clean(left.get("visible_outcome_candidate")) or "UNKNOWN_VISIBLE_OUTCOME"
            for right in rows[left_index + 1 :]:
                right_outcome = _clean(right.get("visible_outcome_candidate")) or "UNKNOWN_VISIBLE_OUTCOME"
                if left_outcome == right_outcome:
                    continue
                left_id = _clean(left.get("football_episode_candidate_id"))
                right_id = _clean(right.get("football_episode_candidate_id"))
                pair_id = "foc_" + _digest(signature, left_id, right_id, left_outcome, right_outcome)[:24]
                contrast_pairs.append({
                    "visible_outcome_contrast_pair_id": pair_id,
                    "football_episode_candidate_id_a": left_id,
                    "football_episode_candidate_id_b": right_id,
                    "visible_outcome_candidate_a": left_outcome,
                    "visible_outcome_candidate_b": right_outcome,
                    "counterevidence_candidate": True,
                    "counterevidence_scope": "SAME_MATCH_SAME_VISIBLE_COMPOSITION_DIFFERENT_VISIBLE_OUTCOME_ONLY",
                    "dependent_episode_projection_only": True,
                    "independent_evidence_vote_count": 0,
                    "causal_falsification_truth": False,
                    "tactical_change_truth": False,
                    "claim_output_allowed": False,
                })

        surface.append({
            "visible_process_composition_signature_candidate": signature,
            "football_episode_candidate_ids": [row["football_episode_candidate_id"] for row in rows],
            "visible_episode_repeat_count_candidate": len(rows),
            "visible_outcome_distribution": dict(sorted(outcome_distribution.items())),
            "different_visible_outcome_candidate": len(outcome_distribution) > 1,
            "visible_outcome_contrast_pairs": contrast_pairs,
            "visible_outcome_contrast_pair_count": len(contrast_pairs),
            "dependent_episode_projection_only": True,
            "independent_evidence_vote_count": 0,
            "recurrence_candidate_is_stable_pattern_truth": False,
            "outcome_variation_candidate_is_tactical_change_truth": False,
            "counterevidence_candidate_is_causal_falsification_truth": False,
            "claim_output_allowed": False,
        })
    return surface


def build_football_episode_boundaries(
    episode_payload: dict[str, Any],
    *,
    gap_seconds: float = DEFAULT_GAP_SECONDS,
) -> dict[str, Any]:
    if episode_payload.get("module_id") != UPSTREAM_MODULE_ID:
        return _fail("upstream_module_id_mismatch")
    if episode_payload.get("status") == "FAIL_CLOSED":
        return _fail("upstream_fail_closed")
    if episode_payload.get("canonical_event_count") != "UNKNOWN":
        return _fail("upstream_canonical_event_count_claimed")
    if episode_payload.get("true_action_count") not in {None, "UNKNOWN"}:
        return _fail("upstream_true_action_count_claimed")
    if episode_payload.get("production_release") is True:
        return _fail("upstream_production_release_claimed")
    if episode_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        return _fail("same_timestamp_policy_breached")
    if episode_payload.get("source_row_order_is_temporal_truth") is not False:
        return _fail("source_row_order_policy_breached")
    if not isinstance(gap_seconds, (int, float)) or gap_seconds <= 0:
        return _fail("gap_seconds_invalid")

    macros = episode_payload.get("episode_candidates")
    layers = episode_payload.get("episode_time_layer_candidates")
    if not isinstance(macros, list) or not isinstance(layers, list):
        return _fail("episode_inputs_missing")

    layer_by_id: dict[str, dict[str, Any]] = {}
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            return _fail(f"time_layer_invalid:{index}")
        layer_id = _clean(layer.get("episode_time_layer_candidate_id"))
        if not layer_id or layer_id in layer_by_id:
            return _fail(f"time_layer_id_invalid_or_duplicate:{index}")
        action_family_counts = layer.get("eligible_action_family_counts")
        if action_family_counts is not None and not isinstance(action_family_counts, Mapping):
            return _fail(f"time_layer_action_family_counts_invalid:{layer_id}")
        layer_by_id[layer_id] = layer

    fine: list[dict[str, Any]] = []
    assigned_layer_refs: set[str] = set()
    reviews: list[str] = []

    for macro_index, macro in enumerate(macros):
        if not isinstance(macro, dict):
            return _fail(f"macro_episode_invalid:{macro_index}")
        macro_id = _clean(macro.get("episode_candidate_id"))
        refs = macro.get("time_layer_refs")
        if not macro_id or not isinstance(refs, list) or not refs:
            return _fail(f"macro_episode_refs_invalid:{macro_index}")
        if len(refs) != len(set(refs)):
            return _fail(f"macro_episode_duplicate_layer_ref:{macro_id}")
        reused_refs = sorted(set(refs) & assigned_layer_refs)
        if reused_refs:
            return _fail(f"macro_episode_cross_macro_layer_reuse:{macro_id}:{reused_refs[0]}")
        try:
            macro_layers = [layer_by_id[ref] for ref in refs]
        except KeyError as exc:
            return _fail(f"macro_episode_layer_ref_missing:{macro_id}:{exc.args[0]}")

        macro_layers = sorted(
            macro_layers,
            key=lambda row: (float(row.get("second_candidate")), _clean(row.get("episode_time_layer_candidate_id"))),
        )

        segment: list[dict[str, Any]] = []
        segment_start_reason = "MACRO_EPISODE_START"

        def close_segment(end_reason: str) -> None:
            nonlocal segment, segment_start_reason
            if not segment:
                return
            first = segment[0]
            last = segment[-1]
            segment_refs = [row["episode_time_layer_candidate_id"] for row in segment]
            context_refs = [ctx for row in segment for ctx in (row.get("context_refs") or [])]
            action_families: dict[str, int] = {}
            for row in segment:
                for family, count in (row.get("eligible_action_family_counts") or {}).items():
                    action_families[str(family)] = action_families.get(str(family), 0) + int(count)
            visible_time_layer_family_sequence = _visible_time_layer_family_sequence(segment)
            teams = sorted({team for row in segment for team in (row.get("team_candidates") or []) if _clean(team)})
            team_scope = teams[0] if len(teams) == 1 else ("MULTI_TEAM_VISIBLE" if teams else "UNKNOWN_TEAM")
            terminal_visible = any(row.get("terminal_action_visible") is True for row in segment)
            restart_visible = any(row.get("restart_visible") is True for row in segment)
            loss_visible = any(row.get("ball_loss_visible") is True for row in segment)
            recovery_visible = any(row.get("recovery_visible") is True for row in segment)

            transition_flags_by_second: dict[float, set[str]] = defaultdict(set)
            for row in segment:
                second = float(row.get("second_candidate"))
                if row.get("ball_loss_visible") is True:
                    transition_flags_by_second[second].add("LOSS")
                if row.get("recovery_visible") is True:
                    transition_flags_by_second[second].add("RECOVERY")
            same_time_loss_recovery = any(
                {"LOSS", "RECOVERY"}.issubset(flags)
                for flags in transition_flags_by_second.values()
            )
            same_time_unordered = any(row.get("same_time_unordered") is True for row in segment) or same_time_loss_recovery
            ordered_transitions: list[str] = []
            if not same_time_loss_recovery:
                for second in sorted(transition_flags_by_second):
                    flags = transition_flags_by_second[second]
                    if "LOSS" in flags:
                        ordered_transitions.append("LOSS")
                    elif "RECOVERY" in flags:
                        ordered_transitions.append("RECOVERY")
            collapsed_transitions: list[str] = []
            for transition in ordered_transitions:
                if not collapsed_transitions or collapsed_transitions[-1] != transition:
                    collapsed_transitions.append(transition)

            if terminal_visible:
                outcome = "TERMINAL_SHOT_VISIBLE"
            elif same_time_loss_recovery:
                outcome = "LOSS_AND_RECOVERY_VISIBLE_ORDER_INDETERMINATE"
            elif loss_visible and recovery_visible and collapsed_transitions == ["LOSS", "RECOVERY"]:
                outcome = "BALL_LOSS_THEN_RECOVERY_VISIBLE"
            elif loss_visible and recovery_visible and collapsed_transitions == ["RECOVERY", "LOSS"]:
                outcome = "RECOVERY_THEN_BALL_LOSS_VISIBLE"
            elif loss_visible and recovery_visible and len(collapsed_transitions) > 2:
                outcome = "LOSS_RECOVERY_INTERLEAVED_VISIBLE"
            elif loss_visible and recovery_visible:
                outcome = "LOSS_AND_RECOVERY_VISIBLE_ORDER_INDETERMINATE"
            elif loss_visible:
                outcome = "BALL_LOSS_VISIBLE"
            elif recovery_visible:
                outcome = "RECOVERY_VISIBLE"
            else:
                outcome = "NO_TERMINAL_OUTCOME_VISIBLE"

            development = "MULTI_ACTION_FAMILY_VISIBLE" if len(action_families) > 1 else (
                next(iter(action_families), "NO_ELIGIBLE_ACTION_FAMILY_VISIBLE")
            )
            composition_basis = {
                "team_scope_candidate": team_scope,
                "action_family_distribution": dict(sorted(action_families.items())),
                "visible_action_family_time_layer_sequence_candidate": visible_time_layer_family_sequence,
            }
            composition_signature = "fpc_" + _digest(composition_basis)[:24]
            candidate_id = "fep_" + _digest(macro_id, segment_refs, segment_start_reason, end_reason)[:24]
            fine.append({
                "football_episode_candidate_id": candidate_id,
                "macro_episode_candidate_id": macro_id,
                "period_candidate": macro.get("period_candidate"),
                "start_second_candidate": first.get("second_candidate"),
                "end_second_candidate": last.get("second_candidate"),
                "duration_candidate_seconds": round(float(last.get("second_candidate")) - float(first.get("second_candidate")), 6),
                "start_evidence_candidate": segment_start_reason,
                "development_candidate": development,
                "break_or_end_evidence_candidate": end_reason,
                "visible_outcome_candidate": outcome,
                "visible_process_composition_signature_candidate": composition_signature,
                "visible_process_composition_signature_basis": composition_basis,
                "visible_action_family_time_layer_sequence_candidate": visible_time_layer_family_sequence,
                "time_layer_refs": segment_refs,
                "context_refs": context_refs,
                "action_family_distribution": dict(sorted(action_families.items())),
                "team_candidates": teams,
                "team_scope_candidate": team_scope,
                "restart_visible": restart_visible,
                "terminal_action_visible": terminal_visible,
                "ball_loss_visible": loss_visible,
                "recovery_visible": recovery_visible,
                "same_time_unordered_visible": same_time_unordered,
                "same_timestamp_internal_ordering_allowed": False,
                "source_row_order_is_temporal_truth": False,
                "boundary_requires_visible_evidence": True,
                "episode_is_possession_truth": False,
                "episode_is_sequence_truth": False,
                "episode_is_phase_truth": False,
                "episode_is_tactical_truth": False,
                "episode_is_causal_truth": False,
                "recurrence_candidate_is_stable_pattern_truth": False,
                "outcome_variation_candidate_is_tactical_change_truth": False,
                "counterevidence_candidate_is_causal_falsification_truth": False,
                "claim_ceiling": CLAIM_CEILING,
            })
            assigned_layer_refs.update(segment_refs)
            segment = []
            segment_start_reason = "CONTINUATION_AFTER_VISIBLE_BOUNDARY"

        layers_by_second: dict[float, list[dict[str, Any]]] = defaultdict(list)
        for layer in macro_layers:
            second = float(layer.get("second_candidate"))
            layers_by_second[second].append(layer)

        previous_second: float | None = None
        for second in sorted(layers_by_second):
            bucket = sorted(
                layers_by_second[second],
                key=lambda row: _clean(row.get("episode_time_layer_candidate_id")),
            )
            if previous_second is not None:
                gap = second - previous_second
                if gap < 0:
                    return _fail(f"negative_time_gap:{macro_id}")
                if gap > gap_seconds:
                    close_segment("ADMITTED_VISIBLE_TIME_GAP")
                    segment_start_reason = "AFTER_ADMITTED_VISIBLE_TIME_GAP"

            bucket_restart_visible = any(row.get("restart_visible") is True for row in bucket)
            if bucket_restart_visible and segment:
                close_segment("VISIBLE_RESTART_BEFORE_NEXT_PROCESS")
                segment_start_reason = "VISIBLE_RESTART"

            segment.extend(bucket)

            bucket_terminal_visible = any(row.get("terminal_action_visible") is True for row in bucket)
            bucket_loss_visible = any(row.get("ball_loss_visible") is True for row in bucket)
            bucket_recovery_visible = any(row.get("recovery_visible") is True for row in bucket)

            if bucket_terminal_visible:
                close_segment("TERMINAL_SHOT_VISIBLE")
                segment_start_reason = "AFTER_TERMINAL_SHOT_VISIBLE"
            elif bucket_loss_visible and bucket_recovery_visible:
                reviews.append("same_timestamp_loss_recovery_order_indeterminate")
                close_segment("LOSS_RECOVERY_VISIBLE_SAME_TIME_UNORDERED")
                segment_start_reason = "AFTER_LOSS_RECOVERY_VISIBLE_SAME_TIME_UNORDERED"

            previous_second = second

        close_segment("MACRO_EPISODE_END")

    complete_layer_refs = set(layer_by_id)
    if assigned_layer_refs != complete_layer_refs:
        return _fail("fine_episode_layer_assignment_coverage_mismatch")

    recurrence_change = _recurrence_change_surface(fine)
    status = "REVIEW_REQUIRED" if reviews or episode_payload.get("status") == "REVIEW_REQUIRED" else "PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "FOOTBALL_EPISODE_BOUNDARY_CANDIDATES_ONLY",
        "upstream_macro_episode_count": len(macros),
        "football_episode_candidates": fine,
        "football_episode_candidate_count": len(fine),
        "episode_recurrence_change_candidates": recurrence_change,
        "episode_recurrence_change_candidate_count": len(recurrence_change),
        "different_visible_outcome_recurrence_candidate_count": sum(
            row.get("different_visible_outcome_candidate") is True for row in recurrence_change
        ),
        "visible_outcome_counterevidence_pair_count": sum(
            int(row.get("visible_outcome_contrast_pair_count") or 0) for row in recurrence_change
        ),
        "all_macro_time_layers_assigned_once": True,
        "boundary_gap_seconds_candidate": float(gap_seconds),
        "boundary_gap_is_calibrated_truth": False,
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews + (["upstream_review_required"] if episode_payload.get("status") == "REVIEW_REQUIRED" else []))),
        "claim_ceiling": CLAIM_CEILING,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "episode_is_possession_truth": False,
        "episode_is_sequence_truth": False,
        "episode_is_phase_truth": False,
        "episode_is_tactical_truth": False,
        "episode_is_causal_truth": False,
        "recurrence_candidate_is_stable_pattern_truth": False,
        "outcome_variation_candidate_is_tactical_change_truth": False,
        "counterevidence_candidate_is_causal_falsification_truth": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
