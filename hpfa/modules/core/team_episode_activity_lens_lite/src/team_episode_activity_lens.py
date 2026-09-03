from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "team_episode_activity_lens_lite_v1"
CONTEXT_MODULE_ID = "minimum_viable_context_lite_v1"
EPISODE_MODULE_ID = "analyst_episode_locator_lite_v1"
IDENTITY_MODULE_ID = "match_local_identity_candidates_lite_v1"
CLAIM_CEILING = "TEAM_CONDITIONED_EPISODE_ACTIVITY_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "team_episode_activity_lens_lite_v1.json"
OUTPUT_TXT = "team_episode_activity_lens_lite_v1.txt"
ANALYST_TXT = "team_episode_activity_lens_analyst_audit_v1.txt"

ACTIVITY_SIGNAL_FIELDS = {
    "CIRCULATION_ACTIVITY_CANDIDATE": ("family", "PASS"),
    "CARRY_DRIBBLE_ACTIVITY_CANDIDATE": ("family", "CARRY_DRIBBLE"),
    "DUEL_PRESSURE_ACTIVITY_CANDIDATE": ("family", "DUEL_PRESSURE"),
    "ADVANCED_ACCESS_ACTIVITY_CANDIDATE": ("zone", "FINAL_THIRD"),
    "TERMINAL_ACTIVITY_CANDIDATE": ("family", "SHOT"),
    "RESTART_RESET_ACTIVITY_CANDIDATE": ("family", "DEAD_BALL"),
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _alias_key(value: Any) -> str:
    return _clean(value).casefold()


def _validate_input(payload: dict[str, Any], expected: str, label: str, blocks: list[str]) -> None:
    if payload.get("module_id") != expected:
        blocks.append(f"{label}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{label}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append(f"{label}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{label}_production_release_claimed")
    if _status(payload.get("status") or payload.get("module_status")) == "FAIL_CLOSED":
        blocks.append(f"{label}_input_fail_closed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{label}_input_hard_blocked")


def build_team_episode_activity_lens(
    context_payload: dict[str, Any],
    episode_payload: dict[str, Any],
    identity_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build descriptive team-conditioned activity signals inside admitted episode scopes.

    This lens uses only action-occurrence-eligible context refs already assigned to
    analyst episode candidates. Signals are multi-label descriptive candidates;
    they are not mutually exclusive football phases, possession states, tactical
    regimes, pressure geometry or causal transition truth.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    _validate_input(context_payload, CONTEXT_MODULE_ID, "context", blocks)
    _validate_input(episode_payload, EPISODE_MODULE_ID, "episode", blocks)
    _validate_input(identity_payload, IDENTITY_MODULE_ID, "identity", blocks)

    contexts = context_payload.get("context_candidates") or []
    episodes = episode_payload.get("episode_candidates") or []
    teams = identity_payload.get("team_identity_candidates") or []
    if not isinstance(contexts, list):
        blocks.append("context_collection_invalid")
        contexts = []
    if not isinstance(episodes, list):
        blocks.append("episode_collection_invalid")
        episodes = []
    if not isinstance(teams, list):
        blocks.append("team_identity_collection_invalid")
        teams = []

    context_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(contexts):
        if not isinstance(row, dict):
            blocks.append(f"context_record_invalid:{index}")
            continue
        context_id = _clean(row.get("context_id"))
        if not context_id or context_id in context_by_id:
            blocks.append(f"context_identity_invalid_or_duplicate:{index}")
            continue
        context_by_id[context_id] = row

    alias_to_team: dict[str, str] = {}
    team_name_by_id: dict[str, str] = {}
    for index, team in enumerate(teams):
        if not isinstance(team, dict):
            blocks.append(f"team_identity_record_invalid:{index}")
            continue
        team_id = _clean(team.get("team_identity_candidate_id"))
        if not team_id:
            blocks.append(f"team_identity_id_missing:{index}")
            continue
        team_name_by_id[team_id] = _clean(team.get("team_normalized_key")) or team_id
        aliases = list(team.get("team_aliases_raw") or [])
        normalized = _clean(team.get("team_normalized_key"))
        if normalized:
            aliases.extend([normalized, normalized.replace("_", " ")])
        for alias in aliases:
            key = _alias_key(alias)
            if key:
                alias_to_team[key] = team_id

    rows: list[dict[str, Any]] = []
    team_signal_episode_counts: dict[str, Counter[str]] = defaultdict(Counter)
    team_signal_volume_counts: dict[str, Counter[str]] = defaultdict(Counter)
    team_known_action_counts: Counter[str] = Counter()
    total_eligible = 0
    total_known_team = 0
    total_unknown_team = 0

    if not blocks:
        for episode in episodes:
            if not isinstance(episode, dict):
                continue
            episode_id = _clean(episode.get("episode_candidate_id"))
            eligible_refs = episode.get("action_occurrence_eligible_context_refs") or []
            if not episode_id or not isinstance(eligible_refs, list):
                reviews.append("episode_missing_identity_or_eligible_context_refs")
                continue
            total_eligible += len(eligible_refs)
            state: dict[str, dict[str, Any]] = defaultdict(
                lambda: {
                    "family": Counter(),
                    "zone": Counter(),
                    "channel": Counter(),
                    "context_ids": [],
                }
            )
            unknown_count = 0
            for context_id_raw in eligible_refs:
                context_id = _clean(context_id_raw)
                context = context_by_id.get(context_id)
                if context is None:
                    blocks.append(f"eligible_context_not_found:{episode_id}:{context_id}")
                    continue
                team_label = _alias_key(context.get("team_label"))
                team_id = alias_to_team.get(team_label)
                if not team_id:
                    unknown_count += 1
                    continue
                item = state[team_id]
                item["family"][_clean(context.get("action_family")) or "UNKNOWN_OR_OTHER"] += 1
                item["zone"][_clean(context.get("zone_candidate")) or "UNKNOWN_ZONE"] += 1
                item["channel"][_clean(context.get("channel_candidate")) or "UNKNOWN_CHANNEL"] += 1
                item["context_ids"].append(context_id)

            total_unknown_team += unknown_count
            for team_id, item in sorted(state.items()):
                known_count = len(item["context_ids"])
                total_known_team += known_count
                team_known_action_counts[team_id] += known_count
                signal_counts: dict[str, int] = {}
                signal_shares: dict[str, float] = {}
                present_signals: list[str] = []
                for signal, (source, key) in ACTIVITY_SIGNAL_FIELDS.items():
                    count = int(item[source].get(key, 0))
                    signal_counts[signal] = count
                    signal_shares[signal] = round(count / known_count, 6) if known_count else 0.0
                    if count > 0:
                        present_signals.append(signal)
                        team_signal_episode_counts[team_id][signal] += 1
                        team_signal_volume_counts[team_id][signal] += count

                rows.append({
                    "episode_candidate_id": episode_id,
                    "period_candidate": episode.get("period_candidate"),
                    "start_second_candidate": episode.get("start_second_candidate"),
                    "end_second_candidate": episode.get("end_second_candidate"),
                    "team_identity_candidate_id": team_id,
                    "team_normalized_key_candidate": team_name_by_id.get(team_id),
                    "known_team_eligible_action_candidate_count": known_count,
                    "episode_unknown_team_eligible_action_candidate_count": unknown_count,
                    "action_family_candidate_counts": dict(sorted(item["family"].items())),
                    "zone_candidate_counts": dict(sorted(item["zone"].items())),
                    "channel_candidate_counts": dict(sorted(item["channel"].items())),
                    "visible_activity_signal_counts": signal_counts,
                    "visible_activity_signal_shares_candidate": signal_shares,
                    "visible_activity_signals_present": present_signals,
                    "source_context_ids": sorted(item["context_ids"]),
                    "activity_signals_are_mutually_exclusive_phases": False,
                    "activity_signal_is_possession_truth": False,
                    "activity_signal_is_tactical_phase_truth": False,
                    "advanced_access_is_territorial_control_truth": False,
                    "duel_pressure_is_true_pressure_geometry": False,
                    "claim_ceiling": CLAIM_CEILING,
                })

    summaries = []
    for team_id in sorted(set(team_known_action_counts) | set(team_signal_episode_counts)):
        summaries.append({
            "team_identity_candidate_id": team_id,
            "team_normalized_key_candidate": team_name_by_id.get(team_id),
            "known_team_eligible_action_candidate_count": int(team_known_action_counts.get(team_id, 0)),
            "episode_count_with_known_team_action": sum(
                1 for row in rows if row["team_identity_candidate_id"] == team_id
            ),
            "activity_signal_episode_counts": dict(sorted(team_signal_episode_counts[team_id].items())),
            "activity_signal_volume_counts": dict(sorted(team_signal_volume_counts[team_id].items())),
        })

    for label, payload in (("context", context_payload), ("episode", episode_payload), ("identity", identity_payload)):
        if _status(payload.get("status") or payload.get("module_status")) == "REVIEW_REQUIRED":
            reviews.append(f"{label}_upstream_review_required")

    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "TEAM_EPISODE_ACTIVITY_LENS_BUILT" if not blocks else "TEAM_EPISODE_ACTIVITY_LENS_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "team_episode_activity_rows": rows if not blocks else [],
        "team_episode_activity_row_count": len(rows) if not blocks else 0,
        "team_activity_summaries": summaries if not blocks else [],
        "input_episode_candidate_count": len(episodes),
        "total_eligible_action_candidate_count": total_eligible if not blocks else 0,
        "known_team_eligible_action_candidate_count": total_known_team if not blocks else 0,
        "unknown_team_eligible_action_candidate_count": total_unknown_team if not blocks else 0,
        "known_team_attribution_coverage_candidate": (
            round(total_known_team / total_eligible, 6) if total_eligible and not blocks else None
        ),
        "activity_signals_are_multi_label_descriptive_candidates": True,
        "activity_signals_are_true_phases": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "pressure_geometry_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    analyst_path = output / ANALYST_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text("\n".join([
        "HPFA TEAM EPISODE ACTIVITY LENS LITE V1",
        f"status={payload.get('status')}",
        f"team_episode_activity_row_count={payload.get('team_episode_activity_row_count', 0)}",
        f"known_team_eligible_action_candidate_count={payload.get('known_team_eligible_action_candidate_count', 0)}",
        f"unknown_team_eligible_action_candidate_count={payload.get('unknown_team_eligible_action_candidate_count', 0)}",
        f"known_team_attribution_coverage_candidate={payload.get('known_team_attribution_coverage_candidate')}",
        "true_phase_truth=false",
        "possession_truth=false",
        "tactical_truth=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    lines = [
        "HPFA ANALYST AUDIT — TEAM-CONDITIONED EPISODE ACTIVITY",
        "These are visible multi-label activity signals inside admitted analyst episode scopes, not mutually exclusive tactical phases.",
    ]
    for row in payload.get("team_activity_summaries") or []:
        lines.append(
            f"- {row.get('team_normalized_key_candidate') or row.get('team_identity_candidate_id')}: "
            f"known_actions={row.get('known_team_eligible_action_candidate_count')} "
            f"episode_scopes={row.get('episode_count_with_known_team_action')} "
            f"signals={row.get('activity_signal_episode_counts')}"
        )
    lines.extend([
        "No signal establishes possession, tactical phase, dominance, team shape, pressure geometry or coach intention.",
        "",
    ])
    analyst_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
