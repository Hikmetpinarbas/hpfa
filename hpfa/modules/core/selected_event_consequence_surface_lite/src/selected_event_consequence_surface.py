from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .common import CANONICAL_EVENT_COUNT, MODULE_ID, OUTPUTS, load_json, validate_input, validate_out
    from .coordinate_frame import resolve_coordinate_frame
    from .event_consequence import build_records, composite_profiles
except ImportError:
    from common import CANONICAL_EVENT_COUNT, MODULE_ID, OUTPUTS, load_json, validate_input, validate_out
    from coordinate_frame import resolve_coordinate_frame
    from event_consequence import build_records, composite_profiles


def build_selected_event_consequence_surface(payload: dict[str, Any]) -> dict[str, Any]:
    blocks, reviews, binding, nodes, source_records = validate_input(payload)
    frame = resolve_coordinate_frame(nodes) if not blocks else {"coordinate_frame_status": "NOT_EVALUATED"}
    if frame.get("coordinate_frame_status") != "PASS_CANDIDATE_FRAME":
        reviews.append("coordinate_frame_review_required")
    records, record_blocks = build_records(payload, frame) if not blocks else ([], [])
    blocks.extend(record_blocks)
    if len(records) != len(source_records):
        blocks.append("selected_event_consequence_coverage_mismatch")
    team_profiles = composite_profiles(records, "team_identity_candidate_id", "TEAM_ACTION_FAMILY_EVENT_CONSEQUENCE_PROFILE_CANDIDATE") if not blocks else []
    actor_profiles = composite_profiles(records, "actor_identity_candidate_id", "ACTOR_ACTION_FAMILY_EVENT_CONSEQUENCE_PROFILE_CANDIDATE") if not blocks else []
    if any(record.get("consequence_class_candidate") == "UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED" for record in records):
        reviews.append("unresolved_event_consequence_candidates_present")
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    def counts(field: str) -> dict[str, int]:
        return dict(sorted(Counter(str(record.get(field)) for record in records).items()))

    return {
        "module_id": MODULE_ID,
        "version": "1.0.0",
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "source_module_id": payload.get("module_id"),
        "source_field_semantics_version": payload.get("field_semantics_version"),
        "coordinate_frame_candidate": frame,
        "selected_event_consequence_candidates": records,
        "selected_event_consequence_candidate_count": len(records),
        "team_action_family_event_consequence_profiles": team_profiles,
        "team_action_family_event_consequence_profile_count": len(team_profiles),
        "actor_action_family_event_consequence_profiles": actor_profiles,
        "actor_action_family_event_consequence_profile_count": len(actor_profiles),
        "zone_delta_class_counts": counts("zone_delta_class"),
        "pressure_first_action_class_counts": counts("pressure_first_action_class"),
        "turnover_window_class_counts": counts("turnover_window_class"),
        "retention_after_action_status_counts": counts("retention_after_action_status"),
        "false_progression_candidate_counts": counts("false_progression_candidate"),
        "consequence_class_candidate_counts": counts("consequence_class_candidate"),
        "source_selected_action_node_count": len(nodes),
        "source_selected_action_consequence_candidate_count": len(source_records),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "consequence_not_value": True,
        "consequence_not_quality": True,
        "zone_delta_not_xT": True,
        "zone_delta_not_progression_truth": True,
        "pressure_escape_not_pressure_truth": True,
        "turnover_to_box_not_transition_superiority": True,
        "false_progression_not_bad_decision": True,
        "analysis_sentence_generated": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "selected_event_consequence_candidate_count",
        "zone_delta_class_counts",
        "turnover_window_class_counts",
        "retention_after_action_status_counts",
        "false_progression_candidate_counts",
        "consequence_class_candidate_counts",
        "hard_block_hits",
        "review_hits",
    )
    lines = ["HPFA SELECTED EVENT CONSEQUENCE SURFACE LITE V1"] + [f"{key}={payload.get(key)}" for key in keys]
    return "\n".join(lines + ["canonical_event_count=UNKNOWN", "production_release=false"]) + "\n"


def analyst_audit(payload: dict[str, Any]) -> str:
    frame = payload.get("coordinate_frame_candidate") or {}
    lines = [
        "HPFA ANALYST AUDIT — SELECTED EVENT CONSEQUENCE SURFACE",
        f"Coordinate frame status: {frame.get('coordinate_frame_status')}",
        f"Coordinate scale candidate: {frame.get('coordinate_scale_candidate')}",
        f"Visible consequence candidates: {payload.get('selected_event_consequence_candidate_count', 0)}",
        f"Zone delta classes: {payload.get('zone_delta_class_counts')}",
        f"Turnover window classes: {payload.get('turnover_window_class_counts')}",
        f"Retention statuses: {payload.get('retention_after_action_status_counts')}",
        f"False-progression candidates: {payload.get('false_progression_candidate_counts')}",
        f"Categorical consequence classes: {payload.get('consequence_class_candidate_counts')}",
        "Analyst-safe meaning: visible selected-action relations are converted into categorical continuation, handover, zone-change and breakdown-window candidates.",
        "These records are not xT, value, quality, possession, pressure, causal, tactical or decision truth.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-action-consequence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_selected_event_consequence_surface(load_json(args.selected_action_consequence, "selected_action_consequence_input_unreadable_or_malformed"))
    write_outputs(payload, args.out)
    print(json.dumps({key: payload.get(key) for key in ("status", "selected_event_consequence_candidate_count", "zone_delta_class_counts", "turnover_window_class_counts", "consequence_class_candidate_counts", "canonical_event_count", "production_release")}, ensure_ascii=False, indent=2))
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
