from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUTPUT_JSON = "reciprocal_segment_scope_falsifier_lite_v1.json"
OUTPUT_TXT = "reciprocal_segment_scope_falsifier_lite_v1.txt"
ANALYST_TXT = "reciprocal_segment_scope_falsifier_analyst_audit_v1.txt"


def _summary(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA RECIPROCAL SEGMENT SCOPE FALSIFIER LITE V1",
        f"status={payload.get('segment_only_falsifier_status')}",
        f"evaluated_count={payload.get('segment_only_falsifier_evaluated_count', 0)}",
        f"segment_only_risk_candidate_count={payload.get('segment_only_risk_candidate_count', 0)}",
        f"multi_episode_not_observed_count={payload.get('segment_only_multi_episode_not_observed_count', 0)}",
        f"pending_count={payload.get('segment_only_pending_count', 0)}",
        f"safety_envelope_propagated={str(payload.get('segment_only_safety_envelope_propagated') is True).lower()}",
        "counter_search_complete_for_final_finding=false",
        "falsifier_coverage_state=PARTIAL",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ])


def _analyst(payload: dict[str, Any]) -> str:
    rows = payload.get("segment_only_evaluations") or []
    rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    risk_rows = [row for row in rows if row.get("segment_only_risk_candidate") is True]
    multi_rows = [
        row for row in rows
        if row.get("segment_only_evaluation_state") == "MULTI_EPISODE_SCOPE_VISIBLE_CANDIDATE"
    ]
    pending_rows = [
        row for row in rows
        if row.get("segment_only_falsifier_evaluable_from_current_episode_scope") is not True
    ]

    lines = [
        "HPFA ANALYST AUDIT — SEGMENT_ONLY EPISODE-SCOPE EVALUATION",
        f"Evaluable finding inputs: {len(rows) - len(pending_rows)}",
        f"Single-episode risk candidates: {len(risk_rows)}",
        f"Multi-episode visible spread candidates: {len(multi_rows)}",
        f"Pending / not evaluable: {len(pending_rows)}",
        "",
    ]
    if risk_rows:
        lines.append("SEGMENT_ONLY_RISK_CANDIDATES")
        for row in risk_rows[:20]:
            lines.append(
                f"- signature={row.get('process_family_signature_candidate')} "
                f"repeat={row.get('visible_repeat_count_candidate')} "
                f"episode_scopes={row.get('unique_episode_scope_count_candidate')}"
            )
        lines.append("")
    if pending_rows:
        lines.append("NOT_EVALUATED")
        for row in pending_rows[:20]:
            lines.append(
                f"- signature={row.get('process_family_signature_candidate')} "
                f"state={row.get('segment_only_evaluation_state')}"
            )
        lines.append("")
    lines.extend([
        "Safe meaning: episode-spread evidence can show whether a repeated same-signature visible process is confined to one admitted episode scope or is visible across multiple admitted episode scopes.",
        "This first slice does not remove SEGMENT_ONLY from the downstream pending falsifier list; C4 safety-envelope propagation remains a separate atomic change.",
        "Multi-episode spread is not recurrence truth, stable tendency, tactical plan or coach intention.",
        "",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    root = Path(out_dir).expanduser().resolve(strict=False)
    if "HPFA" in root.parts and root.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / OUTPUT_JSON
    txt_path = root / OUTPUT_TXT
    analyst_path = root / ANALYST_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(_summary(payload), encoding="utf-8")
    analyst_path.write_text(_analyst(payload), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
