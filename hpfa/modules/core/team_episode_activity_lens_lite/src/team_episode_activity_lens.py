from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "team_episode_activity_lens_lite_v1"
CONTEXT_MODULE_ID = "minimum_viable_context_lite_v1"
SEMANTIC_MODULE_ID = "context_action_semantics_rebind_lite_v1"
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
    "RESTART_RESET_ACTIVITY_CANDIDATE": ("family", "RESTART"),
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _alias_key(value: Any) -> str:
    return _clean(value).casefold()


def _validate(payload: dict[str, Any], expected: str, label: str, blocks: list[str]) -> None:
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


def _index(rows: Any, key: str, label: str, blocks: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        blocks.append(f"{label}_collection_invalid")
        return {}
    out: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"{label}_record_invalid:{idx}")
            continue
        value = _clean(row.get(key))
        if not value or value in out:
            blocks.append(f"{label}_identity_invalid_or_duplicate:{idx}")
            continue
        out[value] = row
    return out


def build_team_episode_activity_lens(
    context_payload: dict[str, Any],
    semantic_payload: dict[str, Any],
    episode_payload: dict[str, Any],
    identity_payload: dict[str, Any],
) -> dict[str, Any]:
    """Describe reviewed visible action activity by team inside admitted episode scopes.

    Eligible context membership comes from the episode layer, while football action
    family comes from reviewed provider semantics. This prevents preliminary
    minimum-context labels from overriding a reviewed action family. Signals remain
    multi-label descriptive candidates, never possession or tactical phase truth.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    for label, payload, expected in (
        ("context", context_payload, CONTEXT_MODULE_ID),
        ("semantic", semantic_payload, SEMANTIC_MODULE_ID),
        ("episode", episode_payload, EPISODE_MODULE_ID),
        ("identity", identity_payload, IDENTITY_MODULE_ID),
    ):
        _validate(payload, expected, label, blocks)

    contexts = _index(context_payload.get("context_candidates") or [], "context_id", "context", blocks)
    semantics = _index(
        semantic_payload.get("context_action_semantic_records") or [],
        "context_id",
        "semantic",
        blocks,
    )
    episodes = episode_payload.get("episode_candidates") or []
    teams = identity_payload.get("team_identity_candidates") or []
    if not isinstance(episodes, list):
        blocks.append("episode_collection_invalid")
        episodes = []
    if not isinstance(teams, list):
        blocks.append("team_identity_collection_invalid")
        teams = []

    alias_to_team: dict[str, str] = {}
    team_name_by_id: dict[str, str] = {}
    for idx, team in enumerate(teams):
        if not isinstance(team, dict):
            blocks.append(f"team_identity_record_invalid:{idx}")
            continue
        team_id = _clean(team.get("team_identity_candidate_id"))
        if not team_id:
            blocks.append(f"team_identity_id_missing:{idx}")
            continue
        normalized = _clean(team.get("team_normalized_key"))
        team_name_by_id[team_id] = normalized or team_id
        aliases = list(team.get("team_aliases_raw") or [])
        if normalized:
            aliases.extend([normalized, normalized.replace("_", " ")])
        for alias in aliases:
            key = _alias_key(alias)
            if key:
                alias_to_team[key] = team_id

    rows: list[dict[str, Any]] = []
    team_signal_episode_counts: dict[str, Counter[str]] = defaultdict(Counter)
    team_signal_volume_counts: dict[str, Counter[str]] = defaultdict(Counter)
    team_known_counts: Counter[str] = Counter()
    total_eligible = total_known = total_unknown_team = total_missing_semantics = 0

    if not blocks:
        for episode in episodes:
            if not isinstance(episode, dict):
                continue
            episode_id = _clean(episode.get("episode_candidate_id"))
            refs = episode.get("action_occurrence_eligible_context_refs") or []
            if not episode_id or not isinstance(refs, list):
                reviews.append("episode_missing_identity_or_eligible_context_refs")
                continue
            total_eligible += len(refs)
            state: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"family": Counter(), "zone": Counter(), "channel": Counter(), "context_ids": []}
            )
            episode_unknown = 0
            for raw_id in refs:
                context_id = _clean(raw_id)
                context = contexts.get(context_id)
                semantic = semantics.get(context_id)
                if context is None:
                    blocks.append(f"eligible_context_not_found:{episode_id}:{context_id}")
                    continue
                if semantic is None or semantic.get("action_occurrence_eligible") is not True:
                    total_missing_semantics += 1
                    reviews.append(f"eligible_context_reviewed_semantics_missing:{context_id}")
                    continue
                team_label = _alias_key(semantic.get("context_team_candidate") or context.get("team_label"))
                team_id = alias_to_team.get(team_label)
                if not team_id:
                    episode_unknown += 1
                    continue
                family = _clean(semantic.get("provider_action_family_candidate")) or "UNKNOWN_OR_OTHER"
                zone = _clean(semantic.get("context_zone_candidate") or context.get("zone_candidate")) or "UNKNOWN_ZONE"
                channel = _clean(semantic.get("context_channel_candidate") or context.get("channel_candidate")) or "UNKNOWN_CHANNEL"
                item = state[team_id]
                item["family"][family] += 1
                item["zone"][zone] += 1
                item["channel"][channel] += 1
                item["context_ids"].append(context_id)

            total_unknown_team += episode_unknown
            for team_id, item in sorted(state.items()):
                known = len(item["context_ids"])
                total_known += known
                team_known_counts[team_id] += known
                signal_counts: dict[str, int] = {}
                signal_shares: dict[str, float] = {}
                present: list[str] = []
                for signal, (source, key) in ACTIVITY_SIGNAL_FIELDS.items():
                    count = int(item[source].get(key, 0))
                    signal_counts[signal] = count
                    signal_shares[signal] = round(count / known, 6) if known else 0.0
                    if count:
                        present.append(signal)
                        team_signal_episode_counts[team_id][signal] += 1
                        team_signal_volume_counts[team_id][signal] += count
                rows.append({
                    "episode_candidate_id": episode_id,
                    "period_candidate": episode.get("period_candidate"),
                    "start_second_candidate": episode.get("start_second_candidate"),
                    "end_second_candidate": episode.get("end_second_candidate"),
                    "team_identity_candidate_id": team_id,
                    "team_normalized_key_candidate": team_name_by_id.get(team_id),
                    "known_team_eligible_action_candidate_count": known,
                    "episode_unknown_team_eligible_action_candidate_count": episode_unknown,
                    "action_family_candidate_counts": dict(sorted(item["family"].items())),
                    "zone_candidate_counts": dict(sorted(item["zone"].items())),
                    "channel_candidate_counts": dict(sorted(item["channel"].items())),
                    "visible_activity_signal_counts": signal_counts,
                    "visible_activity_signal_shares_candidate": signal_shares,
                    "visible_activity_signals_present": present,
                    "source_context_ids": sorted(item["context_ids"]),
                    "action_family_source": "REVIEWED_PROVIDER_SEMANTICS",
                    "activity_signals_are_mutually_exclusive_phases": False,
                    "activity_signal_is_possession_truth": False,
                    "activity_signal_is_tactical_phase_truth": False,
                    "advanced_access_is_territorial_control_truth": False,
                    "duel_pressure_is_true_pressure_geometry": False,
                    "claim_ceiling": CLAIM_CEILING,
                })

    summaries = [
        {
            "team_identity_candidate_id": team_id,
            "team_normalized_key_candidate": team_name_by_id.get(team_id),
            "known_team_eligible_action_candidate_count": int(team_known_counts.get(team_id, 0)),
            "episode_count_with_known_team_action": sum(row["team_identity_candidate_id"] == team_id for row in rows),
            "activity_signal_episode_counts": dict(sorted(team_signal_episode_counts[team_id].items())),
            "activity_signal_volume_counts": dict(sorted(team_signal_volume_counts[team_id].items())),
        }
        for team_id in sorted(set(team_known_counts) | set(team_signal_episode_counts))
    ]

    for label, payload in (
        ("context", context_payload),
        ("semantic", semantic_payload),
        ("episode", episode_payload),
        ("identity", identity_payload),
    ):
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
        "known_team_eligible_action_candidate_count": total_known if not blocks else 0,
        "unknown_team_eligible_action_candidate_count": total_unknown_team if not blocks else 0,
        "reviewed_semantics_missing_for_eligible_context_count": total_missing_semantics if not blocks else 0,
        "known_team_attribution_coverage_candidate": round(total_known / total_eligible, 6) if total_eligible and not blocks else None,
        "activity_signal_family_source": "REVIEWED_PROVIDER_SEMANTICS",
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
        "action_family_source=REVIEWED_PROVIDER_SEMANTICS",
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
        "Action-family counts use reviewed provider semantics; signals are visible multi-label activity candidates, not tactical phases.",
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
