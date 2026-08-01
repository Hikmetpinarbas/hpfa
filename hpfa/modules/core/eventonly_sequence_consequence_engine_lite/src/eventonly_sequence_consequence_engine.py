from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "eventonly_sequence_consequence_engine_lite_v1"
UPSTREAM_MODULE_ID = "selected_action_consequence_surface_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
OUTPUTS = {
    "json": "eventonly_sequence_consequence_result_v1.json",
    "summary": "eventonly_sequence_consequence_summary_v1.txt",
    "analyst": "eventonly_sequence_consequence_analyst_audit_v1.txt",
}
ELIGIBLE_FAMILIES = {"PASS", "CARRY", "TURNOVER", "RECOVERY", "CLEARANCE", "RESTART"}
SEQUENCE_FAMILIES = {"PASS", "CARRY", "TURNOVER", "RECOVERY", "CLEARANCE", "RESTART"}
ADVERSE_PRIMARY = {
    "OPPONENT_HANDOVER_CANDIDATE",
    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
}
AMBIGUOUS_PRIMARY = {
    "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE",
    "BREAKDOWN_WITH_UNCERTAIN_VISIBLE_RESPONSE_CANDIDATE",
}
PROGRESSION_METRICS = (
    "progression_to_final_third_support",
    "progression_to_box_entry_support",
    "progression_to_shot_support",
)


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


def _role_priority(family: str, source_role: str, actor_applicability: str) -> tuple[int, int]:
    if family == "RESTART":
        source_rank = 0 if source_role == "TEAM_SURFACE_CANDIDATE" else 1
    else:
        source_rank = 0 if source_role == "PLAYER_SURFACE_CANDIDATE" else 1
    actor_rank = 0 if actor_applicability == "APPLICABLE_BOUND_CANDIDATE" else 1
    return source_rank, actor_rank


def _is_survival(record: dict[str, Any]) -> bool:
    return record["retention"] == "SAME_TEAM_VISIBLE_RETENTION_CANDIDATE"


def _is_adverse(record: dict[str, Any]) -> bool:
    signals = set(record["signals"])
    return (
        record["retention"] == "OPPONENT_VISIBLE_HANDOVER_CANDIDATE"
        or record["primary"] in ADVERSE_PRIMARY
        or "OPPONENT_SHOT_FOLLOW_UP_VISIBLE" in signals
    )


def _is_ambiguous(record: dict[str, Any]) -> bool:
    return (
        record["primary"] in AMBIGUOUS_PRIMARY
        or record["retention"] == "MIXED_TEAM_SAME_TIME_REVIEW_REQUIRED_CANDIDATE"
        or any("REVIEW_REQUIRED" in signal for signal in record["signals"])
    )


def _is_restart_yield(record: dict[str, Any]) -> bool:
    signals = set(record["signals"])
    return _is_survival(record) or "SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE" in signals


def _metric_record(
    *,
    metric_id: str,
    team_id: str,
    family: str | None,
    records: list[dict[str, Any]],
    numerator_predicate,
    claim_ceiling: str,
) -> dict[str, Any]:
    denominator = len(records)
    numerator_records = [record for record in records if numerator_predicate(record)]
    ambiguous = [record for record in records if _is_ambiguous(record)]
    if denominator == 0:
        return {
            "metric_record_id": "escm_" + digest(metric_id, team_id, family, "blocked")[:24],
            "metric_id": metric_id,
            "team_identity_candidate_id": team_id,
            "anchor_action_family": family,
            "numerator": None,
            "denominator": 0,
            "value_candidate": None,
            "status": "BLOCKED_DENOMINATOR_MISSING",
            "claim_ceiling": claim_ceiling,
            "evidence_anchor_node_ids": [],
            "ambiguous_anchor_count": 0,
        }
    return {
        "metric_record_id": "escm_" + digest(metric_id, team_id, family, denominator)[:24],
        "metric_id": metric_id,
        "team_identity_candidate_id": team_id,
        "anchor_action_family": family,
        "numerator": len(numerator_records),
        "denominator": denominator,
        "value_candidate": round(len(numerator_records) / denominator, 6),
        "status": (
            "REVIEW_REQUIRED_CANDIDATE" if ambiguous else "PASS_CANDIDATE"
        ),
        "claim_ceiling": claim_ceiling,
        "evidence_anchor_node_ids": [
            record["anchor_node_id"] for record in numerator_records[:12]
        ],
        "ambiguous_anchor_count": len(ambiguous),
    }


def build_eventonly_sequence_consequence(
    upstream: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    quarantined: list[dict[str, Any]] = []

    if upstream.get("module_id") != UPSTREAM_MODULE_ID:
        blocks.append("upstream_module_id_mismatch")
    binding = clean(upstream.get("match_surface_binding_id"))
    if not binding:
        blocks.append("upstream_match_surface_binding_missing")
    if upstream.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("upstream_canonical_event_count_claimed")
    if upstream.get("production_release") is True:
        blocks.append("upstream_production_release_claimed")
    if upstream.get("hard_block_hits"):
        blocks.append("upstream_hard_blocks_present")
    upstream_status = clean(upstream.get("module_status") or upstream.get("status"))
    if upstream_status != "PASS":
        reviews.append(f"upstream_status_review:{upstream_status or 'UNKNOWN'}")

    nodes_raw = upstream.get("selected_action_nodes")
    candidates_raw = upstream.get("selected_action_consequence_candidates")
    if not isinstance(nodes_raw, list):
        blocks.append("selected_action_node_inventory_invalid")
        nodes_raw = []
    if not isinstance(candidates_raw, list):
        blocks.append("selected_action_consequence_inventory_invalid")
        candidates_raw = []
    if upstream.get("selected_action_node_count") != len(nodes_raw):
        blocks.append("selected_action_node_count_mismatch")
    if upstream.get("selected_action_consequence_candidate_count") != len(candidates_raw):
        blocks.append("selected_action_consequence_candidate_count_mismatch")

    node_by_id: dict[str, dict[str, Any]] = {}
    for raw in nodes_raw:
        if not isinstance(raw, dict):
            blocks.append("selected_action_node_record_invalid")
            continue
        node_id = clean(raw.get("selected_action_node_id"))
        if not node_id or node_id in node_by_id:
            blocks.append(f"selected_action_node_id_invalid_or_duplicate:{node_id or 'NONE'}")
            continue
        node_by_id[node_id] = raw

    candidate_ids: set[str] = set()
    exploded: list[dict[str, Any]] = []
    unknown_family_counts: Counter[str] = Counter()
    for raw in candidates_raw:
        if not isinstance(raw, dict):
            quarantined.append({"reason": "candidate_record_invalid"})
            continue
        candidate_id = clean(raw.get("selected_action_consequence_candidate_id"))
        anchor_id = clean(raw.get("anchor_selected_action_node_id"))
        if not candidate_id or candidate_id in candidate_ids:
            blocks.append(f"candidate_id_invalid_or_duplicate:{candidate_id or 'NONE'}")
            continue
        candidate_ids.add(candidate_id)
        node = node_by_id.get(anchor_id)
        if node is None:
            blocks.append(f"candidate_anchor_node_missing:{candidate_id}")
            continue
        period = clean(raw.get("period_candidate") or node.get("period_candidate"))
        start = number(raw.get("anchor_start_candidate") or node.get("start_candidate"))
        team_id = clean(raw.get("team_identity_candidate_id") or node.get("team_identity_candidate_id"))
        if not period or start is None or start < 0:
            quarantined.append(
                {"candidate_id": candidate_id, "reason": "missing_time_or_period"}
            )
            reviews.append("missing_time_blocks_ordered_consequence")
            continue
        if not team_id:
            quarantined.append(
                {"candidate_id": candidate_id, "reason": "missing_team_identity"}
            )
            reviews.append("missing_team_blocks_team_rate")
            continue
        if clean(raw.get("match_surface_binding_id")) != binding:
            blocks.append(f"candidate_binding_mismatch:{candidate_id}")
        if clean(node.get("match_surface_binding_id")) != binding:
            blocks.append(f"anchor_node_binding_mismatch:{anchor_id}")

        follow_ids = raw.get("visible_follow_up_node_ids")
        if not isinstance(follow_ids, list):
            follow_ids = []
            reviews.append("follow_up_inventory_invalid_downgraded")
        validated_follow_ids: list[str] = []
        for follow_id_raw in follow_ids:
            follow_id = clean(follow_id_raw)
            follow = node_by_id.get(follow_id)
            if follow is None:
                blocks.append(f"follow_up_node_missing:{candidate_id}:{follow_id or 'NONE'}")
                continue
            follow_period = clean(follow.get("period_candidate"))
            follow_start = number(follow.get("start_candidate"))
            if follow_period != period:
                blocks.append(f"follow_up_period_boundary_violation:{candidate_id}:{follow_id}")
                continue
            if follow_start is None or follow_start <= start:
                blocks.append(f"follow_up_order_violation:{candidate_id}:{follow_id}")
                continue
            validated_follow_ids.append(follow_id)

        families_raw = raw.get("anchor_action_family_candidates")
        if not isinstance(families_raw, list):
            families_raw = []
        families = sorted({clean(value).upper() for value in families_raw if clean(value)})
        for family in families:
            if family not in ELIGIBLE_FAMILIES:
                unknown_family_counts[family or "UNKNOWN"] += 1
                continue
            exploded.append(
                {
                    "candidate_id": candidate_id,
                    "anchor_node_id": anchor_id,
                    "family": family,
                    "team_id": team_id,
                    "actor_id": clean(raw.get("actor_identity_candidate_id")) or None,
                    "actor_applicability": clean(raw.get("actor_identity_applicability")),
                    "source_role": clean(raw.get("source_role") or node.get("source_role")),
                    "bundle_ids": sorted(
                        {
                            clean(value)
                            for value in (node.get("selected_action_bundle_candidate_ids") or [])
                            if clean(value)
                        }
                    ),
                    "period": period,
                    "start": start,
                    "primary": clean(raw.get("primary_consequence_candidate")),
                    "retention": clean(raw.get("retention_after_action_candidate")),
                    "signals": sorted(
                        {
                            clean(value)
                            for value in (raw.get("consequence_signal_candidates") or [])
                            if clean(value)
                        }
                    ),
                    "follow_up_node_ids": validated_follow_ids,
                    "first_visible_delta_seconds": number(
                        raw.get("first_visible_follow_up_delta_seconds")
                    ),
                }
            )

    for family, count in sorted(unknown_family_counts.items()):
        quarantined.append(
            {"reason": "anchor_family_not_admitted_v1", "family": family, "count": count}
        )

    grouped: dict[tuple[str, float, str, str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    for record in exploded:
        reflection_identity = (
            tuple(record["bundle_ids"])
            if record["bundle_ids"]
            else (record["anchor_node_id"],)
        )
        key = (
            record["period"],
            round(record["start"], 6),
            record["team_id"],
            record["family"],
            reflection_identity,
        )
        grouped[key].append(record)

    anchors: list[dict[str, Any]] = []
    suppressed_reflections: list[dict[str, Any]] = []
    for key, records in sorted(grouped.items()):
        ordered = sorted(
            records,
            key=lambda record: (
                *_role_priority(
                    record["family"],
                    record["source_role"],
                    record["actor_applicability"],
                ),
                record["anchor_node_id"],
            ),
        )
        anchors.append(ordered[0])
        for suppressed in ordered[1:]:
            suppressed_reflections.append(
                {
                    "period_candidate": key[0],
                    "start_candidate": key[1],
                    "team_identity_candidate_id": key[2],
                    "anchor_action_family": key[3],
                    "reflection_bundle_candidate_ids": list(key[4]),
                    "kept_anchor_node_id": ordered[0]["anchor_node_id"],
                    "suppressed_anchor_node_id": suppressed["anchor_node_id"],
                    "reason": "same_time_team_family_surface_reflection",
                }
            )

    team_ids = sorted({record["team_id"] for record in anchors})
    if len(team_ids) != 2:
        reviews.append(f"two_team_metric_surface_not_observed:{len(team_ids)}")

    records_by_team: dict[str, list[dict[str, Any]]] = {
        team_id: [record for record in anchors if record["team_id"] == team_id]
        for team_id in team_ids
    }
    metrics: list[dict[str, Any]] = []
    for team_id in team_ids:
        team_records = records_by_team[team_id]
        sequence_records = [
            record for record in team_records if record["family"] in SEQUENCE_FAMILIES
        ]
        metrics.append(
            _metric_record(
                metric_id="sequence_survival_rate",
                team_id=team_id,
                family=None,
                records=sequence_records,
                numerator_predicate=_is_survival,
                claim_ceiling="candidate_sequence_continuation",
            )
        )
        metrics.append(
            _metric_record(
                metric_id="adverse_consequence_rate",
                team_id=team_id,
                family=None,
                records=sequence_records,
                numerator_predicate=_is_adverse,
                claim_ceiling="candidate_consequence_signal",
            )
        )
        for family in sorted(SEQUENCE_FAMILIES):
            family_records = [
                record for record in sequence_records if record["family"] == family
            ]
            if not family_records:
                continue
            metrics.append(
                _metric_record(
                    metric_id="sequence_survival_rate",
                    team_id=team_id,
                    family=family,
                    records=family_records,
                    numerator_predicate=_is_survival,
                    claim_ceiling="candidate_sequence_continuation",
                )
            )
            metrics.append(
                _metric_record(
                    metric_id="adverse_consequence_rate",
                    team_id=team_id,
                    family=family,
                    records=family_records,
                    numerator_predicate=_is_adverse,
                    claim_ceiling="candidate_consequence_signal",
                )
            )
        recovery_records = [
            record for record in team_records if record["family"] == "RECOVERY"
        ]
        metrics.append(
            _metric_record(
                metric_id="regain_stabilization_rate",
                team_id=team_id,
                family="RECOVERY",
                records=recovery_records,
                numerator_predicate=_is_survival,
                claim_ceiling="candidate_stabilization_pattern",
            )
        )
        restart_records = [
            record for record in team_records if record["family"] == "RESTART"
        ]
        metrics.append(
            _metric_record(
                metric_id="restart_trace_yield",
                team_id=team_id,
                family="RESTART",
                records=restart_records,
                numerator_predicate=_is_restart_yield,
                claim_ceiling="candidate_restart_pattern",
            )
        )
        for metric_id in PROGRESSION_METRICS:
            metrics.append(
                {
                    "metric_record_id": "escm_"
                    + digest(metric_id, team_id, "blocked_progression_semantics")[:24],
                    "metric_id": metric_id,
                    "team_identity_candidate_id": team_id,
                    "anchor_action_family": "PROGRESSIVE_ACTION",
                    "numerator": None,
                    "denominator": None,
                    "value_candidate": None,
                    "status": "BLOCKED_SEMANTICS_UNAVAILABLE",
                    "claim_ceiling": "candidate_progression_support",
                    "evidence_anchor_node_ids": [],
                    "ambiguous_anchor_count": 0,
                    "block_reason": (
                        "validated progression anchor semantics and attack-direction/"
                        "coordinate-scale contract are unavailable"
                    ),
                }
            )

    metric_status_counts = Counter(record["status"] for record in metrics)
    family_counts = Counter(record["family"] for record in anchors)
    team_family_counts: dict[str, dict[str, int]] = {}
    for team_id in team_ids:
        team_family_counts[team_id] = dict(
            sorted(Counter(
                record["family"] for record in records_by_team[team_id]
            ).items())
        )

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or any(
        record["status"].startswith(("BLOCKED", "REVIEW_REQUIRED"))
        for record in metrics
    ):
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "match_surface_binding_id": binding,
        "source_module_id": upstream.get("module_id"),
        "source_module_status": upstream_status,
        "source_selected_action_node_count": len(nodes_raw),
        "source_consequence_candidate_count": len(candidates_raw),
        "eligible_anchor_count": len(anchors),
        "eligible_anchor_family_counts": dict(sorted(family_counts.items())),
        "team_eligible_anchor_family_counts": team_family_counts,
        "suppressed_duplicate_reflection_count": len(suppressed_reflections),
        "suppressed_duplicate_reflections": suppressed_reflections,
        "quarantined_record_count": len(quarantined),
        "quarantined_records": quarantined,
        "metric_record_count": len(metrics),
        "metric_status_counts": dict(sorted(metric_status_counts.items())),
        "metric_records": metrics,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "sequence_survival_is_sequence_truth": False,
        "adverse_consequence_is_causality_truth": False,
        "regain_stabilization_is_pressing_truth": False,
        "restart_trace_yield_is_set_piece_quality_truth": False,
        "progression_support_is_line_break_truth": False,
        "tracking_truth": False,
        "video_truth": False,
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "causality_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA EVENT-ONLY SEQUENCE CONSEQUENCE ENGINE LITE V1",
        f"status={payload.get('status')}",
        f"match_surface_binding_id={payload.get('match_surface_binding_id')}",
        f"source_consequence_candidate_count={payload.get('source_consequence_candidate_count')}",
        f"eligible_anchor_count={payload.get('eligible_anchor_count')}",
        f"suppressed_duplicate_reflection_count={payload.get('suppressed_duplicate_reflection_count')}",
        f"quarantined_record_count={payload.get('quarantined_record_count')}",
        f"metric_record_count={payload.get('metric_record_count')}",
        f"metric_status_counts={payload.get('metric_status_counts')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def _analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA EVENT-ONLY SEQUENCE CONSEQUENCE — ANALYST AUDIT V1",
        "",
        "Ne görüldü?",
        (
            "Visible action/consequence surfaces were normalized into denominator-gated "
            "continuation, adverse-consequence, regain-stabilization and restart-yield candidates."
        ),
        "",
        "Nerede görüldü?",
        f"match_surface_binding_id={payload.get('match_surface_binding_id')}",
        f"eligible_anchor_family_counts={payload.get('eligible_anchor_family_counts')}",
        "",
        "Hangi evidence destekliyor?",
    ]
    for record in payload.get("metric_records") or []:
        if record.get("status") == "BLOCKED_SEMANTICS_UNAVAILABLE":
            continue
        lines.append(
            " | ".join(
                [
                    f"team={record.get('team_identity_candidate_id')}",
                    f"metric={record.get('metric_id')}",
                    f"family={record.get('anchor_action_family') or 'ALL'}",
                    f"numerator={record.get('numerator')}",
                    f"denominator={record.get('denominator')}",
                    f"value_candidate={record.get('value_candidate')}",
                    f"status={record.get('status')}",
                ]
            )
        )
    lines.extend(
        [
            "",
            "Analist için güvenli anlamı nedir?",
            (
                "These values describe visible downstream continuation or adverse-response "
                "patterns after eligible event-label anchors. They do not prove possession, "
                "sequence truth, causality, tactical quality, dominance or player quality."
            ),
            "",
            "Blocked outputs:",
            (
                "Progression-to-final-third, progression-to-box and progression-to-shot "
                "metrics remain blocked until progression semantics and attack-direction/"
                "coordinate-scale contracts are validated."
            ),
            "",
            f"status={payload.get('status')}",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> Path:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    (output / OUTPUTS["json"]).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / OUTPUTS["summary"]).write_text(_summary(payload), encoding="utf-8")
    (output / OUTPUTS["analyst"]).write_text(_analyst(payload), encoding="utf-8")
    return output


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-action-consequence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        upstream = load_json(
            args.selected_action_consequence,
            "selected_action_consequence_input_invalid",
        )
        payload = build_eventonly_sequence_consequence(upstream)
        write_outputs(payload, args.out)
    except ValueError as exc:
        print(f"FAIL_CLOSED:{exc}")
        return 2
    print(_summary(payload), end="")
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
