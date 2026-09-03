from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "reciprocal_process_chain_lite_v1"
SEQUENCE_MODULE_ID = "visible_action_sequence_candidates_lite_v1"
TEMPORAL_MODULE_ID = "temporal_episode_signature_lite_v1"
CLAIM_CEILING = "RECIPROCAL_VISIBLE_PROCESS_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "reciprocal_process_chain_lite_v1.json"
OUTPUT_TXT = "reciprocal_process_chain_lite_v1.txt"
ANALYST_TXT = "reciprocal_process_chain_analyst_audit_v1.txt"
PASS_SEQUENCE_STATUSES = {
    "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
    "PASS_SINGLE_LAYER_VISIBLE_TRACE_CANDIDATE",
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _number(value: Any) -> float | None:
    try:
        number = float(_clean(value))
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _period_key(value: Any) -> tuple[int, Any]:
    text = _clean(value)
    try:
        return (0, int(float(text)))
    except (TypeError, ValueError):
        return (1, text)


def _sequence_key(row: dict[str, Any]) -> tuple[Any, ...]:
    start = _number(row.get("start_time_candidate"))
    end = _number(row.get("end_time_candidate"))
    return (
        _period_key(row.get("period_candidate")),
        float("inf") if start is None else start,
        float("inf") if end is None else end,
        _clean(row.get("visible_action_sequence_candidate_id")),
    )


def _validate_input(sequence_payload: dict[str, Any], temporal_payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if sequence_payload.get("module_id") != SEQUENCE_MODULE_ID:
        blocks.append("sequence_module_id_mismatch")
    if temporal_payload.get("module_id") != TEMPORAL_MODULE_ID:
        blocks.append("temporal_module_id_mismatch")
    for name, payload in (("sequence", sequence_payload), ("temporal", temporal_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
            blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")
        status = payload.get("status") or payload.get("module_status")
        if status == "FAIL_CLOSED":
            blocks.append(f"{name}_upstream_fail_closed")
        elif status == "REVIEW_REQUIRED":
            reviews.append(f"{name}_upstream_review_required")
    if sequence_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("sequence_same_time_policy_breached")
    if sequence_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("sequence_row_order_policy_breached")
    return sorted(set(blocks)), sorted(set(reviews))


def _episode_index(temporal_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in temporal_payload.get("temporal_episode_signatures") or []:
        if not isinstance(row, dict):
            continue
        start = _number(row.get("start_second_candidate"))
        end = _number(row.get("end_second_candidate"))
        episode_id = _clean(row.get("episode_candidate_id"))
        if start is None or end is None or end < start or not episode_id:
            continue
        by_period[_clean(row.get("period_candidate"))].append({
            "episode_candidate_id": episode_id,
            "start": start,
            "end": end,
        })
    for rows in by_period.values():
        rows.sort(key=lambda item: (item["start"], item["end"], item["episode_candidate_id"]))
    return by_period


def _bind_episode(sequence: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> tuple[str | None, str]:
    """Bind only when the complete visible-sequence interval fits one episode.

    Start-only containment is unsafe: an independently constructed visible sequence
    may begin inside one episode and end after its boundary. Such a record must be
    review-required rather than silently attached to the first episode.
    """
    start = _number(sequence.get("start_time_candidate"))
    end = _number(sequence.get("end_time_candidate"))
    period = _clean(sequence.get("period_candidate"))
    if start is None or end is None or end < start:
        return None, "SEQUENCE_TIME_INVALID"

    period_rows = index.get(period, [])
    full_matches = [row for row in period_rows if row["start"] <= start and end <= row["end"]]
    if len(full_matches) == 1:
        return full_matches[0]["episode_candidate_id"], "UNIQUE_TIME_CONTAINMENT_CANDIDATE"
    if len(full_matches) > 1:
        return None, "MULTIPLE_EPISODE_TIME_CONTAINMENT_REVIEW_REQUIRED"

    start_matches = [row for row in period_rows if row["start"] <= start <= row["end"]]
    end_matches = [row for row in period_rows if row["start"] <= end <= row["end"]]
    if start_matches or end_matches:
        return None, "SEQUENCE_CROSSES_EPISODE_BOUNDARY_REVIEW_REQUIRED"
    return None, "NO_EPISODE_TIME_CONTAINMENT"


def _positive_counts(row: dict[str, Any], field: str) -> dict[str, int]:
    raw = row.get(field) or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count > 0:
            out[_clean(key)] = count
    return dict(sorted(out.items()))


def _family_counts(row: dict[str, Any]) -> dict[str, int]:
    return _positive_counts(row, "action_family_counts")


def _consequence_counts(row: dict[str, Any]) -> dict[str, int]:
    return _positive_counts(row, "consequence_candidate_counts")


def build_reciprocal_process_chains(sequence_payload: dict[str, Any], temporal_payload: dict[str, Any]) -> dict[str, Any]:
    blocks, reviews = _validate_input(sequence_payload, temporal_payload)
    sequences = sequence_payload.get("visible_action_sequence_candidates") or []
    if not isinstance(sequences, list):
        blocks.append("visible_action_sequence_candidates_invalid")
        sequences = []
    if sequence_payload.get("visible_action_sequence_candidate_count") != len(sequences):
        blocks.append("visible_action_sequence_candidate_count_mismatch")

    valid: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(sequences):
        if not isinstance(row, dict):
            blocks.append(f"sequence_record_invalid:{index}")
            continue
        sequence_id = _clean(row.get("visible_action_sequence_candidate_id"))
        team = _clean(row.get("team_identity_candidate_id"))
        start = _number(row.get("start_time_candidate"))
        end = _number(row.get("end_time_candidate"))
        if not sequence_id or sequence_id in seen:
            blocks.append(f"sequence_id_missing_or_duplicate:{index}")
            continue
        seen.add(sequence_id)
        if row.get("sequence_record_status") not in PASS_SEQUENCE_STATUSES:
            continue
        if not team or start is None or end is None or end < start:
            reviews.append(f"sequence_not_reciprocal_eligible:{sequence_id}")
            continue
        valid.append(row)

    valid.sort(key=_sequence_key)
    episode_index = _episode_index(temporal_payload)
    records: list[dict[str, Any]] = []
    same_time_blocked = 0
    unknown_episode_bindings = 0

    for idx, anchor in enumerate(valid):
        anchor_team = _clean(anchor.get("team_identity_candidate_id"))
        anchor_end = _number(anchor.get("end_time_candidate"))
        anchor_period = _clean(anchor.get("period_candidate"))
        if anchor_end is None:
            continue

        response: dict[str, Any] | None = None
        response_idx: int | None = None
        for j in range(idx + 1, len(valid)):
            candidate = valid[j]
            if _clean(candidate.get("period_candidate")) != anchor_period:
                break
            candidate_start = _number(candidate.get("start_time_candidate"))
            if candidate_start is None:
                continue
            if candidate_start == anchor_end:
                same_time_blocked += 1
                continue
            if candidate_start < anchor_end:
                continue
            candidate_team = _clean(candidate.get("team_identity_candidate_id"))
            if candidate_team and candidate_team != anchor_team:
                response = candidate
                response_idx = j
                break
        if response is None or response_idx is None:
            continue

        response_end = _number(response.get("end_time_candidate"))
        counter: dict[str, Any] | None = None
        if response_end is not None:
            for k in range(response_idx + 1, len(valid)):
                candidate = valid[k]
                if _clean(candidate.get("period_candidate")) != anchor_period:
                    break
                candidate_start = _number(candidate.get("start_time_candidate"))
                if candidate_start is None or candidate_start <= response_end:
                    continue
                if _clean(candidate.get("team_identity_candidate_id")) == anchor_team:
                    counter = candidate
                    break

        anchor_episode_id, anchor_bind = _bind_episode(anchor, episode_index)
        response_episode_id, response_bind = _bind_episode(response, episode_index)
        counter_episode_id, counter_bind = (None, "NOT_APPLICABLE") if counter is None else _bind_episode(counter, episode_index)
        if not anchor_episode_id or not response_episode_id or (counter is not None and not counter_episode_id):
            unknown_episode_bindings += 1

        anchor_id = _clean(anchor.get("visible_action_sequence_candidate_id"))
        response_id = _clean(response.get("visible_action_sequence_candidate_id"))
        counter_id = _clean(counter.get("visible_action_sequence_candidate_id")) if counter else None
        response_start = _number(response.get("start_time_candidate"))
        delta = None if response_start is None else round(response_start - anchor_end, 6)

        record_reviews: list[str] = []
        for bind_status in (anchor_bind, response_bind, counter_bind):
            if bind_status.endswith("REVIEW_REQUIRED") or bind_status in {"NO_EPISODE_TIME_CONTAINMENT", "SEQUENCE_TIME_INVALID"}:
                record_reviews.append(bind_status)
        if counter is None:
            record_reviews.append("NO_VISIBLE_COUNTER_RESPONSE_CANDIDATE")

        records.append({
            "reciprocal_process_chain_candidate_id": "rpc_" + _digest(anchor_id, response_id, counter_id)[:24],
            "anchor_visible_action_sequence_candidate_id": anchor_id,
            "anchor_team_identity_candidate_id": anchor_team,
            "anchor_episode_candidate_id": anchor_episode_id,
            "anchor_episode_binding_status": anchor_bind,
            "anchor_action_family_counts": _family_counts(anchor),
            "anchor_consequence_candidate_counts": _consequence_counts(anchor),
            "response_visible_action_sequence_candidate_id": response_id,
            "response_team_identity_candidate_id": _clean(response.get("team_identity_candidate_id")),
            "response_episode_candidate_id": response_episode_id,
            "response_episode_binding_status": response_bind,
            "response_action_family_counts": _family_counts(response),
            "response_consequence_candidate_counts": _consequence_counts(response),
            "response_relation_candidate": "NEXT_DIFFERENT_TEAM_VISIBLE_SEQUENCE_AFTER_CONFIRMED",
            "response_latency_candidate_seconds": delta,
            "counter_response_visible_action_sequence_candidate_id": counter_id,
            "counter_response_team_identity_candidate_id": _clean(counter.get("team_identity_candidate_id")) if counter else None,
            "counter_response_episode_candidate_id": counter_episode_id,
            "counter_response_episode_binding_status": counter_bind,
            "counter_response_action_family_counts": _family_counts(counter or {}),
            "counter_response_consequence_candidate_counts": _consequence_counts(counter or {}),
            "counter_response_visible": counter is not None,
            "supporting_trackable_action_trace_candidate_ids": sorted(set(
                list(anchor.get("trackable_action_trace_candidate_ids") or [])
                + list(response.get("trackable_action_trace_candidate_ids") or [])
                + list((counter or {}).get("trackable_action_trace_candidate_ids") or [])
            )),
            "review_hits": sorted(set(record_reviews)),
            "allowed_claim": "Observed visible process candidate from one team was followed later in the same period by a visible process candidate from the opponent; a later return process by the anchor team is reported only when positive-time ordering is visible.",
            "forbidden_inference": ["causality", "possession_truth", "tactical_response_truth", "coach_intention", "adaptation_truth", "dominance"],
            "withdrawal_condition": "Withdraw if team identity, positive-time relation, period consistency, episode containment, or upstream sequence eligibility is invalidated.",
            "response_relation_is_causal_truth": False,
            "response_relation_is_tactical_truth": False,
            "counter_response_is_adaptation_truth": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
        records = []
    else:
        if unknown_episode_bindings:
            reviews.append("some_reciprocal_chains_not_uniquely_episode_bound")
        status = "REVIEW_REQUIRED" if reviews else "PASS"

    family_pair_counts = Counter()
    for row in records:
        anchor_family = "+".join(row.get("anchor_action_family_counts") or {}) or "UNKNOWN"
        response_family = "+".join(row.get("response_action_family_counts") or {}) or "UNKNOWN"
        family_pair_counts[f"{anchor_family} -> {response_family}"] += 1

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "RECIPROCAL_PROCESS_CHAINS_BUILT" if status != "FAIL_CLOSED" else "RECIPROCAL_PROCESS_INPUT_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "reciprocal_process_chain_candidates": records,
        "reciprocal_process_chain_candidate_count": len(records),
        "counter_response_visible_count": sum(bool(row.get("counter_response_visible")) for row in records),
        "episode_bound_chain_count": sum(bool(row.get("anchor_episode_candidate_id")) and bool(row.get("response_episode_candidate_id")) for row in records),
        "unknown_episode_binding_count": unknown_episode_bindings,
        "same_time_response_candidate_block_count": same_time_blocked,
        "response_family_pair_counts": dict(sorted(family_pair_counts.items())),
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "response_relation_is_causal_truth": False,
        "response_relation_is_tactical_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def _summary(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA RECIPROCAL PROCESS CHAIN LITE V1",
        f"status={payload.get('status')}",
        f"reciprocal_process_chain_candidate_count={payload.get('reciprocal_process_chain_candidate_count')}",
        f"counter_response_visible_count={payload.get('counter_response_visible_count')}",
        f"episode_bound_chain_count={payload.get('episode_bound_chain_count')}",
        f"same_time_response_candidate_block_count={payload.get('same_time_response_candidate_block_count')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ])


def _analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — RECIPROCAL VISIBLE PROCESS CANDIDATES",
        f"Candidate chains: {payload.get('reciprocal_process_chain_candidate_count', 0)}",
        f"Visible counter-responses: {payload.get('counter_response_visible_count', 0)}",
        "",
    ]
    for row in (payload.get("reciprocal_process_chain_candidates") or [])[:20]:
        lines.append(
            f"- {row.get('anchor_team_identity_candidate_id')} {row.get('anchor_action_family_counts')} -> "
            f"{row.get('response_team_identity_candidate_id')} {row.get('response_action_family_counts')} -> "
            f"counter={row.get('counter_response_action_family_counts') if row.get('counter_response_visible') else 'NOT_VISIBLE'} | "
            f"latency={row.get('response_latency_candidate_seconds')}s"
        )
    lines.extend([
        "",
        "Safe meaning: these chains describe positive-time, same-period visible team alternation between already reviewed sequence candidates.",
        "They are not possession, tactical response, adaptation or causal truth.",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    analyst_path = output / ANALYST_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_path.write_text(_summary(payload), encoding="utf-8")
    analyst_path.write_text(_analyst(payload), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
