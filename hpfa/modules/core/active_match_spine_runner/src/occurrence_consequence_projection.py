from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "occurrence_consequence_projection_v1"
OUTPUT_JSON = "occurrence_consequence_projection_v1.json"
OUTPUT_TXT = "occurrence_consequence_projection_v1.txt"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _values(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sorted_text(values: Any) -> list[str]:
    return sorted({_text(value) for value in _values(values) if _text(value)})


def _union_text(records: list[dict[str, Any]], key: str) -> list[str]:
    values: set[str] = set()
    for record in records:
        values.update(_sorted_text(record.get(key)))
    return sorted(values)


def _candidate_id(occurrence_id: str) -> str:
    digest = hashlib.sha1(occurrence_id.encode("utf-8")).hexdigest()[:24]
    return f"ocp_{digest}"


def build_occurrence_consequence_projection(
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    trace_records = [
        row
        for row in _values(trace_payload.get("trackable_action_trace_candidates"))
        if isinstance(row, dict)
    ]
    consequence_records = [
        row
        for row in _values(consequence_payload.get("trackable_action_consequence_candidates"))
        if isinstance(row, dict)
    ]
    binding_records = [
        row
        for row in _values(trace_payload.get("occurrence_trace_binding_records"))
        if isinstance(row, dict)
    ]

    binding_by_occurrence = {
        _text(row.get("action_occurrence_candidate_id")): row
        for row in binding_records
        if _text(row.get("action_occurrence_candidate_id"))
    }
    traces_by_occurrence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trace in trace_records:
        for occurrence_id in _sorted_text(trace.get("supporting_action_occurrence_candidate_ids")):
            traces_by_occurrence[occurrence_id].append(trace)

    consequences_by_occurrence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for consequence in consequence_records:
        for occurrence_id in _sorted_text(consequence.get("supporting_action_occurrence_candidate_ids")):
            consequences_by_occurrence[occurrence_id].append(consequence)

    occurrence_ids = sorted(set(binding_by_occurrence) | set(traces_by_occurrence) | set(consequences_by_occurrence))
    records: list[dict[str, Any]] = []
    visible_count = 0
    review_count = 0
    no_consequence_record_count = 0
    terminal_support_count = 0

    for occurrence_id in occurrence_ids:
        binding = binding_by_occurrence.get(occurrence_id, {})
        traces = traces_by_occurrence.get(occurrence_id, [])
        consequences = consequences_by_occurrence.get(occurrence_id, [])

        trace_ids = sorted(
            {
                _text(row.get("trackable_action_trace_candidate_id"))
                for row in traces
                if _text(row.get("trackable_action_trace_candidate_id"))
            }
        )
        consequence_ids = sorted(
            {
                _text(row.get("trackable_action_consequence_candidate_id"))
                for row in consequences
                if _text(row.get("trackable_action_consequence_candidate_id"))
            }
        )
        visible_follow_up_ids = _union_text(consequences, "visible_follow_up_trace_ids")
        admitted_after_ids = _union_text(consequences, "admitted_after_follow_up_trace_ids")
        consequence_signals = _union_text(consequences, "consequence_signal_candidates")
        primary_candidates = sorted(
            {
                _text(row.get("primary_consequence_candidate"))
                for row in consequences
                if _text(row.get("primary_consequence_candidate"))
            }
        )
        action_families: set[str] = set()
        actor_ids: set[str] = set()
        team_ids: set[str] = set()
        periods: set[str] = set()
        starts: set[str] = set()
        ends: set[str] = set()
        source_roles: set[str] = set()
        for trace in traces:
            action_families.update(_sorted_text(trace.get("action_family_candidates")))
            if _text(trace.get("actor_identity_candidate_id")):
                actor_ids.add(_text(trace.get("actor_identity_candidate_id")))
            if _text(trace.get("team_identity_candidate_id")):
                team_ids.add(_text(trace.get("team_identity_candidate_id")))
            if _text(trace.get("period_candidate")):
                periods.add(_text(trace.get("period_candidate")))
            if _text(trace.get("start_candidate")):
                starts.add(_text(trace.get("start_candidate")))
            if _text(trace.get("end_candidate")):
                ends.add(_text(trace.get("end_candidate")))
            if _text(trace.get("source_role")):
                source_roles.add(_text(trace.get("source_role")))

        terminal_support = any(row.get("terminal_outcome_support_visible") is True for row in consequences)
        derived_support = any(row.get("derived_consequence_support_visible") is True for row in consequences)
        visible = bool(visible_follow_up_ids or terminal_support or derived_support)
        any_review = any(_text(row.get("record_status")).upper() == "REVIEW_REQUIRED" for row in consequences)
        missing_trace = not trace_ids
        missing_consequence = not consequence_ids
        record_status = "REVIEW_REQUIRED" if (any_review or missing_trace or missing_consequence) else "PASS"

        if visible:
            visible_count += 1
        if record_status == "REVIEW_REQUIRED":
            review_count += 1
        if missing_consequence:
            no_consequence_record_count += 1
        if terminal_support:
            terminal_support_count += 1

        records.append(
            {
                "occurrence_consequence_projection_id": _candidate_id(occurrence_id),
                "action_occurrence_candidate_id": occurrence_id,
                "occurrence_topology": _text(binding.get("occurrence_topology")) or "UNRESOLVED",
                "required_participant_scope": _text(binding.get("required_participant_scope")) or "UNRESOLVED",
                "binding_state": _text(binding.get("binding_state")) or "UNRESOLVED",
                "supporting_trackable_action_trace_candidate_ids": trace_ids,
                "supporting_consequence_candidate_ids": consequence_ids,
                "supporting_trace_candidate_count": len(trace_ids),
                "supporting_consequence_candidate_count": len(consequence_ids),
                "actor_identity_candidate_ids": sorted(actor_ids),
                "team_identity_candidate_ids": sorted(team_ids),
                "source_roles": sorted(source_roles),
                "action_family_candidates": sorted(action_families),
                "period_candidates": sorted(periods),
                "start_candidates": sorted(starts),
                "end_candidates": sorted(ends),
                "visible_follow_up_trace_ids": visible_follow_up_ids,
                "admitted_after_follow_up_trace_ids": admitted_after_ids,
                "consequence_signal_candidates": consequence_signals,
                "primary_consequence_candidates": primary_candidates,
                "terminal_outcome_support_visible": terminal_support,
                "derived_consequence_support_visible": derived_support,
                "visible_consequence_support": visible,
                "record_status": record_status,
                "projection_is_action_identity_truth": False,
                "projection_is_sequence_truth": False,
                "projection_is_possession_truth": False,
                "projection_is_causal_truth": False,
                "same_timestamp_is_total_order": False,
                "source_row_order_is_temporal_truth": False,
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            }
        )

    expected_occurrence_count = int(trace_payload.get("current_occurrence_candidate_count") or 0)
    projection_count = len(records)
    hard_blocks: list[str] = []
    review_hits: list[str] = []
    if expected_occurrence_count and projection_count != expected_occurrence_count:
        hard_blocks.append("occurrence_projection_count_mismatch")
    if review_count:
        review_hits.append("occurrence_consequence_projection_review_required")
    if no_consequence_record_count:
        review_hits.append("occurrence_without_consequence_record_present")

    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "source_trace_status": trace_payload.get("status"),
        "source_consequence_status": consequence_payload.get("status"),
        "source_legacy_trace_candidate_count": trace_payload.get("trackable_action_trace_candidate_count", 0),
        "source_legacy_consequence_candidate_count": consequence_payload.get("trackable_action_consequence_candidate_count", 0),
        "source_action_occurrence_candidate_count": expected_occurrence_count,
        "occurrence_consequence_projection_count": projection_count,
        "occurrence_with_visible_consequence_support_count": visible_count,
        "review_required_occurrence_projection_count": review_count,
        "occurrence_without_consequence_record_count": no_consequence_record_count,
        "occurrence_with_terminal_outcome_support_count": terminal_support_count,
        "occurrence_consequence_projections": records,
        "legacy_trace_records_are_support_evidence_not_action_universe": True,
        "occurrence_projection_is_primary_action_member_candidate_surface": True,
        "projection_is_action_identity_truth": False,
        "projection_is_sequence_truth": False,
        "projection_is_possession_truth": False,
        "projection_is_causal_truth": False,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(
        "\n".join(
            [
                "HPFA OCCURRENCE CONSEQUENCE PROJECTION V1",
                f"status={payload.get('status')}",
                f"source_action_occurrence_candidate_count={payload.get('source_action_occurrence_candidate_count', 0)}",
                f"occurrence_consequence_projection_count={payload.get('occurrence_consequence_projection_count', 0)}",
                f"occurrence_with_visible_consequence_support_count={payload.get('occurrence_with_visible_consequence_support_count', 0)}",
                f"review_required_occurrence_projection_count={payload.get('review_required_occurrence_projection_count', 0)}",
                f"source_legacy_trace_candidate_count={payload.get('source_legacy_trace_candidate_count', 0)}",
                f"source_legacy_consequence_candidate_count={payload.get('source_legacy_consequence_candidate_count', 0)}",
                "legacy_trace_records_are_support_evidence_not_action_universe=true",
                "projection_is_causal_truth=false",
                "canonical_event_count=UNKNOWN",
                "true_action_count=UNKNOWN",
                "production_release=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"json": json_path, "txt": txt_path}
