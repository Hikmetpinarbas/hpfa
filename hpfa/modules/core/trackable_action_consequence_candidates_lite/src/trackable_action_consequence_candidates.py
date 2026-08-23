from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
EVIDENCE_MODULE_ID = "evidence_atom_inventory_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "VISIBLE_CONSEQUENCE_CANDIDATE_ONLY"
WINDOW_SECONDS = (5.0, 8.0, 12.0)
MAX_FOLLOW_UP_LAYERS = 3
SUPPORT_ATOM_CLASSES = {"DERIVED_CONSEQUENCE_ATOM", "TERMINAL_OUTCOME_ATOM"}
ALLOWED_TRACE_ROLES = {"PLAYER_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE"}
REVIEW_CLASSES = {
    "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE",
    "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE",
}
OUTPUTS = {
    "json": "trackable_action_consequence_candidates_lite_v1.json",
    "summary": "trackable_action_consequence_candidates_lite_v1.txt",
    "analyst": "trackable_action_consequence_candidates_analyst_audit_v1.txt",
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _number(value: Any) -> float | None:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return None


def _number_key(value: Any) -> str:
    parsed = _number(value)
    return f"{parsed:.6f}" if parsed is not None else _clean(value)


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def _support_core(record: dict[str, Any]) -> tuple[str, ...]:
    return (
        _clean(record.get("match_surface_binding_id")),
        _clean(record.get("source_role")),
        _clean(record.get("period_candidate")),
        _number_key(record.get("start_candidate")),
        _number_key(record.get("end_candidate")),
        _number_key(record.get("pos_x_candidate")),
        _number_key(record.get("pos_y_candidate")),
    )


def _validate_trace(trace: dict[str, Any], index: int, binding: str) -> list[str]:
    blocks: list[str] = []
    trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
    if not trace_id:
        blocks.append(f"trace_id_missing:{index}")
    if trace.get("match_surface_binding_id") != binding:
        blocks.append(f"trace_binding_mismatch:{index}")
    if trace.get("source_role") not in ALLOWED_TRACE_ROLES:
        blocks.append(f"trace_source_role_rejected:{index}")
    if not _clean(trace.get("team_identity_candidate_id")):
        blocks.append(f"trace_team_identity_candidate_missing:{index}")
    if not _clean(trace.get("actor_identity_candidate_id")):
        blocks.append(f"trace_actor_identity_candidate_missing:{index}")
    if _number(trace.get("start_candidate")) is None or _number(trace.get("end_candidate")) is None:
        blocks.append(f"trace_time_invalid:{index}")
    if not _clean(trace.get("period_candidate")):
        blocks.append(f"trace_period_missing:{index}")
    families = trace.get("action_family_candidates") or []
    if not isinstance(families, list) or not families or not all(_clean(item) for item in families):
        blocks.append(f"trace_action_family_candidates_invalid:{index}")
    if trace.get("trackable_action_candidate_is_event_truth") is True:
        blocks.append(f"trace_event_truth_claimed:{index}")
    if trace.get("physical_action_identity_truth") is True:
        blocks.append(f"trace_physical_action_truth_claimed:{index}")
    if trace.get("sequence_link_allowed") is True:
        blocks.append(f"trace_sequence_link_claimed:{index}")
    if trace.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"trace_canonical_event_count_claimed:{index}")
    return blocks


def _timeline_key(trace: dict[str, Any]) -> tuple[Any, ...]:
    period = _clean(trace.get("period_candidate"))
    try:
        period_key: Any = int(float(period))
    except (TypeError, ValueError):
        period_key = period
    start = _number(trace.get("start_candidate"))
    end = _number(trace.get("end_candidate"))
    return (
        period_key,
        float("inf") if start is None else start,
        float("inf") if end is None else end,
        _clean(trace.get("trackable_action_trace_candidate_id")),
    )


def _team_family_sets(anchor_team: str, future: list[dict[str, Any]]) -> tuple[set[str], set[str], bool]:
    same_team: set[str] = set()
    opponent: set[str] = set()
    missing_team = False
    for trace in future:
        team = _clean(trace.get("team_identity_candidate_id"))
        families = {_clean(item) for item in (trace.get("action_family_candidates") or []) if _clean(item)}
        if not team:
            missing_team = True
        elif team == anchor_team:
            same_team.update(families)
        else:
            opponent.update(families)
    return same_team, opponent, missing_team


def _first_layer_team_state(anchor_team: str, future: list[dict[str, Any]]) -> str:
    if not future:
        return "NONE"
    first_start = _number(future[0].get("start_candidate"))
    layer = [trace for trace in future if _number(trace.get("start_candidate")) == first_start]
    teams = {_clean(trace.get("team_identity_candidate_id")) for trace in layer}
    if "" in teams:
        return "UNKNOWN"
    has_same = anchor_team in teams
    has_opponent = any(team != anchor_team for team in teams)
    if has_same and has_opponent:
        return "MIXED"
    if has_same:
        return "SAME_TEAM"
    if has_opponent:
        return "OPPONENT"
    return "UNKNOWN"


def _classify_consequence(
    anchor: dict[str, Any],
    future: list[dict[str, Any]],
    terminal_support_visible: bool,
    derived_support_visible: bool,
) -> tuple[str, list[str]]:
    team = _clean(anchor.get("team_identity_candidate_id"))
    anchor_families = {_clean(item) for item in (anchor.get("action_family_candidates") or []) if _clean(item)}
    signals: set[str] = set()
    if terminal_support_visible:
        signals.add("TERMINAL_OUTCOME_SUPPORT_VISIBLE")
    if derived_support_visible:
        signals.add("DERIVED_CONSEQUENCE_SUPPORT_VISIBLE")
    if not team:
        signals.add("ANCHOR_TEAM_IDENTITY_MISSING")
        return "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE", sorted(signals)
    if not future:
        if terminal_support_visible:
            return "TERMINAL_OUTCOME_SUPPORT_CANDIDATE", sorted(signals)
        return "NO_VISIBLE_FOLLOW_UP_CANDIDATE", sorted(signals)

    same_team, opponent, missing_team = _team_family_sets(team, future)
    first_state = _first_layer_team_state(team, future)
    flags = {
        "SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE": "SHOT" in same_team,
        "OPPONENT_SHOT_FOLLOW_UP_VISIBLE": "SHOT" in opponent,
        "SAME_TEAM_RESTART_FOLLOW_UP_VISIBLE": "RESTART" in same_team,
        "OPPONENT_RESTART_FOLLOW_UP_VISIBLE": "RESTART" in opponent,
        "SAME_TEAM_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE": bool({"RECOVERY", "INTERCEPTION"} & same_team),
        "OPPONENT_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE": bool({"RECOVERY", "INTERCEPTION"} & opponent),
        "SAME_TEAM_TURNOVER_OR_CONTROL_ERROR_FOLLOW_UP_VISIBLE": bool({"TURNOVER", "CONTROL_ERROR"} & same_team),
        "OPPONENT_TURNOVER_OR_CONTROL_ERROR_FOLLOW_UP_VISIBLE": bool({"TURNOVER", "CONTROL_ERROR"} & opponent),
        "SAME_TEAM_FOLLOW_UP_VISIBLE": bool(same_team),
        "OPPONENT_FOLLOW_UP_VISIBLE": bool(opponent),
        "MIXED_TEAM_FIRST_LAYER_VISIBLE": first_state == "MIXED",
        "FOLLOW_UP_TEAM_IDENTITY_MISSING": missing_team,
    }
    signals.update(name for name, active in flags.items() if active)

    if terminal_support_visible:
        primary = "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"
    elif missing_team:
        primary = "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE"
    elif first_state == "MIXED":
        primary = "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE"
    elif flags["SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE"]:
        primary = "SHOT_FOLLOW_UP_CANDIDATE"
    elif anchor_families & {"TURNOVER", "CONTROL_ERROR"}:
        if flags["SAME_TEAM_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE"]:
            primary = "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"
        elif first_state == "OPPONENT":
            primary = "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"
        else:
            primary = "BREAKDOWN_WITH_UNCERTAIN_VISIBLE_RESPONSE_CANDIDATE"
    elif anchor_families & {"RECOVERY", "INTERCEPTION"} and first_state == "SAME_TEAM":
        primary = "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
    elif first_state == "SAME_TEAM" and "RESTART" in same_team:
        primary = "RESTART_OR_RESET_CANDIDATE"
    elif first_state == "SAME_TEAM":
        primary = "SAME_TEAM_CONTINUATION_CANDIDATE"
    elif first_state == "OPPONENT":
        primary = "OPPONENT_HANDOVER_CANDIDATE"
    else:
        primary = "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE"
    return primary, sorted(signals)


def build_trackable_action_consequence_candidates(
    trace_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if trace_payload.get("module_id") != TRACE_MODULE_ID:
        blocks.append("trace_input_module_id_mismatch")
    if evidence_payload.get("module_id") != EVIDENCE_MODULE_ID:
        blocks.append("evidence_input_module_id_mismatch")
    for prefix, payload in (("trace", trace_payload), ("evidence", evidence_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{prefix}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{prefix}_hard_blocks_present")

    trace_binding = _clean(trace_payload.get("match_surface_binding_id"))
    evidence_binding = _clean(evidence_payload.get("match_surface_binding_id"))
    if not trace_binding or trace_binding != evidence_binding:
        blocks.append("match_surface_binding_mismatch")

    traces = trace_payload.get("trackable_action_trace_candidates") or []
    atoms = evidence_payload.get("evidence_atoms") or []
    if not isinstance(traces, list) or not traces:
        blocks.append("trackable_action_trace_candidates_empty_or_invalid")
        traces = []
    if not isinstance(atoms, list):
        blocks.append("evidence_atoms_invalid")
        atoms = []
    if trace_payload.get("trackable_action_trace_candidate_count") != len(traces):
        blocks.append("trace_candidate_count_mismatch")
    if evidence_payload.get("evidence_atom_count") != len(atoms):
        blocks.append("evidence_atom_count_mismatch")

    trace_ids: set[str] = set()
    for index, trace in enumerate(traces):
        if not isinstance(trace, dict):
            blocks.append(f"trace_record_invalid:{index}")
            continue
        blocks.extend(_validate_trace(trace, index, trace_binding))
        trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
        if trace_id in trace_ids:
            blocks.append(f"duplicate_trace_id:{trace_id}")
        trace_ids.add(trace_id)

    support_index: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for index, atom in enumerate(atoms):
        if not isinstance(atom, dict):
            blocks.append(f"evidence_atom_invalid:{index}")
            continue
        if atom.get("atom_class") not in SUPPORT_ATOM_CLASSES or atom.get("atom_status") != "PASS":
            continue
        if atom.get("match_surface_binding_id") != trace_binding:
            blocks.append(f"support_atom_binding_mismatch:{index}")
            continue
        support_index[_support_core(atom)].append(atom)

    records: list[dict[str, Any]] = []
    by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not blocks:
        for trace in traces:
            by_period[_clean(trace.get("period_candidate"))].append(trace)

        for period_traces in by_period.values():
            period_traces.sort(key=_timeline_key)
            for index, anchor in enumerate(period_traces):
                anchor_start = _number(anchor.get("start_candidate"))
                layer_map: dict[float, list[dict[str, Any]]] = defaultdict(list)
                if anchor_start is not None:
                    for candidate in period_traces[index + 1 :]:
                        candidate_start = _number(candidate.get("start_candidate"))
                        if candidate_start is None:
                            continue
                        delta = candidate_start - anchor_start
                        if delta <= 0:
                            continue
                        if delta > WINDOW_SECONDS[-1]:
                            break
                        layer_map[candidate_start].append(candidate)
                layers = [
                    sorted(layer_map[start], key=_timeline_key)
                    for start in sorted(layer_map)[:MAX_FOLLOW_UP_LAYERS]
                ]
                future = [trace for layer in layers for trace in layer]
                support_atoms = support_index.get(_support_core(anchor), [])
                class_counts = Counter(_clean(atom.get("atom_class")) for atom in support_atoms)
                terminal_visible = class_counts.get("TERMINAL_OUTCOME_ATOM", 0) > 0
                derived_visible = class_counts.get("DERIVED_CONSEQUENCE_ATOM", 0) > 0
                primary, signals = _classify_consequence(
                    anchor,
                    future,
                    terminal_visible,
                    derived_visible,
                )
                first_delta = None
                if future and anchor_start is not None:
                    first_start = _number(future[0].get("start_candidate"))
                    if first_start is not None:
                        first_delta = round(first_start - anchor_start, 6)
                window_counts = {}
                for seconds in WINDOW_SECONDS:
                    window_counts[f"visible_follow_up_trace_count_{int(seconds)}s"] = sum(
                        1
                        for trace in future
                        if _number(trace.get("start_candidate")) is not None
                        and anchor_start is not None
                        and 0 < (_number(trace.get("start_candidate")) or anchor_start) - anchor_start <= seconds
                    )
                record_status = "REVIEW_REQUIRED" if primary in REVIEW_CLASSES else "PASS_CANDIDATE_CLASSIFICATION"
                records.append(
                    {
                        "trackable_action_consequence_candidate_id": "tacc_"
                        + _digest(
                            anchor.get("trackable_action_trace_candidate_id"),
                            [trace.get("trackable_action_trace_candidate_id") for trace in future],
                        )[:24],
                        "anchor_trackable_action_trace_candidate_id": anchor.get("trackable_action_trace_candidate_id"),
                        "match_surface_binding_id": trace_binding,
                        "source_role": anchor.get("source_role"),
                        "team_identity_candidate_id": anchor.get("team_identity_candidate_id"),
                        "actor_identity_candidate_id": anchor.get("actor_identity_candidate_id"),
                        "period_candidate": anchor.get("period_candidate"),
                        "anchor_start_candidate": anchor.get("start_candidate"),
                        "anchor_end_candidate": anchor.get("end_candidate"),
                        "anchor_action_family_candidates": anchor.get("action_family_candidates") or [],
                        "follow_up_layer_count": len(layers),
                        "follow_up_trace_ids_by_layer": [
                            [trace.get("trackable_action_trace_candidate_id") for trace in layer]
                            for layer in layers
                        ],
                        "visible_follow_up_trace_ids": [
                            trace.get("trackable_action_trace_candidate_id") for trace in future
                        ],
                        "first_visible_follow_up_delta_seconds": first_delta,
                        **window_counts,
                        "primary_consequence_candidate": primary,
                        "consequence_signal_candidates": signals,
                        "record_status": record_status,
                        "supporting_consequence_evidence_atom_ids": sorted(
                            _clean(atom.get("evidence_atom_id")) for atom in support_atoms
                        ),
                        "support_atom_class_counts": dict(sorted(class_counts.items())),
                        "terminal_outcome_support_visible": terminal_visible,
                        "derived_consequence_support_visible": derived_visible,
                        "same_time_link_allowed": False,
                        "negative_time_link_allowed": False,
                        "cross_period_link_allowed": False,
                        "window_is_sequence_truth": False,
                        "continuation_is_possession_truth": False,
                        "consequence_candidate_is_causal_truth": False,
                        "team_response_is_tactical_truth": False,
                        "event_instance_allowed": False,
                        "validated_event_identity": False,
                        "canonical_event_count": CANONICAL_EVENT_COUNT,
                        "claim_ceiling": CLAIM_CEILING,
                    }
                )

    if len(records) != len(traces) and not blocks:
        blocks.append("consequence_trace_coverage_mismatch")
    anchor_ids = [_clean(record.get("anchor_trackable_action_trace_candidate_id")) for record in records]
    if len(anchor_ids) != len(set(anchor_ids)) and not blocks:
        blocks.append("consequence_anchor_trace_reused")
    if set(anchor_ids) != trace_ids and not blocks:
        blocks.append("consequence_anchor_trace_set_mismatch")

    consequence_counts = Counter(record.get("primary_consequence_candidate") for record in records)
    review_required_count = sum(record.get("record_status") == "REVIEW_REQUIRED" for record in records)
    classified_count = len(records) - review_required_count
    support_visible_count = sum(bool(record.get("supporting_consequence_evidence_atom_ids")) for record in records)
    window_coverage = {
        f"visible_follow_up_within_{int(seconds)}s": sum(
            int(record.get(f"visible_follow_up_trace_count_{int(seconds)}s") or 0) > 0
            for record in records
        )
        for seconds in WINDOW_SECONDS
    }

    for prefix, payload in (("trace", trace_payload), ("evidence", evidence_payload)):
        status = str(payload.get("module_status") or payload.get("status") or "UNKNOWN")
        if status == "FAIL_CLOSED":
            blocks.append(f"{prefix}_input_fail_closed")
        elif status == "REVIEW_REQUIRED":
            reviews.append(f"{prefix}_upstream_review_required")
        elif status != "PASS":
            reviews.append(f"{prefix}_upstream_status_review:{status}")
    if review_required_count:
        reviews.append("review_required_visible_consequence_candidates_present")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": trace_binding or None,
        "trackable_action_consequence_candidates": records,
        "source_trackable_action_trace_candidate_count": len(traces),
        "trackable_action_consequence_candidate_count": len(records),
        "classified_consequence_candidate_count": classified_count,
        "review_required_consequence_candidate_count": review_required_count,
        "support_visible_trace_count": support_visible_count,
        "primary_consequence_candidate_counts": dict(sorted(consequence_counts.items())),
        "window_coverage_counts": window_coverage,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "window_seconds": list(WINDOW_SECONDS),
        "max_follow_up_time_layers": MAX_FOLLOW_UP_LAYERS,
        "same_time_link_allowed": False,
        "negative_time_link_allowed": False,
        "cross_period_link_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "consequence_candidate_is_causal_truth": False,
        "continuation_candidate_is_possession_truth": False,
        "window_is_sequence_truth": False,
        "team_response_is_tactical_truth": False,
        "sequence_link_allowed": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA TRACKABLE ACTION CONSEQUENCE CANDIDATES LITE V1",
        f"status={payload.get('status')}",
        f"source_trackable_action_trace_candidate_count={payload.get('source_trackable_action_trace_candidate_count')}",
        f"trackable_action_consequence_candidate_count={payload.get('trackable_action_consequence_candidate_count')}",
        f"classified_consequence_candidate_count={payload.get('classified_consequence_candidate_count')}",
        f"review_required_consequence_candidate_count={payload.get('review_required_consequence_candidate_count')}",
        f"support_visible_trace_count={payload.get('support_visible_trace_count')}",
        f"primary_consequence_candidate_counts={payload.get('primary_consequence_candidate_counts')}",
        f"window_coverage_counts={payload.get('window_coverage_counts')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def _analyst(payload: dict[str, Any]) -> str:
    counts = payload.get("primary_consequence_candidate_counts") or {}
    windows = payload.get("window_coverage_counts") or {}
    lines = [
        "HPFA ANALYST AUDIT — TRACKABLE ACTION CONSEQUENCE CANDIDATES",
        f"Visible trackable trace anchors: {payload.get('trackable_action_consequence_candidate_count', 0)}",
        f"Same-team continuation candidates: {counts.get('SAME_TEAM_CONTINUATION_CANDIDATE', 0)}",
        f"Opponent handover candidates: {counts.get('OPPONENT_HANDOVER_CANDIDATE', 0)}",
        f"Shot follow-up candidates: {counts.get('SHOT_FOLLOW_UP_CANDIDATE', 0)}",
        f"No visible follow-up candidates: {counts.get('NO_VISIBLE_FOLLOW_UP_CANDIDATE', 0)}",
        f"Review-required mixed/uncertain candidates: {payload.get('review_required_consequence_candidate_count', 0)}",
        f"Visible follow-up within 5s: {windows.get('visible_follow_up_within_5s', 0)}",
        f"Visible follow-up within 8s: {windows.get('visible_follow_up_within_8s', 0)}",
        f"Visible follow-up within 12s: {windows.get('visible_follow_up_within_12s', 0)}",
        "Analyst-safe meaning: visible trace candidates were linked only to later positive-time traces in the same period, within a capped 12-second window and at most three distinct later time layers.",
        "These are consequence candidates, not causal, possession, sequence, tactical, physical-action or canonical-event truth.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(_analyst(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trackable-action-trace", required=True)
    parser.add_argument("--evidence-atoms", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    trace_payload = load_json(args.trackable_action_trace, "trackable_action_trace_input_unreadable_or_malformed")
    evidence_payload = load_json(args.evidence_atoms, "evidence_atom_input_unreadable_or_malformed")
    payload = build_trackable_action_consequence_candidates(trace_payload, evidence_payload)
    write_outputs(payload, args.out)
    print(json.dumps({
        "status": payload.get("status"),
        "trackable_action_consequence_candidate_count": payload.get("trackable_action_consequence_candidate_count"),
        "classified_consequence_candidate_count": payload.get("classified_consequence_candidate_count"),
        "review_required_consequence_candidate_count": payload.get("review_required_consequence_candidate_count"),
        "primary_consequence_candidate_counts": payload.get("primary_consequence_candidate_counts") or {},
        "window_coverage_counts": payload.get("window_coverage_counts") or {},
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
