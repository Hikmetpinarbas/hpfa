from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "event_derived_phase_state_lite_v1"
SEQUENCE_MODULE_ID = "visible_action_sequence_candidate_admission_lite_v1"
ACTION_MODULE_ID = "selected_action_consequence_surface_lite_v1"
EVENT_MODULE_ID = "selected_event_consequence_surface_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRANSITION_WINDOW_SECONDS = 10.0
OUTPUTS = {
    "json": "event_derived_phase_state_lite_v1.json",
    "summary": "event_derived_phase_state_lite_v1.txt",
    "analyst": "event_derived_phase_state_analyst_audit_v1.txt",
}

RESTART_FAMILIES = {"RESTART"}
FINISHING_FAMILIES = {"SHOT", "PENALTY"}
RECOVERY_FAMILIES = {"RECOVERY", "INTERCEPTION"}


def clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return None


def digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _zone_phase(record: dict[str, Any]) -> str:
    zone = clean(record.get("anchor_zone_candidate")).upper()
    if "BOX" in zone:
        return "BOX_ACCESS_VISIBLE_PHASE_CANDIDATE"
    if "FINAL" in zone or "ATTACKING" in zone:
        return "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE"
    if "MIDDLE" in zone:
        return "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE"
    if "OWN" in zone or "DEFENSIVE" in zone:
        return "BUILD_UP_VISIBLE_PHASE_CANDIDATE"
    rank = record.get("anchor_zone_rank_candidate")
    if isinstance(rank, int):
        if rank >= 3:
            return "BOX_ACCESS_VISIBLE_PHASE_CANDIDATE"
        if rank == 2:
            return "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE"
        if rank == 1:
            return "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE"
        if rank == 0:
            return "BUILD_UP_VISIBLE_PHASE_CANDIDATE"
    return "OPEN_PLAY_ZONE_UNRESOLVED_PHASE_CANDIDATE"


def _base_node_phase(
    node: dict[str, Any],
    record: dict[str, Any],
) -> tuple[str, list[str]]:
    families = {clean(x).upper() for x in node.get("action_family_candidates") or []}
    evidence: list[str] = []
    if families & RESTART_FAMILIES:
        evidence.append("action_family_restart")
        return "RESTART_VISIBLE_PHASE_CANDIDATE", evidence
    if families & FINISHING_FAMILIES:
        evidence.append("action_family_finishing")
        return "FINISHING_VISIBLE_PHASE_CANDIDATE", evidence
    phase = _zone_phase(record)
    if phase == "OPEN_PLAY_ZONE_UNRESOLVED_PHASE_CANDIDATE":
        evidence.append("zone_candidate_unresolved")
    else:
        evidence.append("direction_normalized_zone_candidate")
    return phase, evidence


def _transition_prefix_length(
    sequence: dict[str, Any],
    nodes: list[dict[str, Any]],
) -> int:
    signals = set(sequence.get("trace_signal_candidates") or [])
    if "REGAIN_TO_VISIBLE_CONTINUATION_CANDIDATE" not in signals or not nodes:
        return 0
    first_time = number(nodes[0].get("start_candidate"))
    prefix = 0
    stable_open_play_run = 0
    for node in nodes:
        current = number(node.get("start_candidate"))
        families = {clean(x).upper() for x in node.get("action_family_candidates") or []}
        if families & FINISHING_FAMILIES:
            break
        if first_time is None or current is None:
            break
        if current - first_time > TRANSITION_WINDOW_SECONDS:
            break
        prefix += 1
        stable_open_play_run += 1
        # Hysteresis: two continuation anchors are required before leaving transition.
        if stable_open_play_run >= 2:
            break
    return prefix


def _segment_sequence(
    binding: str,
    sequence: dict[str, Any],
    node_by_id: dict[str, dict[str, Any]],
    event_by_node: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[str] = []
    node_ids = list(sequence.get("primary_selected_action_node_ids") or [])
    if not node_ids:
        return [], ["phase_source_sequence_has_no_primary_nodes"]
    missing = [node_id for node_id in node_ids if node_id not in node_by_id or node_id not in event_by_node]
    if missing:
        return [], [f"phase_source_node_or_event_mapping_missing:{node_id}" for node_id in missing]
    nodes = [node_by_id[node_id] for node_id in node_ids]
    transition_prefix = _transition_prefix_length(sequence, nodes)
    labels: list[tuple[str, list[str]]] = []
    for index, (node, node_id) in enumerate(zip(nodes, node_ids)):
        label, evidence = _base_node_phase(node, event_by_node[node_id])
        if index < transition_prefix and label not in {
            "RESTART_VISIBLE_PHASE_CANDIDATE",
            "FINISHING_VISIBLE_PHASE_CANDIDATE",
        }:
            label = "ATTACK_TRANSITION_VISIBLE_PHASE_CANDIDATE"
            evidence = [*evidence, "regain_to_visible_continuation_trace", "transition_window_contract"]
        labels.append((label, evidence))

    segments: list[dict[str, Any]] = []
    start = 0
    for index in range(1, len(labels) + 1):
        boundary = index == len(labels) or labels[index][0] != labels[start][0]
        if not boundary:
            continue
        segment_ids = node_ids[start:index]
        segment_nodes = nodes[start:index]
        start_time = number(segment_nodes[0].get("start_candidate"))
        end_time = number(segment_nodes[-1].get("start_candidate"))
        phase_class = labels[start][0]
        evidence = sorted({item for _, items in labels[start:index] for item in items})
        segment_id = "edps_" + digest(
            binding,
            sequence.get("visible_action_sequence_candidate_id"),
            phase_class,
            segment_ids,
        )[:24]
        if clean(sequence.get("sequence_context_status")) == "REVIEW_REQUIRED":
            status = "PHASE_REVIEW_REQUIRED"
        elif phase_class == "OPEN_PLAY_ZONE_UNRESOLVED_PHASE_CANDIDATE":
            status = "PHASE_UNRESOLVED"
        else:
            status = "PHASE_DERIVED_WITH_WARNINGS"
        segments.append(
            {
                "event_derived_phase_segment_id": segment_id,
                "source_visible_action_sequence_candidate_id": sequence.get(
                    "visible_action_sequence_candidate_id"
                ),
                "match_surface_binding_id": binding,
                "team_identity_candidate_id": sequence.get("team_identity_candidate_id"),
                "period_candidate": sequence.get("period_candidate"),
                "phase_class_candidate": phase_class,
                "phase_derivation_status": status,
                "start_time_candidate": start_time,
                "end_time_candidate": end_time,
                "source_interval_span_not_physical_duration": True,
                "start_selected_action_node_id": segment_ids[0],
                "end_selected_action_node_id": segment_ids[-1],
                "selected_action_node_ids": segment_ids,
                "visible_anchor_count": len(segment_ids),
                "derivation_evidence": evidence,
                "alternative_phase_candidate": (
                    "OPEN_PLAY_ZONE_UNRESOLVED_PHASE_CANDIDATE"
                    if status in {"PHASE_UNRESOLVED", "PHASE_REVIEW_REQUIRED"}
                    else None
                ),
                "event_derived_phase_is_tactical_intent_truth": False,
                "event_derived_phase_is_off_ball_structure_truth": False,
                "event_derived_phase_is_tracking_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )
        start = index
    return segments, blocks


def _transition_context_windows(
    binding: str,
    sequences: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered = sorted(
        sequences,
        key=lambda item: (
            clean(item.get("period_candidate")),
            float("inf")
            if number(item.get("start_time_candidate")) is None
            else number(item.get("start_time_candidate")),
            clean(item.get("visible_action_sequence_candidate_id")),
        ),
    )
    windows: list[dict[str, Any]] = []
    for previous, current in zip(ordered, ordered[1:]):
        if clean(previous.get("period_candidate")) != clean(current.get("period_candidate")):
            continue
        previous_team = clean(previous.get("team_identity_candidate_id"))
        current_team = clean(current.get("team_identity_candidate_id"))
        if not previous_team or not current_team or previous_team == current_team:
            continue
        start_time = number(current.get("start_time_candidate"))
        end_time = number(current.get("end_time_candidate"))
        windows.append(
            {
                "event_derived_transition_context_window_id": "edtw_"
                + digest(
                    binding,
                    previous.get("visible_action_sequence_candidate_id"),
                    current.get("visible_action_sequence_candidate_id"),
                )[:24],
                "match_surface_binding_id": binding,
                "period_candidate": current.get("period_candidate"),
                "losing_team_identity_candidate_id": previous_team,
                "gaining_team_identity_candidate_id": current_team,
                "source_previous_visible_sequence_candidate_id": previous.get(
                    "visible_action_sequence_candidate_id"
                ),
                "source_next_visible_sequence_candidate_id": current.get(
                    "visible_action_sequence_candidate_id"
                ),
                "window_class_candidate": "CROSS_TEAM_TRANSITION_CONTEXT_WINDOW_CANDIDATE",
                "start_time_candidate": start_time,
                "end_time_candidate": end_time,
                "losing_team_defensive_transition_actions_observed": False,
                "off_ball_response_truth": False,
                "tactical_response_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )
    return windows


def build_event_derived_phase_state(
    sequence_payload: dict[str, Any],
    action_payload: dict[str, Any],
    event_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    if sequence_payload.get("module_id") != SEQUENCE_MODULE_ID:
        blocks.append("visible_sequence_module_id_mismatch")
    if action_payload.get("module_id") != ACTION_MODULE_ID:
        blocks.append("selected_action_module_id_mismatch")
    if event_payload.get("module_id") != EVENT_MODULE_ID:
        blocks.append("selected_event_module_id_mismatch")
    binding = clean(sequence_payload.get("match_surface_binding_id"))
    for name, payload in (
        ("sequence", sequence_payload),
        ("action", action_payload),
        ("event", event_payload),
    ):
        if clean(payload.get("match_surface_binding_id")) != binding or not binding:
            blocks.append(f"{name}_match_surface_binding_mismatch")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")
        upstream_status = clean(payload.get("module_status") or payload.get("status"))
        if upstream_status != "PASS":
            reviews.append(f"{name}_upstream_status_review:{upstream_status or 'UNKNOWN'}")

    nodes = action_payload.get("selected_action_nodes") or []
    events = event_payload.get("selected_event_consequence_candidates") or []
    sequences = sequence_payload.get("visible_action_sequence_candidates") or []
    if not all(isinstance(items, list) for items in (nodes, events, sequences)):
        blocks.append("phase_input_inventory_invalid")
        nodes, events, sequences = [], [], []
    declared_sequence_count = sequence_payload.get("visible_action_sequence_candidate_count")
    if declared_sequence_count is not None and declared_sequence_count != len(sequences):
        blocks.append("visible_action_sequence_candidate_count_mismatch")
    node_by_id = {
        clean(node.get("selected_action_node_id")): node for node in nodes if isinstance(node, dict)
    }
    event_by_node = {
        clean(record.get("anchor_selected_action_node_id")): record
        for record in events
        if isinstance(record, dict)
    }
    segments: list[dict[str, Any]] = []
    if not blocks:
        for sequence in sequences:
            if not isinstance(sequence, dict):
                blocks.append("phase_source_sequence_record_invalid")
                continue
            produced, segment_blocks = _segment_sequence(
                binding, sequence, node_by_id, event_by_node
            )
            segments.extend(produced)
            blocks.extend(segment_blocks)
    if blocks:
        segments = []
    windows = [] if blocks else _transition_context_windows(binding, sequences)
    phase_counts = Counter(segment["phase_class_candidate"] for segment in segments)
    unresolved_count = sum(
        segment["phase_derivation_status"] == "PHASE_UNRESOLVED" for segment in segments
    )
    if unresolved_count:
        reviews.append("unresolved_phase_segments_preserved")
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    derivation_status = (
        "FAIL_CLOSED"
        if blocks
        else ("PHASE_DERIVED_WITH_WARNINGS" if reviews else "PHASE_DERIVED_PASS")
    )
    return {
        "module_id": MODULE_ID,
        "version": "1.0.0",
        "status": status,
        "module_status": status,
        "phase_derivation_status": derivation_status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "source_visible_action_sequence_candidate_count": len(sequences),
        "event_derived_phase_segments": segments,
        "event_derived_phase_segment_count": len(segments),
        "phase_class_candidate_counts": dict(sorted(phase_counts.items())),
        "unresolved_phase_segment_count": unresolved_count,
        "event_derived_transition_context_windows": windows,
        "event_derived_transition_context_window_count": len(windows),
        "transition_window_seconds_contract": TRANSITION_WINDOW_SECONDS,
        "transition_hysteresis_visible_anchor_count": 2,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "phase_state_derived_from_event_evidence": bool(segments) and not blocks,
        "phase_truth": False,
        "phase_truth_elevation_requires_validated_event_identity": True,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "off_ball_structure_truth": False,
        "tracking_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "phase_derivation_status",
        "source_visible_action_sequence_candidate_count",
        "event_derived_phase_segment_count",
        "phase_class_candidate_counts",
        "unresolved_phase_segment_count",
        "event_derived_transition_context_window_count",
        "hard_block_hits",
        "review_hits",
    )
    lines = ["HPFA EVENT-DERIVED PHASE STATE LITE V1"]
    lines.extend(f"{key}={payload.get(key)}" for key in keys)
    lines.extend(["canonical_event_count=UNKNOWN", "production_release=false"])
    return "\n".join(lines) + "\n"


def analyst_audit(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — EVENT-DERIVED PHASE STATE",
        f"Derived phase segments: {payload.get('event_derived_phase_segment_count', 0)}",
        f"Phase classes: {payload.get('phase_class_candidate_counts')}",
        f"Unresolved phase segments: {payload.get('unresolved_phase_segment_count', 0)}",
        (
            "Cross-team transition context windows: "
            f"{payload.get('event_derived_transition_context_window_count', 0)}"
        ),
        (
            "Analyst-safe meaning: visible event evidence was segmented by time, team, "
            "action family and direction-normalized zone candidates."
        ),
        (
            "The segments do not establish tactical intent, off-ball structure, pressure, "
            "fatigue, tracking truth or observed defensive-transition actions."
        ),
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {name: output / filename for name, filename in OUTPUTS.items()}
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--visible-sequence", required=True)
    parser.add_argument("--selected-action-consequence", required=True)
    parser.add_argument("--selected-event-consequence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_event_derived_phase_state(
        load_json(args.visible_sequence, "visible_sequence_input_unreadable_or_malformed"),
        load_json(
            args.selected_action_consequence,
            "selected_action_consequence_input_unreadable_or_malformed",
        ),
        load_json(
            args.selected_event_consequence,
            "selected_event_consequence_input_unreadable_or_malformed",
        ),
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "phase_derivation_status",
                    "event_derived_phase_segment_count",
                    "unresolved_phase_segment_count",
                    "event_derived_transition_context_window_count",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
