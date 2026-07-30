from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "phase_aware_sequence_refinement_lite_v1"
PHASE_MODULE_ID = "event_derived_phase_state_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"

PROTECTED_PHASES = {
    "RESTART_VISIBLE_PHASE_CANDIDATE",
    "ATTACK_TRANSITION_VISIBLE_PHASE_CANDIDATE",
    "FINISHING_VISIBLE_PHASE_CANDIDATE",
}
REVIEW_STATUSES = {"PHASE_REVIEW_REQUIRED", "PHASE_UNRESOLVED"}
OUTPUTS = {
    "json": "phase_aware_sequence_refinement_lite_v1.json",
    "summary": "phase_aware_sequence_refinement_lite_v1.txt",
    "analyst": "phase_aware_sequence_refinement_analyst_audit_v1.txt",
}


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


def _source_phase_order_is_monotonic(
    segments: list[dict[str, Any]],
) -> bool:
    previous_start: float | None = None
    previous_end: float | None = None
    for segment in segments:
        start = number(segment.get("start_time_candidate"))
        end = number(segment.get("end_time_candidate"))
        if start is None or end is None:
            return False
        if previous_start is not None and start < previous_start:
            return False
        if previous_end is not None and end < previous_end:
            return False
        previous_start = start
        previous_end = end
    return True


def _is_zero_span(segment: dict[str, Any]) -> bool:
    start = number(segment.get("start_time_candidate"))
    end = number(segment.get("end_time_candidate"))
    return start is not None and end is not None and abs(start - end) <= 1e-9


def _classify_triplet(
    previous: dict[str, Any],
    middle: dict[str, Any],
    following: dict[str, Any],
) -> tuple[str, list[str]]:
    middle_phase = clean(middle.get("phase_class_candidate"))
    evidence = ["same_sequence_A_B_A_phase_oscillation"]
    if middle_phase in PROTECTED_PHASES:
        return "RETAIN_PROTECTED_PHASE_CHANGE", evidence + [
            "restart_transition_or_finishing_phase_preserved"
        ]

    middle_anchors = middle.get("visible_anchor_count")
    if not isinstance(middle_anchors, int) or middle_anchors < 1:
        return "INSUFFICIENT_ANCHOR_REVIEW_REQUIRED", evidence + [
            "middle_visible_anchor_count_invalid"
        ]
    if any(
        clean(item.get("phase_derivation_status")) in REVIEW_STATUSES
        for item in (previous, middle, following)
    ):
        return "INSUFFICIENT_ANCHOR_REVIEW_REQUIRED", evidence + [
            "triplet_contains_review_bounded_phase"
        ]
    if not _is_zero_span(middle) or middle_anchors > 1:
        return "RETAIN_SUPPORTED_PHASE_CHANGE", evidence + [
            "middle_phase_has_positive_span_or_multiple_anchors"
        ]

    previous_end = number(previous.get("end_time_candidate"))
    middle_start = number(middle.get("start_time_candidate"))
    following_start = number(following.get("start_time_candidate"))
    if (
        previous_end is None
        or middle_start is None
        or following_start is None
        or not (previous_end < middle_start < following_start)
    ):
        return "INSUFFICIENT_ANCHOR_REVIEW_REQUIRED", evidence + [
            "strict_triplet_time_order_not_observed"
        ]

    flank_anchor_counts = [
        previous.get("visible_anchor_count"),
        following.get("visible_anchor_count"),
    ]
    flank_supported = all(
        isinstance(value, int) and value >= 2 for value in flank_anchor_counts
    )
    if not flank_supported:
        return "INSUFFICIENT_ANCHOR_REVIEW_REQUIRED", evidence + [
            "flanking_phase_support_below_two_visible_anchors"
        ]
    return "REFINEMENT_CANDIDATE_SINGLE_ANCHOR_OSCILLATION", evidence + [
        "middle_phase_single_anchor_zero_span",
        "matching_flanks_each_have_multiple_visible_anchors",
    ]


def build_phase_aware_sequence_refinement(
    phase_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    if phase_payload.get("module_id") != PHASE_MODULE_ID:
        blocks.append("event_derived_phase_module_id_mismatch")
    binding = clean(phase_payload.get("match_surface_binding_id"))
    if not binding:
        blocks.append("match_surface_binding_missing")
    if phase_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed")
    if phase_payload.get("production_release") is True:
        blocks.append("production_release_claimed")
    if phase_payload.get("hard_block_hits"):
        blocks.append("upstream_hard_blocks_present")
    upstream_status = clean(
        phase_payload.get("module_status") or phase_payload.get("status")
    )
    if upstream_status != "PASS":
        reviews.append(f"phase_upstream_status_review:{upstream_status or 'UNKNOWN'}")

    segments = phase_payload.get("event_derived_phase_segments")
    if not isinstance(segments, list):
        blocks.append("phase_segment_inventory_invalid")
        segments = []
    declared_count = phase_payload.get("event_derived_phase_segment_count")
    if declared_count is not None and declared_count != len(segments):
        blocks.append("phase_segment_count_mismatch")

    segment_ids: set[str] = set()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sequence_context: dict[str, tuple[str, str]] = {}
    for segment in segments:
        if not isinstance(segment, dict):
            blocks.append("phase_segment_record_invalid")
            continue
        segment_id = clean(segment.get("event_derived_phase_segment_id"))
        sequence_id = clean(
            segment.get("source_visible_action_sequence_candidate_id")
        )
        if not segment_id:
            blocks.append("phase_segment_id_missing")
        elif segment_id in segment_ids:
            blocks.append(f"phase_segment_id_duplicate:{segment_id}")
        else:
            segment_ids.add(segment_id)
        if not sequence_id:
            blocks.append(f"phase_segment_source_sequence_missing:{segment_id or 'NONE'}")
        if clean(segment.get("match_surface_binding_id")) != binding:
            blocks.append(f"phase_segment_binding_mismatch:{segment_id or 'NONE'}")
        start = number(segment.get("start_time_candidate"))
        end = number(segment.get("end_time_candidate"))
        if start is None or end is None or end < start:
            blocks.append(f"phase_segment_time_invalid:{segment_id or 'NONE'}")
        if not clean(segment.get("phase_class_candidate")):
            blocks.append(f"phase_class_missing:{segment_id or 'NONE'}")
        if sequence_id:
            team = clean(segment.get("team_identity_candidate_id"))
            period = clean(segment.get("period_candidate"))
            context = (team, period)
            if not team or not period:
                blocks.append(
                    f"phase_segment_team_or_period_missing:{segment_id or 'NONE'}"
                )
            elif sequence_id in sequence_context and sequence_context[sequence_id] != context:
                blocks.append(f"source_sequence_context_conflict:{sequence_id}")
            else:
                sequence_context[sequence_id] = context
            grouped[sequence_id].append(segment)

    decisions: list[dict[str, Any]] = []
    oscillation_count = 0
    same_timestamp_adjacent_phase_pair_count = 0
    if not blocks:
        for sequence_id in sorted(grouped):
            sequence_segments = grouped[sequence_id]
            if not _source_phase_order_is_monotonic(sequence_segments):
                blocks.append(f"source_sequence_phase_order_invalid:{sequence_id}")
                continue
            same_timestamp_adjacent_phase_pair_count += sum(
                1
                for previous, following in zip(
                    sequence_segments, sequence_segments[1:]
                )
                if number(previous.get("start_time_candidate"))
                == number(following.get("start_time_candidate"))
            )
            for index, segment in enumerate(sequence_segments):
                decision = "RETAIN_NO_A_B_A_OSCILLATION"
                evidence = ["phase_segment_preserved"]
                previous_id = None
                following_id = None
                if 0 < index < len(sequence_segments) - 1:
                    previous = sequence_segments[index - 1]
                    following = sequence_segments[index + 1]
                    previous_phase = clean(previous.get("phase_class_candidate"))
                    middle_phase = clean(segment.get("phase_class_candidate"))
                    following_phase = clean(following.get("phase_class_candidate"))
                    if previous_phase == following_phase and previous_phase != middle_phase:
                        oscillation_count += 1
                        decision, evidence = _classify_triplet(
                            previous, segment, following
                        )
                        previous_id = previous.get("event_derived_phase_segment_id")
                        following_id = following.get("event_derived_phase_segment_id")
                decisions.append(
                    {
                        "phase_refinement_decision_id": "pasr_"
                        + digest(binding, sequence_id, segment.get(
                            "event_derived_phase_segment_id"
                        ))[:24],
                        "source_visible_action_sequence_candidate_id": sequence_id,
                        "source_event_derived_phase_segment_id": segment.get(
                            "event_derived_phase_segment_id"
                        ),
                        "previous_phase_segment_id": previous_id,
                        "following_phase_segment_id": following_id,
                        "phase_class_candidate": segment.get("phase_class_candidate"),
                        "decision_class": decision,
                        "decision_evidence": evidence,
                        "segment_preserved": True,
                        "automatic_merge_applied": False,
                        "automatic_delete_applied": False,
                        "sequence_truth": False,
                    }
                )

    if blocks:
        decisions = []
    elif len(decisions) != len(segments):
        blocks.append("phase_refinement_decision_reconciliation_failed")
        decisions = []
    decision_counts = Counter(x["decision_class"] for x in decisions)
    candidate_count = decision_counts.get(
        "REFINEMENT_CANDIDATE_SINGLE_ANCHOR_OSCILLATION", 0
    )
    insufficient_count = decision_counts.get(
        "INSUFFICIENT_ANCHOR_REVIEW_REQUIRED", 0
    )
    if candidate_count:
        reviews.append("single_anchor_A_B_A_refinement_candidates_preserved")
    if insufficient_count:
        reviews.append("insufficient_anchor_A_B_A_cases_preserved")
    if same_timestamp_adjacent_phase_pair_count:
        reviews.append("same_timestamp_phase_pairs_preserved_without_order_claim")
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "version": "1.0.0",
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "source_event_derived_phase_segment_count": len(segments),
        "source_visible_sequence_count": len(grouped),
        "phase_refinement_decisions": decisions,
        "phase_refinement_decision_count": len(decisions),
        "decision_class_counts": dict(sorted(decision_counts.items())),
        "A_B_A_phase_oscillation_count": oscillation_count,
        "same_timestamp_adjacent_phase_pair_count": (
            same_timestamp_adjacent_phase_pair_count
        ),
        "refinement_candidate_count": candidate_count,
        "insufficient_anchor_review_count": insufficient_count,
        "retained_source_phase_segment_count": len(decisions),
        "automatic_merge_count": 0,
        "automatic_delete_count": 0,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "phase_aware_refinement_candidate_surface_created": bool(decisions) and not blocks,
        "phase_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "tactical_truth": False,
        "off_ball_structure_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "source_event_derived_phase_segment_count",
        "source_visible_sequence_count",
        "phase_refinement_decision_count",
        "decision_class_counts",
        "A_B_A_phase_oscillation_count",
        "same_timestamp_adjacent_phase_pair_count",
        "refinement_candidate_count",
        "insufficient_anchor_review_count",
        "retained_source_phase_segment_count",
        "automatic_merge_count",
        "automatic_delete_count",
        "hard_block_hits",
        "review_hits",
    )
    lines = ["HPFA PHASE-AWARE SEQUENCE REFINEMENT LITE V1"]
    lines.extend(f"{key}={payload.get(key)}" for key in keys)
    lines.extend(["canonical_event_count=UNKNOWN", "production_release=false"])
    return "\n".join(lines) + "\n"


def analyst_audit(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "HPFA ANALYST AUDIT — PHASE-AWARE SEQUENCE REFINEMENT",
            (
                "Observed A-B-A phase oscillations: "
                f"{payload.get('A_B_A_phase_oscillation_count', 0)}"
            ),
            (
                "Same-timestamp adjacent phase pairs: "
                f"{payload.get('same_timestamp_adjacent_phase_pair_count', 0)}"
            ),
            (
                "Single-anchor refinement candidates: "
                f"{payload.get('refinement_candidate_count', 0)}"
            ),
            (
                "Insufficient-anchor cases: "
                f"{payload.get('insufficient_anchor_review_count', 0)}"
            ),
            (
                "Preserved source phase segments: "
                f"{payload.get('retained_source_phase_segment_count', 0)}"
            ),
            "Automatic merges: 0",
            "Automatic deletions: 0",
            (
                "Analyst-safe meaning: short A-B-A phase label changes are separated "
                "into retain, refinement-candidate and insufficient-anchor decisions."
            ),
            (
                "The surface does not prove possession, tactical intention, off-ball "
                "structure or validated sequence truth."
            ),
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "",
        ]
    )


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
    parser.add_argument("--event-derived-phase", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_phase_aware_sequence_refinement(
        load_json(
            args.event_derived_phase,
            "event_derived_phase_input_unreadable_or_malformed",
        )
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "phase_refinement_decision_count",
                    "A_B_A_phase_oscillation_count",
                    "refinement_candidate_count",
                    "insufficient_anchor_review_count",
                    "automatic_merge_count",
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
