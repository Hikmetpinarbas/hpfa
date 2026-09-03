from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUTPUT_JSON = "reciprocal_process_variant_profile_lite_v1.json"
OUTPUT_TXT = "reciprocal_process_variant_profile_lite_v1.txt"
ANALYST_TXT = "reciprocal_process_variant_profile_analyst_audit_v1.txt"
OWNED_OUTPUT_NAMES = (OUTPUT_JSON, OUTPUT_TXT, ANALYST_TXT)


def _validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def clear_outputs(out_dir: str | Path) -> list[Path]:
    """Remove only artifacts owned by this producer before a new invocation.

    This prevents a previous successful run from leaving apparently-current variant
    outputs behind when an upstream sequence/episode stage fails before this producer
    can write fresh artifacts.
    """
    output = _validate_out(out_dir)
    removed: list[Path] = []
    for name in OWNED_OUTPUT_NAMES:
        path = output / name
        if path.is_file():
            path.unlink()
            removed.append(path)
    return removed


def _summary(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA RECIPROCAL PROCESS VARIANT PROFILE LITE V1",
        f"module_id={payload.get('module_id')}",
        f"status={payload.get('process_variant_profile_status')}",
        f"upstream_reciprocal_status={payload.get('upstream_reciprocal_status')}",
        f"process_variant_profile_count={payload.get('process_variant_profile_count', 0)}",
        f"repeated_process_variant_profile_count={payload.get('repeated_process_variant_profile_count', 0)}",
        f"multi_episode_process_variant_profile_count={payload.get('multi_episode_process_variant_profile_count', 0)}",
        f"single_episode_repeat_risk_profile_count={payload.get('single_episode_repeat_risk_profile_count', 0)}",
        f"outcome_variation_profile_count={payload.get('outcome_variation_profile_count', 0)}",
        f"incomplete_episode_binding_profile_count={payload.get('incomplete_episode_binding_profile_count', 0)}",
        "recurrence_truth=false",
        "stable_team_tendency_truth=false",
        "tactical_truth=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ])


def _analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — MATCH-LOCAL VISIBLE PROCESS VARIANTS",
        f"Module: {payload.get('module_id')}",
        f"Status: {payload.get('process_variant_profile_status')}",
        f"Upstream reciprocal status: {payload.get('upstream_reciprocal_status')}",
        f"Visible process-family profiles: {payload.get('process_variant_profile_count', 0)}",
        f"Repeated profiles: {payload.get('repeated_process_variant_profile_count', 0)}",
        f"Repeated across multiple admitted episode scopes: {payload.get('multi_episode_process_variant_profile_count', 0)}",
        f"Repeated inside one admitted episode scope only: {payload.get('single_episode_repeat_risk_profile_count', 0)}",
        f"Profiles with multiple visible outcome signatures: {payload.get('outcome_variation_profile_count', 0)}",
        "",
    ]
    for row in (payload.get("process_variant_profiles") or [])[:20]:
        signature = row.get("process_family_signature_candidate") or {}
        lines.append(
            "- "
            + "+".join(signature.get("anchor_action_families") or ["UNKNOWN"])
            + " -> "
            + "+".join(signature.get("response_action_families") or ["UNKNOWN"])
            + f" | visible_repeat={row.get('visible_repeat_count_candidate')}"
            + f" | episode_scopes={row.get('unique_episode_scope_count_candidate')}"
            + f" | outcome_variants={row.get('distinct_visible_outcome_signature_count_candidate')}"
            + f" | state={row.get('repeat_scope_state_candidate')}"
        )
    lines.extend([
        "",
        "Safe meaning: this surface describes how often the same admitted match-local visible process-family signature appears, where it is episode-bound, and whether its visible outcomes vary.",
        "It does not establish recurrence truth, a stable team tendency, a rehearsed mechanism, tactical flexibility, expected outcome probability or coach intention.",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = _validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    analyst_path = output / ANALYST_TXT
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    txt_path.write_text(_summary(payload), encoding="utf-8")
    analyst_path.write_text(_analyst(payload), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}